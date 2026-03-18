"""Compatibility wrapper for legacy app.models.profile_trophy imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.profile_trophy.
"""

from core.models.profile_trophy import *  # noqa: F401,F403
