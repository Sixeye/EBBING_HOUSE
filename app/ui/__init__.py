"""Compatibility shim for legacy `app.ui.*` imports.

Phase 3A moved the real desktop UI package to `desktop_app/ui`.
We keep this shim so existing imports like `app.ui.main_window` continue
to resolve during the transition.
"""

from __future__ import annotations

from pathlib import Path

# Keep this directory on the package path first (in case transitional helper
# modules are added), then append the new canonical desktop UI location.
_THIS_DIR = Path(__file__).resolve().parent
_DESKTOP_UI_DIR = _THIS_DIR.parents[1] / "desktop_app" / "ui"

__path__ = [str(_THIS_DIR)]
if _DESKTOP_UI_DIR.exists():
    __path__.append(str(_DESKTOP_UI_DIR))

