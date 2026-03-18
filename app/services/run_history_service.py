"""Compatibility wrapper for ``RunHistoryService``.

Phase 4D.3 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.run_history_service`) stable
during the transition.
"""

from core.services.run_history_service import RunHistoryService

__all__ = ["RunHistoryService"]

