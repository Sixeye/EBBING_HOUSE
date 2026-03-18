"""Domain model for lightweight game run history rows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

RunMode = Literal["maze", "hangman", "connect4"]


@dataclass
class RunHistoryEntry:
    """One completed game run.

    We keep this model intentionally small: enough to answer "what happened"
    without introducing heavy analytics complexity.
    """

    id: int | None
    profile_id: int | None
    mode: str
    deck_id: int | None
    started_at: str
    ended_at: str
    did_win: bool
    correct_count: int | None = None
    wrong_count: int | None = None
    score_on_100: float | None = None
    summary_text: str | None = None
    created_at: str | None = None
    profile_name: str | None = None
    deck_name: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RunHistoryEntry":
        """Map a raw SQLite row (optionally joined with profile/deck labels)."""
        return cls(
            id=int(row["id"]) if row["id"] is not None else None,
            profile_id=int(row["profile_id"]) if row["profile_id"] is not None else None,
            mode=str(row["mode"]),
            deck_id=int(row["deck_id"]) if row["deck_id"] is not None else None,
            started_at=str(row["started_at"]),
            ended_at=str(row["ended_at"]),
            did_win=bool(row["did_win"]),
            correct_count=int(row["correct_count"]) if row["correct_count"] is not None else None,
            wrong_count=int(row["wrong_count"]) if row["wrong_count"] is not None else None,
            score_on_100=float(row["score_on_100"]) if row["score_on_100"] is not None else None,
            summary_text=str(row["summary_text"]) if row["summary_text"] is not None else None,
            created_at=str(row["created_at"]) if row["created_at"] is not None else None,
            profile_name=str(row["profile_name"]) if "profile_name" in row.keys() and row["profile_name"] is not None else None,
            deck_name=str(row["deck_name"]) if "deck_name" in row.keys() and row["deck_name"] is not None else None,
        )


__all__ = ["RunMode", "RunHistoryEntry"]
