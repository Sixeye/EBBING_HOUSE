"""Repository for lightweight run history persistence."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.run_history import RunHistoryEntry, RunMode


class RunHistoryRepository:
    """Own SQL operations for completed game run history."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create(
        self,
        *,
        profile_id: int | None,
        mode: RunMode,
        deck_id: int | None,
        started_at: str,
        ended_at: str,
        did_win: bool,
        correct_count: int | None,
        wrong_count: int | None,
        score_on_100: float | None,
        summary_text: str | None = None,
    ) -> RunHistoryEntry:
        """Insert one completed run and return the stored row."""
        with self.database.connection() as conn:
            # Defensive consistency: if profile/deck was deleted between
            # gameplay and persistence, we keep the history row and clear the FK.
            safe_profile_id = profile_id
            safe_deck_id = deck_id
            if profile_id is not None:
                exists = conn.execute(
                    "SELECT 1 FROM profiles WHERE id = ? LIMIT 1",
                    (profile_id,),
                ).fetchone()
                if exists is None:
                    safe_profile_id = None
            if deck_id is not None:
                exists = conn.execute(
                    "SELECT 1 FROM decks WHERE id = ? LIMIT 1",
                    (deck_id,),
                ).fetchone()
                if exists is None:
                    safe_deck_id = None

            cursor = conn.execute(
                """
                INSERT INTO game_runs (
                    profile_id,
                    mode,
                    deck_id,
                    started_at,
                    ended_at,
                    did_win,
                    correct_count,
                    wrong_count,
                    score_on_100,
                    summary_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_profile_id,
                    mode,
                    safe_deck_id,
                    started_at,
                    ended_at,
                    1 if did_win else 0,
                    correct_count,
                    wrong_count,
                    score_on_100,
                    summary_text,
                ),
            )
            run_id = int(cursor.lastrowid)
            row = conn.execute("SELECT * FROM game_runs WHERE id = ?", (run_id,)).fetchone()
        return RunHistoryEntry.from_row(row)

    def list_recent(
        self,
        *,
        limit: int = 20,
        profile_id: int | None = None,
        mode: RunMode | None = None,
    ) -> list[RunHistoryEntry]:
        """List latest runs, optionally filtered by profile and mode."""
        clauses: list[str] = []
        params: list[object] = []

        if profile_id is not None:
            clauses.append("gr.profile_id = ?")
            params.append(profile_id)
        if mode is not None:
            clauses.append("gr.mode = ?")
            params.append(mode)

        where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(max(1, limit))

        with self.database.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    gr.*,
                    p.name AS profile_name,
                    d.name AS deck_name
                FROM game_runs gr
                LEFT JOIN profiles p ON p.id = gr.profile_id
                LEFT JOIN decks d ON d.id = gr.deck_id
                {where_sql}
                ORDER BY gr.ended_at DESC, gr.id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [RunHistoryEntry.from_row(row) for row in rows]


__all__ = ["RunHistoryRepository"]
