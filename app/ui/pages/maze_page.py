"""Maze Challenge page with voxel-style rendering + quiz-gated movement."""

from __future__ import annotations

from app.models.maze_difficulty import DEFAULT_MAZE_DIFFICULTY, MAZE_DIFFICULTY_PRESETS
from app.models.maze_game import MazeDirection
from app.models.quiz_session import QuizSessionSummary
from app.services.deck_service import DeckService
from app.services.maze_session_service import MazeSessionService
from app.services.profile_service import ProfileService
from app.services.run_history_service import RunHistoryService
from app.services.settings_service import SettingsService
from app.services.trophy_service import TrophyService
from app.ui.pages.base_page import BasePage
from app.ui.widgets.game_start_fx import GameStartFxController
from app.ui.widgets.maze_widget import MazeWidget
from app.ui.widgets.motion import flash_widget, set_feedback_visual
from app.ui.widgets.question_card import QuestionCardWidget
from app.ui.widgets.session_summary_card import SessionSummaryCardWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QHideEvent, QResizeEvent, QShowEvent
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


class MazePage(BasePage):
    """Learning-first maze mode.

    Interaction contract (preserved):
    - wall direction click => immediate blocked feedback, no question consumed
    - traversable direction click => one question appears
    - correct answer => one cell movement
    - wrong answer => no movement

    New element:
    - a timer-driven guardian patrol that can catch the player and restart run
    """

    def __init__(
        self,
        translator,
        deck_service: DeckService,
        profile_service: ProfileService,
        settings_service: SettingsService,
        maze_session_service: MazeSessionService,
        trophy_service: TrophyService,
        run_history_service: RunHistoryService,
    ) -> None:
        super().__init__(translator)
        self.deck_service = deck_service
        self.profile_service = profile_service
        self.settings_service = settings_service
        self.maze_session_service = maze_session_service
        self.trophy_service = trophy_service
        self.run_history_service = run_history_service
        self._start_fx = GameStartFxController(self, self.settings_service)

        # Guardian movement stays intentionally slow so quiz thinking remains
        # central and gameplay stress stays moderate.
        self._guardian_timer = QTimer(self)
        self._guardian_timer.setInterval(MAZE_DIFFICULTY_PRESETS[DEFAULT_MAZE_DIFFICULTY].guardian_tick_ms)

        self._build_ui()
        self._connect_signals()
        self.update_texts()
        self._set_move_controls_enabled(False)

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

        primary_row = QHBoxLayout()
        primary_row.setSpacing(8)

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

        self._difficulty_label = QLabel()
        self._difficulty_selector = QComboBox()
        self._difficulty_selector.setMinimumHeight(30)
        self._difficulty_selector.addItem("EASY_PLACEHOLDER", "easy")
        self._difficulty_selector.addItem("NORMAL_PLACEHOLDER", "normal")
        self._difficulty_selector.addItem("HARD_PLACEHOLDER", "hard")
        self._difficulty_selector.setCurrentIndex(1)

        self._refresh_button = QPushButton()
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.setMinimumHeight(30)

        self._start_button = QPushButton()
        self._start_button.setObjectName("PrimaryButton")
        self._start_button.setMinimumHeight(32)

        primary_row.addWidget(self._deck_label)
        primary_row.addWidget(self._deck_selector, 2)
        primary_row.addWidget(self._refresh_button)
        primary_row.addWidget(self._start_button)

        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(8)
        secondary_row.addWidget(self._limit_label)
        secondary_row.addWidget(self._limit_selector, 1)
        secondary_row.addWidget(self._difficulty_label)
        secondary_row.addWidget(self._difficulty_selector, 1)
        secondary_row.addStretch(1)

        self._helper_label = QLabel()
        self._helper_label.setObjectName("PageSubtitle")
        self._helper_label.setWordWrap(True)

        controls_layout.addLayout(primary_row)
        controls_layout.addLayout(secondary_row)
        controls_layout.addWidget(self._helper_label)

        visual_panel = QFrame()
        visual_panel.setObjectName("PlaceholderPanel")
        visual_layout = QHBoxLayout(visual_panel)
        visual_layout.setContentsMargins(12, 10, 12, 10)
        visual_layout.setSpacing(12)

        self._maze_widget = MazeWidget()
        self._maze_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._maze_widget.setMinimumHeight(360)

        right_panel = QFrame()
        right_panel.setObjectName("PlaceholderPanel")
        # Keep status panel secondary so the maze scene remains the core visual.
        right_panel.setMaximumWidth(250)
        right_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        right_col = QVBoxLayout()
        right_col.setContentsMargins(10, 8, 10, 8)
        right_col.setSpacing(5)

        self._position_title_label = QLabel()
        self._position_title_label.setObjectName("SectionTitle")

        self._position_value_label = QLabel()
        self._position_value_label.setObjectName("MetricValue")
        self._position_value_label.setStyleSheet("font-size: 22px;")

        self._status_label = QLabel()
        self._status_label.setObjectName("PageSubtitle")
        self._status_label.setWordWrap(True)

        self._progress_label = QLabel()
        self._progress_label.setObjectName("PageSubtitle")

        self._path_label = QLabel()
        self._path_label.setObjectName("PageSubtitle")
        self._path_label.setWordWrap(True)

        self._distance_label = QLabel()
        self._distance_label.setObjectName("PageSubtitle")
        self._distance_label.setWordWrap(True)

        self._guardian_label = QLabel()
        self._guardian_label.setObjectName("PageSubtitle")
        self._guardian_label.setWordWrap(True)

        self._stats_label = QLabel()
        self._stats_label.setObjectName("PageSubtitle")
        self._stats_label.setWordWrap(True)

        right_col.addWidget(self._position_title_label)
        right_col.addWidget(self._position_value_label)
        right_col.addWidget(self._status_label)
        right_col.addWidget(self._progress_label)
        right_col.addWidget(self._path_label)
        right_col.addWidget(self._distance_label)
        right_col.addWidget(self._guardian_label)
        right_col.addWidget(self._stats_label)
        right_col.addStretch(1)

        right_panel.setLayout(right_col)

        # Maze remains the main visual anchor of the page.
        visual_layout.addWidget(self._maze_widget, 4)
        visual_layout.addWidget(right_panel, 1)
        visual_layout.setStretch(0, 6)
        visual_layout.setStretch(1, 2)

        movement_panel = QFrame()
        movement_panel.setObjectName("PlaceholderPanel")
        movement_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        movement_layout = QVBoxLayout(movement_panel)
        movement_layout.setContentsMargins(12, 7, 12, 7)
        movement_layout.setSpacing(4)

        self._movement_title_label = QLabel()
        self._movement_title_label.setObjectName("SectionTitle")

        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(3)

        self._forward_button = QPushButton()
        self._forward_button.setObjectName("DirectionButton")
        self._forward_button.setFixedSize(28, 28)

        self._left_button = QPushButton()
        self._left_button.setObjectName("DirectionButton")
        self._left_button.setFixedSize(28, 28)

        self._right_button = QPushButton()
        self._right_button.setObjectName("DirectionButton")
        self._right_button.setFixedSize(28, 28)

        self._backward_button = QPushButton()
        self._backward_button.setObjectName("DirectionButton")
        self._backward_button.setFixedSize(28, 28)

        grid.addWidget(self._forward_button, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._left_button, 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._right_button, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self._backward_button, 2, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        movement_layout.addWidget(self._movement_title_label)
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
        self._question_scroll.setMinimumHeight(220)
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

        self._summary_title_label = QLabel()
        self._summary_title_label.setObjectName("SectionTitle")

        self._summary_value_label = QLabel()
        self._summary_value_label.setObjectName("MetricValue")
        self._summary_value_label.setStyleSheet("font-size: 24px;")

        self._summary_details_label = QLabel()
        self._summary_details_label.setObjectName("PageSubtitle")
        self._summary_details_label.setWordWrap(True)

        self._summary_card = SessionSummaryCardWidget(self.translator)

        summary_layout.addWidget(self._summary_title_label)
        summary_layout.addWidget(self._summary_value_label)
        summary_layout.addWidget(self._summary_details_label)
        summary_layout.addWidget(self._summary_card)
        self._summary_panel.hide()

        # This dedicated interaction column prevents the maze page from
        # becoming an excessively tall stack while keeping game controls close.
        self._interaction_panel = QFrame()
        self._interaction_panel.setObjectName("PlaceholderPanel")
        # Keep maze canvas central by limiting side interaction column growth.
        self._interaction_panel.setMaximumWidth(460)
        self._interaction_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
        self._content_layout.addWidget(visual_panel, 4)
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
        self._difficulty_selector.currentIndexChanged.connect(self._on_difficulty_changed)

        self._forward_button.clicked.connect(lambda: self._on_direction_requested("forward"))
        self._backward_button.clicked.connect(lambda: self._on_direction_requested("backward"))
        self._left_button.clicked.connect(lambda: self._on_direction_requested("left"))
        self._right_button.clicked.connect(lambda: self._on_direction_requested("right"))

        self._question_card.selection_changed.connect(self._on_selection_changed)
        self._validate_button.clicked.connect(self._on_validate)
        self._next_button.clicked.connect(self._on_next)
        self._guardian_timer.timeout.connect(self._on_guardian_tick)

    def update_texts(self) -> None:
        current_deck_id = self._deck_selector.currentData()

        self._title_label.setText(self.translator.t("pages.maze.title"))
        self._description_label.setText(self.translator.t("pages.maze.description"))

        self._deck_label.setText(self.translator.t("maze_flow.deck_label"))
        self._limit_label.setText(self.translator.t("maze_flow.limit_label"))
        self._difficulty_label.setText(self.translator.t("maze_flow.difficulty_label"))
        self._limit_selector.setItemText(2, self.translator.t("maze_flow.limit_all"))
        self._difficulty_selector.setItemText(0, self.translator.t("maze_flow.difficulty_easy"))
        self._difficulty_selector.setItemText(1, self.translator.t("maze_flow.difficulty_normal"))
        self._difficulty_selector.setItemText(2, self.translator.t("maze_flow.difficulty_hard"))

        self._refresh_button.setText(self.translator.t("maze_flow.refresh_decks"))
        self._start_button.setText(self.translator.t("maze_flow.start_challenge"))

        self._position_title_label.setText(self.translator.t("maze_flow.position_title"))
        self._movement_title_label.setText(self.translator.t("maze_flow.movement_title"))

        # Per product request, movement controls use arrows for quicker reading.
        self._forward_button.setText("↑")
        self._backward_button.setText("↓")
        self._left_button.setText("←")
        self._right_button.setText("→")
        self._forward_button.setToolTip(self.translator.t("maze_flow.direction_forward"))
        self._backward_button.setToolTip(self.translator.t("maze_flow.direction_backward"))
        self._left_button.setToolTip(self.translator.t("maze_flow.direction_left"))
        self._right_button.setToolTip(self.translator.t("maze_flow.direction_right"))

        self._validate_button.setText(self.translator.t("maze_flow.validate_answer"))
        self._next_button.setText(self.translator.t("maze_flow.next_step"))

        self._summary_title_label.setText(self.translator.t("maze_flow.summary_title"))

        self._question_card.update_texts()
        self._summary_card.update_texts()

        self._sync_difficulty_selector_with_active_challenge()
        self._update_helper_text()
        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._update_status_labels()

    def showEvent(self, event: QShowEvent) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._apply_responsive_layout()
        self._update_guardian_timer_state()

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def hideEvent(self, event: QHideEvent) -> None:  # type: ignore[override]
        super().hideEvent(event)
        if self._guardian_timer.isActive():
            self._guardian_timer.stop()

    def refresh_sources(self) -> None:
        if self.maze_session_service.has_active_challenge() and not self.maze_session_service.is_finished():
            self._sync_difficulty_selector_with_active_challenge()
            self._update_maze_scene()
            self._update_status_labels()
            self._update_helper_text()
            self._update_guardian_timer_state()
            return

        current_deck_id = self._deck_selector.currentData()
        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._update_status_labels()
        self._update_helper_text()
        self._update_guardian_timer_state()

    def _on_difficulty_changed(self) -> None:
        # Difficulty only affects generation/guardian pressure, not quiz rules.
        self._update_helper_text()

    def _refresh_deck_selector(self, select_deck_id: int | None = None) -> None:
        decks = self.deck_service.list_decks()

        self._deck_selector.blockSignals(True)
        self._deck_selector.clear()

        if not decks:
            self._deck_selector.addItem(self.translator.t("maze_flow.no_decks"), None)
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
            self._set_feedback(self.translator.t("maze_flow.error_select_deck"), "error")
            return

        limit = self._limit_selector.currentData()
        difficulty_code = self._selected_difficulty_code()
        active_profile_id = self.profile_service.get_active_profile_id()

        try:
            self.maze_session_service.start_challenge_from_deck(
                deck_id=int(deck_id),
                question_limit=limit,
                shuffle_questions=True,
                difficulty_code=difficulty_code,
                profile_id=active_profile_id,
            )
        except ValueError:
            self._set_feedback(self.translator.t("maze_flow.error_runtime"), "error")
            return

        self._summary_panel.hide()
        self._question_scroll.hide()
        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(False)
        self._set_controls_enabled(False)
        self._set_move_controls_enabled(True)

        self._sync_difficulty_selector_with_active_challenge()
        self._update_maze_scene()
        self._update_status_labels()
        self._update_helper_text()
        self._update_guardian_timer_state()
        self._set_feedback(self.translator.t("maze_flow.session_started"), "info")
        self._start_fx.play(self.translator.t("maze_flow.intro_banner"))

    def _on_guardian_tick(self) -> None:
        if not self.maze_session_service.has_active_challenge():
            self._update_guardian_timer_state()
            return

        try:
            tick = self.maze_session_service.tick_guardian()
        except ValueError:
            self._update_guardian_timer_state()
            return

        self._update_maze_scene()
        self._update_status_labels()

        if tick.challenge_restarted:
            # Guardian contact resets challenge immediately so the user gets
            # a clean retry state instead of partial, confusing recovery.
            self._summary_panel.hide()
            self._question_scroll.hide()
            self._validate_button.setEnabled(False)
            self._next_button.setEnabled(False)
            self._question_card.lock_answers(True)
            self._set_controls_enabled(False)
            self._set_move_controls_enabled(True)
            self._maze_widget.pulse_move_feedback(False)
            self._sync_difficulty_selector_with_active_challenge()
            self._update_helper_text()
            self._set_feedback(
                self.translator.t("maze_flow.feedback_guardian_caught_restart", count=tick.restart_count),
                "error",
            )
            self.notify_toast(
                self.translator.t("maze_flow.feedback_guardian_caught_restart", count=tick.restart_count),
                level="warning",
                duration_ms=3000,
            )

        self._update_guardian_timer_state()

    def _on_direction_requested(self, direction: MazeDirection) -> None:
        try:
            move_request = self.maze_session_service.request_move(direction)
        except ValueError:
            self._set_feedback(self.translator.t("maze_flow.error_runtime"), "error")
            return

        if move_request.blocked_by_wall:
            # Traversability-first rule: walls block immediately, no question step.
            self._maze_widget.pulse_move_feedback(False)
            self._update_status_labels()
            self._set_feedback(self.translator.t("maze_flow.feedback_wall_blocked_immediate"), "info")
            return

        question = move_request.question
        if question is None:
            self._set_feedback(self.translator.t("maze_flow.error_no_question_for_move"), "error")
            return

        current, total = self.maze_session_service.current_question_progress()
        self._question_card.set_question(question, current, total)
        self._question_card.lock_answers(False)

        self._question_scroll.show()
        self._question_scroll.verticalScrollBar().setValue(0)

        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(False)

        self._set_move_controls_enabled(False)
        self._update_status_labels()

        direction_label = self.translator.t(f"maze_flow.direction_{direction}")
        self._set_feedback(
            self.translator.t("maze_flow.question_ready_for_direction", direction=direction_label),
            "info",
        )

    def _on_selection_changed(self) -> None:
        can_validate = (
            self.maze_session_service.has_active_challenge()
            and not self.maze_session_service.is_finished()
            and self.maze_session_service.pending_direction() is not None
            and not self.maze_session_service.current_question_is_validated()
            and self._question_card.has_selection()
        )
        self._validate_button.setEnabled(can_validate)

    def _on_validate(self) -> None:
        selected_answers = self._question_card.selected_answers()
        if not selected_answers:
            self._set_feedback(self.translator.t("maze_flow.error_select_answer"), "error")
            return

        try:
            evaluation = self.maze_session_service.validate_current_answer(selected_answers)
        except ValueError:
            self._set_feedback(self.translator.t("maze_flow.error_runtime"), "error")
            return

        self._question_card.lock_answers(True)
        self._question_card.show_feedback(
            selected_answers=evaluation.selected_answers,
            correct_answers=evaluation.correct_answers,
            explanation=evaluation.explanation,
        )

        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(not self.maze_session_service.is_finished())

        self._maze_widget.pulse_move_feedback(evaluation.moved)
        self._update_maze_scene()
        self._update_status_labels()

        if not evaluation.was_correct:
            answers = "|".join(evaluation.correct_answers)
            self._set_feedback(
                self.translator.t("maze_flow.feedback_wrong", answers=answers),
                "error",
            )
        elif evaluation.reached_exit:
            self._set_feedback(self.translator.t("maze_flow.feedback_exit_reached"), "success")
        else:
            self._set_feedback(self.translator.t("maze_flow.feedback_move_success"), "success")

        if self.maze_session_service.is_finished():
            self._finalize_challenge()

    def _on_next(self) -> None:
        try:
            moved = self.maze_session_service.go_to_next_question()
        except ValueError:
            self._set_feedback(self.translator.t("maze_flow.error_runtime"), "error")
            return

        if moved:
            self._question_scroll.hide()
            self._validate_button.setEnabled(False)
            self._next_button.setEnabled(False)
            self._set_move_controls_enabled(True)
            self._update_status_labels()
            self._set_feedback(self.translator.t("maze_flow.choose_next_direction"), "info")
            return

        self._finalize_challenge()

    def _finalize_challenge(self) -> None:
        summary = self.maze_session_service.build_summary()
        # Completed-run logging only: guardian restarts are kept inside
        # challenge state, not persisted as separate history rows.
        self.run_history_service.record_maze_completed(
            profile_id=self.maze_session_service.active_profile_id(),
            deck_id=self.maze_session_service.active_deck_id(),
            started_at=self.maze_session_service.started_at(),
            summary=summary,
        )

        self._summary_panel.show()
        if summary.did_win:
            self._summary_value_label.setText(self.translator.t("maze_flow.summary_win"))
            self._summary_value_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #39B26A;")
        else:
            self._summary_value_label.setText(self.translator.t("maze_flow.summary_loss"))
            self._summary_value_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #D95B5B;")

        self._summary_details_label.setText(
            self.translator.t(
                "maze_flow.summary_details",
                answered=summary.answered_questions,
                pool=summary.total_questions_pool,
                moves=summary.successful_moves,
                mistakes=summary.mistakes_count,
                walls=summary.wall_hits_count,
                shortest=summary.shortest_path_length,
                remaining=summary.remaining_distance,
                progress=summary.progress_percentage,
                resets=summary.guardian_restart_count,
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
        self._next_button.setEnabled(False)
        self._set_move_controls_enabled(False)
        self._set_controls_enabled(True)
        self._update_status_labels()
        self._update_helper_text()
        self._update_guardian_timer_state()

        if summary.did_win:
            unlocked = self.trophy_service.on_maze_session_completed(
                profile_id=self.maze_session_service.active_profile_id(),
                did_win=True,
            )
            if unlocked:
                names = ", ".join([item.display_name(self.translator.locale) for item in unlocked])
                self._set_feedback(
                    f"{self.translator.t('maze_flow.session_won')} "
                    f"{self.translator.t('trophies_flow.feedback_unlocked', names=names)}",
                    "success",
                )
                self.notify_toast(
                    self.translator.t("trophies_flow.feedback_unlocked", names=names),
                    level="success",
                    duration_ms=3600,
                )
            else:
                self._set_feedback(self.translator.t("maze_flow.session_won"), "success")
            self.notify_toast(
                self.translator.t("maze_flow.session_won"),
                level="success",
                duration_ms=2400,
            )
        else:
            self._set_feedback(self.translator.t("maze_flow.session_lost"), "error")
            self.notify_toast(
                self.translator.t("maze_flow.session_lost"),
                level="warning",
                duration_ms=2400,
            )

    def _update_maze_scene(self) -> None:
        if not self.maze_session_service.has_active_challenge():
            return

        self._maze_widget.set_scene(
            layout_rows=self.maze_session_service.layout_rows(),
            player_pos=self.maze_session_service.current_position(),
            guardian_pos=self.maze_session_service.guardian_position(),
            start_pos=self.maze_session_service.start_position(),
            exit_pos=self.maze_session_service.exit_position(),
            reachable_cells=self.maze_session_service.reachable_positions(),
        )

    def _update_status_labels(self) -> None:
        if not self.maze_session_service.has_active_challenge():
            self._position_value_label.setText("-")
            self._status_label.setText(self.translator.t("maze_flow.status_idle"))
            self._progress_label.setText(self.translator.t("maze_flow.progress_idle"))
            self._path_label.setText(self.translator.t("maze_flow.path_idle"))
            self._distance_label.setText(self.translator.t("maze_flow.distance_idle"))
            self._guardian_label.setText(self.translator.t("maze_flow.guardian_idle"))
            self._stats_label.setText(self.translator.t("maze_flow.stats_idle"))
            return

        row, col = self.maze_session_service.current_position()
        self._position_value_label.setText(
            self.translator.t("maze_flow.position_value", row=row + 1, col=col + 1)
        )

        shortest = self.maze_session_service.shortest_path_length()
        remaining = self.maze_session_service.minimum_distance_to_exit()
        progress = self.maze_session_service.progress_percentage()

        self._path_label.setText(
            self.translator.t(
                "maze_flow.path_progress",
                shortest=shortest,
                remaining=remaining,
                progress=progress,
            )
        )
        self._distance_label.setText(
            self.translator.t("maze_flow.distance_progress", remaining=remaining)
        )

        guardian_row, guardian_col = self.maze_session_service.guardian_position()
        self._guardian_label.setText(
            self.translator.t(
                "maze_flow.guardian_status",
                row=guardian_row + 1,
                col=guardian_col + 1,
                radius=self.maze_session_service.guardian_patrol_radius(),
                resets=self.maze_session_service.guardian_restart_count(),
            )
        )

        if self.maze_session_service.is_finished():
            if self.maze_session_service.did_win():
                self._status_label.setText(self.translator.t("maze_flow.summary_win"))
            else:
                self._status_label.setText(self.translator.t("maze_flow.summary_loss"))
            self._progress_label.setText(self.translator.t("maze_flow.progress_finished"))
        else:
            pending_direction = self.maze_session_service.pending_direction()
            if pending_direction is None:
                self._status_label.setText(self.translator.t("maze_flow.status_choose_direction"))
            else:
                direction_label = self.translator.t(f"maze_flow.direction_{pending_direction}")
                self._status_label.setText(
                    self.translator.t("maze_flow.status_answer_for_direction", direction=direction_label)
                )
            current, total = self.maze_session_service.current_question_progress()
            self._progress_label.setText(
                self.translator.t("maze_flow.progress_text", current=current, total=total)
            )

        self._stats_label.setText(
            self.translator.t(
                "maze_flow.stats_value",
                moves=self.maze_session_service.successful_moves(),
                mistakes=self.maze_session_service.mistakes_count(),
                walls=self.maze_session_service.wall_hits_count(),
                resets=self.maze_session_service.guardian_restart_count(),
            )
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._deck_selector.setEnabled(enabled)
        self._limit_selector.setEnabled(enabled)
        self._difficulty_selector.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)

        if enabled:
            self._update_start_state()
        else:
            self._start_button.setEnabled(False)

    def _set_move_controls_enabled(self, enabled: bool) -> None:
        self._forward_button.setEnabled(enabled)
        self._backward_button.setEnabled(enabled)
        self._left_button.setEnabled(enabled)
        self._right_button.setEnabled(enabled)

        if enabled:
            flash_widget(self._maze_widget, start_opacity=0.82, duration_ms=150)

    def _update_start_state(self) -> None:
        if self.maze_session_service.has_active_challenge() and not self.maze_session_service.is_finished():
            self._start_button.setEnabled(False)
            return

        self._start_button.setEnabled(self._deck_selector.currentData() is not None)

    def _update_guardian_timer_state(self) -> None:
        should_run = (
            self.isVisible()
            and self.maze_session_service.has_active_challenge()
            and not self.maze_session_service.is_finished()
        )

        if self.maze_session_service.has_active_challenge():
            self._guardian_timer.setInterval(self.maze_session_service.guardian_tick_interval_ms())

        if should_run and not self._guardian_timer.isActive():
            self._guardian_timer.start()
        elif not should_run and self._guardian_timer.isActive():
            self._guardian_timer.stop()

    def _selected_difficulty_code(self) -> str:
        code = self._difficulty_selector.currentData()
        if isinstance(code, str) and code in MAZE_DIFFICULTY_PRESETS:
            return code
        return DEFAULT_MAZE_DIFFICULTY

    def _sync_difficulty_selector_with_active_challenge(self) -> None:
        if (
            not self.maze_session_service.has_active_challenge()
            or self.maze_session_service.is_finished()
        ):
            return
        active_code = self.maze_session_service.active_difficulty_code()
        index = self._difficulty_selector.findData(active_code)
        if index < 0:
            return
        self._difficulty_selector.blockSignals(True)
        self._difficulty_selector.setCurrentIndex(index)
        self._difficulty_selector.blockSignals(False)

    def _update_helper_text(self) -> None:
        code = self._selected_difficulty_code()
        if (
            self.maze_session_service.has_active_challenge()
            and not self.maze_session_service.is_finished()
        ):
            code = self.maze_session_service.active_difficulty_code()

        self._helper_label.setText(
            f"{self.translator.t('maze_flow.helper_text')}\n"
            f"{self.translator.t(f'maze_flow.difficulty_hint_{code}')} "
            f"{self.translator.t('maze_flow.difficulty_deck_hint')}"
        )

    def _set_feedback(self, message: str, state: str) -> None:
        self._feedback_label.setText(message)
        set_feedback_visual(self._feedback_label, state)

    def _apply_responsive_layout(self) -> None:
        """Give maze canvas priority on wide windows, stack when narrow."""
        # Breakpoint uses page width after sidebar reservation.
        if self.width() < 1000:
            self._content_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._interaction_panel.setMaximumWidth(16777215)
            self._question_scroll.setMinimumHeight(220)
        else:
            self._content_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._interaction_panel.setMaximumWidth(460)
            self._question_scroll.setMinimumHeight(190)


__all__ = ["MazePage"]
