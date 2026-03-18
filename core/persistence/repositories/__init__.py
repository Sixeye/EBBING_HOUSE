"""Repository classes for persistence access."""

from core.persistence.repositories.deck_repository import DeckRepository
from core.persistence.repositories.profile_repository import ProfileRepository
from core.persistence.repositories.question_progress_repository import QuestionProgressRepository
from core.persistence.repositories.question_repository import QuestionRepository
from core.persistence.repositories.run_history_repository import RunHistoryRepository
from core.persistence.repositories.settings_repository import SettingsRepository
from core.persistence.repositories.trophy_repository import TrophyRepository
from core.persistence.repositories.profile_trophy_repository import ProfileTrophyRepository

__all__ = [
    "DeckRepository",
    "ProfileRepository",
    "QuestionProgressRepository",
    "QuestionRepository",
    "RunHistoryRepository",
    "SettingsRepository",
    "TrophyRepository",
    "ProfileTrophyRepository",
]
