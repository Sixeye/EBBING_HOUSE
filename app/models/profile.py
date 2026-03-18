"""Compatibility wrapper for legacy app.models.profile imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.profile.
"""

from core.models.profile import *  # noqa: F401,F403
