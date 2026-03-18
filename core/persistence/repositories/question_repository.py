"""Repository for question persistence operations."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.question import Question


class QuestionRepository:
    """Handles question insert/list/count operations for decks."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create(self, question: Question) -> Question:
        """Insert one question and return the persisted row."""
        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO questions (
                    deck_id,
                    external_id,
                    question_text,
                    choice_a,
                    choice_b,
                    choice_c,
                    choice_d,
                    correct_answers,
                    mode,
                    explanation,
                    question_image_path,
                    explanation_image_path,
                    difficulty,
                    tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question.deck_id,
                    question.external_id,
                    question.question_text,
                    question.choice_a,
                    question.choice_b,
                    question.choice_c,
                    question.choice_d,
                    question.correct_answers,
                    question.mode,
                    question.explanation,
                    question.question_image_path,
                    question.explanation_image_path,
                    question.difficulty,
                    question.tags,
                ),
            )
            question_id = int(cursor.lastrowid)
            row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return Question.from_row(row)

    def bulk_create(self, questions: list[Question]) -> int:
        """Insert many questions efficiently in one transaction."""
        if not questions:
            return 0

        payload = [
            (
                item.deck_id,
                item.external_id,
                item.question_text,
                item.choice_a,
                item.choice_b,
                item.choice_c,
                item.choice_d,
                item.correct_answers,
                item.mode,
                item.explanation,
                item.question_image_path,
                item.explanation_image_path,
                item.difficulty,
                item.tags,
            )
            for item in questions
        ]

        with self.database.connection() as conn:
            conn.executemany(
                """
                INSERT INTO questions (
                    deck_id,
                    external_id,
                    question_text,
                    choice_a,
                    choice_b,
                    choice_c,
                    choice_d,
                    correct_answers,
                    mode,
                    explanation,
                    question_image_path,
                    explanation_image_path,
                    difficulty,
                    tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
        return len(payload)

    def list_by_deck(self, deck_id: int) -> list[Question]:
        with self.database.connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM questions
                WHERE deck_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (deck_id,),
            ).fetchall()
        return [Question.from_row(row) for row in rows]

    def get_by_id(self, question_id: int) -> Question | None:
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return Question.from_row(row) if row else None

    def count_by_deck(self, deck_id: int) -> int:
        with self.database.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM questions WHERE deck_id = ?",
                (deck_id,),
            ).fetchone()
        return int(row["total"])

    def update(self, question: Question) -> bool:
        """Update one existing question.

        We keep this explicit CRUD method so manual authoring UI can edit
        questions without bypassing repository boundaries.
        """
        if question.id is None:
            raise ValueError("Cannot update a question without an id.")

        with self.database.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE questions
                SET
                    deck_id = ?,
                    external_id = ?,
                    question_text = ?,
                    choice_a = ?,
                    choice_b = ?,
                    choice_c = ?,
                    choice_d = ?,
                    correct_answers = ?,
                    mode = ?,
                    explanation = ?,
                    question_image_path = ?,
                    explanation_image_path = ?,
                    difficulty = ?,
                    tags = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    question.deck_id,
                    question.external_id,
                    question.question_text,
                    question.choice_a,
                    question.choice_b,
                    question.choice_c,
                    question.choice_d,
                    question.correct_answers,
                    question.mode,
                    question.explanation,
                    question.question_image_path,
                    question.explanation_image_path,
                    question.difficulty,
                    question.tags,
                    question.id,
                ),
            )
        return cursor.rowcount > 0

    def delete(self, question_id: int) -> bool:
        with self.database.connection() as conn:
            cursor = conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return cursor.rowcount > 0

    def delete_by_deck(self, deck_id: int) -> int:
        with self.database.connection() as conn:
            cursor = conn.execute("DELETE FROM questions WHERE deck_id = ?", (deck_id,))
        return int(cursor.rowcount)
