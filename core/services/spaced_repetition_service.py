"""Profile-based spaced-repetition progression and due selection logic."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from core.models.question import Question
from core.models.question_progress import QuestionProgress
from core.persistence.repositories.deck_repository import DeckRepository
from core.persistence.repositories.profile_repository import ProfileRepository
from core.persistence.repositories.question_progress_repository import QuestionProgressRepository
from core.persistence.repositories.question_repository import QuestionRepository


class SpacedRepetitionService:
    """Compute question intervals and per-profile due queues.

    This service is intentionally lightweight:
    - repository layer handles SQL
    - service layer handles scheduling/memory progression rules
    """

    MAX_INTERVAL_DAYS = 120
    MIN_INTERVAL_DAYS = 0
    MIN_MASTERY = 0.0
    MAX_MASTERY = 100.0

    def __init__(
        self,
        profile_repository: ProfileRepository,
        deck_repository: DeckRepository,
        question_repository: QuestionRepository,
        progress_repository: QuestionProgressRepository,
    ) -> None:
        self.profile_repository = profile_repository
        self.deck_repository = deck_repository
        self.question_repository = question_repository
        self.progress_repository = progress_repository

    def get_due_questions(
        self,
        profile_id: int,
        deck_id: int,
        as_of: date | datetime | None = None,
        limit: int | None = None,
    ) -> list[Question]:
        """Return due questions for one learner profile and one deck."""
        self._ensure_profile_exists(profile_id)
        self._ensure_deck_exists(deck_id)

        as_of_dt = self._normalize_as_of(as_of)
        as_of_timestamp = self._to_db_timestamp(as_of_dt)
        return self.progress_repository.list_due_questions(
            profile_id=profile_id,
            deck_id=deck_id,
            as_of_timestamp=as_of_timestamp,
            limit=limit,
        )

    def record_review_result(
        self,
        profile_id: int,
        question_id: int,
        was_correct: bool,
        response_time_seconds: float | None = None,
        reviewed_at: datetime | None = None,
    ) -> QuestionProgress:
        """Update spaced-repetition state for one profile/question review.

        `response_time_seconds` is accepted for forward compatibility with
        richer analytics, even though interval math does not use it yet.
        """
        self._ensure_profile_exists(profile_id)
        question = self.question_repository.get_by_id(question_id)
        if question is None:
            raise ValueError(f"Question with id {question_id} does not exist.")

        now = reviewed_at or datetime.utcnow()
        current = self.progress_repository.get(profile_id=profile_id, question_id=question_id)

        if current is None:
            current = QuestionProgress(
                id=None,
                profile_id=profile_id,
                question_id=question_id,
                interval_days=0,
                consecutive_correct=0,
                mastery_score=0.0,
                review_count=0,
                correct_count=0,
                last_reviewed_at=None,
                next_due_at=self._to_db_timestamp(now),
            )

        updated = self._compute_next_progress(current, was_correct=was_correct, reviewed_at=now)
        return self.progress_repository.upsert(updated)

    def _compute_next_progress(
        self,
        current: QuestionProgress,
        was_correct: bool,
        reviewed_at: datetime,
    ) -> QuestionProgress:
        """Apply simple Ebbinghaus-inspired progression rules.

        Correct answers gradually stretch intervals.
        Incorrect answers reset short-term memory confidence and shrink interval.
        """
        next_state = QuestionProgress(
            id=current.id,
            profile_id=current.profile_id,
            question_id=current.question_id,
            interval_days=current.interval_days,
            consecutive_correct=current.consecutive_correct,
            mastery_score=current.mastery_score,
            review_count=current.review_count + 1,
            correct_count=current.correct_count,
            last_reviewed_at=self._to_db_timestamp(reviewed_at),
            next_due_at=current.next_due_at,
            created_at=current.created_at,
            updated_at=current.updated_at,
        )

        if was_correct:
            next_state.correct_count += 1
            next_state.consecutive_correct += 1

            next_state.interval_days = self._next_interval_after_success(
                current_interval=current.interval_days,
                consecutive_correct=next_state.consecutive_correct,
            )
            next_state.mastery_score = self._clamp_mastery(
                current.mastery_score + self._mastery_gain(next_state.consecutive_correct)
            )
        else:
            next_state.consecutive_correct = 0

            next_state.interval_days = self._next_interval_after_failure(
                current_interval=current.interval_days
            )
            next_state.mastery_score = self._clamp_mastery(
                current.mastery_score - self._mastery_loss(current.interval_days)
            )

        next_due_dt = reviewed_at + timedelta(days=next_state.interval_days)
        next_state.next_due_at = self._to_db_timestamp(next_due_dt)
        return next_state

    def _next_interval_after_success(self, current_interval: int, consecutive_correct: int) -> int:
        if current_interval <= 0:
            return 1
        if current_interval == 1:
            return 2

        grown = max(current_interval + 1, int(round(current_interval * 1.8)))
        if consecutive_correct >= 4:
            grown += 1
        return min(self.MAX_INTERVAL_DAYS, grown)

    def _next_interval_after_failure(self, current_interval: int) -> int:
        # Wrong answers should not keep long intervals; we collapse memory
        # confidence quickly while avoiding abrupt zeroing for all cases.
        if current_interval <= 1:
            return 0
        if current_interval <= 4:
            return 1
        return max(1, current_interval // 2)

    def _mastery_gain(self, consecutive_correct: int) -> float:
        if consecutive_correct <= 1:
            return 12.0
        if consecutive_correct <= 3:
            return 8.0
        return 5.0

    def _mastery_loss(self, current_interval: int) -> float:
        if current_interval >= 7:
            return 15.0
        return 10.0

    def _clamp_mastery(self, value: float) -> float:
        return max(self.MIN_MASTERY, min(self.MAX_MASTERY, round(value, 2)))

    def _normalize_as_of(self, as_of: date | datetime | None) -> datetime:
        if as_of is None:
            return datetime.utcnow()
        if isinstance(as_of, datetime):
            return as_of
        # `date` inputs represent "due by end of this day".
        return datetime.combine(as_of, time.max.replace(microsecond=0))

    def _to_db_timestamp(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")

    def _ensure_profile_exists(self, profile_id: int) -> None:
        if self.profile_repository.get_by_id(profile_id) is None:
            raise ValueError(f"Profile with id {profile_id} does not exist.")

    def _ensure_deck_exists(self, deck_id: int) -> None:
        if self.deck_repository.get_by_id(deck_id) is None:
            raise ValueError(f"Deck with id {deck_id} does not exist.")
