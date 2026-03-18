"""Compatibility wrapper for legacy app.models.maze_game imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.maze_game.
"""

from core.models.maze_game import *  # noqa: F401,F403
