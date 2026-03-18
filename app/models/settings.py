"""Compatibility wrapper for legacy app.models.settings imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.settings.
"""

from core.models.settings import *  # noqa: F401,F403
