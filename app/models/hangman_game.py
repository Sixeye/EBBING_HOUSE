"""Domain models for the Hangman mini-game session state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HangmanGameState:
    """Mutable state for one hangman challenge.

    The challenge wraps quiz questions but adds a reversible danger meter:
    - incorrect answer -> danger +1
    - correct answer -> danger -1 (down to 0)
    """

    deck_id: int
    deck_name: str
    max_wrong_answers: int
    total_questions_pool: int
    profile_id: int | None = None
    started_at: str | None = None
    danger_steps: int = 0
    finished: bool = False
    did_fail: bool = False
    did_save: bool = False

    @property
    def wrong_answers_remaining(self) -> int:
        return max(0, self.max_wrong_answers - self.danger_steps)

    @property
    def wrong_answers_used(self) -> int:
        """Compatibility alias used by existing UI labels.

        In the new ruleset this value represents *current danger* steps.
        """
        return self.danger_steps


@dataclass
class HangmanGameSummary:
    """Final hangman challenge summary shown at end of session."""

    deck_name: str
    total_questions_pool: int
    answered_questions: int
    correct_answers_count: int
    wrong_answers_count: int
    score_on_20: float
    score_on_100: float
    percentage: float
    average_response_time_seconds: float | None
    wrong_answers_used: int
    wrong_answers_remaining: int
    did_save: bool
    did_fail: bool


__all__ = ["HangmanGameState", "HangmanGameSummary"]
