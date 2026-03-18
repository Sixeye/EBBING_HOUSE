"""Compatibility wrapper for legacy ``app.db.database`` imports.

Why this file exists:
- During refactor phase 4B, canonical SQLite code moved to
  ``core.persistence.sqlite``.
- A dynamic alias in ``app/db/__init__.py`` keeps source-mode imports working.
- PyInstaller static analysis is stricter and may not resolve dynamic alias-only
  submodules reliably in packaged runtimes.

This explicit wrapper gives PyInstaller a concrete module to collect, while
preserving the old import path used by desktop bootstrap code.
"""

from core.persistence.sqlite.database import DatabaseManager

__all__ = ["DatabaseManager"]

