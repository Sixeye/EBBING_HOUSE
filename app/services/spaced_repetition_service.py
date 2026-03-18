"""Compatibility wrapper for ``SpacedRepetitionService``.

Phase 4D.5 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.spaced_repetition_service`)
stable during the transition.
"""

from core.services.spaced_repetition_service import SpacedRepetitionService

__all__ = ["SpacedRepetitionService"]

