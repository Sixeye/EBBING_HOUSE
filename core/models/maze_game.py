"""Domain models for Maze Challenge generation and session flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.models.question import Question

MazeDirection = Literal["forward", "backward", "left", "right"]


@dataclass(frozen=True)
class MazeLayout:
    """Immutable generated maze.

    Grid markers:
    - `#`: wall
    - `.`: traversable floor
    - `S`: start
    - `E`: exit
    """

    key: str
    rows: tuple[str, ...]
    start_pos: tuple[int, int]
    exit_pos: tuple[int, int]
    shortest_path_length: int

    @property
    def width(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    @property
    def height(self) -> int:
        return len(self.rows)


@dataclass
class MazeMoveRequest:
    """Result of a direction click before answer validation.

    Product rule:
    - wall target => blocked immediately, no question consumed
    - traversable target => provide one question for quiz-gated movement
    """

    direction: MazeDirection
    blocked_by_wall: bool
    question: Question | None
    target_position: tuple[int, int] | None


@dataclass
class MazeGuardianTick:
    """Result of one guardian patrol timer step."""

    moved: bool
    caught_player: bool
    challenge_restarted: bool
    guardian_position: tuple[int, int]
    player_position: tuple[int, int]
    restart_count: int


@dataclass
class MazeChallengeState:
    """Mutable in-memory session state for one maze run."""

    deck_id: int
    deck_name: str
    layout: MazeLayout
    total_questions_pool: int
    question_limit: int | None = None
    shuffle_questions: bool = True
    difficulty_code: str = "normal"
    profile_id: int | None = None
    started_at: str | None = None
    current_position: tuple[int, int] = (0, 0)
    pending_direction: MazeDirection | None = None
    pending_target_position: tuple[int, int] | None = None
    guardian_origin: tuple[int, int] = (0, 0)
    guardian_position: tuple[int, int] = (0, 0)
    guardian_patrol_path: tuple[tuple[int, int], ...] = tuple()
    guardian_patrol_index: int = 0
    guardian_patrol_forward: bool = True
    guardian_patrol_radius: int = 2
    guardian_tick_ms: int = 900
    guardian_restart_count: int = 0
    mistakes_count: int = 0
    successful_moves: int = 0
    wall_hits_count: int = 0
    finished: bool = False
    did_win: bool = False


@dataclass
class MazeMoveEvaluation:
    """Result returned after validating a traversable movement attempt."""

    direction: MazeDirection
    selected_answers: list[str]
    correct_answers: list[str]
    explanation: str | None
    response_time_seconds: float
    was_correct: bool
    moved: bool
    new_position: tuple[int, int]
    reached_exit: bool


@dataclass
class MazeChallengeSummary:
    """Final challenge summary shown in the Maze page."""

    deck_name: str
    total_questions_pool: int
    answered_questions: int
    correct_answers_count: int
    wrong_answers_count: int
    score_on_20: float
    score_on_100: float
    percentage: float
    average_response_time_seconds: float | None
    mistakes_count: int
    successful_moves: int
    wall_hits_count: int
    shortest_path_length: int
    remaining_distance: int
    progress_percentage: float
    guardian_restart_count: int
    did_win: bool


__all__ = [
    "MazeDirection",
    "MazeLayout",
    "MazeMoveRequest",
    "MazeGuardianTick",
    "MazeChallengeState",
    "MazeMoveEvaluation",
    "MazeChallengeSummary",
]
