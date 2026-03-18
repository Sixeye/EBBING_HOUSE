"""Compatibility wrapper for ``SettingsService``.

Phase 4D.2 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.settings_service`) stable during
the transition.
"""

from core.services.settings_service import SettingsService

__all__ = ["SettingsService"]

