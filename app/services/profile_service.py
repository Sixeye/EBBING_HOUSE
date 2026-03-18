"""Compatibility wrapper for ``ProfileService``.

Phase 4D.3 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.profile_service`) stable
during the transition.
"""

from core.services.profile_service import ProfileService

__all__ = ["ProfileService"]

