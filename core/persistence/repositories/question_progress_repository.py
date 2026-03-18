"""Repository for spaced-repetition question progress."""

from __future__ import annotations

from datetime import datetime

from app.db.database import DatabaseManager
from app.models.question import Question
from app.models.question_progress import QuestionProgress


class QuestionProgressRepository:
    """Owns SQL for profile-specific due scheduling state."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def get(self, profile_id: int, question_id: int) -> QuestionProgress | None:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM question_progress
                WHERE profile_id = ? AND question_id = ?
                """,
                (profile_id, question_id),
            ).fetchone()

        return QuestionProgress.from_row(row) if row else None

    def upsert(self, progress: QuestionProgress) -> QuestionProgress:
        """Insert or update a progress row while preserving uniqueness."""
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO question_progress (
                    profile_id,
                    question_id,
                    interval_days,
                    consecutive_correct,
                    mastery_score,
                    review_count,
                    correct_count,
                    last_reviewed_at,
                    next_due_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id, question_id) DO UPDATE SET
                    interval_days = excluded.interval_days,
                    consecutive_correct = excluded.consecutive_correct,
                    mastery_score = excluded.mastery_score,
                    review_count = excluded.review_count,
                    correct_count = excluded.correct_count,
                    last_reviewed_at = excluded.last_reviewed_at,
                    next_due_at = excluded.next_due_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    progress.profile_id,
                    progress.question_id,
                    progress.interval_days,
                    progress.consecutive_correct,
                    progress.mastery_score,
                    progress.review_count,
                    progress.correct_count,
                    progress.last_reviewed_at,
                    progress.next_due_at,
                ),
            )

            row = conn.execute(
                """
                SELECT *
                FROM question_progress
                WHERE profile_id = ? AND question_id = ?
                """,
                (progress.profile_id, progress.question_id),
            ).fetchone()

        return QuestionProgress.from_row(row)

    def list_due_questions(
        self,
        profile_id: int,
        deck_id: int,
        as_of_timestamp: str,
        limit: int | None = None,
    ) -> list[Question]:
        """Return due and unseen questions for one profile/deck.

        Unseen = no progress row yet for (profile_id, question_id), and those
        are considered immediately due.
        """
        query = """
            SELECT q.*
            FROM questions q
            LEFT JOIN question_progress qp
                ON qp.question_id = q.id
                AND qp.profile_id = ?
            WHERE q.deck_id = ?
              AND (qp.id IS NULL OR qp.next_due_at <= ?)
            ORDER BY
                CASE WHEN qp.next_due_at IS NULL THEN 0 ELSE 1 END,
                qp.next_due_at ASC,
                q.id ASC
        """
        params: list[object] = [profile_id, deck_id, as_of_timestamp]

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self.database.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [Question.from_row(row) for row in rows]

    def count_tracked_questions(self, profile_id: int) -> int:
        """Count how many questions already have progress rows for a profile."""
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM question_progress
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()
        return int(row["total"]) if row else 0

    def count_mastered_questions(
        self,
        profile_id: int,
        mastery_threshold: float = 80.0,
    ) -> int:
        """Count profile questions that reached at least `mastery_threshold`."""
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM question_progress
                WHERE profile_id = ? AND mastery_score >= ?
                """,
                (profile_id, mastery_threshold),
            ).fetchone()
        return int(row["total"]) if row else 0

    def sum_correct_answers(self, profile_id: int) -> int:
        """Aggregate total validated correct answers stored in progress rows."""
        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(correct_count), 0) AS total
                FROM question_progress
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()
        return int(row["total"]) if row else 0

    def count_due_questions_for_profile(
        self,
        profile_id: int,
        as_of_timestamp: str | None = None,
    ) -> int:
        """Count due+unseen questions across all decks for one profile."""
        as_of = as_of_timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        with self.database.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS due_count
                FROM questions q
                LEFT JOIN question_progress qp
                    ON qp.question_id = q.id
                    AND qp.profile_id = ?
                WHERE qp.id IS NULL OR qp.next_due_at <= ?
                """,
                (profile_id, as_of),
            ).fetchone()

        return int(row["due_count"]) if row else 0

    def list_for_profile_and_deck(self, profile_id: int, deck_id: int) -> list[QuestionProgress]:
        """Return progress rows for one profile limited to one deck.

        Why this query exists:
        - question selection needs a deck-level snapshot of past performance
        - doing one join query avoids N+1 lookups when ordering a session
        """
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT qp.*
                FROM question_progress qp
                INNER JOIN questions q ON q.id = qp.question_id
                WHERE qp.profile_id = ? AND q.deck_id = ?
                """,
                (profile_id, deck_id),
            ).fetchall()

        return [QuestionProgress.from_row(row) for row in rows]
