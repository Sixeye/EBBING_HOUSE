"""Repository for trophy definition persistence."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.trophy import Trophy


class TrophyRepository:
    """Owns SQL for built-in trophy definitions."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def upsert(self, trophy: Trophy) -> Trophy:
        """Insert/update one trophy definition by stable `code`."""
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO trophies (
                    code,
                    name_en,
                    name_fr,
                    description_en,
                    description_fr,
                    category,
                    rarity
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name_en = excluded.name_en,
                    name_fr = excluded.name_fr,
                    description_en = excluded.description_en,
                    description_fr = excluded.description_fr,
                    category = excluded.category,
                    rarity = excluded.rarity
                """,
                (
                    trophy.code,
                    trophy.name_en,
                    trophy.name_fr,
                    trophy.description_en,
                    trophy.description_fr,
                    trophy.category,
                    trophy.rarity,
                ),
            )
            row = conn.execute("SELECT * FROM trophies WHERE code = ?", (trophy.code,)).fetchone()

        return Trophy.from_row(row)

    def get_by_code(self, code: str) -> Trophy | None:
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM trophies WHERE code = ?", (code,)).fetchone()
        return Trophy.from_row(row) if row else None

    def list_all(self) -> list[Trophy]:
        with self.database.connection() as conn:
            rows = conn.execute("SELECT * FROM trophies ORDER BY id ASC").fetchall()
        return [Trophy.from_row(row) for row in rows]

    def count_all(self) -> int:
        with self.database.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM trophies").fetchone()
        return int(row["total"]) if row else 0
