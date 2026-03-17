"""Transitional compatibility shim for desktop bootstrap.

Phase 1 moves the desktop composition root to `desktop_app/` but keeps
the historical import path (`app.core.bootstrap.AppBootstrap`) working.
This avoids a big-bang import rewrite before phase 2 extraction work.
"""

from desktop_app.bootstrap_desktop import AppBootstrap, DesktopAppBootstrap

__all__ = ["AppBootstrap", "DesktopAppBootstrap"]

