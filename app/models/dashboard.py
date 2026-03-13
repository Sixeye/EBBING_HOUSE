"""Data structures used by the dashboard UI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DueDeckStat:
    """Small DTO for top decks that currently need attention."""

    deck_id: int
    deck_name: str
    due_count: int


@dataclass
class DashboardMetrics:
    """Snapshot of key progress indicators displayed on the home page."""

    active_profile_id: int | None
    active_profile_name: str | None
    due_today_count: int
    tracked_questions_count: int
    average_mastery_score: float
    mastered_questions_count: int
    weak_questions_count: int
    total_reviews_count: int
    reviewed_today_count: int
    encouragement_key: str
    top_due_decks: list[DueDeckStat] = field(default_factory=list)
