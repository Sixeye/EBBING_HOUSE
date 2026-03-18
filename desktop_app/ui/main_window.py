"""Main application window for EBBING_HOUSE."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.i18n.translator import Translator
from app.services.csv_import_service import CsvImportService
from app.services.csv_validation_service import CsvValidationService
from app.services.connect4_session_service import Connect4SessionService
from app.services.dashboard_service import DashboardService
from app.services.deck_service import DeckService
from app.services.hangman_session_service import HangmanSessionService
from app.services.maze_session_service import MazeSessionService
from app.services.memory_garden_service import MemoryGardenService
from app.services.profile_service import ProfileService
from app.services.question_authoring_service import QuestionAuthoringService
from app.services.question_import_service import QuestionImportService
from app.services.quiz_session_service import QuizSessionService
from app.services.run_history_service import RunHistoryService
from app.services.settings_service import SettingsService
from app.services.spaced_repetition_service import SpacedRepetitionService
from app.services.trophy_service import TrophyService
from desktop_app.themes.branding import build_window_icon
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.pages.connect4_page import Connect4Page
from desktop_app.ui.pages.dashboard_page import DashboardPage
from desktop_app.ui.pages.hangman_page import HangmanPage
from desktop_app.ui.pages.history_page import HistoryPage
from desktop_app.ui.pages.import_csv_page import ImportCsvPage
from desktop_app.ui.pages.memory_garden_page import MemoryGardenPage
from desktop_app.ui.pages.maze_page import MazePage
from desktop_app.ui.pages.profiles_page import ProfilesPage
from desktop_app.ui.pages.review_page import ReviewPage
from desktop_app.ui.pages.settings_page import SettingsPage
from desktop_app.ui.pages.support_page import SupportPage
from desktop_app.ui.pages.trophies_page import TrophiesPage
from desktop_app.ui.widgets.animated_stack import AnimatedStackedWidget
from desktop_app.ui.widgets.motion import apply_standard_micro_interactions
from desktop_app.ui.widgets.background_music_controller import BackgroundMusicController
from desktop_app.ui.widgets.sidebar import SidebarWidget
from desktop_app.ui.widgets.toast import ToastManager


class MainWindow(QMainWindow):
    """Root window hosting sidebar navigation and page stack."""

    def __init__(
        self,
        translator: Translator,
        dashboard_service: DashboardService,
        settings_service: SettingsService,
        deck_service: DeckService,
        csv_import_service: CsvImportService,
        csv_validation_service: CsvValidationService,
        question_import_service: QuestionImportService,
        question_authoring_service: QuestionAuthoringService,
        quiz_session_service: QuizSessionService,
        hangman_session_service: HangmanSessionService,
        connect4_session_service: Connect4SessionService,
        maze_session_service: MazeSessionService,
        memory_garden_service: MemoryGardenService,
        profile_service: ProfileService,
        spaced_repetition_service: SpacedRepetitionService,
        trophy_service: TrophyService,
        run_history_service: RunHistoryService,
    ) -> None:
        super().__init__()

        self.translator = translator
        self.dashboard_service = dashboard_service
        self.settings_service = settings_service
        self.deck_service = deck_service
        self.csv_import_service = csv_import_service
        self.csv_validation_service = csv_validation_service
        self.question_import_service = question_import_service
        self.question_authoring_service = question_authoring_service
        self.quiz_session_service = quiz_session_service
        self.hangman_session_service = hangman_session_service
        self.connect4_session_service = connect4_session_service
        self.maze_session_service = maze_session_service
        self.memory_garden_service = memory_garden_service
        self.profile_service = profile_service
        self.spaced_repetition_service = spaced_repetition_service
        self.trophy_service = trophy_service
        self.run_history_service = run_history_service

        # Keep a comfortable default while allowing smaller desktop windows.
        self.setMinimumSize(920, 620)
        self.resize(1280, 820)
        self.setWindowIcon(build_window_icon())

        self._pages: Dict[str, BasePage] = {}
        self._toast_manager: ToastManager | None = None
        self._background_music: BackgroundMusicController | None = None

        self._build_ui()
        self._connect_signals()
        self._on_language_changed(self.translator.locale)
        self._navigate_to("dashboard")

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = SidebarWidget(self.translator)
        self.stack = AnimatedStackedWidget()

        dashboard_page = DashboardPage(
            self.translator,
            self.dashboard_service,
            self.run_history_service,
        )
        dashboard_page.start_review_requested.connect(self._open_review_from_dashboard)
        dashboard_page.due_deck_review_requested.connect(self._open_review_for_due_deck)
        dashboard_page.open_memory_garden_requested.connect(self._open_memory_garden)
        dashboard_page.open_support_requested.connect(self._open_support_page)
        dashboard_page.open_history_requested.connect(self._open_history_page)

        profiles_page = ProfilesPage(
            translator=self.translator,
            profile_service=self.profile_service,
            trophy_service=self.trophy_service,
        )
        profiles_page.profile_state_changed.connect(self._on_profiles_changed)

        memory_garden_page = MemoryGardenPage(
            translator=self.translator,
            profile_service=self.profile_service,
            memory_garden_service=self.memory_garden_service,
        )
        memory_garden_page.open_review_due_requested.connect(self._open_review_due_from_garden)
        memory_garden_page.open_review_due_for_deck_requested.connect(self._open_review_for_due_deck)

        review_page = ReviewPage(
            translator=self.translator,
            deck_service=self.deck_service,
            profile_service=self.profile_service,
            quiz_session_service=self.quiz_session_service,
            spaced_repetition_service=self.spaced_repetition_service,
            trophy_service=self.trophy_service,
        )

        settings_page = SettingsPage(
            translator=self.translator,
            settings_service=self.settings_service,
        )
        settings_page.language_change_requested.connect(self._set_locale)
        settings_page.sounds_changed.connect(self._on_sounds_setting_changed)

        import_page = ImportCsvPage(
            translator=self.translator,
            csv_import_service=self.csv_import_service,
            csv_validation_service=self.csv_validation_service,
            question_import_service=self.question_import_service,
            question_authoring_service=self.question_authoring_service,
            deck_service=self.deck_service,
            profile_service=self.profile_service,
            trophy_service=self.trophy_service,
        )

        # Keep all pages in one map so navigation can stay key-driven and scalable.
        self._pages = {
            "dashboard": dashboard_page,
            "memory_garden": memory_garden_page,
            "profiles": profiles_page,
            # Three navigation keys share one page instance so CRUD logic stays
            # centralized while becoming clearly discoverable in the sidebar.
            "decks": import_page,
            "questions": import_page,
            "import_csv": import_page,
            "review": review_page,
            "hangman": HangmanPage(
                translator=self.translator,
                deck_service=self.deck_service,
                profile_service=self.profile_service,
                settings_service=self.settings_service,
                hangman_session_service=self.hangman_session_service,
                trophy_service=self.trophy_service,
                run_history_service=self.run_history_service,
            ),
            "connect4": Connect4Page(
                translator=self.translator,
                deck_service=self.deck_service,
                profile_service=self.profile_service,
                settings_service=self.settings_service,
                connect4_session_service=self.connect4_session_service,
                run_history_service=self.run_history_service,
            ),
            "maze": MazePage(
                translator=self.translator,
                deck_service=self.deck_service,
                profile_service=self.profile_service,
                settings_service=self.settings_service,
                maze_session_service=self.maze_session_service,
                trophy_service=self.trophy_service,
                run_history_service=self.run_history_service,
            ),
            "history": HistoryPage(
                translator=self.translator,
                profile_service=self.profile_service,
                run_history_service=self.run_history_service,
            ),
            "trophies": TrophiesPage(
                translator=self.translator,
                profile_service=self.profile_service,
                trophy_service=self.trophy_service,
            ),
            "settings": settings_page,
            "support": SupportPage(self.translator),
        }

        added_widgets: set[int] = set()
        for page in self._pages.values():
            # Alias keys ("decks"/"questions"/"import_csv") may reference the
            # same QWidget; stack should contain each page widget only once.
            page_id = id(page)
            if page_id in added_widgets:
                continue
            self.stack.addWidget(page)
            added_widgets.add(page_id)

        # Content host adds breathing room around pages and keeps the main frame clean.
        content_host = QWidget()
        content_host.setObjectName("ContentHost")
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(0)

        # A global page scroll area improves responsiveness on smaller windows.
        # We keep horizontal scrolling disabled to preserve layout coherence.
        self._page_scroll = QScrollArea()
        self._page_scroll.setObjectName("PageScrollArea")
        self._page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._page_scroll.setWidgetResizable(True)
        self._page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._page_scroll.setWidget(self.stack)
        content_layout.addWidget(self._page_scroll)

        layout.addWidget(self.sidebar)
        layout.addWidget(content_host, 1)

        # Global non-blocking toast layer. We parent it to the content host so
        # notifications stay aligned with page content (not above the sidebar).
        self._toast_manager = ToastManager(content_host)

        # Apply one centralized micro-interaction pass so all major action
        # controls get the same subtle motion language.
        apply_standard_micro_interactions(root)

        # Background music is optional and lightweight. If the track or backend
        # is unavailable, controller stays inert and UI shows a disabled speaker.
        self._background_music = BackgroundMusicController(self, self.settings_service)
        self._background_music.apply_settings()
        self._sync_audio_controls()

    def _connect_signals(self) -> None:
        self.sidebar.navigation_requested.connect(self._navigate_to)
        self.sidebar.locale_changed.connect(self._set_locale)
        self.sidebar.audio_toggle_requested.connect(self._on_audio_toggle_requested)
        self.translator.language_changed.connect(self._on_language_changed)

    def _navigate_to(self, page_key: str) -> None:
        page = self._pages.get(page_key)
        if not page:
            return

        self.sidebar.set_active_page(page_key)
        self.stack.setCurrentWidget(page)

        if isinstance(page, ImportCsvPage):
            if page_key == "decks":
                page.set_navigation_context("decks")
            elif page_key == "questions":
                page.set_navigation_context("questions")
            else:
                page.set_navigation_context("import")
            page.refresh_content_sources()

        # Keep high-signal pages fresh each time they become visible.
        if isinstance(page, DashboardPage):
            page.refresh_metrics()
        elif isinstance(page, MemoryGardenPage):
            page.refresh_garden()
        elif isinstance(page, HangmanPage):
            page.refresh_sources()
        elif isinstance(page, Connect4Page):
            page.refresh_sources()
        elif isinstance(page, MazePage):
            page.refresh_sources()
        elif isinstance(page, TrophiesPage):
            page.refresh_content()
        elif isinstance(page, HistoryPage):
            page.refresh_runs()
        elif isinstance(page, SettingsPage):
            page.refresh_settings()

        self._sync_stack_height_to_active_page()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_stack_height_to_active_page()

    def _sync_stack_height_to_active_page(self) -> None:
        """Keep global page-scroll height aligned with the visible page.

        Root cause fixed:
        the shared stacked widget could keep the previous tall page height
        (content authoring/import), which made game pages look vertically
        stretched even though their own layouts were compact.

        We explicitly size the stack to the active page hint or viewport height
        (whichever is larger) so:
        - long pages still scroll
        - compact game pages no longer inherit huge hidden-page height
        """
        if not hasattr(self, "_page_scroll"):
            return

        current_page = self.stack.currentWidget()
        if current_page is None:
            return

        viewport = self._page_scroll.viewport().size()
        if viewport.height() <= 0 or viewport.width() <= 0:
            return

        page_hint_height = max(1, current_page.sizeHint().height())
        target_height = max(viewport.height(), page_hint_height)

        self.stack.setMinimumHeight(target_height)
        self.stack.setMaximumHeight(target_height)
        self.stack.resize(viewport.width(), target_height)

    def _open_memory_garden(self) -> None:
        self._navigate_to("memory_garden")

    def _open_support_page(self) -> None:
        self._navigate_to("support")

    def _open_history_page(self) -> None:
        self._navigate_to("history")

    def _open_review_due_from_garden(self) -> None:
        metrics = self.dashboard_service.get_metrics()
        if metrics.active_profile_id is None:
            self._navigate_to("profiles")
            return

        self._navigate_to("review")
        review_page = self._pages.get("review")
        if isinstance(review_page, ReviewPage):
            review_page.apply_active_profile_defaults(prefer_due_mode=True)

    def _open_review_from_dashboard(self) -> None:
        metrics = self.dashboard_service.get_metrics()

        # CTA behavior is state-aware:
        # - no active profile -> Profiles page
        # - due queue exists -> Review in due mode
        # - no due queue -> Review in practice-ready mode
        if metrics.active_profile_id is None:
            self._navigate_to("profiles")
            return

        self._navigate_to("review")
        review_page = self._pages.get("review")
        if isinstance(review_page, ReviewPage):
            review_page.apply_active_profile_defaults(prefer_due_mode=metrics.due_today_count > 0)

    def _open_review_for_due_deck(self, deck_id: int) -> None:
        """Open review prefilled for a deck-focused due launch.

        This route is shared by both Dashboard urgency actions and Memory
        Garden tree actions so deck-targeted due navigation stays consistent.
        """
        active_profile_id = self.profile_service.get_active_profile_id()
        if active_profile_id is None:
            self._navigate_to("profiles")
            return

        self._navigate_to("review")
        review_page = self._pages.get("review")
        if isinstance(review_page, ReviewPage):
            # Always use the current global active profile as source of truth.
            review_page.apply_due_mode_defaults(profile_id=active_profile_id, deck_id=deck_id)

    def _on_profiles_changed(self) -> None:
        dashboard_page = self._pages.get("dashboard")
        if isinstance(dashboard_page, DashboardPage):
            dashboard_page.refresh_metrics()

        review_page = self._pages.get("review")
        if isinstance(review_page, ReviewPage):
            review_page.apply_active_profile_defaults(prefer_due_mode=False)

        memory_garden_page = self._pages.get("memory_garden")
        if isinstance(memory_garden_page, MemoryGardenPage):
            memory_garden_page.refresh_garden()

        trophies_page = self._pages.get("trophies")
        if isinstance(trophies_page, TrophiesPage):
            trophies_page.refresh_content()

        history_page = self._pages.get("history")
        if isinstance(history_page, HistoryPage):
            history_page.refresh_runs()

    def _set_locale(self, locale: str) -> None:
        # Persist language preference immediately so next app launch reuses it.
        self.settings_service.set_app_language(locale)
        self.translator.set_locale(locale)

    def _on_language_changed(self, _locale: str) -> None:
        self.sidebar.update_texts()

        for page in self._pages.values():
            page.update_texts()

        self.setWindowTitle(self.translator.t("app.name"))
        self._sync_audio_controls()
        self._sync_stack_height_to_active_page()

    def _on_audio_toggle_requested(self) -> None:
        if self._background_music is None:
            return

        if not self._background_music.is_available():
            # Keep feedback non-blocking and explicit when music track is missing.
            self.show_toast(
                self.translator.t("audio_flow.unavailable_toast"),
                level="warning",
                duration_ms=2500,
            )
            self._sync_audio_controls()
            return

        self._background_music.toggle_enabled()
        self._sync_audio_controls()
        self._refresh_settings_page_state()

    def _on_sounds_setting_changed(self, _enabled: bool) -> None:
        if self._background_music is None:
            return
        # Settings page and speaker button control the same persisted flag.
        self._background_music.apply_settings()
        self._sync_audio_controls()

    def _sync_audio_controls(self) -> None:
        """Reflect current audio preference/backend availability in sidebar UI."""
        if self._background_music is None:
            return
        self.sidebar.set_audio_state(
            enabled=self._background_music.is_enabled_preference(),
            available=self._background_music.is_available(),
        )

    def _refresh_settings_page_state(self) -> None:
        settings_page = self._pages.get("settings")
        if isinstance(settings_page, SettingsPage):
            settings_page.refresh_settings()

    def show_toast(
        self,
        message: str,
        *,
        level: str = "info",
        duration_ms: int = 2600,
        title: str | None = None,
    ) -> None:
        """Display non-blocking toast feedback.

        We route all toasts through one manager so queueing and visual style
        stay consistent across all pages.
        """
        if self._toast_manager is None:
            return

        # Respect user preference for reduced motion.
        animations_enabled = self.settings_service.get_settings().animations_enabled
        self._toast_manager.show_toast(
            message,
            level=level,
            duration_ms=duration_ms,
            title=title,
            animations_enabled=animations_enabled,
        )
