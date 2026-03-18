"""Compatibility wrapper for ``QuestionImportService``.

Phase 4D.2 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.question_import_service`) stable
during the transition.
"""

from core.services.question_import_service import QuestionImportService

__all__ = ["QuestionImportService"]

