"""Portable user-data path helpers.

This module intentionally excludes desktop packaging concepts (`_MEIPASS`,
bundled assets, Qt resource loading). It only handles writable user paths
that remain relevant for desktop today and mobile/other runtimes later.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

from app.config.settings import APP_DATA_DIRNAME, DATABASE_FILENAME


def get_app_data_dir() -> Path:
    """Return an OS-appropriate writable directory for app user data."""
    system = platform.system().lower()

    if system == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    elif system == "windows":
        appdata = os.getenv("APPDATA")
        base_dir = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
    else:
        base_dir = Path.home() / ".local" / "share"

    data_dir = base_dir / APP_DATA_DIRNAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_database_path() -> Path:
    """Return the absolute path of the local SQLite file."""
    return get_app_data_dir() / DATABASE_FILENAME


def get_media_dir(*parts: str) -> Path:
    """Return the app-managed writable media directory.

    Authoring images are copied here so references survive source-file moves.
    """
    media_dir = get_app_data_dir() / "media"
    for part in parts:
        media_dir = media_dir / part
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def resolve_media_reference(reference: str | None) -> Path | None:
    """Resolve a persisted media reference to an absolute path."""
    if not reference:
        return None
    raw = Path(reference)
    if raw.is_absolute():
        return raw
    return get_app_data_dir() / raw


__all__ = [
    "get_app_data_dir",
    "get_database_path",
    "get_media_dir",
    "resolve_media_reference",
]

