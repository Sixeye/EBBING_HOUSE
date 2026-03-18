"""Compatibility wrapper for legacy app.models.dashboard imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.dashboard.
"""

from core.models.dashboard import *  # noqa: F401,F403
