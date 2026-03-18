"""Compatibility wrapper for legacy app.models.run_history imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.run_history.
"""

from core.models.run_history import *  # noqa: F401,F403
