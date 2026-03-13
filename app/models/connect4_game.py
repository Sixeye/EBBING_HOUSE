"""Domain models for the Connect Four mini-game."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.question import Question

# Board encoding keeps rendering + logic explicit:
# 0 = empty, 1 = player, 2 = opponent.
Connect4Cell = int


@dataclass
class Connect4ChallengeState:
    """Mutable in-memory state for one Connect Four challenge."""

    deck_id: int
    deck_name: str
    total_questions_pool: int
    profile_id: int | None = None
    started_at: str | None = None
    rows: int = 6
    cols: int = 7
    board: list[list[Connect4Cell]] = field(default_factory=list)
    pending_column: int | None = None
    current_turn: str = "player"
    player_moves: int = 0
    opponent_moves: int = 0
    wrong_answers_count: int = 0
    finished: bool = False
    did_win: bool = False
    did_lose: bool = False
    did_draw: bool = False

    @property
    def is_player_turn(self) -> bool:
        return self.current_turn == "player"


@dataclass(frozen=True)
class Connect4MoveRequest:
    """Result of selecting a column before answer validation."""

    column: int
    blocked: bool
    question: Question | None
    reason: str | None = None


@dataclass(frozen=True)
class Connect4AnswerEvaluation:
    """Result of validating one player answer + applying turn consequences."""

    selected_answers: list[str]
    correct_answers: list[str]
    explanation: str | None
    response_time_seconds: float
    was_correct: bool
    player_disc_dropped: bool
    opponent_discs_dropped: int
    player_won: bool
    opponent_won: bool
    draw: bool
    consumed_question: bool


@dataclass(frozen=True)
class Connect4ChallengeSummary:
    """Final summary data for UI presentation."""

    deck_name: str
    total_questions_pool: int
    answered_questions: int
    correct_answers_count: int
    wrong_answers_count: int
    score_on_20: float
    score_on_100: float
    percentage: float
    average_response_time_seconds: float | None
    player_moves: int
    opponent_moves: int
    did_win: bool
    did_lose: bool
    did_draw: bool


__all__ = [
    "Connect4Cell",
    "Connect4ChallengeState",
    "Connect4MoveRequest",
    "Connect4AnswerEvaluation",
    "Connect4ChallengeSummary",
]
