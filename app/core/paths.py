"""Cross-platform path helpers.

This module deliberately separates two concerns:
- writable user data (SQLite, imported media)
- read-only bundled resources (images, audio, locales)

Naive `Path(__file__)` usage often works in development but breaks after a
PyInstaller build, because bundled files are extracted under `sys._MEIPASS`
instead of living next to the Python modules. Centralizing that logic here
keeps the rest of the app packaging-safe and easier to reason about.
"""

from __future__ import annotations

import os
import platform
import sys
from functools import lru_cache
from pathlib import Path

from app.config.settings import APP_DATA_DIRNAME, DATABASE_FILENAME

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_bundled_runtime() -> bool:
    """Return True when running from a frozen bundle (PyInstaller-style)."""
    return bool(getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None))


@lru_cache(maxsize=1)
def get_resource_root() -> Path:
    """Return the root directory containing packaged read-only resources.

    - In development: the project root
    - In a PyInstaller bundle: the extraction directory pointed to by `_MEIPASS`
    """
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return PROJECT_ROOT


def get_resource_path(*parts: str) -> Path:
    """Build a path inside the runtime resource tree."""
    return get_resource_root().joinpath(*parts)


def find_resource_path(*relative_candidates: str | Path) -> Path | None:
    """Return the first existing bundled resource path from candidate paths.

    Candidates are written relative to the runtime resource root so the same
    code works in:
    - local development
    - PyInstaller one-folder builds
    - PyInstaller one-file builds after extraction
    """
    seen: set[Path] = set()
    for candidate in relative_candidates:
        raw = Path(candidate)
        path = raw if raw.is_absolute() else get_resource_path(*raw.parts)
        try:
            dedupe_key = path.resolve()
        except OSError:
            dedupe_key = path
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        if path.exists():
            return path
    return None


def get_locales_dir() -> Path:
    """Return bundled locale directory.

    Locale JSON files are read-only resources and must therefore come from the
    runtime resource tree, not the user data directory.
    """
    return get_resource_path("app", "i18n", "locales")


def get_app_asset_dir(*parts: str) -> Path:
    """Return a bundled path under `app/assets`.

    This is where internal art/audio shipped with the application lives.
    """
    return get_resource_path("app", "assets", *parts)


def get_project_asset_dir(*parts: str) -> Path:
    """Return a bundled path under top-level `assets`.

    We keep this helper because branding currently uses the canonical user-facing
    location `assets/images/EBBING_HOUSE_APP.png`.
    """
    return get_resource_path("assets", *parts)


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


__all__ = [
    "PROJECT_ROOT",
    "is_bundled_runtime",
    "get_resource_root",
    "get_resource_path",
    "find_resource_path",
    "get_locales_dir",
    "get_app_asset_dir",
    "get_project_asset_dir",
    "get_app_data_dir",
    "get_database_path",
    "get_media_dir",
    "resolve_media_reference",
]
