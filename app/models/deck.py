"""Compatibility wrapper for legacy app.models.deck imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.deck.
"""

from core.models.deck import *  # noqa: F401,F403
