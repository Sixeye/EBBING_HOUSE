"""Domain models for the Memory Garden visual progression system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryGardenTree:
    """One deck-representative tree in the profile garden.

    The tree contains both raw learning metrics and precomputed visual buckets.
    This keeps rendering code simple and deterministic.
    """

    deck_id: int
    deck_name: str
    category: str | None
    tracked_questions: int
    mastered_questions: int
    weak_questions: int
    due_questions: int
    average_mastery: float
    trunk_blocks: int
    foliage_blocks: int
    accent_blocks: int
    health_state: str  # "lush" | "growing" | "fragile"


@dataclass
class MemoryGardenSnapshot:
    """Complete profile-scoped garden payload used by UI rendering."""

    profile_id: int | None
    profile_name: str | None
    trees: list[MemoryGardenTree] = field(default_factory=list)
    total_tracked_questions: int = 0
    total_due_questions: int = 0
    total_weak_questions: int = 0
    average_mastery_score: float = 0.0
    trophies_unlocked: int = 0
    mood_key: str = "memory_garden.mood.no_profile"

    @property
    def has_active_profile(self) -> bool:
        return self.profile_id is not None

    @property
    def has_growth(self) -> bool:
        return len(self.trees) > 0


__all__ = ["MemoryGardenTree", "MemoryGardenSnapshot"]
