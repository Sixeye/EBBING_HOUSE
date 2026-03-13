"""Maze Challenge session orchestration.

Educational loop remains the core mechanic:
- click a direction
- if target is a wall => blocked immediately, no question consumed
- if target is traversable => present one quiz question
- correct answer executes move, wrong answer denies move

This service now also runs a lightweight guardian patrol used by the Maze page.
"""

from __future__ import annotations

import random
import time
from collections import deque
from datetime import datetime

from app.models.maze_difficulty import (
    DEFAULT_MAZE_DIFFICULTY,
    MAZE_DIFFICULTY_PRESETS,
    MazeDifficultyPreset,
    get_maze_difficulty_preset,
)
from app.models.maze_game import (
    MazeChallengeState,
    MazeChallengeSummary,
    MazeDirection,
    MazeGuardianTick,
    MazeLayout,
    MazeMoveEvaluation,
    MazeMoveRequest,
)
from app.repositories.deck_repository import DeckRepository
from app.repositories.question_repository import QuestionRepository
from app.services.maze_generation_service import MazeGenerationService
from app.services.question_selection_service import QuestionSelectionService
from app.services.quiz_session_service import QuizSessionService


class MazeSessionService:
    """Coordinate generated maze state with reusable quiz validation logic."""

    SESSION_SOURCE = "maze"

    _DIRECTION_DELTAS: dict[MazeDirection, tuple[int, int]] = {
        "forward": (-1, 0),
        "backward": (1, 0),
        "left": (0, -1),
        "right": (0, 1),
    }

    def __init__(
        self,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
        question_selection_service: QuestionSelectionService | None = None,
        maze_generation_service: MazeGenerationService | None = None,
    ) -> None:
        self._quiz_session_service = QuizSessionService(
            deck_repository=deck_repository,
            question_repository=question_repository,
            question_selection_service=question_selection_service,
        )
        # One generator per difficulty keeps dimensions explicit and avoids
        # mutable width/height state on a shared generator instance.
        self._maze_generation_services: dict[str, MazeGenerationService] = {
            "easy": MazeGenerationService(
                width=MAZE_DIFFICULTY_PRESETS["easy"].maze_width,
                height=MAZE_DIFFICULTY_PRESETS["easy"].maze_height,
            ),
            "normal": maze_generation_service
            or MazeGenerationService(
                width=MAZE_DIFFICULTY_PRESETS["normal"].maze_width,
                height=MAZE_DIFFICULTY_PRESETS["normal"].maze_height,
            ),
            "hard": MazeGenerationService(
                width=MAZE_DIFFICULTY_PRESETS["hard"].maze_width,
                height=MAZE_DIFFICULTY_PRESETS["hard"].maze_height,
            ),
        }
        self._state: MazeChallengeState | None = None
        self._last_layout_rows_by_difficulty: dict[str, tuple[str, ...]] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def start_challenge_from_deck(
        self,
        deck_id: int,
        question_limit: int | None = None,
        shuffle_questions: bool = True,
        profile_id: int | None = None,
        difficulty_code: str = DEFAULT_MAZE_DIFFICULTY,
        guardian_restart_count: int = 0,
    ) -> MazeChallengeState:
        """Start a new challenge with a fresh solvable maze.

        `guardian_restart_count` is used internally when the guardian catches
        the player and we restart the challenge in-place.
        """
        difficulty = self._resolve_difficulty(difficulty_code)
        generator = self._maze_generation_services[difficulty.code]
        layout = generator.generate_layout()

        # We retry generation when consecutive layouts are identical so each
        # new session feels fresh.
        last_layout_rows = self._last_layout_rows_by_difficulty.get(difficulty.code)
        for attempt in range(32):
            if last_layout_rows is None or layout.rows != last_layout_rows:
                break
            seed = (time.time_ns() ^ (attempt * 2654435761)) & 0xFFFFFFFF
            layout = generator.generate_layout(seed=seed)
        self._last_layout_rows_by_difficulty[difficulty.code] = layout.rows

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

        guardian_origin, guardian_patrol_path, guardian_patrol_radius = self._build_guardian_patrol(
            layout=layout,
            desired_radius=difficulty.guardian_patrol_radius,
        )

        self._state = MazeChallengeState(
            deck_id=quiz_state.deck_id,
            deck_name=quiz_state.deck_name,
            layout=layout,
            total_questions_pool=quiz_state.total_questions,
            question_limit=question_limit,
            shuffle_questions=shuffle_questions,
            difficulty_code=difficulty.code,
            profile_id=profile_id,
            started_at=_utc_now_sql(),
            current_position=layout.start_pos,
            guardian_origin=guardian_origin,
            guardian_position=guardian_origin,
            guardian_patrol_path=guardian_patrol_path,
            guardian_patrol_index=0,
            guardian_patrol_forward=True,
            guardian_patrol_radius=guardian_patrol_radius,
            guardian_tick_ms=difficulty.guardian_tick_ms,
            guardian_restart_count=max(0, guardian_restart_count),
        )
        return self._state

    def has_active_challenge(self) -> bool:
        return self._state is not None and self._quiz_session_service.has_active_session()

    def is_finished(self) -> bool:
        return self._require_state().finished

    def did_win(self) -> bool:
        return self._require_state().did_win

    def active_profile_id(self) -> int | None:
        return self._require_state().profile_id

    def active_deck_id(self) -> int:
        return self._require_state().deck_id

    def started_at(self) -> str | None:
        return self._require_state().started_at

    def active_difficulty_code(self) -> str:
        return self._require_state().difficulty_code

    def active_difficulty(self) -> MazeDifficultyPreset:
        return self._resolve_difficulty(self._require_state().difficulty_code)

    def reset(self) -> None:
        self._quiz_session_service.reset()
        self._state = None

    # ------------------------------------------------------------------
    # Maze view-state helpers
    # ------------------------------------------------------------------
    def layout_rows(self) -> tuple[str, ...]:
        return self._require_state().layout.rows

    def start_position(self) -> tuple[int, int]:
        return self._require_state().layout.start_pos

    def exit_position(self) -> tuple[int, int]:
        return self._require_state().layout.exit_pos

    def current_position(self) -> tuple[int, int]:
        return self._require_state().current_position

    def guardian_position(self) -> tuple[int, int]:
        return self._require_state().guardian_position

    def guardian_origin(self) -> tuple[int, int]:
        return self._require_state().guardian_origin

    def guardian_patrol_radius(self) -> int:
        return self._require_state().guardian_patrol_radius

    def guardian_tick_interval_ms(self) -> int:
        return self._require_state().guardian_tick_ms

    def guardian_restart_count(self) -> int:
        return self._require_state().guardian_restart_count

    def pending_direction(self) -> MazeDirection | None:
        return self._require_state().pending_direction

    def shortest_path_length(self) -> int:
        return self._require_state().layout.shortest_path_length

    def remaining_shortest_distance(self) -> int:
        state = self._require_state()
        generator = self._maze_generation_services.get(
            state.difficulty_code,
            self._maze_generation_services[DEFAULT_MAZE_DIFFICULTY],
        )
        remaining = generator.shortest_distance(
            layout=state.layout,
            start=state.current_position,
            end=state.layout.exit_pos,
        )
        # Defensive fallback: in a valid maze this should never be negative.
        if remaining < 0:
            return state.layout.shortest_path_length
        return remaining

    def minimum_distance_to_exit(self) -> int:
        """Alias used by the UI to communicate clear progression wording."""
        return self.remaining_shortest_distance()

    def progress_percentage(self) -> float:
        """Progress based on real shortest-path geometry.

        Progress = (shortest_path - remaining_distance) / shortest_path.
        """
        shortest = max(1, self.shortest_path_length())
        remaining = max(0, self.minimum_distance_to_exit())
        progress = ((shortest - remaining) / shortest) * 100.0
        return max(0.0, min(100.0, round(progress, 1)))

    def reachable_positions(self) -> set[tuple[int, int]]:
        state = self._require_state()
        positions: set[tuple[int, int]] = set()
        for direction in self._DIRECTION_DELTAS:
            target = self._target_position(state.current_position, direction)
            if self._is_walkable(state.layout, target):
                positions.add(target)
        return positions

    def reachable_directions(self) -> set[MazeDirection]:
        state = self._require_state()
        directions: set[MazeDirection] = set()
        for direction in self._DIRECTION_DELTAS:
            target = self._target_position(state.current_position, direction)
            if self._is_walkable(state.layout, target):
                directions.add(direction)
        return directions

    def mistakes_count(self) -> int:
        return self._require_state().mistakes_count

    def successful_moves(self) -> int:
        return self._require_state().successful_moves

    def wall_hits_count(self) -> int:
        return self._require_state().wall_hits_count

    def current_question_progress(self) -> tuple[int, int]:
        return self._quiz_session_service.current_position()

    def current_question_is_validated(self) -> bool:
        return self._quiz_session_service.current_question_is_validated()

    # ------------------------------------------------------------------
    # Guardian patrol
    # ------------------------------------------------------------------
    def tick_guardian(self) -> MazeGuardianTick:
        """Advance guardian by one patrol step.

        The page drives this method via a timer. Keeping patrol in the service
        makes contact/restart logic testable outside the UI.
        """
        state = self._require_state()

        if state.finished:
            return MazeGuardianTick(
                moved=False,
                caught_player=False,
                challenge_restarted=False,
                guardian_position=state.guardian_position,
                player_position=state.current_position,
                restart_count=state.guardian_restart_count,
            )

        if state.guardian_position == state.current_position:
            restarted_state = self._restart_after_guardian_contact(state)
            return MazeGuardianTick(
                moved=False,
                caught_player=True,
                challenge_restarted=True,
                guardian_position=restarted_state.guardian_position,
                player_position=restarted_state.current_position,
                restart_count=restarted_state.guardian_restart_count,
            )

        moved, new_position = self._advance_guardian_position(state)
        state.guardian_position = new_position

        if state.guardian_position == state.current_position:
            restarted_state = self._restart_after_guardian_contact(state)
            return MazeGuardianTick(
                moved=moved,
                caught_player=True,
                challenge_restarted=True,
                guardian_position=restarted_state.guardian_position,
                player_position=restarted_state.current_position,
                restart_count=restarted_state.guardian_restart_count,
            )

        return MazeGuardianTick(
            moved=moved,
            caught_player=False,
            challenge_restarted=False,
            guardian_position=state.guardian_position,
            player_position=state.current_position,
            restart_count=state.guardian_restart_count,
        )

    # ------------------------------------------------------------------
    # Direction + quiz flow
    # ------------------------------------------------------------------
    def request_move(self, direction: MazeDirection) -> MazeMoveRequest:
        """Handle direction click according to traversable-first rule.

        If target is blocked, we return immediately with `blocked_by_wall=True`
        and do not consume a question.
        """
        state = self._require_state()
        if state.finished:
            raise ValueError("Maze challenge is already finished.")

        if direction not in self._DIRECTION_DELTAS:
            raise ValueError("Unsupported movement direction.")

        if state.pending_direction is not None and not self._quiz_session_service.current_question_is_validated():
            raise ValueError("Validate the current movement question first.")

        if self._quiz_session_service.current_question_is_validated():
            raise ValueError("Click Next to continue before choosing another direction.")

        target = self._target_position(state.current_position, direction)
        if not self._is_walkable(state.layout, target):
            state.wall_hits_count += 1
            state.pending_direction = None
            state.pending_target_position = None
            return MazeMoveRequest(
                direction=direction,
                blocked_by_wall=True,
                question=None,
                target_position=None,
            )

        state.pending_direction = direction
        state.pending_target_position = target
        question = self._quiz_session_service.current_question()
        if question is None:
            raise ValueError("No question available for this move.")

        return MazeMoveRequest(
            direction=direction,
            blocked_by_wall=False,
            question=question,
            target_position=target,
        )

    def validate_current_answer(self, selected_answers: list[str]) -> MazeMoveEvaluation:
        """Validate answer for a traversable move attempt."""
        state = self._require_state()
        if state.finished:
            raise ValueError("Maze challenge is already finished.")
        if state.pending_direction is None or state.pending_target_position is None:
            raise ValueError("Choose a traversable direction before validating an answer.")

        attempted_direction = state.pending_direction
        target_position = state.pending_target_position
        evaluation = self._quiz_session_service.validate_current_answer(selected_answers)

        moved = False
        reached_exit = False

        if evaluation.is_correct:
            state.current_position = target_position
            state.successful_moves += 1
            moved = True
            reached_exit = state.current_position == state.layout.exit_pos
            if reached_exit:
                state.finished = True
                state.did_win = True
        else:
            # Wrong answer consumes this traversable attempt but keeps position.
            state.mistakes_count += 1

        state.pending_direction = None
        state.pending_target_position = None

        return MazeMoveEvaluation(
            direction=attempted_direction,
            selected_answers=evaluation.selected_answers,
            correct_answers=evaluation.correct_answers,
            explanation=evaluation.explanation,
            response_time_seconds=evaluation.response_time_seconds,
            was_correct=evaluation.is_correct,
            moved=moved,
            new_position=state.current_position,
            reached_exit=reached_exit,
        )

    def go_to_next_question(self) -> bool:
        """Advance after one validated traversable movement attempt."""
        state = self._require_state()

        if state.finished:
            return False

        if state.pending_direction is not None:
            raise ValueError("Validate the current move before continuing.")

        moved = self._quiz_session_service.go_to_next_question()
        if not moved:
            state.finished = True
            state.did_win = False
            return False

        return True

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def build_summary(self) -> MazeChallengeSummary:
        state = self._require_state()
        if not state.finished:
            raise ValueError("Cannot build summary before challenge is finished.")

        attempts = self._quiz_session_service.attempts_snapshot()
        answered = len(attempts)
        correct = len([attempt for attempt in attempts if attempt.is_correct])
        wrong = max(0, answered - correct)

        percentage = (correct / answered * 100.0) if answered else 0.0
        score_100 = percentage
        score_20 = percentage / 5.0

        average_time = None
        if attempts:
            average_time = sum(item.response_time_seconds for item in attempts) / len(attempts)

        return MazeChallengeSummary(
            deck_name=state.deck_name,
            total_questions_pool=state.total_questions_pool,
            answered_questions=answered,
            correct_answers_count=correct,
            wrong_answers_count=wrong,
            score_on_20=round(score_20, 2),
            score_on_100=round(score_100, 2),
            percentage=round(percentage, 2),
            average_response_time_seconds=round(average_time, 2) if average_time is not None else None,
            mistakes_count=state.mistakes_count,
            successful_moves=state.successful_moves,
            wall_hits_count=state.wall_hits_count,
            shortest_path_length=state.layout.shortest_path_length,
            remaining_distance=self.remaining_shortest_distance(),
            progress_percentage=self.progress_percentage(),
            guardian_restart_count=state.guardian_restart_count,
            did_win=state.did_win,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_state(self) -> MazeChallengeState:
        if self._state is None or not self._quiz_session_service.has_active_session():
            raise ValueError("No active maze challenge. Start one first.")
        return self._state

    @staticmethod
    def _resolve_difficulty(code: str | None) -> MazeDifficultyPreset:
        return get_maze_difficulty_preset(code)

    def _target_position(
        self,
        origin: tuple[int, int],
        direction: MazeDirection,
    ) -> tuple[int, int]:
        dr, dc = self._DIRECTION_DELTAS[direction]
        return origin[0] + dr, origin[1] + dc

    def _advance_guardian_position(self, state: MazeChallengeState) -> tuple[bool, tuple[int, int]]:
        path = state.guardian_patrol_path
        if len(path) <= 1:
            return False, state.guardian_position

        previous = state.guardian_position
        index = state.guardian_patrol_index

        # Ping-pong patrol avoids teleporting and keeps movement understandable.
        if state.guardian_patrol_forward:
            if index >= len(path) - 1:
                state.guardian_patrol_forward = False
                index = max(0, index - 1)
            else:
                index += 1
        else:
            if index <= 0:
                state.guardian_patrol_forward = True
                index = min(len(path) - 1, index + 1)
            else:
                index -= 1

        state.guardian_patrol_index = index
        current = path[index]
        return current != previous, current

    def _restart_after_guardian_contact(self, state: MazeChallengeState) -> MazeChallengeState:
        """Restart challenge from scratch when guardian catches the player."""
        return self.start_challenge_from_deck(
            deck_id=state.deck_id,
            question_limit=state.question_limit,
            shuffle_questions=state.shuffle_questions,
            difficulty_code=state.difficulty_code,
            profile_id=state.profile_id,
            guardian_restart_count=state.guardian_restart_count + 1,
        )

    def _build_guardian_patrol(
        self,
        layout: MazeLayout,
        desired_radius: int,
    ) -> tuple[tuple[int, int], tuple[tuple[int, int], ...], int]:
        """Create a small deterministic patrol path around one origin cell.

        We keep radius small so the guardian feels threatening but readable.
        """
        distances_from_start = self._distances_from_layout(layout, layout.start_pos)
        walkable_positions = [
            position
            for position in distances_from_start
            if position not in {layout.start_pos, layout.exit_pos}
        ]
        if not walkable_positions:
            return layout.start_pos, (layout.start_pos,), 0

        center = (layout.height // 2, layout.width // 2)
        minimum_safe_distance = max(4, layout.shortest_path_length // 5)
        candidates = [
            position
            for position in walkable_positions
            if distances_from_start.get(position, 0) >= minimum_safe_distance
        ]
        if not candidates:
            candidates = walkable_positions

        # Center-biased origin keeps the patrol in the middle game space,
        # so the player encounters it naturally instead of immediately.
        origin = min(
            candidates,
            key=lambda pos: (
                abs(pos[0] - center[0]) + abs(pos[1] - center[1]),
                -distances_from_start.get(pos, 0),
            ),
        )

        radius = max(1, desired_radius)
        patrol_cells = self._cells_within_patrol_radius(
            layout=layout,
            origin=origin,
            radius=radius,
        )
        if len(patrol_cells) < 2:
            radius = min(4, radius + 1)
            patrol_cells = self._cells_within_patrol_radius(
                layout=layout,
                origin=origin,
                radius=radius,
            )

        if not patrol_cells:
            return origin, (origin,), radius

        random_seed = (hash(layout.key) ^ (layout.shortest_path_length * 73856093)) & 0xFFFFFFFF
        rng = random.Random(random_seed)

        patrol_path: list[tuple[int, int]] = [origin]
        current = origin
        steps = max(6, min(14, len(patrol_cells) * 2))

        for _ in range(steps):
            neighbors = [item for item in self._neighbors4(current) if item in patrol_cells]
            if not neighbors:
                break

            previous = patrol_path[-2] if len(patrol_path) > 1 else None
            forward_neighbors = [item for item in neighbors if item != previous]
            next_position = rng.choice(forward_neighbors or neighbors)

            if next_position != current:
                patrol_path.append(next_position)
                current = next_position

        if len(patrol_path) == 1:
            for item in self._neighbors4(origin):
                if item in patrol_cells:
                    patrol_path.append(item)
                    break

        return origin, tuple(patrol_path), radius

    def _cells_within_patrol_radius(
        self,
        layout: MazeLayout,
        origin: tuple[int, int],
        radius: int,
    ) -> set[tuple[int, int]]:
        forbidden = {layout.start_pos, layout.exit_pos}
        cells: set[tuple[int, int]] = set()
        for row in range(layout.height):
            for col in range(layout.width):
                position = (row, col)
                if position in forbidden:
                    continue
                if abs(row - origin[0]) + abs(col - origin[1]) > radius:
                    continue
                if not self._is_walkable(layout, position):
                    continue
                cells.add(position)

        if origin not in cells and self._is_walkable(layout, origin):
            cells.add(origin)
        return cells

    def _distances_from_layout(
        self,
        layout: MazeLayout,
        source: tuple[int, int],
    ) -> dict[tuple[int, int], int]:
        distances: dict[tuple[int, int], int] = {source: 0}
        queue: deque[tuple[int, int]] = deque([source])

        while queue:
            current = queue.popleft()
            for neighbor in self._neighbors4(current):
                if neighbor in distances:
                    continue
                if not self._is_walkable(layout, neighbor):
                    continue
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

        return distances

    @staticmethod
    def _neighbors4(position: tuple[int, int]) -> tuple[tuple[int, int], ...]:
        row, col = position
        return (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        )

    @staticmethod
    def _is_walkable(layout: MazeLayout, position: tuple[int, int]) -> bool:
        row, col = position
        if row < 0 or col < 0 or row >= layout.height or col >= layout.width:
            return False

        cell = layout.rows[row][col]
        return cell in {".", "S", "E"}


__all__ = ["MazeSessionService"]


def _utc_now_sql() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
