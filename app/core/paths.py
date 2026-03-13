"""Cross-platform path helpers."""

from __future__ import annotations

import os
import platform
from pathlib import Path

from app.config.settings import APP_DATA_DIRNAME, DATABASE_FILENAME


def get_app_data_dir() -> Path:
    """Return an OS-appropriate directory for local application data."""
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
    """Return the app-managed media directory.

    We store authoring images under app data, not user absolute paths only,
    so content remains portable and resilient when files move.
    """
    media_dir = get_app_data_dir() / "media"
    for part in parts:
        media_dir = media_dir / part
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def resolve_media_reference(reference: str | None) -> Path | None:
    """Resolve a persisted media reference to an absolute path.

    - absolute refs are returned as-is
    - relative refs are resolved under the app data directory
    """
    if not reference:
        return None
    raw = Path(reference)
    if raw.is_absolute():
        return raw
    return get_app_data_dir() / raw
