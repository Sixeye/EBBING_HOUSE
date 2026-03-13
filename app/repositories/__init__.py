"""Repository classes for persistence access."""

from app.repositories.deck_repository import DeckRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.question_progress_repository import QuestionProgressRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.run_history_repository import RunHistoryRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trophy_repository import TrophyRepository
from app.repositories.profile_trophy_repository import ProfileTrophyRepository

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
