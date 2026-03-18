"""Compatibility shim for legacy `app.models.*` imports.

Phase 4A moved canonical domain models to `core.models`.
This package keeps historical imports working during the transition.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import core.models as _core_models
from core.models import *  # noqa: F401,F403 - deliberate compatibility re-export.

_THIS_DIR = Path(__file__).resolve().parent
_CORE_MODELS_DIR = _THIS_DIR.parents[1] / "core" / "models"

# Keep the local package directory first, then point module lookups
# to `core/models` so imports like `app.models.question` continue to work.
__path__ = [str(_THIS_DIR)]
if _CORE_MODELS_DIR.exists():
    __path__.append(str(_CORE_MODELS_DIR))

# Ensure `app.models.<module>` resolves to the exact same module object as
# `core.models.<module>`. This prevents duplicate class objects in memory
# (important for isinstance checks and type identity across layers).
_MODEL_MODULES = (
    "connect4_game",
    "csv_preview",
    "dashboard",
    "deck",
    "hangman_game",
    "maze_difficulty",
    "maze_game",
    "memory_garden",
    "profile",
    "profile_trophy",
    "question",
    "question_progress",
    "quiz_session",
    "run_history",
    "settings",
    "trophy",
)
for _module_name in _MODEL_MODULES:
    _core_module = importlib.import_module(f"core.models.{_module_name}")
    sys.modules.setdefault(f"{__name__}.{_module_name}", _core_module)

__all__ = getattr(_core_models, "__all__", [])
