"""Compatibility wrapper for legacy app.repositories.deck_repository imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in
core.persistence.repositories.deck_repository.
"""

from core.persistence.repositories.deck_repository import *  # noqa: F401,F403
