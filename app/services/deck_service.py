"""Compatibility wrapper for ``DeckService``.

Phase 4D.2 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.deck_service`) stable during
the transition.
"""

from core.services.deck_service import DeckService

__all__ = ["DeckService"]

