"""Hangman challenge service built on top of QuizSessionService."""

from __future__ import annotations

from datetime import datetime

from app.models.hangman_game import HangmanGameState, HangmanGameSummary
from app.models.quiz_session import QuestionEvaluation
from app.repositories.deck_repository import DeckRepository
from app.repositories.question_repository import QuestionRepository
from app.services.quiz_session_service import QuizSessionService
from app.services.question_selection_service import QuestionSelectionService


class HangmanSessionService:
    """Orchestrate a hangman mini-game without duplicating quiz logic.

    Design choice:
    - QuizSessionService remains source of truth for question sequencing and
      exact-match answer validation.
    - This class adds only hangman-specific danger progression.
    """

    SESSION_SOURCE = "hangman"

    def __init__(
        self,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
        question_selection_service: QuestionSelectionService | None = None,
        default_max_wrong_answers: int = 6,
    ) -> None:
        self._quiz_session_service = QuizSessionService(
            deck_repository=deck_repository,
            question_repository=question_repository,
            question_selection_service=question_selection_service,
        )
        self._default_max_wrong_answers = max(1, default_max_wrong_answers)
        self._state: HangmanGameState | None = None

    def start_challenge_from_deck(
        self,
        deck_id: int,
        question_limit: int | None = None,
        shuffle_questions: bool = False,
        profile_id: int | None = None,
        max_wrong_answers: int | None = None,
    ) -> HangmanGameState:
        """Start a hangman challenge from one deck.

        We reuse quiz session start so question loading/validation rules stay
        centralized and consistent across review + hangman modes.
        """
        max_wrong = max_wrong_answers or self._default_max_wrong_answers
        if max_wrong <= 0:
            raise ValueError("max_wrong_answers must be greater than zero.")

        session = self._quiz_session_service.start_session_from_deck(
            deck_id=deck_id,
            question_limit=question_limit,
            shuffle_questions=shuffle_questions,
            session_source=self.SESSION_SOURCE,
            profile_id=profile_id,
            prioritize_failed_first=True,
            record_progress_on_validate=False,
            progress_update_callback=None,
        )

        self._state = HangmanGameState(
            deck_id=session.deck_id,
            deck_name=session.deck_name,
            max_wrong_answers=max_wrong,
            total_questions_pool=session.total_questions,
            profile_id=profile_id,
            started_at=_utc_now_sql(),
            danger_steps=0,
            finished=False,
            did_fail=False,
            did_save=False,
        )
        return self._state

    def has_active_challenge(self) -> bool:
        return self._state is not None and self._quiz_session_service.has_active_session()

    def is_finished(self) -> bool:
        state = self._require_state()
        return state.finished

    def did_fail(self) -> bool:
        return self._require_state().did_fail

    def did_save(self) -> bool:
        return self._require_state().did_save

    def wrong_answers_used(self) -> int:
        return self._require_state().wrong_answers_used

    def wrong_answers_remaining(self) -> int:
        return self._require_state().wrong_answers_remaining

    def max_wrong_answers(self) -> int:
        return self._require_state().max_wrong_answers

    def current_question(self):
        state = self._require_state()
        if state.finished:
            return None
        return self._quiz_session_service.current_question()

    def current_position(self) -> tuple[int, int]:
        return self._quiz_session_service.current_position()

    def answered_count(self) -> int:
        return self._quiz_session_service.answered_count()

    def current_question_is_validated(self) -> bool:
        state = self._require_state()
        if state.finished:
            return True
        return self._quiz_session_service.current_question_is_validated()

    def validate_current_answer(self, selected_answers: list[str]) -> QuestionEvaluation:
        """Validate answer and update hangman danger progression.

        Current model:
        - wrong answer => danger increases by one step
        - correct answer => danger decreases by one step (min 0)
        - reaching max wrong answers => immediate failure
        """
        state = self._require_state()
        if state.finished:
            raise ValueError("Hangman challenge is already finished.")

        evaluation = self._quiz_session_service.validate_current_answer(selected_answers)
        if evaluation.is_correct:
            state.danger_steps = max(0, state.danger_steps - 1)
        else:
            state.danger_steps += 1
            if state.danger_steps >= state.max_wrong_answers:
                state.finished = True
                state.did_fail = True
                state.did_save = False

        return evaluation

    def go_to_next_question(self) -> bool:
        """Advance to next question when possible.

        Returns True if moved to another question.
        Returns False when challenge reached a terminal state.
        """
        state = self._require_state()
        if state.finished:
            return False

        moved = self._quiz_session_service.go_to_next_question()
        if not moved:
            state.finished = True
            state.did_fail = False
            state.did_save = True
            return False

        return True

    def build_summary(self) -> HangmanGameSummary:
        """Build final challenge summary from quiz attempts + hangman state."""
        state = self._require_state()
        if not state.finished:
            raise ValueError("Cannot build summary before challenge is finished.")

        # Quiz summary gives reliable timing/correct counters from actual
        # validated attempts. We then compute hangman-specific stats on top.
        base_summary = self._quiz_session_service.build_summary()
        answered = self._quiz_session_service.answered_count()
        correct = base_summary.correct_answers_count
        wrong = max(0, answered - correct)

        percentage = (correct / answered * 100.0) if answered else 0.0
        score_100 = percentage
        score_20 = percentage / 5.0

        return HangmanGameSummary(
            deck_name=state.deck_name,
            total_questions_pool=state.total_questions_pool,
            answered_questions=answered,
            correct_answers_count=correct,
            wrong_answers_count=wrong,
            score_on_20=round(score_20, 2),
            score_on_100=round(score_100, 2),
            percentage=round(percentage, 2),
            average_response_time_seconds=base_summary.average_response_time_seconds,
            wrong_answers_used=state.danger_steps,
            wrong_answers_remaining=state.wrong_answers_remaining,
            did_save=state.did_save,
            did_fail=state.did_fail,
        )

    def active_profile_id(self) -> int | None:
        state = self._require_state()
        return state.profile_id

    def active_deck_id(self) -> int:
        return self._require_state().deck_id

    def started_at(self) -> str | None:
        return self._require_state().started_at

    def reset(self) -> None:
        self._quiz_session_service.reset()
        self._state = None

    def _require_state(self) -> HangmanGameState:
        if self._state is None or not self._quiz_session_service.has_active_session():
            raise ValueError("No active hangman challenge. Start one first.")
        return self._state


__all__ = ["HangmanSessionService"]


def _utc_now_sql() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
