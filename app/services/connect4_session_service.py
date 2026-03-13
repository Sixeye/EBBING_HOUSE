"""Connect Four session engine gated by quiz correctness."""

from __future__ import annotations

from datetime import datetime

from app.models.connect4_game import (
    Connect4AnswerEvaluation,
    Connect4ChallengeState,
    Connect4ChallengeSummary,
    Connect4MoveRequest,
)
from app.models.quiz_session import QuestionAttempt
from app.repositories.deck_repository import DeckRepository
from app.repositories.question_repository import QuestionRepository
from app.services.question_selection_service import QuestionSelectionService
from app.services.quiz_session_service import QuizSessionService


class Connect4SessionService:
    """Run a lightweight educational Connect Four challenge.

    Core product rule:
    - player selects a column
    - one quiz question gates that movement
    - correct answer => player disc is dropped
    - wrong answer => player disc is not dropped and opponent gets one extra turn
    """

    SESSION_SOURCE = "connect4"
    PLAYER_DISC = 1
    OPPONENT_DISC = 2

    def __init__(
        self,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
        question_selection_service: QuestionSelectionService | None = None,
    ) -> None:
        self._quiz_session_service = QuizSessionService(
            deck_repository=deck_repository,
            question_repository=question_repository,
            question_selection_service=question_selection_service,
        )
        self._state: Connect4ChallengeState | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start_challenge_from_deck(
        self,
        deck_id: int,
        question_limit: int | None = None,
        shuffle_questions: bool = True,
        profile_id: int | None = None,
    ) -> Connect4ChallengeState:
        quiz_state = self._quiz_session_service.start_session_from_deck(
            deck_id=deck_id,
            question_limit=question_limit,
            shuffle_questions=shuffle_questions,
            session_source=self.SESSION_SOURCE,
            profile_id=profile_id,
            prioritize_failed_first=True,
            record_progress_on_validate=False,
            progress_update_callback=None,
        )

        rows = 6
        cols = 7
        self._state = Connect4ChallengeState(
            deck_id=quiz_state.deck_id,
            deck_name=quiz_state.deck_name,
            total_questions_pool=quiz_state.total_questions,
            profile_id=profile_id,
            started_at=_utc_now_sql(),
            rows=rows,
            cols=cols,
            board=[[0 for _ in range(cols)] for _ in range(rows)],
            pending_column=None,
            current_turn="player",
            player_moves=0,
            opponent_moves=0,
            wrong_answers_count=0,
            finished=False,
            did_win=False,
            did_lose=False,
            did_draw=False,
        )
        return self._state

    def has_active_challenge(self) -> bool:
        return self._state is not None and self._quiz_session_service.has_active_session()

    def is_finished(self) -> bool:
        return self._require_state().finished

    def did_win(self) -> bool:
        return self._require_state().did_win

    def did_lose(self) -> bool:
        return self._require_state().did_lose

    def did_draw(self) -> bool:
        return self._require_state().did_draw

    def active_profile_id(self) -> int | None:
        return self._require_state().profile_id

    def active_deck_id(self) -> int:
        return self._require_state().deck_id

    def started_at(self) -> str | None:
        return self._require_state().started_at

    def board_snapshot(self) -> list[list[int]]:
        state = self._require_state()
        return [list(row) for row in state.board]

    def pending_column(self) -> int | None:
        return self._require_state().pending_column

    def current_question(self):
        state = self._require_state()
        if state.finished:
            return None
        return self._quiz_session_service.current_question()

    def current_question_progress(self) -> tuple[int, int]:
        return self._quiz_session_service.current_position()

    def current_question_is_validated(self) -> bool:
        return self._quiz_session_service.current_question_is_validated()

    def player_moves(self) -> int:
        return self._require_state().player_moves

    def opponent_moves(self) -> int:
        return self._require_state().opponent_moves

    def wrong_answers_count(self) -> int:
        return self._require_state().wrong_answers_count

    def current_turn(self) -> str:
        return self._require_state().current_turn

    def request_player_move(self, column: int) -> Connect4MoveRequest:
        state = self._require_state()
        if state.finished:
            raise ValueError("Challenge already finished.")
        if state.pending_column is not None and not self._quiz_session_service.current_question_is_validated():
            raise ValueError("Validate current answer before selecting another column.")
        if self._quiz_session_service.current_question_is_validated():
            raise ValueError("Question already validated. Continue with next question first.")
        if not state.is_player_turn:
            raise ValueError("It is not the player's turn.")
        if column < 0 or column >= state.cols:
            raise ValueError("Invalid column.")

        if self._next_open_row(state.board, column) is None:
            return Connect4MoveRequest(
                column=column,
                blocked=True,
                question=None,
                reason="column_full",
            )

        question = self._quiz_session_service.current_question()
        if question is None:
            raise ValueError("No question available for this turn.")

        state.pending_column = column
        return Connect4MoveRequest(
            column=column,
            blocked=False,
            question=question,
            reason=None,
        )

    def validate_current_answer(self, selected_answers: list[str]) -> Connect4AnswerEvaluation:
        """Validate answer and execute board consequences for this turn."""
        state = self._require_state()
        if state.finished:
            raise ValueError("Challenge already finished.")
        if state.pending_column is None:
            raise ValueError("Select a column before validating the answer.")

        evaluation = self._quiz_session_service.validate_current_answer(selected_answers)
        opponent_moves = 0
        player_disc_dropped = False

        if evaluation.is_correct:
            drop_row = self._drop_disc(state.board, state.pending_column, self.PLAYER_DISC)
            if drop_row is not None:
                player_disc_dropped = True
                state.player_moves += 1
                if self._has_connect4(state.board, drop_row, state.pending_column, self.PLAYER_DISC):
                    state.finished = True
                    state.did_win = True
            if not state.finished and self._is_board_full(state.board):
                state.finished = True
                state.did_draw = True

            # Normal pacing: opponent responds with one move after player action.
            if not state.finished:
                opponent_moves = self._run_opponent_turns(state, turns=1)
        else:
            # Wrong answer: player loses turn and opponent gains one extra move.
            state.wrong_answers_count += 1
            opponent_moves = self._run_opponent_turns(state, turns=2)

        state.pending_column = None
        state.current_turn = "none" if state.finished else "player"

        if not state.finished:
            moved = self._quiz_session_service.go_to_next_question()
            if not moved:
                # Out of questions ends the challenge gracefully.
                state.finished = True
                if not state.did_win and not state.did_draw:
                    state.did_lose = True
                state.current_turn = "none"

        return Connect4AnswerEvaluation(
            selected_answers=evaluation.selected_answers,
            correct_answers=evaluation.correct_answers,
            explanation=evaluation.explanation,
            response_time_seconds=evaluation.response_time_seconds,
            was_correct=evaluation.is_correct,
            player_disc_dropped=player_disc_dropped,
            opponent_discs_dropped=opponent_moves,
            player_won=state.did_win,
            opponent_won=state.did_lose,
            draw=state.did_draw,
            consumed_question=True,
        )

    def build_summary(self) -> Connect4ChallengeSummary:
        state = self._require_state()
        if not state.finished:
            raise ValueError("Cannot build summary before challenge ends.")

        attempts = self._quiz_session_service.attempts_snapshot()
        answered = len(attempts)
        correct = len([attempt for attempt in attempts if attempt.is_correct])
        wrong = max(0, answered - correct)

        percentage = (correct / answered * 100.0) if answered else 0.0
        score_100 = percentage
        score_20 = percentage / 5.0

        avg_time = self._average_response_time(attempts)

        return Connect4ChallengeSummary(
            deck_name=state.deck_name,
            total_questions_pool=state.total_questions_pool,
            answered_questions=answered,
            correct_answers_count=correct,
            wrong_answers_count=wrong,
            score_on_20=round(score_20, 2),
            score_on_100=round(score_100, 2),
            percentage=round(percentage, 2),
            average_response_time_seconds=avg_time,
            player_moves=state.player_moves,
            opponent_moves=state.opponent_moves,
            did_win=state.did_win,
            did_lose=state.did_lose,
            did_draw=state.did_draw,
        )

    def reset(self) -> None:
        self._quiz_session_service.reset()
        self._state = None

    # ------------------------------------------------------------------
    # Internal board helpers
    # ------------------------------------------------------------------
    def _run_opponent_turns(self, state: Connect4ChallengeState, turns: int) -> int:
        """Execute one or two opponent turns depending on answer correctness."""
        done = 0
        for _ in range(max(0, turns)):
            column = self._choose_opponent_column(state.board)
            if column is None:
                state.finished = True
                state.did_draw = True
                break

            row = self._drop_disc(state.board, column, self.OPPONENT_DISC)
            if row is None:
                # Defensive fallback; should not happen if column is valid.
                continue

            done += 1
            state.opponent_moves += 1

            if self._has_connect4(state.board, row, column, self.OPPONENT_DISC):
                state.finished = True
                state.did_lose = True
                break
            if self._is_board_full(state.board):
                state.finished = True
                state.did_draw = True
                break
        return done

    def _choose_opponent_column(self, board: list[list[int]]) -> int | None:
        valid_columns = [col for col in range(len(board[0])) if self._next_open_row(board, col) is not None]
        if not valid_columns:
            return None

        # 1) Win immediately if possible.
        for col in valid_columns:
            if self._would_win(board, col, self.OPPONENT_DISC):
                return col

        # 2) Block immediate player win.
        for col in valid_columns:
            if self._would_win(board, col, self.PLAYER_DISC):
                return col

        # 3) Prefer center columns for stronger average positions.
        center = len(board[0]) // 2
        ordered = sorted(valid_columns, key=lambda col: (abs(col - center), col))
        return ordered[0] if ordered else None

    def _would_win(self, board: list[list[int]], column: int, disc: int) -> bool:
        snapshot = [list(row) for row in board]
        row = self._drop_disc(snapshot, column, disc)
        if row is None:
            return False
        return self._has_connect4(snapshot, row, column, disc)

    @staticmethod
    def _drop_disc(board: list[list[int]], column: int, disc: int) -> int | None:
        for row in range(len(board) - 1, -1, -1):
            if board[row][column] == 0:
                board[row][column] = disc
                return row
        return None

    @staticmethod
    def _next_open_row(board: list[list[int]], column: int) -> int | None:
        for row in range(len(board) - 1, -1, -1):
            if board[row][column] == 0:
                return row
        return None

    @staticmethod
    def _is_board_full(board: list[list[int]]) -> bool:
        return all(cell != 0 for cell in board[0])

    def _has_connect4(self, board: list[list[int]], row: int, col: int, disc: int) -> bool:
        # Check around last move in four axes.
        directions = ((0, 1), (1, 0), (1, 1), (1, -1))
        for dr, dc in directions:
            count = 1
            count += self._count_direction(board, row, col, dr, dc, disc)
            count += self._count_direction(board, row, col, -dr, -dc, disc)
            if count >= 4:
                return True
        return False

    @staticmethod
    def _count_direction(
        board: list[list[int]],
        row: int,
        col: int,
        dr: int,
        dc: int,
        disc: int,
    ) -> int:
        total = 0
        r = row + dr
        c = col + dc
        rows = len(board)
        cols = len(board[0]) if rows else 0
        while 0 <= r < rows and 0 <= c < cols and board[r][c] == disc:
            total += 1
            r += dr
            c += dc
        return total

    @staticmethod
    def _average_response_time(attempts: list[QuestionAttempt]) -> float | None:
        if not attempts:
            return None
        return round(sum(item.response_time_seconds for item in attempts) / len(attempts), 2)

    def _require_state(self) -> Connect4ChallengeState:
        if self._state is None or not self._quiz_session_service.has_active_session():
            raise ValueError("No active Connect Four challenge. Start one first.")
        return self._state


__all__ = ["Connect4SessionService"]


def _utc_now_sql() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
