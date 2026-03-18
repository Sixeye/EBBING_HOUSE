"""Compatibility wrapper for ``QuestionSelectionService``.

Phase 4D.4 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.question_selection_service`)
stable during the transition.
"""

from core.services.question_selection_service import QuestionSelectionService

__all__ = ["QuestionSelectionService"]

