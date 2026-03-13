"""Question ordering policy shared by review and mini-game sessions.

This service keeps selection logic explicit and explainable:
- prioritize past failures first (when profile data exists)
- then surface unseen / less-rehearsed questions
- keep variety with constrained shuffle
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from app.models.question import Question
from app.models.question_progress import QuestionProgress
from app.repositories.question_progress_repository import QuestionProgressRepository


@dataclass(frozen=True)
class _QuestionPriority:
    """Computed ordering metadata for one question."""

    question: Question
    # 0 = failed before, 1 = unseen, 2 = seen non-failed
    tier: int
    wrong_count: int
    review_count: int
    mastery_score: float
    last_reviewed_at: str | None


class QuestionSelectionService:
    """Apply lightweight pedagogical ordering without overengineering.

    We intentionally avoid opaque "AI ranking". The heuristic is deterministic
    in structure (clear tiers) with only small shuffle noise for freshness.
    """

    def __init__(self, progress_repository: QuestionProgressRepository) -> None:
        self.progress_repository = progress_repository
        # In-memory memory to avoid repeating exactly the same first question
        # between consecutive sessions with the same context.
        self._last_first_question_by_context: dict[str, int] = {}

    def prioritize_for_session(
        self,
        *,
        questions: list[Question],
        deck_id: int,
        profile_id: int | None,
        session_source: str,
    ) -> list[Question]:
        """Order questions with failed-first policy and constrained variety."""
        if not questions:
            return []

        rng = random.Random(time.time_ns())
        context_key = f"{session_source}:{profile_id or 0}:{deck_id}"

        progress_by_question_id = self._progress_by_question_id(
            profile_id=profile_id,
            deck_id=deck_id,
        )
        priorities = [self._build_priority(item, progress_by_question_id.get(item.id)) for item in questions]

        failed = [item for item in priorities if item.tier == 0]
        unseen = [item for item in priorities if item.tier == 1]
        seen_non_failed = [item for item in priorities if item.tier == 2]

        # Tier 1: failed questions first, strongest pain points first.
        failed_ordered = self._shuffle_failed_tier(failed, rng)
        # Tier 2: unseen questions next so fresh material still appears.
        unseen_ordered = self._shuffle_simple_tier(unseen, rng)
        # Tier 3: seen non-failed, bias toward less-rehearsed / lower mastery.
        seen_ordered = self._shuffle_seen_tier(seen_non_failed, rng)

        ordered = [*failed_ordered, *unseen_ordered, *seen_ordered]
        # We only swap within the current first tier to preserve pedagogical
        # priority (for example failed questions must stay before unseen).
        first_tier_size = len(failed_ordered) or len(unseen_ordered) or len(seen_ordered)
        self._avoid_immediate_first_repeat(
            ordered,
            context_key=context_key,
            first_tier_size=first_tier_size,
        )
        return ordered

    def _progress_by_question_id(
        self,
        *,
        profile_id: int | None,
        deck_id: int,
    ) -> dict[int, QuestionProgress]:
        if profile_id is None:
            return {}
        rows = self.progress_repository.list_for_profile_and_deck(
            profile_id=profile_id,
            deck_id=deck_id,
        )
        # question_id is unique per profile in question_progress.
        return {item.question_id: item for item in rows}

    def _build_priority(
        self,
        question: Question,
        progress: QuestionProgress | None,
    ) -> _QuestionPriority:
        if progress is None:
            return _QuestionPriority(
                question=question,
                tier=1,
                wrong_count=0,
                review_count=0,
                mastery_score=0.0,
                last_reviewed_at=None,
            )

        review_count = max(0, int(progress.review_count))
        correct_count = max(0, int(progress.correct_count))
        wrong_count = max(0, review_count - correct_count)

        if wrong_count > 0:
            tier = 0
        else:
            tier = 2

        return _QuestionPriority(
            question=question,
            tier=tier,
            wrong_count=wrong_count,
            review_count=review_count,
            mastery_score=float(progress.mastery_score),
            last_reviewed_at=progress.last_reviewed_at,
        )

    def _shuffle_failed_tier(
        self,
        items: list[_QuestionPriority],
        rng: random.Random,
    ) -> list[Question]:
        if not items:
            return []

        # Recent/repeated failures should appear earlier. We keep that ordering
        # strict so repeated failures are not diluted by randomness.
        rows = sorted(
            items,
            key=lambda item: (
                item.wrong_count,
                item.review_count,
                # ISO timestamp string order matches chronological order.
                item.last_reviewed_at or "",
                item.question.id or 0,
            ),
            reverse=True,
        )
        return [item.question for item in rows]

    def _shuffle_seen_tier(
        self,
        items: list[_QuestionPriority],
        rng: random.Random,
    ) -> list[Question]:
        if not items:
            return []

        # Among non-failed seen items, prioritize lower rehearsal/mastery but
        # avoid a rigid static order.
        rows = sorted(
            items,
            key=lambda item: (
                item.review_count,
                item.mastery_score,
                item.question.id or 0,
            ),
        )
        return self._local_bucket_shuffle(rows, rng, bucket_size=4)

    def _shuffle_simple_tier(
        self,
        items: list[_QuestionPriority],
        rng: random.Random,
    ) -> list[Question]:
        if not items:
            return []
        rows = list(items)
        rng.shuffle(rows)
        return [item.question for item in rows]

    def _local_bucket_shuffle(
        self,
        items: list[_QuestionPriority],
        rng: random.Random,
        bucket_size: int,
    ) -> list[Question]:
        """Shuffle only inside small contiguous buckets.

        This preserves pedagogical priority while avoiding "always same exact
        sequence" monotony.
        """
        if not items:
            return []

        bucket_size = max(2, bucket_size)
        output: list[Question] = []
        for start in range(0, len(items), bucket_size):
            bucket = list(items[start : start + bucket_size])
            rng.shuffle(bucket)
            output.extend(item.question for item in bucket)
        return output

    def _avoid_immediate_first_repeat(
        self,
        ordered_questions: list[Question],
        *,
        context_key: str,
        first_tier_size: int,
    ) -> None:
        """Avoid repeating the same first question in back-to-back sessions."""
        if not ordered_questions:
            return

        first_id = ordered_questions[0].id
        previous_first = self._last_first_question_by_context.get(context_key)
        if first_id is not None and previous_first == first_id and first_tier_size > 1:
            for idx in range(1, min(first_tier_size, len(ordered_questions))):
                candidate_id = ordered_questions[idx].id
                if candidate_id is None or candidate_id == previous_first:
                    continue
                ordered_questions[0], ordered_questions[idx] = (
                    ordered_questions[idx],
                    ordered_questions[0],
                )
                break

        final_first = ordered_questions[0].id
        if final_first is not None:
            self._last_first_question_by_context[context_key] = final_first
