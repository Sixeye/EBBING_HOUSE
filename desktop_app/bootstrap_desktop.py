"""Desktop composition root and dependency wiring.

Phase 1 intent:
- isolate desktop bootstrap outside the future `core/` package
- keep runtime behavior identical by preserving existing service wiring
- avoid touching domain/service/repository modules yet
"""

from __future__ import annotations

from app.config.settings import DEFAULT_LOCALE
from app.core.paths import get_database_path, get_locales_dir
from app.db.database import DatabaseManager
from app.i18n.translator import Translator
from app.repositories.deck_repository import DeckRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.profile_trophy_repository import ProfileTrophyRepository
from app.repositories.question_progress_repository import QuestionProgressRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.run_history_repository import RunHistoryRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.trophy_repository import TrophyRepository
from app.services.csv_import_service import CsvImportService
from app.services.csv_validation_service import CsvValidationService
from app.services.connect4_session_service import Connect4SessionService
from app.services.dashboard_service import DashboardService
from app.services.deck_service import DeckService
from app.services.hangman_session_service import HangmanSessionService
from app.services.maze_generation_service import MazeGenerationService
from app.services.maze_session_service import MazeSessionService
from app.services.memory_garden_service import MemoryGardenService
from app.services.profile_service import ProfileService
from app.services.question_authoring_service import QuestionAuthoringService
from app.services.question_import_service import QuestionImportService
from app.services.question_selection_service import QuestionSelectionService
from app.services.quiz_session_service import QuizSessionService
from app.services.run_history_service import RunHistoryService
from app.services.settings_service import SettingsService
from app.services.spaced_repetition_service import SpacedRepetitionService
from app.services.trophy_service import TrophyService
from app.ui.main_window import MainWindow


class DesktopAppBootstrap:
    """Desktop dependency container kept compatible with current behavior."""

    def __init__(self) -> None:
        self.database = DatabaseManager(get_database_path())

        # Repositories isolate SQL and row mapping from the UI layer.
        self.profile_repository = ProfileRepository(self.database)
        self.deck_repository = DeckRepository(self.database)
        self.question_repository = QuestionRepository(self.database)
        self.question_progress_repository = QuestionProgressRepository(self.database)
        self.settings_repository = SettingsRepository(self.database)
        self.trophy_repository = TrophyRepository(self.database)
        self.profile_trophy_repository = ProfileTrophyRepository(self.database)
        self.run_history_repository = RunHistoryRepository(self.database)

        # Services are intentionally thin for now and ready for future rules.
        self.profile_service = ProfileService(
            repository=self.profile_repository,
            settings_repository=self.settings_repository,
        )
        self.deck_service = DeckService(self.deck_repository)
        self.settings_service = SettingsService(self.settings_repository)
        self.csv_import_service = CsvImportService()
        self.csv_validation_service = CsvValidationService()
        self.question_import_service = QuestionImportService(
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
        )
        self.question_selection_service = QuestionSelectionService(
            progress_repository=self.question_progress_repository,
        )
        self.question_authoring_service = QuestionAuthoringService(
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
        )
        self.quiz_session_service = QuizSessionService(
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
            question_selection_service=self.question_selection_service,
        )
        self.hangman_session_service = HangmanSessionService(
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
            question_selection_service=self.question_selection_service,
            default_max_wrong_answers=6,
        )
        self.connect4_session_service = Connect4SessionService(
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
            question_selection_service=self.question_selection_service,
        )
        self.maze_generation_service = MazeGenerationService(width=17, height=13)
        self.maze_session_service = MazeSessionService(
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
            question_selection_service=self.question_selection_service,
            maze_generation_service=self.maze_generation_service,
        )
        self.memory_garden_service = MemoryGardenService(self.database)
        self.spaced_repetition_service = SpacedRepetitionService(
            profile_repository=self.profile_repository,
            deck_repository=self.deck_repository,
            question_repository=self.question_repository,
            progress_repository=self.question_progress_repository,
        )
        self.trophy_service = TrophyService(
            trophy_repository=self.trophy_repository,
            profile_trophy_repository=self.profile_trophy_repository,
            progress_repository=self.question_progress_repository,
        )
        self.run_history_service = RunHistoryService(self.run_history_repository)

        self.translator = Translator(locales_dir=get_locales_dir(), default_locale=DEFAULT_LOCALE)
        self.dashboard_service = DashboardService(self.database)

    def initialize(self) -> None:
        """Create DB schema and load persisted app-level settings."""
        self.database.initialize()
        self.settings_repository.ensure_defaults()
        self.trophy_service.ensure_builtins()

        # Apply saved locale so the UI opens in the user's preferred language.
        locale = self.settings_repository.get_settings().app_language or DEFAULT_LOCALE
        self.translator.set_locale(locale)

    def create_main_window(self) -> MainWindow:
        """Build the main window with already initialized dependencies."""
        return MainWindow(
            translator=self.translator,
            dashboard_service=self.dashboard_service,
            settings_service=self.settings_service,
            deck_service=self.deck_service,
            csv_import_service=self.csv_import_service,
            csv_validation_service=self.csv_validation_service,
            question_import_service=self.question_import_service,
            question_authoring_service=self.question_authoring_service,
            quiz_session_service=self.quiz_session_service,
            hangman_session_service=self.hangman_session_service,
            connect4_session_service=self.connect4_session_service,
            maze_session_service=self.maze_session_service,
            memory_garden_service=self.memory_garden_service,
            profile_service=self.profile_service,
            spaced_repetition_service=self.spaced_repetition_service,
            trophy_service=self.trophy_service,
            run_history_service=self.run_history_service,
        )


# Transitional alias keeps naming stable for older call sites while
# phase-1 introduces the new desktop-specific module path.
AppBootstrap = DesktopAppBootstrap


__all__ = ["DesktopAppBootstrap", "AppBootstrap"]
