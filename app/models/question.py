"""Compatibility wrapper for legacy app.models.question imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.question.
"""

from core.models.question import *  # noqa: F401,F403
