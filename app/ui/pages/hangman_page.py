"""Hangman mini-game page powered by quiz questions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from app.models.quiz_session import QuizSessionSummary
from app.services.deck_service import DeckService
from app.services.hangman_session_service import HangmanSessionService
from app.services.profile_service import ProfileService
from app.services.run_history_service import RunHistoryService
from app.services.settings_service import SettingsService
from app.services.trophy_service import TrophyService
from app.ui.pages.base_page import BasePage
from app.ui.widgets.game_start_fx import GameStartFxController
from app.ui.widgets.hangman_widget import HangmanWidget
from app.ui.widgets.motion import flash_widget, repolish, set_feedback_visual
from app.ui.widgets.question_card import QuestionCardWidget
from app.ui.widgets.session_summary_card import SessionSummaryCardWidget
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
)


class HangmanPage(BasePage):
    """Quiz-driven hangman challenge page.

    Educational core stays central: we only gamify consequence of answer
    correctness while reusing the same question validation rules.
    """

    def __init__(
        self,
        translator,
        deck_service: DeckService,
        profile_service: ProfileService,
        settings_service: SettingsService,
        hangman_session_service: HangmanSessionService,
        trophy_service: TrophyService,
        run_history_service: RunHistoryService,
    ) -> None:
        super().__init__(translator)
        self.deck_service = deck_service
        self.profile_service = profile_service
        self.settings_service = settings_service
        self.hangman_session_service = hangman_session_service
        self.trophy_service = trophy_service
        self.run_history_service = run_history_service
        self._start_fx = GameStartFxController(self, self.settings_service)
        self._last_wrong_answers = 0

        self._build_ui()
        self._connect_signals()
        self.update_texts()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        controls_panel = QFrame()
        controls_panel.setObjectName("PlaceholderPanel")
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setContentsMargins(12, 10, 12, 10)
        controls_layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(10)

        self._deck_label = QLabel()
        self._deck_selector = QComboBox()
        self._deck_selector.setMinimumHeight(30)

        self._limit_label = QLabel()
        self._limit_selector = QComboBox()
        self._limit_selector.setMinimumHeight(30)
        self._limit_selector.addItem("10", 10)
        self._limit_selector.addItem("20", 20)
        self._limit_selector.addItem("ALL_PLACEHOLDER", None)
        self._limit_selector.setCurrentIndex(2)

        self._refresh_button = QPushButton()
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.setMinimumHeight(30)

        self._start_button = QPushButton()
        self._start_button.setObjectName("PrimaryButton")
        self._start_button.setMinimumHeight(32)

        row.addWidget(self._deck_label)
        row.addWidget(self._deck_selector, 2)
        row.addWidget(self._limit_label)
        row.addWidget(self._limit_selector, 1)
        row.addWidget(self._refresh_button)
        row.addWidget(self._start_button)

        self._helper_label = QLabel()
        self._helper_label.setObjectName("PageSubtitle")
        self._helper_label.setWordWrap(True)

        controls_layout.addLayout(row)
        controls_layout.addWidget(self._helper_label)

        visual_panel = QFrame()
        visual_panel.setObjectName("PlaceholderPanel")
        # Keep the game area dominant but avoid unbounded vertical stretching.
        visual_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        visual_layout = QVBoxLayout(visual_panel)
        visual_layout.setContentsMargins(12, 10, 12, 10)
        visual_layout.setSpacing(8)

        self._hangman_widget = HangmanWidget()
        self._hangman_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._danger_title_label = QLabel()
        self._danger_title_label.setObjectName("SectionTitle")

        self._danger_count_label = QLabel()
        self._danger_count_label.setObjectName("DangerValueLabel")
        self._danger_count_label.setProperty("dangerState", "idle")

        self._danger_remaining_label = QLabel()
        self._danger_remaining_label.setObjectName("PageSubtitle")
        self._danger_remaining_label.setWordWrap(True)

        self._progress_label = QLabel()
        self._progress_label.setObjectName("PageSubtitle")
        self._progress_label.setWordWrap(True)

        danger_strip = QFrame()
        danger_strip.setObjectName("PlaceholderPanel")
        danger_layout = QGridLayout(danger_strip)
        danger_layout.setContentsMargins(10, 8, 10, 8)
        danger_layout.setHorizontalSpacing(10)
        danger_layout.setVerticalSpacing(4)
        # Keep danger/status compact and horizontal so the scene keeps most area.
        danger_layout.addWidget(self._danger_title_label, 0, 0, 1, 3)
        danger_layout.addWidget(self._danger_count_label, 1, 0)
        danger_layout.addWidget(self._danger_remaining_label, 1, 1)
        danger_layout.addWidget(self._progress_label, 1, 2)
        danger_layout.setColumnStretch(0, 1)
        danger_layout.setColumnStretch(1, 1)
        danger_layout.setColumnStretch(2, 1)

        # The game scene is intentionally dominant; status moves to a compact strip.
        visual_layout.addWidget(self._hangman_widget, 1)
        visual_layout.addWidget(danger_strip, 0)

        self._question_card = QuestionCardWidget(self.translator)
        self._question_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        # The mini-game must stay readable with long educational content, so
        # question content gets its own scroll region while controls stay fixed.
        self._question_scroll = QScrollArea()
        self._question_scroll.setObjectName("QuestionScrollArea")
        self._question_scroll.setWidgetResizable(True)
        self._question_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._question_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._question_scroll.setMinimumHeight(190)
        self._question_scroll.setWidget(self._question_card)
        self._question_scroll.hide()

        actions_panel = QFrame()
        actions_panel.setObjectName("PlaceholderPanel")
        actions_layout = QHBoxLayout(actions_panel)
        actions_layout.setContentsMargins(12, 8, 12, 8)
        actions_layout.setSpacing(8)

        self._validate_button = QPushButton()
        self._validate_button.setObjectName("SecondaryButton")
        self._validate_button.setMinimumHeight(32)
        self._validate_button.setEnabled(False)

        self._next_button = QPushButton()
        self._next_button.setObjectName("PrimaryButton")
        self._next_button.setMinimumHeight(32)
        self._next_button.setEnabled(False)

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setProperty("feedbackState", "info")
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        actions_layout.addWidget(self._validate_button)
        actions_layout.addWidget(self._next_button)
        actions_layout.addWidget(self._feedback_label, 1)

        self._summary_panel = QFrame()
        self._summary_panel.setObjectName("PlaceholderPanel")
        summary_layout = QVBoxLayout(self._summary_panel)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)

        self._summary_status_title = QLabel()
        self._summary_status_title.setObjectName("SectionTitle")

        self._summary_status_value = QLabel()
        self._summary_status_value.setObjectName("MetricValue")

        self._summary_details = QLabel()
        self._summary_details.setObjectName("PageSubtitle")
        self._summary_details.setWordWrap(True)

        self._summary_card = SessionSummaryCardWidget(self.translator)

        summary_layout.addWidget(self._summary_status_title)
        summary_layout.addWidget(self._summary_status_value)
        summary_layout.addWidget(self._summary_details)
        summary_layout.addWidget(self._summary_card)

        self._summary_panel.hide()

        # Interaction column keeps question/feedback close to controls so the
        # page uses width instead of becoming an overly tall stack.
        self._interaction_panel = QFrame()
        self._interaction_panel.setObjectName("PlaceholderPanel")
        self._interaction_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        # Width cap prevents the text/action column from starving the game
        # visual in side-by-side mode.
        self._interaction_panel.setMaximumWidth(460)
        interaction_layout = QVBoxLayout(self._interaction_panel)
        interaction_layout.setContentsMargins(10, 8, 10, 8)
        interaction_layout.setSpacing(8)
        interaction_layout.addWidget(self._question_scroll, 1)
        interaction_layout.addWidget(actions_panel)
        interaction_layout.addWidget(self._summary_panel)

        self._content_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._content_layout.addWidget(visual_panel, 3)
        self._content_layout.addWidget(self._interaction_panel, 2)
        self._content_layout.setStretch(0, 5)
        self._content_layout.setStretch(1, 3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(controls_panel)
        layout.addLayout(self._content_layout, 1)
        self._apply_responsive_layout()

    def _connect_signals(self) -> None:
        self._refresh_button.clicked.connect(self._refresh_deck_selector)
        self._start_button.clicked.connect(self._on_start_challenge)
        self._deck_selector.currentIndexChanged.connect(self._update_start_state)
        self._question_card.selection_changed.connect(self._on_selection_changed)
        self._validate_button.clicked.connect(self._on_validate)
        self._next_button.clicked.connect(self._on_next)

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        """Use horizontal space on wide windows and stack only when needed."""
        # Previous layout still let side panels eat too much game space.
        # We now keep a wider side-by-side range and only stack when necessary.
        if self.width() < 980:
            self._content_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._interaction_panel.setMaximumWidth(16777215)
            self._question_scroll.setMinimumHeight(220)
        else:
            self._content_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._interaction_panel.setMaximumWidth(460)
            self._question_scroll.setMinimumHeight(190)

    def update_texts(self) -> None:
        current_deck_id = self._deck_selector.currentData()

        self._title_label.setText(self.translator.t("pages.hangman.title"))
        self._description_label.setText(self.translator.t("pages.hangman.description"))
        self._deck_label.setText(self.translator.t("hangman_flow.deck_label"))
        self._limit_label.setText(self.translator.t("hangman_flow.limit_label"))
        self._limit_selector.setItemText(2, self.translator.t("hangman_flow.limit_all"))
        self._refresh_button.setText(self.translator.t("hangman_flow.refresh_decks"))
        self._start_button.setText(self.translator.t("hangman_flow.start_challenge"))
        self._helper_label.setText(self.translator.t("hangman_flow.helper_text"))

        self._danger_title_label.setText(self.translator.t("hangman_flow.danger_title"))
        self._validate_button.setText(self.translator.t("hangman_flow.validate_answer"))
        self._next_button.setText(self.translator.t("hangman_flow.next_question"))

        self._summary_status_title.setText(self.translator.t("hangman_flow.summary_title"))

        self._question_card.update_texts()
        self._summary_card.update_texts()

        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._update_danger_ui()

    def refresh_sources(self) -> None:
        """Refresh deck sources when page becomes visible."""
        if (
            self.hangman_session_service.has_active_challenge()
            and not self.hangman_session_service.is_finished()
        ):
            # Avoid mutating selectors while a live challenge is running.
            self._update_danger_ui()
            return

        current_deck_id = self._deck_selector.currentData()
        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._update_danger_ui()

    def _refresh_deck_selector(self, select_deck_id: int | None = None) -> None:
        decks = self.deck_service.list_decks()

        self._deck_selector.blockSignals(True)
        self._deck_selector.clear()
        if not decks:
            self._deck_selector.addItem(self.translator.t("hangman_flow.no_decks"), None)
        else:
            for deck in decks:
                label = deck.name if not deck.category else f"{deck.name} ({deck.category})"
                self._deck_selector.addItem(label, deck.id)

        if select_deck_id is not None:
            index = self._deck_selector.findData(select_deck_id)
            if index >= 0:
                self._deck_selector.setCurrentIndex(index)

        self._deck_selector.blockSignals(False)
        self._update_start_state()

    def _on_start_challenge(self) -> None:
        deck_id = self._deck_selector.currentData()
        if deck_id is None:
            self._set_feedback(self.translator.t("hangman_flow.error_select_deck"), "error")
            return

        question_limit = self._limit_selector.currentData()
        active_profile_id = self.profile_service.get_active_profile_id()

        try:
            self.hangman_session_service.start_challenge_from_deck(
                deck_id=int(deck_id),
                question_limit=question_limit,
                shuffle_questions=False,
                profile_id=active_profile_id,
            )
        except ValueError:
            self._set_feedback(self.translator.t("hangman_flow.error_runtime"), "error")
            return

        self._summary_panel.hide()
        self._last_wrong_answers = 0
        self._show_current_question()
        self._update_danger_ui()
        self._set_feedback(self.translator.t("hangman_flow.session_started"), "info")
        self._set_controls_enabled(False)
        self._start_fx.play(self.translator.t("hangman_flow.intro_banner"))

    def _show_current_question(self) -> None:
        question = self.hangman_session_service.current_question()
        if question is None:
            return

        current, total = self.hangman_session_service.current_position()
        self._question_card.set_question(question, current, total)
        self._question_card.lock_answers(False)
        self._question_scroll.show()
        self._question_scroll.verticalScrollBar().setValue(0)

        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(False)
        self._next_button.setText(self.translator.t("hangman_flow.next_question"))

        self._progress_label.setText(
            self.translator.t("hangman_flow.progress_text", current=current, total=total)
        )

    def _on_selection_changed(self) -> None:
        can_validate = (
            self.hangman_session_service.has_active_challenge()
            and not self.hangman_session_service.is_finished()
            and not self.hangman_session_service.current_question_is_validated()
            and self._question_card.has_selection()
        )
        self._validate_button.setEnabled(can_validate)

    def _on_validate(self) -> None:
        selected = self._question_card.selected_answers()
        if not selected:
            self._set_feedback(self.translator.t("hangman_flow.error_select_answer"), "error")
            return

        try:
            evaluation = self.hangman_session_service.validate_current_answer(selected)
        except ValueError:
            self._set_feedback(self.translator.t("hangman_flow.error_runtime"), "error")
            return

        self._question_card.lock_answers(True)
        self._question_card.show_feedback(
            selected_answers=evaluation.selected_answers,
            correct_answers=evaluation.correct_answers,
            explanation=evaluation.explanation,
        )

        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(True)

        if evaluation.is_correct:
            self._set_feedback(self.translator.t("hangman_flow.feedback_correct"), "success")
        else:
            answers = "|".join(evaluation.correct_answers)
            self._set_feedback(self.translator.t("hangman_flow.feedback_wrong", answers=answers), "error")

        self._hangman_widget.pulse_feedback(evaluation.is_correct)
        self._update_danger_ui()

        if self.hangman_session_service.did_fail():
            self._next_button.setText(self.translator.t("hangman_flow.show_result"))
            self._set_feedback(self.translator.t("hangman_flow.feedback_failed_now"), "error")
            return

        current, total = self.hangman_session_service.current_position()
        if current >= total:
            self._next_button.setText(self.translator.t("hangman_flow.finish_challenge"))
        else:
            self._next_button.setText(self.translator.t("hangman_flow.next_question"))

    def _on_next(self) -> None:
        try:
            moved = self.hangman_session_service.go_to_next_question()
        except ValueError:
            self._set_feedback(self.translator.t("hangman_flow.error_runtime"), "error")
            return

        if moved:
            self._show_current_question()
            self._set_feedback(self.translator.t("hangman_flow.feedback_next_ready"), "info")
            return

        summary = self.hangman_session_service.build_summary()
        # We persist only completed challenges, never mid-run states.
        self.run_history_service.record_hangman_completed(
            profile_id=self.hangman_session_service.active_profile_id(),
            deck_id=self.hangman_session_service.active_deck_id(),
            started_at=self.hangman_session_service.started_at(),
            summary=summary,
        )
        self._render_summary(summary)
        self._question_scroll.hide()
        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(False)

        if summary.did_save:
            feedback = self.translator.t("hangman_flow.session_saved")
            unlocked = self.trophy_service.on_hangman_session_completed(
                profile_id=self.hangman_session_service.active_profile_id(),
                did_win=True,
            )
            if unlocked:
                names = ", ".join([item.display_name(self.translator.locale) for item in unlocked])
                feedback = f"{feedback} {self.translator.t('trophies_flow.feedback_unlocked', names=names)}"
                self.notify_toast(
                    self.translator.t("trophies_flow.feedback_unlocked", names=names),
                    level="success",
                    duration_ms=3400,
                )
            self._set_feedback(feedback, "success")
            self.notify_toast(
                self.translator.t("hangman_flow.session_saved"),
                level="success",
            )
        else:
            self._set_feedback(self.translator.t("hangman_flow.session_failed"), "error")
            self.notify_toast(
                self.translator.t("hangman_flow.session_failed"),
                level="warning",
            )

        self._set_controls_enabled(True)
        self._update_danger_ui()

    def _render_summary(self, summary) -> None:
        self._summary_panel.show()

        if summary.did_save:
            self._summary_status_value.setText(self.translator.t("hangman_flow.summary_saved"))
            self._summary_status_value.setStyleSheet("font-size: 28px; font-weight: 700; color: #39B26A;")
        else:
            self._summary_status_value.setText(self.translator.t("hangman_flow.summary_failed"))
            self._summary_status_value.setStyleSheet("font-size: 28px; font-weight: 700; color: #D95B5B;")

        self._summary_details.setText(
            self.translator.t(
                "hangman_flow.summary_details",
                answered=summary.answered_questions,
                pool=summary.total_questions_pool,
                used=summary.wrong_answers_used,
                max=summary.wrong_answers_used + summary.wrong_answers_remaining,
            )
        )

        # Reuse the shared summary widget for score consistency across modes.
        self._summary_card.set_summary(
            QuizSessionSummary(
                deck_name=summary.deck_name,
                total_questions=summary.answered_questions,
                correct_answers_count=summary.correct_answers_count,
                wrong_answers_count=summary.wrong_answers_count,
                score_on_20=summary.score_on_20,
                score_on_100=summary.score_on_100,
                percentage=summary.percentage,
                average_response_time_seconds=summary.average_response_time_seconds,
            )
        )

    def _update_danger_ui(self) -> None:
        if not self.hangman_session_service.has_active_challenge():
            self._hangman_widget.reset(max_wrong_answers=6)
            self._last_wrong_answers = 0
            self._danger_count_label.setText(self.translator.t("hangman_flow.danger_idle"))
            self._set_danger_state("idle")
            self._danger_remaining_label.setText(self.translator.t("hangman_flow.remaining_idle"))
            self._progress_label.setText(self.translator.t("hangman_flow.progress_idle"))
            return

        used = self.hangman_session_service.wrong_answers_used()
        max_wrong = self.hangman_session_service.max_wrong_answers()
        remaining = self.hangman_session_service.wrong_answers_remaining()
        self._hangman_widget.set_progress(used, max_wrong)

        self._danger_count_label.setText(
            self.translator.t("hangman_flow.danger_value", used=used, max=max_wrong)
        )
        self._danger_remaining_label.setText(
            self.translator.t("hangman_flow.remaining_value", remaining=remaining)
        )

        if remaining <= 1:
            self._set_danger_state("critical")
        elif used == 0:
            self._set_danger_state("safe")
        else:
            self._set_danger_state("warning")

        if used != self._last_wrong_answers:
            flash_widget(self._danger_count_label, start_opacity=0.64, duration_ms=170)
            self._last_wrong_answers = used

        if self.hangman_session_service.is_finished():
            if self.hangman_session_service.did_save():
                self._progress_label.setText(self.translator.t("hangman_flow.progress_saved"))
            else:
                self._progress_label.setText(self.translator.t("hangman_flow.progress_failed"))
        else:
            current, total = self.hangman_session_service.current_position()
            self._progress_label.setText(
                self.translator.t("hangman_flow.progress_text", current=current, total=total)
            )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._deck_selector.setEnabled(enabled)
        self._limit_selector.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)
        if enabled:
            self._update_start_state()
        else:
            self._start_button.setEnabled(False)

    def _update_start_state(self) -> None:
        if (
            self.hangman_session_service.has_active_challenge()
            and not self.hangman_session_service.is_finished()
        ):
            self._start_button.setEnabled(False)
            return
        self._start_button.setEnabled(self._deck_selector.currentData() is not None)

    def _set_feedback(self, message: str, state: str) -> None:
        self._feedback_label.setText(message)
        set_feedback_visual(self._feedback_label, state)

    def _set_danger_state(self, state: str) -> None:
        if self._danger_count_label.property("dangerState") == state:
            return
        self._danger_count_label.setProperty("dangerState", state)
        repolish(self._danger_count_label)


__all__ = ["HangmanPage"]
