"""Manual question authoring service for in-app CRUD workflows."""

from __future__ import annotations

import html
import re
import shutil
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from app.core.paths import get_app_data_dir, get_media_dir
from app.models.question import Question
from app.repositories.deck_repository import DeckRepository
from app.repositories.question_repository import QuestionRepository


class QuestionAuthoringService:
    """Provide a lightweight, explicit API for manual QCM authoring.

    This service complements CSV import:
    - CSV import is optimized for bulk content ingestion.
    - Manual authoring is optimized for one-by-one creation/editing.
    """

    MODE_SINGLE = "single_choice"
    MODE_MULTIPLE = "multiple_choice"
    ALLOWED_MODES = {MODE_SINGLE, MODE_MULTIPLE}
    ALLOWED_ANSWER_LETTERS = {"A", "B", "C", "D"}
    CATEGORY_TAG_PREFIX = "category:"

    def __init__(
        self,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
    ) -> None:
        self.deck_repository = deck_repository
        self.question_repository = question_repository

    def list_by_deck(self, deck_id: int) -> list[Question]:
        self._ensure_deck_exists(deck_id)
        return self.question_repository.list_by_deck(deck_id)

    def create_manual_question(
        self,
        *,
        deck_id: int,
        category: str,
        question_text: str,
        choice_a: str,
        choice_b: str,
        choice_c: str,
        choice_d: str,
        selected_answers: list[str],
        mode: str,
        explanation: str,
        question_image_input: str | None,
        explanation_image_input: str | None,
        difficulty: int,
        tags: str,
    ) -> Question:
        """Validate author input and persist one new question row."""
        self._ensure_deck_exists(deck_id)
        normalized = self._build_validated_question(
            question=Question(
                id=None,
                deck_id=deck_id,
                question_text=question_text,
                choice_a=choice_a,
                choice_b=choice_b,
                choice_c=choice_c or None,
                choice_d=choice_d or None,
                correct_answers="|".join(selected_answers),
                mode=mode,
                explanation=explanation or None,
                question_image_path=question_image_input or None,
                explanation_image_path=explanation_image_input or None,
                difficulty=difficulty,
                tags=tags or None,
            ),
            category=category,
            selected_answers=selected_answers,
        )
        return self.question_repository.create(normalized)

    def update_manual_question(
        self,
        *,
        question_id: int,
        deck_id: int,
        category: str,
        question_text: str,
        choice_a: str,
        choice_b: str,
        choice_c: str,
        choice_d: str,
        selected_answers: list[str],
        mode: str,
        explanation: str,
        question_image_input: str | None,
        explanation_image_input: str | None,
        difficulty: int,
        tags: str,
    ) -> Question:
        """Validate and update one existing question row."""
        self._ensure_deck_exists(deck_id)
        existing = self.question_repository.get_by_id(question_id)
        if existing is None:
            raise ValueError("Question not found.")

        draft = replace(
            existing,
            deck_id=deck_id,
            question_text=question_text,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c or None,
            choice_d=choice_d or None,
            correct_answers="|".join(selected_answers),
            mode=mode,
            explanation=explanation or None,
            question_image_path=question_image_input or None,
            explanation_image_path=explanation_image_input or None,
            difficulty=difficulty,
            tags=tags or None,
        )
        normalized = self._build_validated_question(
            question=draft,
            category=category,
            selected_answers=selected_answers,
        )
        self.question_repository.update(normalized)
        refreshed = self.question_repository.get_by_id(question_id)
        if refreshed is None:
            raise ValueError("Question could not be loaded after update.")
        return refreshed

    def delete_question(self, question_id: int) -> bool:
        return self.question_repository.delete(question_id)

    def split_category_and_tags(self, tags: str | None) -> tuple[str, str]:
        """Decode category from tag payload.

        Current schema does not have a dedicated question-level `category`
        column, so we store category in tags with a reserved prefix.
        """
        if not tags:
            return "", ""

        category = ""
        free_tags: list[str] = []
        for raw_token in tags.split(","):
            token = raw_token.strip()
            if not token:
                continue
            lower = token.lower()
            if lower.startswith(self.CATEGORY_TAG_PREFIX) and not category:
                category = token[len(self.CATEGORY_TAG_PREFIX) :].strip()
            else:
                free_tags.append(token)
        return category, ", ".join(free_tags)

    def _build_validated_question(
        self,
        *,
        question: Question,
        category: str,
        selected_answers: list[str],
    ) -> Question:
        question_text = question.question_text.strip()
        choice_a = question.choice_a.strip()
        choice_b = question.choice_b.strip()
        choice_c = (question.choice_c or "").strip() or None
        choice_d = (question.choice_d or "").strip() or None
        explanation = (question.explanation or "").strip() or None
        mode = question.mode.strip()

        if not self._has_meaningful_text(question_text):
            raise ValueError("Question text is required.")
        if not choice_a:
            raise ValueError("Choice A is required.")
        if not choice_b:
            raise ValueError("Choice B is required.")
        if mode not in self.ALLOWED_MODES:
            raise ValueError("Invalid mode.")

        normalized_answers = self._normalize_selected_answers(selected_answers)
        available = {"A", "B"}
        if choice_c:
            available.add("C")
        if choice_d:
            available.add("D")
        for letter in normalized_answers:
            if letter not in available:
                raise ValueError(f"Answer '{letter}' has no non-empty choice.")

        if mode == self.MODE_SINGLE and len(normalized_answers) != 1:
            raise ValueError("single_choice requires exactly one correct answer.")
        if mode == self.MODE_MULTIPLE and len(normalized_answers) < 1:
            raise ValueError("multiple_choice requires at least one correct answer.")

        # Keep difficulty in the same [1..5] range used by CSV validation.
        difficulty = min(5, max(1, int(question.difficulty)))
        composed_tags = self._compose_tags(category=category, tags=question.tags)
        question_image_path = self._normalize_media_reference(question.question_image_path)
        explanation_image_path = self._normalize_media_reference(question.explanation_image_path)

        return replace(
            question,
            question_text=question_text,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c,
            choice_d=choice_d,
            correct_answers="|".join(normalized_answers),
            mode=mode,
            explanation=explanation,
            question_image_path=question_image_path,
            explanation_image_path=explanation_image_path,
            difficulty=difficulty,
            tags=composed_tags,
        )

    def _ensure_deck_exists(self, deck_id: int) -> None:
        if self.deck_repository.get_by_id(deck_id) is None:
            raise ValueError("Selected deck does not exist.")

    def _normalize_selected_answers(self, selected_answers: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for answer in selected_answers:
            token = answer.strip().upper()
            if token not in self.ALLOWED_ANSWER_LETTERS:
                continue
            if token in seen:
                continue
            seen.add(token)
            normalized.append(token)
        if not normalized:
            raise ValueError("Select at least one correct answer.")
        return normalized

    def _compose_tags(self, *, category: str, tags: str | None) -> str | None:
        category = category.strip()
        free_tags: list[str] = []

        if tags:
            for token in tags.replace(";", ",").replace("|", ",").split(","):
                cleaned = token.strip()
                if cleaned:
                    free_tags.append(cleaned)

        deduped: list[str] = []
        seen: set[str] = set()
        for token in free_tags:
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(token)

        if category:
            category_token = f"{self.CATEGORY_TAG_PREFIX}{category}"
            deduped = [item for item in deduped if not item.lower().startswith(self.CATEGORY_TAG_PREFIX)]
            deduped.insert(0, category_token)

        if not deduped:
            return None
        return ", ".join(deduped)

    def _has_meaningful_text(self, value: str) -> bool:
        if not value.strip():
            return False

        # Authoring uses rich text. We strip tags for required-field checks so
        # "<p><br/></p>" is treated as empty while real content remains valid.
        stripped = re.sub(r"<[^>]+>", " ", value)
        stripped = html.unescape(stripped).replace("\xa0", " ")
        return bool(stripped.strip())

    def _normalize_media_reference(self, source: str | None) -> str | None:
        """Store media references in an app-managed location.

        Strategy:
        - if reference is already relative (managed), keep it
        - if reference is absolute external path, copy into app media dir
        - if file no longer exists, drop reference safely
        """
        if source is None:
            return None
        raw = source.strip()
        if not raw:
            return None

        raw_path = Path(raw)
        if not raw_path.is_absolute():
            return raw.replace("\\", "/")

        if not raw_path.exists() or not raw_path.is_file():
            return None

        media_dir = get_media_dir("questions")
        suffix = raw_path.suffix or ".img"
        target_name = f"{uuid4().hex}{suffix.lower()}"
        target_path = media_dir / target_name
        shutil.copy2(raw_path, target_path)

        # Persist relative path so data remains portable across environments.
        return str(target_path.relative_to(get_app_data_dir())).replace("\\", "/")


__all__ = ["QuestionAuthoringService"]
