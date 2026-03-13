"""Domain model for unlocked trophies per learner profile."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class ProfileTrophy:
    """One unlock event for one profile/trophy pair."""

    id: int | None
    profile_id: int
    trophy_id: int
    unlocked_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ProfileTrophy":
        return cls(
            id=row["id"],
            profile_id=row["profile_id"],
            trophy_id=row["trophy_id"],
            unlocked_at=row["unlocked_at"],
        )
