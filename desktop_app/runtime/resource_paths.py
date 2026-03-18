"""Desktop packaged-resource path helpers.

These helpers stay desktop-specific because they depend on PyInstaller-style
runtime extraction (`sys._MEIPASS`) and bundled read-only asset layout.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

# This module lives in `desktop_app/runtime/`, so parents[2] reaches
# the repository root in development.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_bundled_runtime() -> bool:
    """Return True when running from a frozen bundle (PyInstaller-style)."""
    return bool(getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None))


@lru_cache(maxsize=1)
def get_resource_root() -> Path:
    """Return the root directory containing bundled read-only resources."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return PROJECT_ROOT


def get_resource_path(*parts: str) -> Path:
    """Build a path inside the runtime resource tree."""
    return get_resource_root().joinpath(*parts)


def find_resource_path(*relative_candidates: str | Path) -> Path | None:
    """Return the first existing bundled resource path from candidates."""
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
    """Return bundled locale directory."""
    return get_resource_path("app", "i18n", "locales")


def get_app_asset_dir(*parts: str) -> Path:
    """Return a bundled path under `app/assets`."""
    return get_resource_path("app", "assets", *parts)


def get_project_asset_dir(*parts: str) -> Path:
    """Return a bundled path under top-level `assets`."""
    return get_resource_path("assets", *parts)


__all__ = [
    "PROJECT_ROOT",
    "is_bundled_runtime",
    "get_resource_root",
    "get_resource_path",
    "find_resource_path",
    "get_locales_dir",
    "get_app_asset_dir",
    "get_project_asset_dir",
]

