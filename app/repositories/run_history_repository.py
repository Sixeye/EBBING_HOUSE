"""Compatibility wrapper for legacy app.repositories.run_history_repository imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in
core.persistence.repositories.run_history_repository.
"""

from core.persistence.repositories.run_history_repository import *  # noqa: F401,F403
