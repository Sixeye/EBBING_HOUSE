"""Compatibility wrapper for legacy app.repositories.profile_trophy_repository imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in
core.persistence.repositories.profile_trophy_repository.
"""

from core.persistence.repositories.profile_trophy_repository import *  # noqa: F401,F403
