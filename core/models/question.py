"""Domain model for imported or authored questions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Question:
    """One MCQ-style question stored in the local database."""

    id: int | None
    deck_id: int
    question_text: str
    choice_a: str
    choice_b: str
    choice_c: str | None = None
    choice_d: str | None = None
    correct_answers: str = "A"
    mode: str = "single_choice"
    external_id: str | None = None
    explanation: str | None = None
    question_image_path: str | None = None
    explanation_image_path: str | None = None
    difficulty: int = 1
    tags: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Question":
        """Map a raw SQLite row into a domain object."""
        return cls(
            id=row["id"],
            deck_id=row["deck_id"],
            external_id=row["external_id"],
            question_text=row["question_text"],
            choice_a=row["choice_a"],
            choice_b=row["choice_b"],
            choice_c=row["choice_c"],
            choice_d=row["choice_d"],
            correct_answers=row["correct_answers"],
            mode=row["mode"],
            explanation=row["explanation"],
            question_image_path=row["question_image_path"] if "question_image_path" in row.keys() else None,
            explanation_image_path=row["explanation_image_path"] if "explanation_image_path" in row.keys() else None,
            difficulty=row["difficulty"],
            tags=row["tags"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
