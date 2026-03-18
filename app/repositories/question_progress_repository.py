"""Compatibility wrapper for legacy app.repositories.question_progress_repository imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in
core.persistence.repositories.question_progress_repository.
"""

from core.persistence.repositories.question_progress_repository import *  # noqa: F401,F403
