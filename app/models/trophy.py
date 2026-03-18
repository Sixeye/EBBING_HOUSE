"""Compatibility wrapper for legacy app.models.trophy imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.trophy.
"""

from core.models.trophy import *  # noqa: F401,F403
