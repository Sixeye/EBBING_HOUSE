"""Compatibility wrapper for legacy app.models.maze_difficulty imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.maze_difficulty.
"""

from core.models.maze_difficulty import *  # noqa: F401,F403
