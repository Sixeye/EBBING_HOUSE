"""Compatibility shim for legacy `app.db.*` imports.

Phase 4B moved canonical SQLite modules to `core.persistence.sqlite`.
This package keeps historical imports functional during the transition.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from core.persistence.sqlite import DatabaseManager, initialize_schema

_THIS_DIR = Path(__file__).resolve().parent
_CORE_SQLITE_DIR = _THIS_DIR.parents[1] / "core" / "persistence" / "sqlite"

# Keep local package path, then append canonical sqlite path so
# `from app.db.database import DatabaseManager` continues to resolve.
__path__ = [str(_THIS_DIR)]
if _CORE_SQLITE_DIR.exists():
    __path__.append(str(_CORE_SQLITE_DIR))

# Prevent duplicate module objects across old/new namespaces.
for _module_name in ("database", "schema"):
    _core_module = importlib.import_module(f"core.persistence.sqlite.{_module_name}")
    sys.modules.setdefault(f"{__name__}.{_module_name}", _core_module)

__all__ = ["DatabaseManager", "initialize_schema"]

