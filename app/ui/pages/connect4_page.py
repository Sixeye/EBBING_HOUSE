"""Connect Four challenge page where quiz correctness drives turns."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
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

from app.models.quiz_session import QuizSessionSummary
from app.services.connect4_session_service import Connect4SessionService
from app.services.deck_service import DeckService
from app.services.profile_service import ProfileService
from app.services.run_history_service import RunHistoryService
from app.services.settings_service import SettingsService
from app.ui.pages.base_page import BasePage
from app.ui.widgets.connect4_widget import Connect4Widget
from app.ui.widgets.game_start_fx import GameStartFxController
from app.ui.widgets.motion import set_feedback_visual
from app.ui.widgets.question_card import QuestionCardWidget
from app.ui.widgets.session_summary_card import SessionSummaryCardWidget


class Connect4Page(BasePage):
    """Educational Connect Four mode.

    Rules implemented in service:
    - correct answer => player disc
    - wrong answer => no player disc + opponent gets one extra move
    """

    def __init__(
        self,
        translator,
        deck_service: DeckService,
        profile_service: ProfileService,
        settings_service: SettingsService,
        connect4_session_service: Connect4SessionService,
        run_history_service: RunHistoryService,
    ) -> None:
        super().__init__(translator)
        self.deck_service = deck_service
        self.profile_service = profile_service
        self.settings_service = settings_service
        self.connect4_session_service = connect4_session_service
        self.run_history_service = run_history_service
        self._start_fx = GameStartFxController(self, self.settings_service)

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

        board_panel = QFrame()
        board_panel.setObjectName("PlaceholderPanel")
        # Board stays primary, but vertical policy is preferred to avoid a
        # stretched "tower" effect on tall stacked pages.
        board_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        board_layout = QVBoxLayout(board_panel)
        board_layout.setContentsMargins(12, 10, 12, 10)
        board_layout.setSpacing(8)

        self._board_widget = Connect4Widget()
        self._board_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._turn_label = QLabel()
        self._turn_label.setObjectName("SectionTitle")
        self._turn_label.setWordWrap(True)

        self._progress_label = QLabel()
        self._progress_label.setObjectName("PageSubtitle")
        self._progress_label.setWordWrap(True)

        self._stats_label = QLabel()
        self._stats_label.setObjectName("PageSubtitle")
        self._stats_label.setWordWrap(True)

        status_strip = QFrame()
        status_strip.setObjectName("PlaceholderPanel")
        status_layout = QGridLayout(status_strip)
        status_layout.setContentsMargins(10, 8, 10, 8)
        status_layout.setHorizontalSpacing(10)
        status_layout.setVerticalSpacing(4)
        # Keep status compact and horizontal so the board remains the visual star.
        status_layout.addWidget(self._turn_label, 0, 0)
        status_layout.addWidget(self._progress_label, 0, 1)
        status_layout.addWidget(self._stats_label, 0, 2)
        status_layout.setColumnStretch(0, 2)
        status_layout.setColumnStretch(1, 2)
        status_layout.setColumnStretch(2, 2)

        board_layout.addWidget(status_strip, 0)
        board_layout.addWidget(self._board_widget, 1)

        movement_panel = QFrame()
        movement_panel.setObjectName("PlaceholderPanel")
        movement_layout = QVBoxLayout(movement_panel)
        # Keep column controls compact so the board/question area keeps focus.
        movement_layout.setContentsMargins(8, 6, 8, 6)
        movement_layout.setSpacing(4)

        self._columns_title = QLabel()
        self._columns_title.setObjectName("SectionTitle")

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        self._column_buttons: list[QPushButton] = []
        for column in range(7):
            button = QPushButton()
            button.setObjectName("SecondaryButton")
            # Numeric-only controls are faster to scan than verb-heavy labels
            # ("Drop 1", "Drop 2", ...), especially during rapid gameplay.
            button.setFixedSize(28, 28)
            button.clicked.connect(lambda _checked=False, col=column: self._on_column_selected(col))
            self._column_buttons.append(button)
            grid.addWidget(button, 0, column)

        movement_layout.addWidget(self._columns_title)
        movement_layout.addLayout(grid)

        self._question_card = QuestionCardWidget(self.translator)
        self._question_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

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

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setProperty("feedbackState", "info")
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        actions_layout.addWidget(self._validate_button)
        actions_layout.addWidget(self._feedback_label, 1)

        self._summary_panel = QFrame()
        self._summary_panel.setObjectName("PlaceholderPanel")
        summary_layout = QVBoxLayout(self._summary_panel)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)

        self._summary_title_label = QLabel()
        self._summary_title_label.setObjectName("SectionTitle")

        self._summary_value_label = QLabel()
        self._summary_value_label.setObjectName("MetricValue")

        self._summary_details_label = QLabel()
        self._summary_details_label.setObjectName("PageSubtitle")
        self._summary_details_label.setWordWrap(True)

        self._summary_card = SessionSummaryCardWidget(self.translator)

        summary_layout.addWidget(self._summary_title_label)
        summary_layout.addWidget(self._summary_value_label)
        summary_layout.addWidget(self._summary_details_label)
        summary_layout.addWidget(self._summary_card)
        self._summary_panel.hide()

        # Interaction column keeps the board visually dominant and avoids a
        # long vertical page by grouping controls + question on the right.
        self._interaction_panel = QFrame()
        self._interaction_panel.setObjectName("PlaceholderPanel")
        self._interaction_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        # Keep the board visually dominant on wide layouts by capping the
        # interaction column width.
        self._interaction_panel.setMaximumWidth(450)
        interaction_layout = QVBoxLayout(self._interaction_panel)
        interaction_layout.setContentsMargins(10, 8, 10, 8)
        interaction_layout.setSpacing(8)
        interaction_layout.addWidget(movement_panel)
        interaction_layout.addWidget(self._question_scroll, 1)
        interaction_layout.addWidget(actions_panel)
        interaction_layout.addWidget(self._summary_panel)

        self._content_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._content_layout.addWidget(board_panel, 3)
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

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        """Prefer side-by-side layout, stack only on tighter windows."""
        # We keep board-first composition longer so status/question panels
        # cannot dominate the page in medium windows.
        if self.width() < 1000:
            self._content_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._interaction_panel.setMaximumWidth(16777215)
            self._question_scroll.setMinimumHeight(220)
        else:
            self._content_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._interaction_panel.setMaximumWidth(450)
            self._question_scroll.setMinimumHeight(190)

    def update_texts(self) -> None:
        current_deck_id = self._deck_selector.currentData()

        self._title_label.setText(self.translator.t("pages.connect4.title"))
        self._description_label.setText(self.translator.t("pages.connect4.description"))
        self._deck_label.setText(self.translator.t("connect4_flow.deck_label"))
        self._limit_label.setText(self.translator.t("connect4_flow.limit_label"))
        self._limit_selector.setItemText(2, self.translator.t("connect4_flow.limit_all"))
        self._refresh_button.setText(self.translator.t("connect4_flow.refresh_decks"))
        self._start_button.setText(self.translator.t("connect4_flow.start_challenge"))
        self._helper_label.setText(self.translator.t("connect4_flow.helper_text"))
        self._columns_title.setText(self.translator.t("connect4_flow.columns_title"))
        self._validate_button.setText(self.translator.t("connect4_flow.validate_answer"))
        self._summary_title_label.setText(self.translator.t("connect4_flow.summary_title"))

        for index, button in enumerate(self._column_buttons, start=1):
            # Keep labels numeric-only to make column choice immediate.
            button.setText(str(index))
            button.setToolTip(self.translator.t("connect4_flow.column_tooltip", col=index))

        self._question_card.update_texts()
        self._summary_card.update_texts()

        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._update_status_labels()

    def refresh_sources(self) -> None:
        if (
            self.connect4_session_service.has_active_challenge()
            and not self.connect4_session_service.is_finished()
        ):
            self._update_status_labels()
            return
        current_deck_id = self._deck_selector.currentData()
        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._update_status_labels()

    def _refresh_deck_selector(self, select_deck_id: int | None = None) -> None:
        decks = self.deck_service.list_decks()
        self._deck_selector.blockSignals(True)
        self._deck_selector.clear()
        if not decks:
            self._deck_selector.addItem(self.translator.t("connect4_flow.no_decks"), None)
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
            self._set_feedback(self.translator.t("connect4_flow.error_select_deck"), "error")
            return

        question_limit = self._limit_selector.currentData()
        active_profile_id = self.profile_service.get_active_profile_id()
        try:
            self.connect4_session_service.start_challenge_from_deck(
                deck_id=int(deck_id),
                question_limit=question_limit,
                shuffle_questions=True,
                profile_id=active_profile_id,
            )
        except ValueError:
            self._set_feedback(self.translator.t("connect4_flow.error_runtime"), "error")
            return

        self._summary_panel.hide()
        self._question_scroll.hide()
        self._question_card.lock_answers(True)
        self._validate_button.setEnabled(False)
        self._set_controls_enabled(False)
        self._set_column_controls_enabled(True)
        self._board_widget.set_board(self.connect4_session_service.board_snapshot())
        self._update_status_labels()
        self._set_feedback(self.translator.t("connect4_flow.session_started"), "info")
        self._start_fx.play(self.translator.t("connect4_flow.intro_banner"))

    def _on_column_selected(self, column: int) -> None:
        try:
            request = self.connect4_session_service.request_player_move(column)
        except ValueError:
            self._set_feedback(self.translator.t("connect4_flow.error_runtime"), "error")
            return

        if request.blocked:
            self._set_feedback(self.translator.t("connect4_flow.feedback_column_full"), "info")
            return

        if request.question is None:
            self._set_feedback(self.translator.t("connect4_flow.error_no_question"), "error")
            return

        current, total = self.connect4_session_service.current_question_progress()
        self._question_card.set_question(request.question, current, total)
        self._question_card.lock_answers(False)
        self._question_scroll.show()
        self._question_scroll.verticalScrollBar().setValue(0)
        self._validate_button.setEnabled(False)
        self._set_column_controls_enabled(False)
        self._update_status_labels()
        self._set_feedback(
            self.translator.t("connect4_flow.question_ready", col=column + 1),
            "info",
        )

    def _on_selection_changed(self) -> None:
        can_validate = (
            self.connect4_session_service.has_active_challenge()
            and not self.connect4_session_service.is_finished()
            and self.connect4_session_service.pending_column() is not None
            and not self.connect4_session_service.current_question_is_validated()
            and self._question_card.has_selection()
        )
        self._validate_button.setEnabled(can_validate)

    def _on_validate(self) -> None:
        selected = self._question_card.selected_answers()
        if not selected:
            self._set_feedback(self.translator.t("connect4_flow.error_select_answer"), "error")
            return

        try:
            evaluation = self.connect4_session_service.validate_current_answer(selected)
        except ValueError:
            self._set_feedback(self.translator.t("connect4_flow.error_runtime"), "error")
            return

        self._question_card.lock_answers(True)
        self._question_card.show_feedback(
            selected_answers=evaluation.selected_answers,
            correct_answers=evaluation.correct_answers,
            explanation=evaluation.explanation,
        )
        self._validate_button.setEnabled(False)

        self._board_widget.set_board(self.connect4_session_service.board_snapshot())
        self._update_status_labels()

        if evaluation.was_correct:
            self._set_feedback(self.translator.t("connect4_flow.feedback_correct_move"), "success")
        else:
            answers = "|".join(evaluation.correct_answers)
            self._set_feedback(
                self.translator.t(
                    "connect4_flow.feedback_wrong_extra_turn",
                    answers=answers,
                    turns=evaluation.opponent_discs_dropped,
                ),
                "error",
            )

        if self.connect4_session_service.is_finished():
            self._finalize_challenge()
            return

        self._question_scroll.hide()
        self._set_column_controls_enabled(True)
        self._set_feedback(self.translator.t("connect4_flow.choose_column"), "info")

    def _finalize_challenge(self) -> None:
        summary = self.connect4_session_service.build_summary()
        # History stays lightweight: one row per completed challenge.
        self.run_history_service.record_connect4_completed(
            profile_id=self.connect4_session_service.active_profile_id(),
            deck_id=self.connect4_session_service.active_deck_id(),
            started_at=self.connect4_session_service.started_at(),
            summary=summary,
        )
        self._summary_panel.show()

        if summary.did_win:
            self._summary_value_label.setText(self.translator.t("connect4_flow.summary_win"))
            self._summary_value_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #39B26A;")
            self._set_feedback(self.translator.t("connect4_flow.session_won"), "success")
            self.notify_toast(self.translator.t("connect4_flow.session_won"), level="success")
        elif summary.did_draw:
            self._summary_value_label.setText(self.translator.t("connect4_flow.summary_draw"))
            self._summary_value_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #AAAAAE;")
            self._set_feedback(self.translator.t("connect4_flow.session_draw"), "info")
            self.notify_toast(self.translator.t("connect4_flow.session_draw"), level="info")
        else:
            self._summary_value_label.setText(self.translator.t("connect4_flow.summary_lost"))
            self._summary_value_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #D95B5B;")
            self._set_feedback(self.translator.t("connect4_flow.session_lost"), "error")
            self.notify_toast(self.translator.t("connect4_flow.session_lost"), level="warning")

        self._summary_details_label.setText(
            self.translator.t(
                "connect4_flow.summary_details",
                answered=summary.answered_questions,
                pool=summary.total_questions_pool,
                player=summary.player_moves,
                opponent=summary.opponent_moves,
            )
        )

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

        self._question_scroll.hide()
        self._validate_button.setEnabled(False)
        self._set_column_controls_enabled(False)
        self._set_controls_enabled(True)
        self._update_status_labels()

    def _update_status_labels(self) -> None:
        if not self.connect4_session_service.has_active_challenge():
            self._turn_label.setText(self.translator.t("connect4_flow.turn_idle"))
            self._progress_label.setText(self.translator.t("connect4_flow.progress_idle"))
            self._stats_label.setText(self.translator.t("connect4_flow.stats_idle"))
            self._board_widget.reset()
            return

        if self.connect4_session_service.is_finished():
            if self.connect4_session_service.did_win():
                self._turn_label.setText(self.translator.t("connect4_flow.turn_finished_win"))
            elif self.connect4_session_service.did_draw():
                self._turn_label.setText(self.translator.t("connect4_flow.turn_finished_draw"))
            else:
                self._turn_label.setText(self.translator.t("connect4_flow.turn_finished_lost"))
        elif self.connect4_session_service.pending_column() is None:
            self._turn_label.setText(self.translator.t("connect4_flow.turn_player"))
        else:
            self._turn_label.setText(self.translator.t("connect4_flow.turn_answer_required"))

        current, total = self.connect4_session_service.current_question_progress()
        self._progress_label.setText(
            self.translator.t("connect4_flow.progress_text", current=current, total=total)
        )
        self._stats_label.setText(
            self.translator.t(
                "connect4_flow.stats_value",
                player=self.connect4_session_service.player_moves(),
                opponent=self.connect4_session_service.opponent_moves(),
                wrong=self.connect4_session_service.wrong_answers_count(),
            )
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._deck_selector.setEnabled(enabled)
        self._limit_selector.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)
        if enabled:
            self._update_start_state()
        else:
            self._start_button.setEnabled(False)

    def _set_column_controls_enabled(self, enabled: bool) -> None:
        for button in self._column_buttons:
            button.setEnabled(enabled)

    def _update_start_state(self) -> None:
        if (
            self.connect4_session_service.has_active_challenge()
            and not self.connect4_session_service.is_finished()
        ):
            self._start_button.setEnabled(False)
            return
        self._start_button.setEnabled(self._deck_selector.currentData() is not None)

    def _set_feedback(self, message: str, state: str) -> None:
        self._feedback_label.setText(message)
        set_feedback_visual(self._feedback_label, state)


__all__ = ["Connect4Page"]
