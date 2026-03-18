"""Compatibility wrapper for legacy app.models.csv_preview imports.

This concrete module helps PyInstaller resolve legacy submodule imports in
packaged runtime while canonical implementation lives in core.models.csv_preview.
"""

from core.models.csv_preview import *  # noqa: F401,F403
