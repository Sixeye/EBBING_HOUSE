"""Repository for profile trophy unlock persistence."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.profile_trophy import ProfileTrophy
from app.models.trophy import Trophy


class ProfileTrophyRepository:
    """Owns SQL for unlocking/listing trophies for one profile."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def unlock(self, profile_id: int, trophy_id: int) -> bool:
        """Unlock one trophy once.

        Returns True when a new unlock row was inserted, False if already
        unlocked before.
        """
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO profile_trophies (profile_id, trophy_id)
                VALUES (?, ?)
                """,
                (profile_id, trophy_id),
            )
        return cursor.rowcount > 0

    def has_unlocked(self, profile_id: int, trophy_id: int) -> bool:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM profile_trophies
                WHERE profile_id = ? AND trophy_id = ?
                LIMIT 1
                """,
                (profile_id, trophy_id),
            ).fetchone()
        return row is not None

    def list_unlock_rows(self, profile_id: int) -> list[ProfileTrophy]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM profile_trophies
                WHERE profile_id = ?
                ORDER BY unlocked_at DESC, id DESC
                """,
                (profile_id,),
            ).fetchall()
        return [ProfileTrophy.from_row(row) for row in rows]

    def list_unlocked_trophies(self, profile_id: int) -> list[Trophy]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.*,
                    pt.unlocked_at AS unlocked_at
                FROM trophies t
                JOIN profile_trophies pt ON pt.trophy_id = t.id
                WHERE pt.profile_id = ?
                ORDER BY pt.unlocked_at DESC, t.id ASC
                """,
                (profile_id,),
            ).fetchall()
        return [Trophy.from_row(row) for row in rows]

    def list_locked_trophies(self, profile_id: int) -> list[Trophy]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT t.*
                FROM trophies t
                LEFT JOIN profile_trophies pt
                    ON pt.trophy_id = t.id
                    AND pt.profile_id = ?
                WHERE pt.id IS NULL
                ORDER BY t.id ASC
                """,
                (profile_id,),
            ).fetchall()
        return [Trophy.from_row(row) for row in rows]

    def count_unlocked(self, profile_id: int) -> int:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM profile_trophies
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()
        return int(row["total"]) if row else 0

    def latest_unlocked_trophy(self, profile_id: int) -> Trophy | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    t.*,
                    pt.unlocked_at AS unlocked_at
                FROM profile_trophies pt
                JOIN trophies t ON t.id = pt.trophy_id
                WHERE pt.profile_id = ?
                ORDER BY pt.unlocked_at DESC, pt.id DESC
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()
        return Trophy.from_row(row) if row else None
