"""Repository for deck persistence operations."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.deck import Deck


class DeckRepository:
    """Handles CRUD queries for study decks."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create(
        self,
        name: str,
        profile_id: int | None = None,
        category: str | None = None,
        description: str | None = None,
    ) -> Deck:
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO decks (profile_id, name, category, description)
                VALUES (?, ?, ?, ?)
                """,
                (profile_id, name, category, description),
            )
            deck_id = int(cursor.lastrowid)
            row = conn.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
        return Deck.from_row(row)

    def get_by_id(self, deck_id: int) -> Deck | None:
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM decks WHERE id = ?", (deck_id,)).fetchone()
        return Deck.from_row(row) if row else None

    def list_all(self) -> list[Deck]:
        with self.database.connection() as conn:
            rows = conn.execute("SELECT * FROM decks ORDER BY created_at DESC, id DESC").fetchall()
        return [Deck.from_row(row) for row in rows]

    def list_by_profile(self, profile_id: int) -> list[Deck]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM decks
                WHERE profile_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (profile_id,),
            ).fetchall()
        return [Deck.from_row(row) for row in rows]

    def update(self, deck: Deck) -> bool:
        if deck.id is None:
            raise ValueError("Cannot update a deck without an id.")

        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE decks
                SET
                    profile_id = ?,
                    name = ?,
                    category = ?,
                    description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (deck.profile_id, deck.name, deck.category, deck.description, deck.id),
            )
        return cursor.rowcount > 0

    def delete(self, deck_id: int) -> bool:
        with self.database.connection() as conn:
            cursor = conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
        return cursor.rowcount > 0

