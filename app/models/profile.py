"""Domain model for learner profiles."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Profile:
    """Represents one learner identity in the app."""

    id: int | None
    name: str
    language: str = "en"
    theme: str = "dark"
    grading_mode: str = "score_20"
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Profile":
        """Map a raw SQLite row to the domain model."""
        return cls(
            id=row["id"],
            name=row["name"],
            language=row["language"],
            theme=row["theme"],
            grading_mode=row["grading_mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

