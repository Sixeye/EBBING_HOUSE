"""Quiz session engine independent from UI widgets."""

from __future__ import annotations

import random
import re
import time
from datetime import datetime

from app.models.question import Question
from app.models.quiz_session import (
    ProgressUpdateCallback,
    QuestionAttempt,
    QuestionEvaluation,
    QuizSessionState,
    QuizSessionSummary,
)
from app.repositories.deck_repository import DeckRepository
from app.repositories.question_repository import QuestionRepository
from app.services.question_selection_service import QuestionSelectionService


class QuizSessionService:
    """Manage question flow, answer validation, and session scoring.

    Keeping this logic outside the Review page makes behavior testable and
    prevents UI code from becoming a fragile state machine.
    """

    ANSWER_ORDER = ("A", "B", "C", "D")
    ANSWER_SEPARATOR = "|"

    def __init__(
        self,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
        question_selection_service: QuestionSelectionService | None = None,
    ) -> None:
        self.deck_repository = deck_repository
        self.question_repository = question_repository
        self.question_selection_service = question_selection_service
        self._session: QuizSessionState | None = None

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------
    def start_session(
        self,
        deck_id: int,
        question_limit: int | None = None,
        shuffle_questions: bool = False,
    ) -> QuizSessionState:
        """Backward-compatible practice session starter.

        Existing callers can keep using this API while newer flows can use
        `start_session_from_deck` or `start_session_from_questions`.
        """
        return self.start_session_from_deck(
            deck_id=deck_id,
            question_limit=question_limit,
            shuffle_questions=shuffle_questions,
            session_source="practice",
            profile_id=None,
            prioritize_failed_first=False,
            record_progress_on_validate=False,
            progress_update_callback=None,
        )

    def start_session_from_deck(
        self,
        deck_id: int,
        question_limit: int | None = None,
        shuffle_questions: bool = False,
        session_source: str = "practice",
        profile_id: int | None = None,
        prioritize_failed_first: bool = False,
        record_progress_on_validate: bool = False,
        progress_update_callback: ProgressUpdateCallback | None = None,
    ) -> QuizSessionState:
        """Start a session by loading all questions from a deck."""
        deck = self.deck_repository.get_by_id(deck_id)
        if deck is None:
            raise ValueError("Selected deck does not exist.")

        questions = self.question_repository.list_by_deck(deck_id)
        if not questions:
            raise ValueError("Selected deck has no questions.")

        return self.start_session_from_questions(
            deck_id=deck_id,
            deck_name=deck.name,
            questions=questions,
            question_limit=question_limit,
            shuffle_questions=shuffle_questions,
            session_source=session_source,
            profile_id=profile_id,
            prioritize_failed_first=prioritize_failed_first,
            record_progress_on_validate=record_progress_on_validate,
            progress_update_callback=progress_update_callback,
        )

    def start_session_from_questions(
        self,
        deck_id: int,
        deck_name: str,
        questions: list[Question],
        question_limit: int | None = None,
        shuffle_questions: bool = False,
        session_source: str = "practice",
        profile_id: int | None = None,
        prioritize_failed_first: bool = False,
        record_progress_on_validate: bool = False,
        progress_update_callback: ProgressUpdateCallback | None = None,
    ) -> QuizSessionState:
        """Start a session from an explicit question list.

        This supports specialized sources like "Due today" queues while keeping
        the same answer/summary engine.
        """
        items = list(questions)
        if not items:
            raise ValueError("No questions available for this session.")

        # Failed-first ordering is explicit and profile-aware. We apply it
        # before limit slicing so prioritized weak points are not dropped.
        if prioritize_failed_first and self.question_selection_service is not None:
            items = self.question_selection_service.prioritize_for_session(
                questions=items,
                deck_id=deck_id,
                profile_id=profile_id,
                session_source=session_source,
            )
        elif shuffle_questions:
            # Backward-compatible random order for flows that do not opt in to
            # pedagogical prioritization.
            random.shuffle(items)

        if question_limit is not None:
            if question_limit <= 0:
                raise ValueError("Question limit must be greater than zero.")
            items = items[:question_limit]

        if not items:
            raise ValueError("No questions available for this session.")

        if record_progress_on_validate and progress_update_callback is None:
            raise ValueError("Progress recording requires a progress update callback.")

        self._session = QuizSessionState(
            deck_id=deck_id,
            deck_name=deck_name,
            questions=items,
            session_source=session_source,
            profile_id=profile_id,
            record_progress_on_validate=record_progress_on_validate,
            progress_update_callback=progress_update_callback,
            current_index=0,
            attempts=[],
            current_question_validated=False,
            finished=False,
            current_question_started_monotonic=time.monotonic(),
        )
        return self._session

    # ------------------------------------------------------------------
    # Session status
    # ------------------------------------------------------------------
    def has_active_session(self) -> bool:
        return self._session is not None

    def is_finished(self) -> bool:
        return bool(self._session and self._session.finished)

    def active_session_source(self) -> str | None:
        if self._session is None:
            return None
        return self._session.session_source

    def active_profile_id(self) -> int | None:
        if self._session is None:
            return None
        return self._session.profile_id

    def current_question(self) -> Question | None:
        session = self._require_session()
        if session.finished:
            return None
        return session.questions[session.current_index]

    def current_position(self) -> tuple[int, int]:
        """Return 1-based question position and total questions."""
        session = self._require_session()
        if session.finished:
            return session.total_questions, session.total_questions
        return session.current_index + 1, session.total_questions

    def answered_count(self) -> int:
        session = self._require_session()
        return session.answered_questions

    def attempts_snapshot(self) -> list[QuestionAttempt]:
        """Return a safe copy of validated attempts for summary-oriented modes.

        Mini-games (for example Hangman or Maze) sometimes need custom summary
        formulas that differ from the default deck-session summary.
        """
        session = self._require_session()
        return list(session.attempts)

    def current_question_is_validated(self) -> bool:
        session = self._require_session()
        return session.current_question_validated

    # ------------------------------------------------------------------
    # Validation and progression
    # ------------------------------------------------------------------
    def validate_current_answer(self, selected_answers: list[str]) -> QuestionEvaluation:
        """Validate one question by exact set match against canonical answers.

        Exact match rule:
        - selected A only vs correct A|C -> incorrect
        - selected A|C vs correct A|C -> correct
        - selected A|B|C vs correct A|C -> incorrect
        """
        session = self._require_session()
        if session.finished:
            raise ValueError("Session is already finished.")
        if session.current_question_validated:
            raise ValueError("Current question has already been validated.")

        normalized_selected = self._normalize_answer_letters(selected_answers)
        if not normalized_selected:
            raise ValueError("Select at least one answer before validation.")

        question = session.questions[session.current_index]
        normalized_correct = self._normalize_answer_letters([question.correct_answers])

        # Set equality expresses exact correctness for single and multiple modes.
        is_correct = set(normalized_selected) == set(normalized_correct)
        response_time = max(0.0, time.monotonic() - session.current_question_started_monotonic)
        reviewed_at = datetime.utcnow()

        # In due-mode sessions we can persist spaced-repetition progress here.
        if session.record_progress_on_validate:
            if session.profile_id is None:
                raise ValueError("Session profile is missing for progress recording.")
            if question.id is None:
                raise ValueError("Question id is missing; cannot record progress.")
            if session.progress_update_callback is None:
                raise ValueError("Progress callback is missing for this session.")

            session.progress_update_callback(question.id, is_correct, reviewed_at, response_time)

        attempt = QuestionAttempt(
            question_id=question.id,
            selected_answers=self.ANSWER_SEPARATOR.join(normalized_selected),
            correct_answers=self.ANSWER_SEPARATOR.join(normalized_correct),
            is_correct=is_correct,
            response_time_seconds=response_time,
        )
        session.attempts.append(attempt)
        session.current_question_validated = True

        return QuestionEvaluation(
            question_id=question.id,
            selected_answers=normalized_selected,
            correct_answers=normalized_correct,
            is_correct=is_correct,
            explanation=question.explanation,
            response_time_seconds=response_time,
        )

    def go_to_next_question(self) -> bool:
        """Advance session if the current question has been validated.

        Returns True when moved to another question.
        Returns False when session reached end and was marked finished.
        """
        session = self._require_session()
        if session.finished:
            return False
        if not session.current_question_validated:
            raise ValueError("Validate the current question before continuing.")

        is_last_question = session.current_index >= (session.total_questions - 1)
        if is_last_question:
            session.finished = True
            return False

        session.current_index += 1
        session.current_question_validated = False
        session.current_question_started_monotonic = time.monotonic()
        return True

    def build_summary(self) -> QuizSessionSummary:
        session = self._require_session()
        total = session.total_questions
        correct = len([attempt for attempt in session.attempts if attempt.is_correct])
        wrong = max(0, total - correct)

        percentage = (correct / total * 100.0) if total else 0.0
        score_100 = percentage
        score_20 = percentage / 5.0

        average_time = None
        if session.attempts:
            average_time = sum(a.response_time_seconds for a in session.attempts) / len(session.attempts)

        return QuizSessionSummary(
            deck_name=session.deck_name,
            total_questions=total,
            correct_answers_count=correct,
            wrong_answers_count=wrong,
            score_on_20=round(score_20, 2),
            score_on_100=round(score_100, 2),
            percentage=round(percentage, 2),
            average_response_time_seconds=round(average_time, 2) if average_time is not None else None,
        )

    def reset(self) -> None:
        self._session = None

    def _require_session(self) -> QuizSessionState:
        if self._session is None:
            raise ValueError("No active quiz session. Start a session first.")
        return self._session

    def _normalize_answer_letters(self, values: list[str]) -> list[str]:
        """Normalize answer letters to canonical order and separator.

        We accept flexible separators while keeping one canonical in-memory
        format to avoid subtle comparison bugs.
        """
        tokens: list[str] = []
        for value in values:
            parts = re.split(r"[|,;/\s]+", value.strip().upper())
            tokens.extend([part for part in parts if part])

        unique = set(tokens)
        return [letter for letter in self.ANSWER_ORDER if letter in unique]
