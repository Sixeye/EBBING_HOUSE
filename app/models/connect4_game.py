"""Compatibility wrapper for legacy app.models.connect4_game imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.connect4_game.
"""

from core.models.connect4_game import *  # noqa: F401,F403
