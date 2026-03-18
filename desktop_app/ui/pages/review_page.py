"""Review page with practice mode and profile-based due-today mode."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
)

from app.services.deck_service import DeckService
from app.services.profile_service import ProfileService
from app.services.quiz_session_service import QuizSessionService
from app.services.spaced_repetition_service import SpacedRepetitionService
from app.services.trophy_service import TrophyService
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.widgets.motion import set_feedback_visual
from desktop_app.ui.widgets.question_card import QuestionCardWidget
from desktop_app.ui.widgets.session_summary_card import SessionSummaryCardWidget


class ReviewPage(BasePage):
    """Quiz page supporting both practice and due-today review flows."""

    MODE_PRACTICE = "practice"
    MODE_DUE_TODAY = "due_today"

    def __init__(
        self,
        translator,
        deck_service: DeckService,
        profile_service: ProfileService,
        quiz_session_service: QuizSessionService,
        spaced_repetition_service: SpacedRepetitionService,
        trophy_service: TrophyService,
    ) -> None:
        super().__init__(translator)
        self.deck_service = deck_service
        self.profile_service = profile_service
        self.quiz_session_service = quiz_session_service
        self.spaced_repetition_service = spaced_repetition_service
        self.trophy_service = trophy_service

        self._last_due_count: int | None = None
        self._pending_unlock_names: list[str] = []
        self._feedback_state: str = "info"

        self._build_ui()
        self._connect_signals()
        self.update_texts()
        self.apply_active_profile_defaults(prefer_due_mode=False)

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        self._top_panel = QFrame()
        self._top_panel.setObjectName("PlaceholderPanel")
        self._top_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        top_layout = QVBoxLayout(self._top_panel)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(6)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        self._mode_label = QLabel()
        self._mode_selector = QComboBox()
        self._mode_selector.setMinimumHeight(30)
        self._mode_selector.addItem("PRACTICE_PLACEHOLDER", self.MODE_PRACTICE)
        self._mode_selector.addItem("DUE_PLACEHOLDER", self.MODE_DUE_TODAY)

        self._profile_label = QLabel()
        self._profile_selector = QComboBox()
        self._profile_selector.setMinimumHeight(30)

        self._refresh_button = QPushButton()
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.setMinimumHeight(30)

        mode_row.addWidget(self._mode_label)
        mode_row.addWidget(self._mode_selector, 1)
        mode_row.addWidget(self._profile_label)
        mode_row.addWidget(self._profile_selector, 1)
        mode_row.addWidget(self._refresh_button)

        deck_row = QHBoxLayout()
        deck_row.setSpacing(10)

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

        self._start_button = QPushButton()
        self._start_button.setObjectName("PrimaryButton")
        self._start_button.setMinimumHeight(32)

        deck_row.addWidget(self._deck_label)
        deck_row.addWidget(self._deck_selector, 2)
        deck_row.addWidget(self._limit_label)
        deck_row.addWidget(self._limit_selector, 1)
        deck_row.addWidget(self._start_button)

        self._mode_helper_label = QLabel()
        self._mode_helper_label.setObjectName("PageSubtitle")
        self._mode_helper_label.setWordWrap(True)

        self._due_count_label = QLabel()
        self._due_count_label.setObjectName("PageSubtitle")
        self._due_count_label.setWordWrap(True)

        self._progress_label = QLabel()
        self._progress_label.setObjectName("PageSubtitle")

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(self._mode_helper_label, 1)
        status_row.addWidget(self._due_count_label, 1)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        progress_row.addWidget(self._progress_label)
        progress_row.addWidget(self._progress_bar, 1)

        top_layout.addLayout(mode_row)
        top_layout.addLayout(deck_row)
        top_layout.addLayout(status_row)
        top_layout.addLayout(progress_row)

        self._question_card = QuestionCardWidget(self.translator)
        self._question_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        # Long questions/answers/explanations must remain readable. Wrapping
        # alone is not enough when content exceeds viewport height, so we place
        # the card in a scroll area while keeping action buttons visible.
        self._question_scroll = QScrollArea()
        self._question_scroll.setObjectName("QuestionScrollArea")
        self._question_scroll.setWidgetResizable(True)
        self._question_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._question_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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

        self._summary_card = SessionSummaryCardWidget(self.translator)
        self._summary_card.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(self._top_panel)
        layout.addWidget(self._question_scroll, 1)
        layout.addWidget(actions_panel)
        layout.addWidget(self._summary_card)

    def _connect_signals(self) -> None:
        self._start_button.clicked.connect(self._on_start_session)
        self._refresh_button.clicked.connect(self._refresh_selectors)

        self._mode_selector.currentIndexChanged.connect(self._on_mode_changed)
        self._profile_selector.currentIndexChanged.connect(self._on_filters_changed)
        self._deck_selector.currentIndexChanged.connect(self._on_filters_changed)
        self._limit_selector.currentIndexChanged.connect(self._on_filters_changed)

        self._question_card.selection_changed.connect(self._on_selection_changed)
        self._validate_button.clicked.connect(self._on_validate)
        self._next_button.clicked.connect(self._on_next)

    def update_texts(self) -> None:
        current_deck_id = self._deck_selector.currentData()
        current_profile_id = self._profile_selector.currentData()

        self._title_label.setText(self.translator.t("pages.review.title"))
        self._description_label.setText(self.translator.t("pages.review.description"))

        self._mode_label.setText(self.translator.t("review_flow.mode_label"))
        self._mode_selector.setItemText(0, self.translator.t("review_flow.mode_practice"))
        self._mode_selector.setItemText(1, self.translator.t("review_flow.mode_due_today"))

        self._profile_label.setText(self.translator.t("review_flow.profile_label"))
        self._deck_label.setText(self.translator.t("review_flow.deck_label"))
        self._limit_label.setText(self.translator.t("review_flow.limit_label"))
        self._limit_selector.setItemText(2, self.translator.t("review_flow.limit_all"))

        self._refresh_button.setText(self.translator.t("review_flow.refresh_sources"))
        self._start_button.setText(self.translator.t("review_flow.start_session"))
        self._validate_button.setText(self.translator.t("review_flow.validate_answer"))

        if self.quiz_session_service.has_active_session() and not self.quiz_session_service.is_finished():
            position, total = self.quiz_session_service.current_position()
            self._progress_label.setText(
                self.translator.t("review_flow.progress_text", current=position, total=total)
            )
        else:
            self._progress_label.setText(self.translator.t("review_flow.progress_idle"))

        self._question_card.update_texts()
        self._summary_card.update_texts()

        self._refresh_selectors(select_deck_id=current_deck_id, select_profile_id=current_profile_id)

    # ------------------------------------------------------------------
    # Source selection and mode controls
    # ------------------------------------------------------------------
    def _refresh_selectors(
        self,
        select_deck_id: int | None = None,
        select_profile_id: int | None = None,
    ) -> None:
        self._refresh_deck_selector(select_deck_id=select_deck_id)
        self._refresh_profile_selector(select_profile_id=select_profile_id)
        self._apply_mode_ui()
        self._update_due_count_display()

    def _refresh_deck_selector(self, select_deck_id: int | None = None) -> None:
        decks = self.deck_service.list_decks()

        self._deck_selector.blockSignals(True)
        self._deck_selector.clear()

        if not decks:
            self._deck_selector.addItem(self.translator.t("review_flow.no_decks"), None)
        else:
            for deck in decks:
                label = deck.name if not deck.category else f"{deck.name} ({deck.category})"
                self._deck_selector.addItem(label, deck.id)

        if select_deck_id is not None:
            index = self._deck_selector.findData(select_deck_id)
            if index >= 0:
                self._deck_selector.setCurrentIndex(index)

        self._deck_selector.blockSignals(False)

    def _refresh_profile_selector(self, select_profile_id: int | None = None) -> None:
        profiles = self.profile_service.list_profiles()
        active_profile_id = self.profile_service.get_active_profile_id()
        target_profile_id = select_profile_id if select_profile_id is not None else active_profile_id

        self._profile_selector.blockSignals(True)
        self._profile_selector.clear()

        if not profiles:
            self._profile_selector.addItem(self.translator.t("review_flow.no_profiles"), None)
        else:
            for profile in profiles:
                self._profile_selector.addItem(profile.name, profile.id)

        if target_profile_id is not None:
            index = self._profile_selector.findData(target_profile_id)
            if index >= 0:
                self._profile_selector.setCurrentIndex(index)

        self._profile_selector.blockSignals(False)

    def apply_active_profile_defaults(self, prefer_due_mode: bool = False) -> None:
        """Apply active profile defaults without forcing the user permanently.

        Review stays flexible: the learner can still switch profile or mode
        manually, but this helper reduces clicks for the common "review due now"
        path from the dashboard.
        """
        if self.quiz_session_service.has_active_session() and not self.quiz_session_service.is_finished():
            return

        active_profile_id = self.profile_service.get_active_profile_id()
        self._refresh_profile_selector(select_profile_id=active_profile_id)

        if prefer_due_mode and active_profile_id is not None:
            due_mode_index = self._mode_selector.findData(self.MODE_DUE_TODAY)
            if due_mode_index >= 0:
                self._mode_selector.setCurrentIndex(due_mode_index)
        elif prefer_due_mode and active_profile_id is None:
            self._set_feedback(self.translator.t("review_flow.no_active_profile"), "info")

        self._apply_mode_ui()
        self._update_due_count_display()

    def apply_due_mode_defaults(self, profile_id: int | None, deck_id: int | None) -> None:
        """Prefill review page for deck-focused due launches from dashboard.

        We intentionally do not auto-start the session. Prefilling keeps the
        flow fast while still letting learners confirm context before launching.
        """
        if self.quiz_session_service.has_active_session() and not self.quiz_session_service.is_finished():
            return

        self._refresh_selectors(select_deck_id=deck_id, select_profile_id=profile_id)

        due_mode_index = self._mode_selector.findData(self.MODE_DUE_TODAY)
        if due_mode_index >= 0:
            self._mode_selector.setCurrentIndex(due_mode_index)

        self._apply_mode_ui()
        self._update_due_count_display()

        profile_found = profile_id is None or self._profile_selector.findData(profile_id) >= 0
        deck_found = deck_id is None or self._deck_selector.findData(deck_id) >= 0

        if not profile_found:
            self._set_feedback(self.translator.t("review_flow.prefill_profile_missing"), "error")
            return
        if not deck_found:
            self._set_feedback(self.translator.t("review_flow.prefill_deck_missing"), "error")
            return

        if self._last_due_count == 0:
            self._set_feedback(self.translator.t("review_flow.prefill_no_due_for_deck"), "info")
            return

        self._set_feedback(self.translator.t("review_flow.prefill_ready_due"), "success")

    def _on_mode_changed(self) -> None:
        self._apply_mode_ui()
        self._update_due_count_display()

    def _on_filters_changed(self) -> None:
        self._update_due_count_display()

    def _apply_mode_ui(self) -> None:
        is_due_mode = self._current_mode() == self.MODE_DUE_TODAY

        # Profile is required only for due sessions because progress state is
        # profile-specific. Practice mode intentionally does not need one.
        self._profile_label.setEnabled(is_due_mode)
        self._profile_selector.setEnabled(is_due_mode)

        if is_due_mode:
            self._mode_helper_label.setText(self.translator.t("review_flow.helper_due"))
        else:
            self._mode_helper_label.setText(self.translator.t("review_flow.helper_practice"))

    def _update_due_count_display(self) -> None:
        mode = self._current_mode()
        deck_id = self._deck_selector.currentData()
        profile_id = self._profile_selector.currentData()
        limit = self._limit_selector.currentData()

        if mode == self.MODE_PRACTICE:
            self._last_due_count = None
            self._due_count_label.setText(self.translator.t("review_flow.due_count_practice"))
            self._update_start_button_state()
            return

        if deck_id is None or profile_id is None:
            self._last_due_count = None
            self._due_count_label.setText(self.translator.t("review_flow.due_count_missing"))
            self._update_start_button_state()
            return

        try:
            due_questions = self.spaced_repetition_service.get_due_questions(
                profile_id=int(profile_id),
                deck_id=int(deck_id),
                as_of=None,
                limit=None,
            )
        except Exception:
            self._last_due_count = None
            self._due_count_label.setText(self.translator.t("review_flow.due_count_error"))
            self._update_start_button_state()
            return

        due_total = len(due_questions)
        self._last_due_count = due_total

        if due_total == 0:
            self._due_count_label.setText(self.translator.t("review_flow.due_count_none"))
            self._update_start_button_state()
            return

        session_count = due_total if limit is None else min(due_total, int(limit))
        self._due_count_label.setText(
            self.translator.t("review_flow.due_count_value", due=due_total, session=session_count)
        )
        self._update_start_button_state()

    def _update_start_button_state(self) -> None:
        mode = self._current_mode()
        has_deck = self._deck_selector.currentData() is not None

        if mode == self.MODE_PRACTICE:
            self._start_button.setEnabled(has_deck)
            return

        has_profile = self._profile_selector.currentData() is not None
        has_due = self._last_due_count is not None and self._last_due_count > 0
        self._start_button.setEnabled(has_deck and has_profile and has_due)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._mode_selector.setEnabled(enabled)
        self._profile_selector.setEnabled(enabled and self._current_mode() == self.MODE_DUE_TODAY)
        self._deck_selector.setEnabled(enabled)
        self._limit_selector.setEnabled(enabled)
        self._refresh_button.setEnabled(enabled)

        # Start button availability depends on current filters/mode, not only on
        # previous widget state. Recompute explicitly to avoid sticky disabled UI.
        if enabled:
            self._update_start_button_state()
        else:
            self._start_button.setEnabled(False)

    def _current_mode(self) -> str:
        mode = self._mode_selector.currentData()
        if isinstance(mode, str):
            return mode
        return self.MODE_PRACTICE

    # ------------------------------------------------------------------
    # Session start/flow
    # ------------------------------------------------------------------
    def _on_start_session(self) -> None:
        mode = self._current_mode()
        deck_id = self._deck_selector.currentData()
        if deck_id is None:
            self._set_feedback(self.translator.t("review_flow.error_select_deck"), "error")
            return

        limit = self._limit_selector.currentData()

        if mode == self.MODE_PRACTICE:
            self._start_practice_session(deck_id=int(deck_id), question_limit=limit)
            return

        self._start_due_today_session(deck_id=int(deck_id), question_limit=limit)

    def _start_practice_session(self, deck_id: int, question_limit: int | None) -> None:
        self._pending_unlock_names = []
        active_profile_id = self.profile_service.get_active_profile_id()
        try:
            # Product choice: practice mode does NOT alter SRS progress.
            # We still pass active_profile_id when available so question order
            # can prioritize previously failed items for that learner.
            self.quiz_session_service.start_session_from_deck(
                deck_id=deck_id,
                question_limit=question_limit,
                shuffle_questions=False,
                session_source=self.MODE_PRACTICE,
                profile_id=active_profile_id,
                prioritize_failed_first=True,
                record_progress_on_validate=False,
                progress_update_callback=None,
            )
        except ValueError:
            # Avoid leaking raw service exceptions (often English) into
            # localized UI. We keep runtime feedback fully translated.
            self._set_feedback(self.translator.t("review_flow.error_runtime"), "error")
            return

        self._summary_card.hide()
        self._show_current_question()
        self._set_feedback(self.translator.t("review_flow.session_started_practice"), "info")
        self._set_controls_enabled(False)

    def _start_due_today_session(self, deck_id: int, question_limit: int | None) -> None:
        self._pending_unlock_names = []
        profile_id = self._profile_selector.currentData()
        if profile_id is None:
            self._set_feedback(self.translator.t("review_flow.error_select_profile"), "error")
            return

        try:
            due_questions = self.spaced_repetition_service.get_due_questions(
                profile_id=int(profile_id),
                deck_id=deck_id,
                as_of=None,
                # We fetch the full due pool first, then session ordering can
                # prioritize failed questions before applying any limit.
                limit=None,
            )
        except ValueError:
            self._set_feedback(self.translator.t("review_flow.error_runtime"), "error")
            return

        if not due_questions:
            self._set_feedback(self.translator.t("review_flow.no_due_questions"), "info")
            self._summary_card.hide()
            self._question_scroll.hide()
            return

        deck = self.deck_service.get_deck_by_id(deck_id)
        deck_name = deck.name if deck is not None else self._deck_selector.currentText()

        try:
            self.quiz_session_service.start_session_from_questions(
                deck_id=deck_id,
                deck_name=deck_name,
                questions=due_questions,
                question_limit=question_limit,
                shuffle_questions=False,
                session_source=self.MODE_DUE_TODAY,
                profile_id=int(profile_id),
                prioritize_failed_first=True,
                record_progress_on_validate=True,
                progress_update_callback=self._build_progress_callback(profile_id=int(profile_id)),
            )
        except ValueError:
            self._set_feedback(self.translator.t("review_flow.error_runtime"), "error")
            return

        self._summary_card.hide()
        self._show_current_question()
        self._set_feedback(self.translator.t("review_flow.session_started_due"), "info")
        self._set_controls_enabled(False)

    def _build_progress_callback(self, profile_id: int):
        # The callback is executed by QuizSessionService immediately after each
        # validated answer in due mode, making SRS writes explicit and traceable.
        def _callback(
            question_id: int,
            was_correct: bool,
            reviewed_at: datetime,
            response_time_seconds: float,
        ) -> None:
            self.spaced_repetition_service.record_review_result(
                profile_id=profile_id,
                question_id=question_id,
                was_correct=was_correct,
                response_time_seconds=response_time_seconds,
                reviewed_at=reviewed_at,
            )

            # Trophy evaluation is kept in a dedicated service so UI remains
            # declarative: this page only reacts to newly unlocked names.
            unlocked = self.trophy_service.on_due_answer_recorded(
                profile_id=profile_id,
                question_id=question_id,
                was_correct=was_correct,
            )
            self._pending_unlock_names.extend(
                [item.display_name(self.translator.locale) for item in unlocked]
            )

        return _callback

    def _show_current_question(self) -> None:
        question = self.quiz_session_service.current_question()
        if question is None:
            return

        position, total = self.quiz_session_service.current_position()
        self._question_card.set_question(question, position, total)
        self._question_card.lock_answers(False)
        self._question_scroll.show()
        self._question_scroll.verticalScrollBar().setValue(0)

        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(False)
        self._next_button.setText(self.translator.t("review_flow.next_question"))

        self._update_progress_widgets()

    def _on_selection_changed(self) -> None:
        # Validate should be available only if user selected at least one option.
        can_validate = (
            self.quiz_session_service.has_active_session()
            and not self.quiz_session_service.is_finished()
            and not self.quiz_session_service.current_question_is_validated()
            and self._question_card.has_selection()
        )
        self._validate_button.setEnabled(can_validate)

    def _on_validate(self) -> None:
        selected_answers = self._question_card.selected_answers()
        if not selected_answers:
            self._set_feedback(self.translator.t("review_flow.error_select_answer"), "error")
            return

        try:
            evaluation = self.quiz_session_service.validate_current_answer(selected_answers)
        except ValueError:
            self._set_feedback(self.translator.t("review_flow.error_runtime"), "error")
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
            self._set_feedback(self.translator.t("review_flow.feedback_correct"), "success")
        else:
            correct_text = "|".join(evaluation.correct_answers)
            self._set_feedback(
                self.translator.t("review_flow.feedback_wrong", answers=correct_text),
                "error",
            )

        # Keep unlock feedback subtle: append it to existing answer feedback
        # instead of interrupting the quiz flow with modal dialogs.
        self._append_pending_unlock_feedback()

        position, total = self.quiz_session_service.current_position()
        if position >= total:
            self._next_button.setText(self.translator.t("review_flow.finish_session"))
        else:
            self._next_button.setText(self.translator.t("review_flow.next_question"))

        self._update_progress_widgets()

    def _on_next(self) -> None:
        try:
            moved = self.quiz_session_service.go_to_next_question()
        except ValueError as exc:
            self._set_feedback(self.translator.t("review_flow.error_runtime"), "error")
            return

        if moved:
            self._show_current_question()
            self._set_feedback(self.translator.t("review_flow.feedback_next_ready"), "info")
            return

        summary = self.quiz_session_service.build_summary()
        self._summary_card.set_summary(summary)
        self._summary_card.show()
        self._question_scroll.hide()

        self._validate_button.setEnabled(False)
        self._next_button.setEnabled(False)
        self._next_button.setText(self.translator.t("review_flow.finish_session"))

        session_source = self.quiz_session_service.active_session_source() or self.MODE_PRACTICE
        session_profile_id = self.quiz_session_service.active_profile_id()
        if session_profile_id is None:
            # Practice sessions can still reward the currently active learner.
            session_profile_id = self.profile_service.get_active_profile_id()

        unlocked = self.trophy_service.on_review_session_completed(
            profile_id=session_profile_id,
            summary=summary,
            session_source=session_source,
        )
        unlocked_names = [item.display_name(self.translator.locale) for item in unlocked]
        finished_message = self._with_unlock_feedback(
            self.translator.t("review_flow.session_finished"),
            unlocked_names,
        )
        self._set_feedback(finished_message, "success")
        self.notify_toast(self.translator.t("review_flow.session_finished"), level="success")
        if unlocked_names:
            self.notify_toast(
                self.translator.t(
                    "trophies_flow.feedback_unlocked",
                    names=", ".join(unlocked_names),
                ),
                level="success",
                duration_ms=3400,
            )
        self._update_progress_widgets(final=True)

        self._set_controls_enabled(True)
        self._update_due_count_display()

    def _update_progress_widgets(self, final: bool = False) -> None:
        if not self.quiz_session_service.has_active_session():
            self._progress_bar.setValue(0)
            self._progress_label.setText(self.translator.t("review_flow.progress_idle"))
            return

        position, total = self.quiz_session_service.current_position()
        answered = self.quiz_session_service.answered_count()

        percent = int((answered / total) * 100) if total else 0
        self._progress_bar.setValue(percent)

        if final:
            self._progress_label.setText(self.translator.t("review_flow.progress_completed"))
        else:
            self._progress_label.setText(
                self.translator.t("review_flow.progress_text", current=position, total=total)
            )

    def _set_feedback(self, message: str, state: str) -> None:
        self._feedback_state = state
        self._feedback_label.setText(message)
        # Styling remains CSS-driven; this helper only flips semantic state and
        # applies a tiny opacity pulse so updates feel responsive but calm.
        set_feedback_visual(self._feedback_label, state)

    def _append_pending_unlock_feedback(self) -> None:
        if not self._pending_unlock_names:
            return

        unlock_message = self.translator.t(
            "trophies_flow.feedback_unlocked",
            names=", ".join(self._pending_unlock_names),
        )
        current = self._feedback_label.text().strip()
        combined = f"{current} {unlock_message}".strip()
        # Preserve the existing message severity (for example incorrect answer
        # should stay red even if a milestone trophy also unlocks).
        self._set_feedback(combined, self._feedback_state)
        self.notify_toast(unlock_message, level="success", duration_ms=3200)
        self._pending_unlock_names = []

    def _with_unlock_feedback(self, base_message: str, unlocked_names: list[str]) -> str:
        if not unlocked_names:
            return base_message
        unlock_message = self.translator.t(
            "trophies_flow.feedback_unlocked",
            names=", ".join(unlocked_names),
        )
        return f"{base_message} {unlock_message}"
