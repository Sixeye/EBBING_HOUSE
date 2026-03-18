"""Compatibility wrapper for legacy app.models.quiz_session imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.quiz_session.
"""

from core.models.quiz_session import *  # noqa: F401,F403
