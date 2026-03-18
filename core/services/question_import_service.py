"""Service that imports validated CSV question payloads into SQLite."""

from __future__ import annotations

from core.models.csv_preview import CsvNormalizedQuestion
from core.models.question import Question
from core.persistence.repositories.deck_repository import DeckRepository
from core.persistence.repositories.question_repository import QuestionRepository


class QuestionImportService:
    """Bridge between CSV validation output and repository insertions."""

    def __init__(
        self,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
    ) -> None:
        self.deck_repository = deck_repository
        self.question_repository = question_repository

    def import_validated_rows(
        self,
        deck_id: int,
        rows: list[CsvNormalizedQuestion],
    ) -> int:
        """Import normalized questions into a specific deck.

        `rows` must already be validated by CsvValidationService.
        """
        if not rows:
            return 0

        deck = self.deck_repository.get_by_id(deck_id)
        if deck is None:
            raise ValueError(f"Deck with id {deck_id} does not exist.")

        questions = [
            Question(
                id=None,
                deck_id=deck_id,
                external_id=row.external_id,
                question_text=row.question_text,
                choice_a=row.choice_a,
                choice_b=row.choice_b,
                choice_c=row.choice_c,
                choice_d=row.choice_d,
                correct_answers=row.correct_answers,
                mode=row.mode,
                explanation=row.explanation,
                difficulty=row.difficulty,
                tags=row.tags,
            )
            for row in rows
        ]

        return self.question_repository.bulk_create(questions)
