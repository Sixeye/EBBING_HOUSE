"""Domain model for profile-based spaced-repetition progress."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class QuestionProgress:
    """Tracks one learner's memory state for one question."""

    id: int | None
    profile_id: int
    question_id: int
    interval_days: int = 0
    consecutive_correct: int = 0
    mastery_score: float = 0.0
    review_count: int = 0
    correct_count: int = 0
    last_reviewed_at: str | None = None
    next_due_at: str = ""
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "QuestionProgress":
        """Map a SQLite row into a typed progress model."""
        return cls(
            id=row["id"],
            profile_id=row["profile_id"],
            question_id=row["question_id"],
            interval_days=row["interval_days"],
            consecutive_correct=row["consecutive_correct"],
            mastery_score=float(row["mastery_score"]),
            review_count=row["review_count"],
            correct_count=row["correct_count"],
            last_reviewed_at=row["last_reviewed_at"],
            next_due_at=row["next_due_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

