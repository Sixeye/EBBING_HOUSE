"""Compatibility wrapper for legacy app.models.question_progress imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.question_progress.
"""

from core.models.question_progress import *  # noqa: F401,F403
