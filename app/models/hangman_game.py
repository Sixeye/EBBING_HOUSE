"""Compatibility wrapper for legacy app.models.hangman_game imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.hangman_game.
"""

from core.models.hangman_game import *  # noqa: F401,F403
