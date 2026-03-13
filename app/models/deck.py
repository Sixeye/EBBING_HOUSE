"""Domain model for study decks."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Deck:
    """Collection of questions used during review sessions."""

    id: int | None
    profile_id: int | None
    name: str
    category: str | None = None
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Deck":
        """Map a raw SQLite row to a typed deck object."""
        return cls(
            id=row["id"],
            profile_id=row["profile_id"],
            name=row["name"],
            category=row["category"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

