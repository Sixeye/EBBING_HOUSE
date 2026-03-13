"""Domain model for global application settings."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class GlobalSettings:
    """Singleton settings row used for app-level preferences."""

    id: int = 1
    app_language: str = "en"
    default_theme: str = "dark"
    animations_enabled: bool = True
    sounds_enabled: bool = True
    # One active learner across the app keeps the UX simple in V1.
    active_profile_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "GlobalSettings":
        """Map a SQLite row to a strongly typed settings object."""
        return cls(
            id=row["id"],
            app_language=row["app_language"],
            default_theme=row["default_theme"],
            animations_enabled=bool(row["animations_enabled"]),
            sounds_enabled=bool(row["sounds_enabled"]),
            active_profile_id=row["active_profile_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
