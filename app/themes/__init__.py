"""Compatibility shim for legacy `app.themes.*` imports.

Phase 3A moved the canonical Qt theme modules to `desktop_app/themes`.
This shim preserves existing imports until phase 3B import cleanup.
"""

from __future__ import annotations

from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_DESKTOP_THEMES_DIR = _THIS_DIR.parents[1] / "desktop_app" / "themes"

__path__ = [str(_THIS_DIR)]
if _DESKTOP_THEMES_DIR.exists():
    __path__.append(str(_DESKTOP_THEMES_DIR))

