"""Domain model for built-in trophy definitions and unlocked view rows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Trophy:
    """One trophy/badge definition.

    `unlocked_at` is optional and used when rows are loaded from a joined
    profile_trophies query for UI presentation.
    """

    id: int | None
    code: str
    name_en: str
    name_fr: str
    description_en: str
    description_fr: str
    category: str
    rarity: str
    created_at: str | None = None
    unlocked_at: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Trophy":
        data = dict(row)
        return cls(
            id=data.get("id"),
            code=str(data.get("code", "")),
            name_en=str(data.get("name_en", "")),
            name_fr=str(data.get("name_fr", "")),
            description_en=str(data.get("description_en", "")),
            description_fr=str(data.get("description_fr", "")),
            category=str(data.get("category", "general")),
            rarity=str(data.get("rarity", "common")),
            created_at=data.get("created_at"),
            unlocked_at=data.get("unlocked_at"),
        )

    def display_name(self, locale: str) -> str:
        return self.name_fr if locale == "fr" else self.name_en

    def display_description(self, locale: str) -> str:
        return self.description_fr if locale == "fr" else self.description_en
