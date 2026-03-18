"""Compatibility wrapper for legacy app.models.memory_garden imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.memory_garden.
"""

from core.models.memory_garden import *  # noqa: F401,F403
