"""Compatibility shim for legacy `app.repositories.*` imports.

Phase 4C moved canonical repositories to `core.persistence.repositories`.
This package keeps old imports functional during incremental migration.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from core.persistence.repositories import (
    DeckRepository,
    ProfileRepository,
    ProfileTrophyRepository,
    QuestionProgressRepository,
    QuestionRepository,
    RunHistoryRepository,
    SettingsRepository,
    TrophyRepository,
)

_THIS_DIR = Path(__file__).resolve().parent
_CORE_REPOSITORIES_DIR = _THIS_DIR.parents[1] / "core" / "persistence" / "repositories"

# Allow legacy submodule imports (`app.repositories.deck_repository`) to resolve.
__path__ = [str(_THIS_DIR)]
if _CORE_REPOSITORIES_DIR.exists():
    __path__.append(str(_CORE_REPOSITORIES_DIR))

# Keep module identity stable across old and new namespaces.
_REPOSITORY_MODULES = (
    "deck_repository",
    "profile_repository",
    "profile_trophy_repository",
    "question_progress_repository",
    "question_repository",
    "run_history_repository",
    "settings_repository",
    "trophy_repository",
)
for _module_name in _REPOSITORY_MODULES:
    _core_module = importlib.import_module(f"core.persistence.repositories.{_module_name}")
    sys.modules.setdefault(f"{__name__}.{_module_name}", _core_module)

__all__ = [
    "DeckRepository",
    "ProfileRepository",
    "ProfileTrophyRepository",
    "QuestionProgressRepository",
    "QuestionRepository",
    "RunHistoryRepository",
    "SettingsRepository",
    "TrophyRepository",
]

