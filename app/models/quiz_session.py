"""Domain models for in-memory quiz session execution."""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable

from app.models.question import Question

ProgressUpdateCallback = Callable[[int, bool, datetime, float], None]


@dataclass
class QuestionAttempt:
    """Stores one validated attempt for one question."""

    question_id: int | None
    selected_answers: str
    correct_answers: str
    is_correct: bool
    response_time_seconds: float


@dataclass
class QuestionEvaluation:
    """Returned immediately after answer validation."""

    question_id: int | None
    selected_answers: list[str]
    correct_answers: list[str]
    is_correct: bool
    explanation: str | None
    response_time_seconds: float


@dataclass
class QuizSessionSummary:
    """Final session metrics shown in the end-of-session summary."""

    deck_name: str
    total_questions: int
    correct_answers_count: int
    wrong_answers_count: int
    score_on_20: float
    score_on_100: float
    percentage: float
    average_response_time_seconds: float | None


@dataclass
class QuizSessionState:
    """Mutable state for one running quiz session."""

    deck_id: int
    deck_name: str
    questions: list[Question] = field(default_factory=list)
    session_source: str = "practice"
    profile_id: int | None = None
    record_progress_on_validate: bool = False
    progress_update_callback: ProgressUpdateCallback | None = None
    current_index: int = 0
    attempts: list[QuestionAttempt] = field(default_factory=list)
    current_question_validated: bool = False
    finished: bool = False
    current_question_started_monotonic: float = 0.0

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def answered_questions(self) -> int:
        return len(self.attempts)
