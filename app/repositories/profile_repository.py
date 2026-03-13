"""Repository for profile persistence."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.profile import Profile


class ProfileRepository:
    """Owns SQL operations related to learner profiles."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create(
        self,
        name: str,
        language: str = "en",
        theme: str = "dark",
        grading_mode: str = "score_20",
    ) -> Profile:
        """Create a new profile and return the stored record."""
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO profiles (name, language, theme, grading_mode)
                VALUES (?, ?, ?, ?)
                """,
                (name, language, theme, grading_mode),
            )
            profile_id = int(cursor.lastrowid)
            row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()

        return Profile.from_row(row)

    def get_by_id(self, profile_id: int) -> Profile | None:
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return Profile.from_row(row) if row else None

    def list_all(self) -> list[Profile]:
        with self.database.connection() as conn:
            rows = conn.execute("SELECT * FROM profiles ORDER BY created_at DESC, id DESC").fetchall()
        return [Profile.from_row(row) for row in rows]

    def update(self, profile: Profile) -> bool:
        """Update editable profile attributes.

        Returns True when one row was actually updated.
        """
        if profile.id is None:
            raise ValueError("Cannot update a profile without an id.")

        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE profiles
                SET
                    name = ?,
                    language = ?,
                    theme = ?,
                    grading_mode = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (profile.name, profile.language, profile.theme, profile.grading_mode, profile.id),
            )
        return cursor.rowcount > 0

    def delete(self, profile_id: int) -> bool:
        with self.database.connection() as conn:
            cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        return cursor.rowcount > 0

