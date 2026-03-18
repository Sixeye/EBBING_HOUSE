"""Dashboard page used as the main daily home screen."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.i18n.translator import Translator
from app.models.dashboard import DashboardMetrics
from app.services.dashboard_service import DashboardService
from app.services.run_history_service import RunHistoryService
from desktop_app.themes.branding import load_brand_banner
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.widgets.metric_card import MetricCard
from desktop_app.ui.widgets.motion import flash_widget, repolish


class DashboardPage(BasePage):
    """Home page that answers 'what should I do now?' for the active learner."""

    start_review_requested = Signal()
    due_deck_review_requested = Signal(int)
    open_memory_garden_requested = Signal()
    open_support_requested = Signal()
    open_history_requested = Signal()

    def __init__(
        self,
        translator: Translator,
        dashboard_service: DashboardService,
        run_history_service: RunHistoryService,
    ) -> None:
        super().__init__(translator)
        self.dashboard_service = dashboard_service
        self.run_history_service = run_history_service
        self._metrics = DashboardMetrics(
            active_profile_id=None,
            active_profile_name=None,
            due_today_count=0,
            tracked_questions_count=0,
            average_mastery_score=0.0,
            mastered_questions_count=0,
            weak_questions_count=0,
            total_reviews_count=0,
            reviewed_today_count=0,
            encouragement_key="dashboard.encouragement.no_profile",
            top_due_decks=[],
        )

        self._build_ui()
        self.update_texts()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._subtitle_label = QLabel()
        self._subtitle_label.setObjectName("PageSubtitle")
        self._subtitle_label.setWordWrap(True)

        self._hero_panel = QFrame()
        self._hero_panel.setObjectName("HeroPanel")
        hero_layout = QVBoxLayout(self._hero_panel)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(5)

        # Brand banner is visible but restrained: we keep it compact so daily
        # learning actions remain the visual priority.
        self._hero_brand_banner = QLabel()
        self._hero_brand_banner.setObjectName("BrandBanner")
        self._hero_brand_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hero_brand_banner.setMinimumHeight(82)
        self._hero_brand_banner.setMaximumHeight(102)
        self._hero_brand_banner.setScaledContents(False)

        self._hero_brand_note_label = QLabel()
        self._hero_brand_note_label.setObjectName("BrandSubtitle")
        self._hero_brand_note_label.setWordWrap(True)

        self._hero_title_label = QLabel()
        self._hero_title_label.setObjectName("HeroTitle")

        self._hero_message_label = QLabel()
        self._hero_message_label.setObjectName("HeroSubtitle")
        self._hero_message_label.setWordWrap(True)

        hero_layout.addWidget(self._hero_brand_banner)
        hero_layout.addWidget(self._hero_brand_note_label)
        hero_layout.addWidget(self._hero_title_label)
        hero_layout.addWidget(self._hero_message_label)

        # Two operational cards drive the daily workflow:
        # - learner context (active profile)
        # - due queue with primary action button
        self._active_panel = QFrame()
        self._active_panel.setObjectName("PlaceholderPanel")
        active_layout = QVBoxLayout(self._active_panel)
        active_layout.setContentsMargins(14, 12, 14, 12)
        active_layout.setSpacing(3)

        self._active_title_label = QLabel()
        self._active_title_label.setObjectName("SectionTitle")

        self._active_value_label = QLabel()
        self._active_value_label.setObjectName("MetricValue")

        self._active_status_label = QLabel()
        self._active_status_label.setObjectName("PageSubtitle")
        self._active_status_label.setWordWrap(True)

        active_layout.addWidget(self._active_title_label)
        active_layout.addWidget(self._active_value_label)
        active_layout.addWidget(self._active_status_label)
        active_layout.addStretch(1)

        self._due_panel = QFrame()
        self._due_panel.setObjectName("HeroPanel")
        due_layout = QVBoxLayout(self._due_panel)
        due_layout.setContentsMargins(14, 12, 14, 12)
        due_layout.setSpacing(5)

        self._due_title_label = QLabel()
        self._due_title_label.setObjectName("SectionTitle")

        self._due_value_label = QLabel()
        self._due_value_label.setObjectName("DueValueLabel")
        self._due_value_label.setProperty("dueState", "idle")

        self._due_status_label = QLabel()
        self._due_status_label.setObjectName("PageSubtitle")
        self._due_status_label.setWordWrap(True)

        self._cta_button = QPushButton()
        self._cta_button.setObjectName("PrimaryButton")
        self._cta_button.setMinimumHeight(34)
        self._cta_button.clicked.connect(self.start_review_requested.emit)

        self._garden_button = QPushButton()
        self._garden_button.setObjectName("SecondaryButton")
        self._garden_button.setMinimumHeight(32)
        self._garden_button.clicked.connect(self.open_memory_garden_requested.emit)

        # Keep support discoverable but discreet: one calm secondary action.
        self._support_button = QPushButton()
        self._support_button.setObjectName("SecondaryButton")
        self._support_button.setMinimumHeight(30)
        self._support_button.clicked.connect(self.open_support_requested.emit)

        due_layout.addWidget(self._due_title_label)
        due_layout.addWidget(self._due_value_label)
        due_layout.addWidget(self._due_status_label)
        due_layout.addWidget(self._cta_button, alignment=Qt.AlignmentFlag.AlignLeft)
        due_layout.addWidget(self._garden_button, alignment=Qt.AlignmentFlag.AlignLeft)
        due_layout.addWidget(self._support_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self._top_cards_layout = QGridLayout()
        self._top_cards_layout.setHorizontalSpacing(12)
        self._top_cards_layout.setVerticalSpacing(12)
        self._top_cards_layout.addWidget(self._active_panel, 0, 0)
        self._top_cards_layout.addWidget(self._due_panel, 0, 1)

        # These cards focus on metrics we can compute honestly from existing data.
        self._cards: dict[str, MetricCard] = {
            "tracked": MetricCard(animation_delay_ms=0),
            "mastery": MetricCard(animation_delay_ms=70),
            "momentum": MetricCard(animation_delay_ms=140),
            "weak": MetricCard(animation_delay_ms=210),
        }
        self._cards_grid = QGridLayout()
        self._cards_grid.setHorizontalSpacing(12)
        self._cards_grid.setVerticalSpacing(12)
        self._cards_grid.setColumnStretch(0, 1)
        self._cards_grid.setColumnStretch(1, 1)
        self._cards_grid.addWidget(self._cards["tracked"], 0, 0)
        self._cards_grid.addWidget(self._cards["mastery"], 0, 1)
        self._cards_grid.addWidget(self._cards["momentum"], 1, 0)
        self._cards_grid.addWidget(self._cards["weak"], 1, 1)

        self._urgency_panel = QFrame()
        self._urgency_panel.setObjectName("PlaceholderPanel")
        urgency_layout = QVBoxLayout(self._urgency_panel)
        urgency_layout.setContentsMargins(14, 12, 14, 12)
        urgency_layout.setSpacing(5)

        self._urgency_title_label = QLabel()
        self._urgency_title_label.setObjectName("SectionTitle")
        urgency_layout.addWidget(self._urgency_title_label)

        self._urgency_rows: list[tuple[QFrame, QLabel, QPushButton]] = []
        for _ in range(3):
            row_frame = QFrame()
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            row_label = QLabel()
            row_label.setObjectName("PageSubtitle")
            row_label.setWordWrap(True)

            row_button = QPushButton()
            row_button.setObjectName("SecondaryButton")
            row_button.setMinimumHeight(30)
            row_button.clicked.connect(self._on_urgency_review_clicked)

            row_layout.addWidget(row_label, 1)
            row_layout.addWidget(row_button)

            self._urgency_rows.append((row_frame, row_label, row_button))
            urgency_layout.addWidget(row_frame)

        self._urgency_empty_label = QLabel()
        self._urgency_empty_label.setObjectName("PageSubtitle")
        self._urgency_empty_label.setWordWrap(True)
        urgency_layout.addWidget(self._urgency_empty_label)

        self._recent_runs_panel = QFrame()
        self._recent_runs_panel.setObjectName("PlaceholderPanel")
        recent_layout = QVBoxLayout(self._recent_runs_panel)
        recent_layout.setContentsMargins(14, 12, 14, 12)
        recent_layout.setSpacing(5)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self._recent_runs_title_label = QLabel()
        self._recent_runs_title_label.setObjectName("SectionTitle")

        self._recent_runs_button = QPushButton()
        self._recent_runs_button.setObjectName("SecondaryButton")
        self._recent_runs_button.setMinimumHeight(30)
        self._recent_runs_button.clicked.connect(self.open_history_requested.emit)

        header_row.addWidget(self._recent_runs_title_label, 1)
        header_row.addWidget(self._recent_runs_button)
        recent_layout.addLayout(header_row)

        self._recent_run_labels: list[QLabel] = []
        for _ in range(4):
            item = QLabel()
            item.setObjectName("PageSubtitle")
            item.setWordWrap(True)
            item.hide()
            self._recent_run_labels.append(item)
            recent_layout.addWidget(item)

        self._recent_runs_empty_label = QLabel()
        self._recent_runs_empty_label.setObjectName("PageSubtitle")
        self._recent_runs_empty_label.setWordWrap(True)
        recent_layout.addWidget(self._recent_runs_empty_label)

        # Keep lower dashboard blocks side-by-side on wider desktops so the
        # page does not feel like one long vertical feed.
        self._bottom_panels_layout = QGridLayout()
        self._bottom_panels_layout.setHorizontalSpacing(12)
        self._bottom_panels_layout.setVerticalSpacing(12)
        self._bottom_panels_layout.addWidget(self._urgency_panel, 0, 0)
        self._bottom_panels_layout.addWidget(self._recent_runs_panel, 0, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)
        layout.addWidget(self._hero_panel)
        layout.addLayout(self._top_cards_layout)
        layout.addLayout(self._cards_grid)
        layout.addLayout(self._bottom_panels_layout)
        self._apply_responsive_layout()

    def refresh_metrics(self) -> None:
        """Load and render dashboard metrics from real persistence state."""
        previous_due_count = self._metrics.due_today_count
        self._metrics = self.dashboard_service.get_metrics()
        metrics = self._metrics
        has_active_profile = metrics.active_profile_id is not None

        self._hero_message_label.setText(self.translator.t(metrics.encouragement_key))
        self._active_title_label.setText(self.translator.t("dashboard.active_card_title"))
        self._due_title_label.setText(self.translator.t("dashboard.due_card_title"))
        self._urgency_title_label.setText(self.translator.t("dashboard.deck_urgency_title"))
        self._recent_runs_title_label.setText(self.translator.t("dashboard.recent_runs_title"))
        self._recent_runs_button.setText(self.translator.t("dashboard.recent_runs_action"))
        self._garden_button.setText(self.translator.t("dashboard.cta_memory_garden"))
        self._support_button.setText(self.translator.t("dashboard.cta_support"))
        for _, _, button in self._urgency_rows:
            button.setText(self.translator.t("dashboard.deck_urgency_action"))

        if not has_active_profile:
            self._active_value_label.setText(self.translator.t("dashboard.active_card_none_value"))
            self._active_status_label.setText(self.translator.t("dashboard.active_card_none_status"))
            self._due_value_label.setText("--")
            self._set_due_state("idle")
            self._due_status_label.setText(self.translator.t("dashboard.due_card_no_profile"))
            self._cta_button.setText(self.translator.t("dashboard.cta_select_profile"))
        else:
            self._active_value_label.setText(metrics.active_profile_name or "?")
            if metrics.tracked_questions_count == 0:
                self._active_status_label.setText(self.translator.t("dashboard.active_card_new_status"))
            else:
                self._active_status_label.setText(
                    self.translator.t(
                        "dashboard.active_card_ready_status",
                        tracked=metrics.tracked_questions_count,
                    )
                )

            self._due_value_label.setText(str(metrics.due_today_count))
            if metrics.due_today_count == 0:
                self._set_due_state("clear")
                self._due_status_label.setText(self.translator.t("dashboard.due_card_all_caught_up"))
                self._cta_button.setText(self.translator.t("dashboard.cta_practice"))
            else:
                self._set_due_state("due")
                self._due_status_label.setText(
                    self.translator.t("dashboard.due_card_due_status", count=metrics.due_today_count)
                )
                self._cta_button.setText(self.translator.t("dashboard.cta_due_today"))

        if metrics.due_today_count != previous_due_count:
            flash_widget(self._due_value_label, start_opacity=0.7, duration_ms=180)

        self._cards["tracked"].update_content(
            title=self.translator.t("dashboard.metrics.tracked.title"),
            value=str(metrics.tracked_questions_count),
            hint=self.translator.t(
                "dashboard.metrics.tracked.hint",
                reviews=metrics.total_reviews_count,
            ),
        )
        self._cards["mastery"].update_content(
            title=self.translator.t("dashboard.metrics.mastery.title"),
            value=f"{metrics.average_mastery_score:.1f}%",
            hint=self.translator.t(
                "dashboard.metrics.mastery.hint",
                mastered=metrics.mastered_questions_count,
            ),
        )
        self._cards["momentum"].update_content(
            title=self.translator.t("dashboard.metrics.momentum.title"),
            value=str(metrics.total_reviews_count),
            hint=self.translator.t(
                "dashboard.metrics.momentum.hint",
                today=metrics.reviewed_today_count,
            ),
        )
        self._cards["weak"].update_content(
            title=self.translator.t("dashboard.metrics.weak.title"),
            value=str(metrics.weak_questions_count),
            hint=self.translator.t("dashboard.metrics.weak.hint"),
        )

        self._render_urgency_rows()
        self._render_recent_runs()

    def _render_urgency_rows(self) -> None:
        metrics = self._metrics
        if metrics.active_profile_id is None:
            for row_frame, _, _ in self._urgency_rows:
                row_frame.hide()
            self._urgency_empty_label.setText(
                self.translator.t("dashboard.deck_urgency_empty_no_profile")
            )
            self._urgency_empty_label.show()
            return

        if not metrics.top_due_decks:
            for row_frame, _, _ in self._urgency_rows:
                row_frame.hide()
            self._urgency_empty_label.setText(
                self.translator.t("dashboard.deck_urgency_empty_all_caught_up")
            )
            self._urgency_empty_label.show()
            return

        self._urgency_empty_label.hide()
        for index, (row_frame, row_label, row_button) in enumerate(self._urgency_rows):
            if index < len(metrics.top_due_decks):
                deck_stat = metrics.top_due_decks[index]
                row_label.setText(
                    self.translator.t(
                        "dashboard.deck_urgency_row",
                        deck=deck_stat.deck_name,
                        count=deck_stat.due_count,
                    )
                )
                row_button.setProperty("deck_id", deck_stat.deck_id)
                row_frame.show()
            else:
                row_frame.hide()

    def _render_recent_runs(self) -> None:
        metrics = self._metrics
        for label in self._recent_run_labels:
            label.hide()

        if metrics.active_profile_id is None:
            self._recent_runs_empty_label.setText(
                self.translator.t("dashboard.recent_runs_empty_no_profile")
            )
            self._recent_runs_empty_label.show()
            return

        runs = self.run_history_service.list_recent_runs(
            profile_id=metrics.active_profile_id,
            limit=4,
        )
        if not runs:
            self._recent_runs_empty_label.setText(
                self.translator.t("dashboard.recent_runs_empty")
            )
            self._recent_runs_empty_label.show()
            return

        self._recent_runs_empty_label.hide()
        for index, run in enumerate(runs):
            if index >= len(self._recent_run_labels):
                break
            line = self.translator.t(
                "dashboard.recent_runs_row",
                time=run.ended_at,
                mode=self._mode_label(run.mode),
                result=self._result_label(run.did_win, run.summary_text),
                deck=run.deck_name or self.translator.t("dashboard.recent_runs_deck_unknown"),
            )
            self._recent_run_labels[index].setText(line)
            self._recent_run_labels[index].show()

    def _mode_label(self, mode: str) -> str:
        key = f"history_flow.mode.{mode}"
        resolved = self.translator.t(key)
        return mode if resolved == key else resolved

    def _result_label(self, did_win: bool, summary_text: str | None) -> str:
        if summary_text and summary_text.startswith("draw"):
            return self.translator.t("dashboard.recent_runs_result_draw")
        return (
            self.translator.t("dashboard.recent_runs_result_win")
            if did_win
            else self.translator.t("dashboard.recent_runs_result_loss")
        )

    def _on_urgency_review_clicked(self) -> None:
        sender = self.sender()
        if sender is None:
            return

        deck_id = sender.property("deck_id")
        if isinstance(deck_id, int):
            # Routing + edge-case checks are handled centrally in MainWindow so
            # dashboard remains UI-focused and simple.
            self.due_deck_review_requested.emit(deck_id)

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("dashboard.title"))
        self._subtitle_label.setText(self.translator.t("dashboard.subtitle"))
        self._hero_brand_note_label.setText(self.translator.t("branding.dashboard_note"))
        self._hero_title_label.setText(self.translator.t("app.welcome"))
        self._refresh_brand_banner()
        self.refresh_metrics()

    def _set_due_state(self, state: str) -> None:
        if self._due_value_label.property("dueState") == state:
            return
        self._due_value_label.setProperty("dueState", state)
        repolish(self._due_value_label)

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_responsive_layout()
        self._refresh_brand_banner()

    def _apply_responsive_layout(self) -> None:
        """Reflow key dashboard blocks for small/medium desktop widths."""
        width = self.width()

        # Top operational cards stack on narrower windows to avoid crushed text.
        if width < 960:
            self._top_cards_layout.addWidget(self._active_panel, 0, 0)
            self._top_cards_layout.addWidget(self._due_panel, 1, 0)
            self._top_cards_layout.setColumnStretch(0, 1)
            self._top_cards_layout.setColumnStretch(1, 0)
        else:
            self._top_cards_layout.addWidget(self._active_panel, 0, 0)
            self._top_cards_layout.addWidget(self._due_panel, 0, 1)
            self._top_cards_layout.setColumnStretch(0, 1)
            self._top_cards_layout.setColumnStretch(1, 1)

        # Metric cards switch to a single column in tighter layouts for better
        # readability and consistent card heights.
        cards = (
            self._cards["tracked"],
            self._cards["mastery"],
            self._cards["momentum"],
            self._cards["weak"],
        )
        for card in cards:
            self._cards_grid.removeWidget(card)

        if width < 940:
            for index, card in enumerate(cards):
                self._cards_grid.addWidget(card, index, 0)
            self._cards_grid.setColumnStretch(0, 1)
            self._cards_grid.setColumnStretch(1, 0)
        else:
            self._cards_grid.addWidget(cards[0], 0, 0)
            self._cards_grid.addWidget(cards[1], 0, 1)
            self._cards_grid.addWidget(cards[2], 1, 0)
            self._cards_grid.addWidget(cards[3], 1, 1)
            self._cards_grid.setColumnStretch(0, 1)
            self._cards_grid.setColumnStretch(1, 1)

        # Lower blocks share width on medium/large screens for denser reading.
        if width < 960:
            self._bottom_panels_layout.addWidget(self._urgency_panel, 0, 0)
            self._bottom_panels_layout.addWidget(self._recent_runs_panel, 1, 0)
            self._bottom_panels_layout.setColumnStretch(0, 1)
            self._bottom_panels_layout.setColumnStretch(1, 0)
        else:
            self._bottom_panels_layout.addWidget(self._urgency_panel, 0, 0)
            self._bottom_panels_layout.addWidget(self._recent_runs_panel, 0, 1)
            self._bottom_panels_layout.setColumnStretch(0, 1)
            self._bottom_panels_layout.setColumnStretch(1, 1)

    def _refresh_brand_banner(self) -> None:
        """Fit hero banner with face-aware framing.

        Root issue fixed:
        the raw image has generous vertical padding and lower text, so a strict
        geometric center crop made the face/head feel visually too low.

        We keep aspect-ratio-safe scaling and apply a slightly upper focal point
        to center the Ebbinghaus face in the visible hero strip.
        """
        target_width = max(280, min(520, self._hero_panel.width() - 40))
        self._hero_brand_banner.setPixmap(
            load_brand_banner(
                target_width,
                88,
                # 0.36 keeps forehead/glasses/beard balanced so the visible
                # strip feels centered on the face (not on the lower text glow).
                focal_point=(0.5, 0.36),
            )
        )
