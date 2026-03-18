"""Compatibility wrapper for legacy app.repositories.settings_repository imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in
core.persistence.repositories.settings_repository.
"""

from core.persistence.repositories.settings_repository import *  # noqa: F401,F403
