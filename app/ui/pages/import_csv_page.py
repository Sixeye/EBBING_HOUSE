"""CSV import page with validation, preview, and database insertion workflow."""

from __future__ import annotations

import html
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QResizeEvent, QTextListFormat
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QToolButton,
    QSpinBox,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.models.csv_preview import CsvValidationIssue, CsvValidationResult
from app.models.question import Question
from app.core.paths import resolve_media_reference
from app.services.csv_import_service import CsvImportService
from app.services.csv_validation_service import CsvValidationService
from app.services.deck_service import DeckService
from app.services.profile_service import ProfileService
from app.services.question_authoring_service import QuestionAuthoringService
from app.services.question_import_service import QuestionImportService
from app.services.trophy_service import TrophyService
from app.ui.pages.base_page import BasePage
from app.ui.widgets.motion import set_feedback_visual


class ImportCsvPage(BasePage):
    """Practical import workflow for non-technical users.

    This page keeps the flow linear and explicit:
    1) select file, 2) validate+preview, 3) choose/create deck, 4) import.
    """

    PREVIEW_LIMIT = 200

    def __init__(
        self,
        translator,
        csv_import_service: CsvImportService,
        csv_validation_service: CsvValidationService,
        question_import_service: QuestionImportService,
        question_authoring_service: QuestionAuthoringService,
        deck_service: DeckService,
        profile_service: ProfileService,
        trophy_service: TrophyService,
    ) -> None:
        super().__init__(translator)

        self.csv_import_service = csv_import_service
        self.csv_validation_service = csv_validation_service
        self.question_import_service = question_import_service
        self.question_authoring_service = question_authoring_service
        self.deck_service = deck_service
        self.profile_service = profile_service
        self.trophy_service = trophy_service

        self._selected_file_path: str = ""
        self._validation_result: CsvValidationResult | None = None
        self._editing_question_id: int | None = None
        self._manual_questions_by_id: dict[int, Question] = {}
        self._manual_question_image_source: str | None = None
        self._manual_explanation_image_source: str | None = None
        # This page can be opened from three clear menu entries:
        # - import_csv
        # - decks
        # - questions
        # We reuse one implementation and switch visible focus context.
        self._navigation_context = "import"

        self._build_ui()
        self._connect_signals()
        self._refresh_deck_selector()
        self.update_texts()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        self._context_hint_label = QLabel()
        self._context_hint_label.setObjectName("PageSubtitle")
        self._context_hint_label.setWordWrap(True)

        # Help stays close to the import flow so non-technical users do not
        # need external docs before preparing their CSV files.
        self._help_panel = QFrame()
        self._help_panel.setObjectName("PlaceholderPanel")
        help_layout = QVBoxLayout(self._help_panel)
        help_layout.setContentsMargins(12, 10, 12, 10)
        help_layout.setSpacing(6)

        self._help_title_label = QLabel()
        self._help_title_label.setObjectName("SectionTitle")

        self._help_description_label = QLabel()
        self._help_description_label.setObjectName("PageSubtitle")
        self._help_description_label.setWordWrap(True)

        self._help_conventions_label = QLabel()
        self._help_conventions_label.setObjectName("PageSubtitle")
        self._help_conventions_label.setWordWrap(True)

        self._help_example_title_label = QLabel()
        self._help_example_title_label.setObjectName("SectionTitle")

        self._help_example_value_label = QLabel()
        self._help_example_value_label.setObjectName("PageSubtitle")
        self._help_example_value_label.setWordWrap(True)
        self._help_example_value_label.setTextFormat(Qt.TextFormat.PlainText)
        self._help_example_value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._help_fields_table = QTableWidget()
        self._help_fields_table.setMinimumHeight(190)
        self._help_fields_table.setColumnCount(3)
        self._help_fields_table.verticalHeader().setVisible(False)
        self._help_fields_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._help_fields_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._help_fields_table.setAlternatingRowColors(True)
        self._help_fields_table.setWordWrap(True)
        self._help_fields_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._help_fields_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._help_fields_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._help_fields_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        template_buttons_row = QHBoxLayout()
        template_buttons_row.setSpacing(10)

        self._template_blank_button = QPushButton()
        self._template_blank_button.setObjectName("SecondaryButton")
        self._template_blank_button.setMinimumHeight(32)

        self._template_example_button = QPushButton()
        self._template_example_button.setObjectName("SecondaryButton")
        self._template_example_button.setMinimumHeight(32)

        self._template_status_label = QLabel()
        self._template_status_label.setObjectName("PageSubtitle")
        self._template_status_label.setWordWrap(True)

        template_buttons_row.addWidget(self._template_blank_button)
        template_buttons_row.addWidget(self._template_example_button)
        template_buttons_row.addWidget(self._template_status_label, 1)

        help_layout.addWidget(self._help_title_label)
        help_layout.addWidget(self._help_description_label)
        help_layout.addWidget(self._help_conventions_label)
        help_layout.addWidget(self._help_fields_table)
        help_layout.addWidget(self._help_example_title_label)
        help_layout.addWidget(self._help_example_value_label)
        help_layout.addLayout(template_buttons_row)

        self._controls_panel = QFrame()
        self._controls_panel.setObjectName("PlaceholderPanel")
        controls_layout = QVBoxLayout(self._controls_panel)
        controls_layout.setContentsMargins(12, 10, 12, 10)
        controls_layout.setSpacing(6)

        self._file_section_label = QLabel()
        self._file_section_label.setObjectName("SectionTitle")

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        self._choose_file_button = QPushButton()
        self._choose_file_button.setObjectName("SecondaryButton")
        self._choose_file_button.setMinimumHeight(32)

        self._selected_file_label = QLabel()
        self._selected_file_label.setObjectName("PageSubtitle")
        self._selected_file_label.setWordWrap(True)

        file_row.addWidget(self._choose_file_button)
        file_row.addWidget(self._selected_file_label, 1)

        validation_row = QHBoxLayout()
        validation_row.setSpacing(10)

        self._validate_button = QPushButton()
        self._validate_button.setObjectName("SecondaryButton")
        self._validate_button.setMinimumHeight(32)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("PageSubtitle")
        self._summary_label.setWordWrap(True)

        validation_row.addWidget(self._validate_button)
        validation_row.addWidget(self._summary_label, 1)

        self._deck_section_label = QLabel()
        self._deck_section_label.setObjectName("SectionTitle")

        deck_row = QHBoxLayout()
        deck_row.setSpacing(10)

        self._deck_select_label = QLabel()

        self._deck_selector = QComboBox()
        self._deck_selector.setMinimumHeight(32)

        self._refresh_decks_button = QPushButton()
        self._refresh_decks_button.setObjectName("SecondaryButton")
        self._refresh_decks_button.setMinimumHeight(32)

        deck_row.addWidget(self._deck_select_label)
        deck_row.addWidget(self._deck_selector, 1)
        deck_row.addWidget(self._refresh_decks_button)

        self._create_deck_section_label = QLabel()
        self._create_deck_section_label.setObjectName("SectionTitle")

        create_deck_row = QHBoxLayout()
        create_deck_row.setSpacing(10)

        self._new_deck_name_input = QLineEdit()
        self._new_deck_name_input.setMinimumHeight(32)

        self._new_deck_category_input = QLineEdit()
        self._new_deck_category_input.setMinimumHeight(32)

        self._create_deck_button = QPushButton()
        self._create_deck_button.setObjectName("SecondaryButton")
        self._create_deck_button.setMinimumHeight(32)

        create_deck_row.addWidget(self._new_deck_name_input, 2)
        create_deck_row.addWidget(self._new_deck_category_input, 1)
        create_deck_row.addWidget(self._create_deck_button)

        self._manage_deck_section_label = QLabel()
        self._manage_deck_section_label.setObjectName("SectionTitle")

        manage_deck_row = QHBoxLayout()
        manage_deck_row.setSpacing(10)

        self._edit_deck_name_input = QLineEdit()
        self._edit_deck_name_input.setMinimumHeight(32)

        self._edit_deck_category_input = QLineEdit()
        self._edit_deck_category_input.setMinimumHeight(32)

        self._edit_deck_description_input = QLineEdit()
        self._edit_deck_description_input.setMinimumHeight(32)

        manage_deck_row.addWidget(self._edit_deck_name_input, 2)
        manage_deck_row.addWidget(self._edit_deck_category_input, 1)
        manage_deck_row.addWidget(self._edit_deck_description_input, 2)

        manage_deck_actions = QHBoxLayout()
        manage_deck_actions.setSpacing(10)

        self._update_deck_button = QPushButton()
        self._update_deck_button.setObjectName("SecondaryButton")
        self._update_deck_button.setMinimumHeight(32)

        self._delete_deck_button = QPushButton()
        self._delete_deck_button.setObjectName("SecondaryButton")
        self._delete_deck_button.setMinimumHeight(32)

        self._deck_manage_status_label = QLabel()
        self._deck_manage_status_label.setObjectName("FeedbackLabel")
        self._deck_manage_status_label.setProperty("feedbackState", "info")
        self._deck_manage_status_label.setWordWrap(True)

        manage_deck_actions.addWidget(self._update_deck_button)
        manage_deck_actions.addWidget(self._delete_deck_button)
        manage_deck_actions.addWidget(self._deck_manage_status_label, 1)

        import_row = QHBoxLayout()
        import_row.setSpacing(10)

        self._import_button = QPushButton()
        self._import_button.setObjectName("PrimaryButton")
        self._import_button.setMinimumHeight(34)
        self._import_button.setEnabled(False)

        self._import_status_label = QLabel()
        self._import_status_label.setObjectName("PageSubtitle")
        self._import_status_label.setWordWrap(True)

        import_row.addWidget(self._import_button)
        import_row.addWidget(self._import_status_label, 1)

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setProperty("feedbackState", "info")
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        controls_layout.addWidget(self._file_section_label)
        controls_layout.addLayout(file_row)
        controls_layout.addLayout(validation_row)
        controls_layout.addWidget(self._deck_section_label)
        controls_layout.addLayout(deck_row)
        controls_layout.addWidget(self._create_deck_section_label)
        controls_layout.addLayout(create_deck_row)
        controls_layout.addWidget(self._manage_deck_section_label)
        controls_layout.addLayout(manage_deck_row)
        controls_layout.addLayout(manage_deck_actions)
        controls_layout.addLayout(import_row)
        controls_layout.addWidget(self._feedback_label)

        self._manual_panel = QFrame()
        self._manual_panel.setObjectName("PlaceholderPanel")
        manual_layout = QVBoxLayout(self._manual_panel)
        manual_layout.setContentsMargins(12, 10, 12, 10)
        manual_layout.setSpacing(6)

        self._manual_section_label = QLabel()
        self._manual_section_label.setObjectName("SectionTitle")

        manual_top_row = QHBoxLayout()
        manual_top_row.setSpacing(10)

        self._manual_mode_label = QLabel()
        self._manual_mode_selector = QComboBox()
        self._manual_mode_selector.setMinimumHeight(32)
        self._manual_mode_selector.addItem("single_choice", "single_choice")
        self._manual_mode_selector.addItem("multiple_choice", "multiple_choice")

        self._manual_difficulty_label = QLabel()
        self._manual_difficulty_spin = QSpinBox()
        self._manual_difficulty_spin.setMinimumHeight(32)
        self._manual_difficulty_spin.setRange(1, 5)
        self._manual_difficulty_spin.setValue(1)

        self._manual_category_input = QLineEdit()
        self._manual_category_input.setMinimumHeight(32)

        manual_top_row.addWidget(self._manual_mode_label)
        manual_top_row.addWidget(self._manual_mode_selector, 1)
        manual_top_row.addWidget(self._manual_difficulty_label)
        manual_top_row.addWidget(self._manual_difficulty_spin)
        manual_top_row.addWidget(self._manual_category_input, 2)

        self._manual_question_label = QLabel()
        self._manual_question_label.setObjectName("SectionTitle")
        self._manual_question_input = QTextEdit()
        self._manual_question_input.setMinimumHeight(112)
        self._manual_question_input.setAcceptRichText(True)

        # Lightweight rich-text toolbar: enough for educational authoring
        # without becoming a full word-processor UI.
        rich_toolbar = QHBoxLayout()
        rich_toolbar.setSpacing(6)
        self._manual_rich_label = QLabel()
        self._manual_rich_bold_button = QToolButton()
        self._manual_rich_italic_button = QToolButton()
        self._manual_rich_underline_button = QToolButton()
        self._manual_rich_bullets_button = QToolButton()
        for button in (
            self._manual_rich_bold_button,
            self._manual_rich_italic_button,
            self._manual_rich_underline_button,
            self._manual_rich_bullets_button,
        ):
            button.setObjectName("SecondaryButton")
            button.setAutoRaise(False)
            button.setMinimumSize(30, 30)
        rich_toolbar.addWidget(self._manual_rich_label)
        rich_toolbar.addWidget(self._manual_rich_bold_button)
        rich_toolbar.addWidget(self._manual_rich_italic_button)
        rich_toolbar.addWidget(self._manual_rich_underline_button)
        rich_toolbar.addWidget(self._manual_rich_bullets_button)
        rich_toolbar.addStretch(1)

        question_image_controls = QHBoxLayout()
        question_image_controls.setSpacing(8)
        self._manual_question_image_label = QLabel()
        self._manual_question_image_choose_button = QPushButton()
        self._manual_question_image_choose_button.setObjectName("SecondaryButton")
        self._manual_question_image_choose_button.setMinimumHeight(30)
        self._manual_question_image_clear_button = QPushButton()
        self._manual_question_image_clear_button.setObjectName("SecondaryButton")
        self._manual_question_image_clear_button.setMinimumHeight(30)
        question_image_controls.addWidget(self._manual_question_image_label)
        question_image_controls.addWidget(self._manual_question_image_choose_button)
        question_image_controls.addWidget(self._manual_question_image_clear_button)
        question_image_controls.addStretch(1)

        self._manual_question_image_preview = QLabel()
        self._manual_question_image_preview.setObjectName("ImagePreview")
        self._manual_question_image_preview.setMinimumHeight(110)
        self._manual_question_image_preview.setMaximumHeight(160)
        self._manual_question_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._manual_question_image_preview.setWordWrap(True)

        self._manual_choice_a_input = QLineEdit()
        self._manual_choice_a_input.setMinimumHeight(32)
        self._manual_choice_b_input = QLineEdit()
        self._manual_choice_b_input.setMinimumHeight(32)
        self._manual_choice_c_input = QLineEdit()
        self._manual_choice_c_input.setMinimumHeight(32)
        self._manual_choice_d_input = QLineEdit()
        self._manual_choice_d_input.setMinimumHeight(32)

        choices_row_1 = QHBoxLayout()
        choices_row_1.setSpacing(10)
        choices_row_1.addWidget(self._manual_choice_a_input, 1)
        choices_row_1.addWidget(self._manual_choice_b_input, 1)

        choices_row_2 = QHBoxLayout()
        choices_row_2.setSpacing(10)
        choices_row_2.addWidget(self._manual_choice_c_input, 1)
        choices_row_2.addWidget(self._manual_choice_d_input, 1)

        self._manual_correct_label = QLabel()
        self._manual_correct_label.setObjectName("SectionTitle")
        correct_row = QHBoxLayout()
        correct_row.setSpacing(10)
        self._correct_a_checkbox = QCheckBox("A")
        self._correct_b_checkbox = QCheckBox("B")
        self._correct_c_checkbox = QCheckBox("C")
        self._correct_d_checkbox = QCheckBox("D")
        self._manual_correct_checkboxes = {
            "A": self._correct_a_checkbox,
            "B": self._correct_b_checkbox,
            "C": self._correct_c_checkbox,
            "D": self._correct_d_checkbox,
        }
        for checkbox in self._manual_correct_checkboxes.values():
            correct_row.addWidget(checkbox)
        correct_row.addStretch(1)

        self._manual_explanation_input = QTextEdit()
        self._manual_explanation_input.setMinimumHeight(94)
        self._manual_explanation_input.setAcceptRichText(True)
        self._manual_explanation_label = QLabel()
        self._manual_explanation_label.setObjectName("SectionTitle")

        explanation_image_controls = QHBoxLayout()
        explanation_image_controls.setSpacing(8)
        self._manual_explanation_image_label = QLabel()
        self._manual_explanation_image_choose_button = QPushButton()
        self._manual_explanation_image_choose_button.setObjectName("SecondaryButton")
        self._manual_explanation_image_choose_button.setMinimumHeight(30)
        self._manual_explanation_image_clear_button = QPushButton()
        self._manual_explanation_image_clear_button.setObjectName("SecondaryButton")
        self._manual_explanation_image_clear_button.setMinimumHeight(30)
        explanation_image_controls.addWidget(self._manual_explanation_image_label)
        explanation_image_controls.addWidget(self._manual_explanation_image_choose_button)
        explanation_image_controls.addWidget(self._manual_explanation_image_clear_button)
        explanation_image_controls.addStretch(1)

        self._manual_explanation_image_preview = QLabel()
        self._manual_explanation_image_preview.setObjectName("ImagePreview")
        self._manual_explanation_image_preview.setMinimumHeight(96)
        self._manual_explanation_image_preview.setMaximumHeight(146)
        self._manual_explanation_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._manual_explanation_image_preview.setWordWrap(True)

        self._manual_tags_input = QLineEdit()
        self._manual_tags_input.setMinimumHeight(32)

        manual_actions_row = QHBoxLayout()
        manual_actions_row.setSpacing(10)
        self._manual_save_button = QPushButton()
        self._manual_save_button.setObjectName("PrimaryButton")
        self._manual_save_button.setMinimumHeight(34)
        self._manual_clear_button = QPushButton()
        self._manual_clear_button.setObjectName("SecondaryButton")
        self._manual_clear_button.setMinimumHeight(34)
        manual_actions_row.addWidget(self._manual_save_button)
        manual_actions_row.addWidget(self._manual_clear_button)
        manual_actions_row.addStretch(1)

        self._manual_feedback_label = QLabel()
        self._manual_feedback_label.setObjectName("FeedbackLabel")
        self._manual_feedback_label.setProperty("feedbackState", "info")
        self._manual_feedback_label.setWordWrap(True)

        self._manual_list_title_label = QLabel()
        self._manual_list_title_label.setObjectName("SectionTitle")

        self._manual_questions_table = QTableWidget()
        self._manual_questions_table.setMinimumHeight(170)
        self._manual_questions_table.setColumnCount(7)
        self._manual_questions_table.verticalHeader().setVisible(False)
        self._manual_questions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._manual_questions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._manual_questions_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._manual_questions_table.setAlternatingRowColors(True)
        self._manual_questions_table.setWordWrap(True)
        self._manual_questions_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._manual_questions_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        manual_list_actions = QHBoxLayout()
        manual_list_actions.setSpacing(10)
        self._manual_refresh_list_button = QPushButton()
        self._manual_refresh_list_button.setObjectName("SecondaryButton")
        self._manual_refresh_list_button.setMinimumHeight(32)
        self._manual_edit_button = QPushButton()
        self._manual_edit_button.setObjectName("SecondaryButton")
        self._manual_edit_button.setMinimumHeight(32)
        self._manual_edit_button.setEnabled(False)
        self._manual_delete_button = QPushButton()
        self._manual_delete_button.setObjectName("SecondaryButton")
        self._manual_delete_button.setMinimumHeight(32)
        self._manual_delete_button.setEnabled(False)
        manual_list_actions.addWidget(self._manual_refresh_list_button)
        manual_list_actions.addWidget(self._manual_edit_button)
        manual_list_actions.addWidget(self._manual_delete_button)
        manual_list_actions.addStretch(1)

        manual_layout.addWidget(self._manual_section_label)
        manual_layout.addLayout(manual_top_row)
        manual_layout.addLayout(rich_toolbar)
        manual_layout.addWidget(self._manual_question_label)
        manual_layout.addWidget(self._manual_question_input)
        manual_layout.addLayout(question_image_controls)
        manual_layout.addWidget(self._manual_question_image_preview)
        manual_layout.addLayout(choices_row_1)
        manual_layout.addLayout(choices_row_2)
        manual_layout.addWidget(self._manual_correct_label)
        manual_layout.addLayout(correct_row)
        manual_layout.addWidget(self._manual_explanation_label)
        manual_layout.addWidget(self._manual_explanation_input)
        manual_layout.addLayout(explanation_image_controls)
        manual_layout.addWidget(self._manual_explanation_image_preview)
        manual_layout.addWidget(self._manual_tags_input)
        manual_layout.addLayout(manual_actions_row)
        manual_layout.addWidget(self._manual_feedback_label)
        manual_layout.addWidget(self._manual_list_title_label)
        manual_layout.addWidget(self._manual_questions_table)
        manual_layout.addLayout(manual_list_actions)

        self._preview_panel = QFrame()
        self._preview_panel.setObjectName("PlaceholderPanel")
        preview_layout = QVBoxLayout(self._preview_panel)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(6)

        self._preview_title_label = QLabel()
        self._preview_title_label.setObjectName("SectionTitle")

        self._preview_table = QTableWidget()
        self._preview_table.setMinimumHeight(200)
        self._preview_table.setColumnCount(6)
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setWordWrap(True)
        self._preview_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._preview_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self._errors_title_label = QLabel()
        self._errors_title_label.setObjectName("SectionTitle")

        self._errors_list = QListWidget()
        self._errors_list.setWordWrap(True)

        preview_layout.addWidget(self._preview_title_label)
        preview_layout.addWidget(self._preview_table)
        preview_layout.addWidget(self._errors_title_label)
        preview_layout.addWidget(self._errors_list)

        # Top split: quick help + import/deck controls side by side on wide
        # windows. This keeps context visible without forcing long scrolling.
        self._top_split_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._top_split_layout.setContentsMargins(0, 0, 0, 0)
        self._top_split_layout.setSpacing(10)
        self._top_split_layout.addWidget(self._help_panel, 3)
        self._top_split_layout.addWidget(self._controls_panel, 2)

        # Bottom split: authoring and preview can share width on desktop.
        self._bottom_split_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._bottom_split_layout.setContentsMargins(0, 0, 0, 0)
        self._bottom_split_layout.setSpacing(10)
        self._bottom_split_layout.addWidget(self._manual_panel, 3)
        self._bottom_split_layout.addWidget(self._preview_panel, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(self._context_hint_label)
        layout.addLayout(self._top_split_layout)
        layout.addLayout(self._bottom_split_layout, 1)
        self._apply_responsive_layout()

    def set_navigation_context(self, context: str) -> None:
        """Switch page focus based on sidebar entry.

        We intentionally reuse this page for deck/question/import management
        so CRUD logic remains centralized and beginner-friendly.
        """
        normalized = context if context in {"import", "decks", "questions"} else "import"
        self._navigation_context = normalized
        self._apply_navigation_context()

    def refresh_content_sources(self) -> None:
        """Refresh deck/question data when page becomes visible."""
        current_deck_id = self._deck_selector.currentData()
        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._refresh_manual_questions()

    def _connect_signals(self) -> None:
        self._choose_file_button.clicked.connect(self._on_choose_file)
        self._validate_button.clicked.connect(self._on_validate_file)
        self._refresh_decks_button.clicked.connect(self._refresh_deck_selector)
        self._create_deck_button.clicked.connect(self._on_create_deck)
        self._update_deck_button.clicked.connect(self._on_update_selected_deck)
        self._delete_deck_button.clicked.connect(self._on_delete_selected_deck)
        self._import_button.clicked.connect(self._on_import)
        self._template_blank_button.clicked.connect(lambda: self._on_export_template(include_example_row=False))
        self._template_example_button.clicked.connect(lambda: self._on_export_template(include_example_row=True))
        self._deck_selector.currentIndexChanged.connect(self._on_deck_selection_changed)
        self._manual_save_button.clicked.connect(self._on_save_manual_question)
        self._manual_clear_button.clicked.connect(self._reset_manual_form)
        self._manual_refresh_list_button.clicked.connect(self._refresh_manual_questions)
        self._manual_edit_button.clicked.connect(self._on_edit_selected_question)
        self._manual_delete_button.clicked.connect(self._on_delete_selected_question)
        self._manual_mode_selector.currentIndexChanged.connect(self._enforce_mode_answer_rules)
        self._manual_questions_table.itemSelectionChanged.connect(self._on_manual_selection_changed)
        self._manual_rich_bold_button.clicked.connect(lambda: self._toggle_rich_style("bold"))
        self._manual_rich_italic_button.clicked.connect(lambda: self._toggle_rich_style("italic"))
        self._manual_rich_underline_button.clicked.connect(lambda: self._toggle_rich_style("underline"))
        self._manual_rich_bullets_button.clicked.connect(self._insert_rich_bullets)
        self._manual_question_image_choose_button.clicked.connect(
            lambda: self._pick_manual_image("question")
        )
        self._manual_question_image_clear_button.clicked.connect(
            lambda: self._clear_manual_image("question")
        )
        self._manual_explanation_image_choose_button.clicked.connect(
            lambda: self._pick_manual_image("explanation")
        )
        self._manual_explanation_image_clear_button.clicked.connect(
            lambda: self._clear_manual_image("explanation")
        )
        for letter, checkbox in self._manual_correct_checkboxes.items():
            checkbox.toggled.connect(
                lambda checked, selected=letter: self._on_correct_checkbox_toggled(selected, checked)
            )

    def _apply_responsive_layout(self) -> None:
        """Reflow heavy authoring blocks based on desktop width.

        Root cause of "too tall" feeling here was strict vertical stacking of
        four large panels. We use side-by-side panels when width allows it and
        stack back on tighter windows to protect readability.
        """
        width = self.width()
        # Top area (help + controls) can split earlier to cut vertical depth
        # without harming readability.
        if width < 940:
            self._top_split_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        else:
            self._top_split_layout.setDirection(QBoxLayout.Direction.LeftToRight)

        # Bottom area includes the heavy authoring form; keep it stacked until
        # wider desktops to avoid a cramped editing experience.
        if width < 1220:
            self._bottom_split_layout.setDirection(QBoxLayout.Direction.TopToBottom)
        else:
            self._bottom_split_layout.setDirection(QBoxLayout.Direction.LeftToRight)

    def update_texts(self) -> None:
        current_deck_id = self._deck_selector.currentData()
        self._apply_navigation_context()
        self._help_title_label.setText(self.translator.t("import_csv_flow.help.title"))
        self._help_description_label.setText(self.translator.t("import_csv_flow.help.description"))

        required_fields = ", ".join(sorted(self.csv_validation_service.REQUIRED_COLUMNS))
        self._help_conventions_label.setText(
            self.translator.t(
                "import_csv_flow.help.conventions",
                mode_single=self.csv_validation_service.MODE_SINGLE,
                mode_multiple=self.csv_validation_service.MODE_MULTIPLE,
                separator=self.csv_validation_service.CORRECT_ANSWERS_SEPARATOR,
                required_fields=required_fields,
            )
        )
        self._help_example_title_label.setText(self.translator.t("import_csv_flow.help.minimal_example_title"))
        self._help_example_value_label.setText(self.translator.t("import_csv_flow.help.minimal_example"))
        self._template_blank_button.setText(self.translator.t("import_csv_flow.help.download_blank"))
        self._template_example_button.setText(self.translator.t("import_csv_flow.help.download_example"))
        self._help_fields_table.setHorizontalHeaderLabels(
            [
                self.translator.t("import_csv_flow.help.columns.field"),
                self.translator.t("import_csv_flow.help.columns.required"),
                self.translator.t("import_csv_flow.help.columns.description"),
            ]
        )
        self._populate_help_fields_table()

        self._file_section_label.setText(self.translator.t("import_csv_flow.file_section"))
        self._choose_file_button.setText(self.translator.t("import_csv_flow.choose_file"))

        if self._selected_file_path:
            self._selected_file_label.setText(
                self.translator.t("import_csv_flow.selected_file", path=self._selected_file_path)
            )
        else:
            self._selected_file_label.setText(self.translator.t("import_csv_flow.no_file_selected"))

        self._validate_button.setText(self.translator.t("import_csv_flow.validate"))
        self._deck_section_label.setText(self.translator.t("import_csv_flow.deck_section"))
        self._deck_select_label.setText(self.translator.t("import_csv_flow.deck_select_label"))
        self._refresh_decks_button.setText(self.translator.t("import_csv_flow.refresh_decks"))

        self._create_deck_section_label.setText(self.translator.t("import_csv_flow.create_deck_section"))
        self._new_deck_name_input.setPlaceholderText(self.translator.t("import_csv_flow.new_deck_name"))
        self._new_deck_category_input.setPlaceholderText(
            self.translator.t("import_csv_flow.new_deck_category")
        )
        self._create_deck_button.setText(self.translator.t("import_csv_flow.create_deck"))
        self._manage_deck_section_label.setText(self.translator.t("import_csv_flow.manage_deck_section"))
        self._edit_deck_name_input.setPlaceholderText(self.translator.t("import_csv_flow.edit_deck_name"))
        self._edit_deck_category_input.setPlaceholderText(self.translator.t("import_csv_flow.edit_deck_category"))
        self._edit_deck_description_input.setPlaceholderText(
            self.translator.t("import_csv_flow.edit_deck_description")
        )
        self._update_deck_button.setText(self.translator.t("import_csv_flow.update_deck"))
        self._delete_deck_button.setText(self.translator.t("import_csv_flow.delete_deck"))
        self._import_button.setText(self.translator.t("import_csv_flow.import"))

        self._manual_section_label.setText(self.translator.t("import_csv_flow.manual.section"))
        self._manual_mode_label.setText(self.translator.t("import_csv_flow.manual.mode"))
        self._manual_difficulty_label.setText(self.translator.t("import_csv_flow.manual.difficulty"))
        self._manual_question_label.setText(self.translator.t("import_csv_flow.manual.question"))
        self._manual_correct_label.setText(self.translator.t("import_csv_flow.manual.correct"))
        self._manual_explanation_label.setText(self.translator.t("import_csv_flow.manual.explanation"))
        self._manual_list_title_label.setText(self.translator.t("import_csv_flow.manual.existing_title"))
        self._manual_rich_label.setText(self.translator.t("import_csv_flow.manual.rich_tools"))
        self._manual_rich_bold_button.setText("B")
        self._manual_rich_italic_button.setText("I")
        self._manual_rich_underline_button.setText("U")
        self._manual_rich_bullets_button.setText("•")
        self._manual_rich_bold_button.setToolTip(self.translator.t("import_csv_flow.manual.rich_bold"))
        self._manual_rich_italic_button.setToolTip(self.translator.t("import_csv_flow.manual.rich_italic"))
        self._manual_rich_underline_button.setToolTip(
            self.translator.t("import_csv_flow.manual.rich_underline")
        )
        self._manual_rich_bullets_button.setToolTip(
            self.translator.t("import_csv_flow.manual.rich_bullets")
        )

        single_index = self._manual_mode_selector.findData("single_choice")
        multiple_index = self._manual_mode_selector.findData("multiple_choice")
        if single_index >= 0:
            self._manual_mode_selector.setItemText(
                single_index,
                self.translator.t("import_csv_flow.manual.mode_single"),
            )
        if multiple_index >= 0:
            self._manual_mode_selector.setItemText(
                multiple_index,
                self.translator.t("import_csv_flow.manual.mode_multiple"),
            )

        self._manual_category_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.category"))
        self._manual_question_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.question_placeholder"))
        self._manual_choice_a_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.choice_a"))
        self._manual_choice_b_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.choice_b"))
        self._manual_choice_c_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.choice_c"))
        self._manual_choice_d_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.choice_d"))
        self._manual_explanation_input.setPlaceholderText(
            self.translator.t("import_csv_flow.manual.explanation")
        )
        self._manual_tags_input.setPlaceholderText(self.translator.t("import_csv_flow.manual.tags"))
        self._manual_question_image_label.setText(self.translator.t("import_csv_flow.manual.question_image"))
        self._manual_explanation_image_label.setText(
            self.translator.t("import_csv_flow.manual.explanation_image")
        )
        self._manual_question_image_choose_button.setText(
            self.translator.t("import_csv_flow.manual.choose_image")
        )
        self._manual_explanation_image_choose_button.setText(
            self.translator.t("import_csv_flow.manual.choose_image")
        )
        self._manual_question_image_clear_button.setText(
            self.translator.t("import_csv_flow.manual.clear_image")
        )
        self._manual_explanation_image_clear_button.setText(
            self.translator.t("import_csv_flow.manual.clear_image")
        )
        self._manual_save_button.setText(
            self.translator.t(
                "import_csv_flow.manual.update"
                if self._editing_question_id is not None
                else "import_csv_flow.manual.save"
            )
        )
        self._manual_clear_button.setText(self.translator.t("import_csv_flow.manual.clear"))
        self._manual_refresh_list_button.setText(self.translator.t("import_csv_flow.manual.refresh_list"))
        self._manual_edit_button.setText(self.translator.t("import_csv_flow.manual.edit_selected"))
        self._manual_delete_button.setText(self.translator.t("import_csv_flow.manual.delete_selected"))

        self._preview_title_label.setText(self.translator.t("import_csv_flow.preview_title"))
        self._errors_title_label.setText(self.translator.t("import_csv_flow.errors_title"))

        self._preview_table.setHorizontalHeaderLabels(
            [
                self.translator.t("import_csv_flow.preview_columns.row"),
                self.translator.t("import_csv_flow.preview_columns.question"),
                self.translator.t("import_csv_flow.preview_columns.mode"),
                self.translator.t("import_csv_flow.preview_columns.correct"),
                self.translator.t("import_csv_flow.preview_columns.difficulty"),
                self.translator.t("import_csv_flow.preview_columns.status"),
            ]
        )
        self._manual_questions_table.setHorizontalHeaderLabels(
            [
                self.translator.t("import_csv_flow.manual.columns.id"),
                self.translator.t("import_csv_flow.manual.columns.question"),
                self.translator.t("import_csv_flow.manual.columns.explanation"),
                self.translator.t("import_csv_flow.manual.columns.mode"),
                self.translator.t("import_csv_flow.manual.columns.correct"),
                self.translator.t("import_csv_flow.manual.columns.difficulty"),
                self.translator.t("import_csv_flow.manual.columns.tags"),
            ]
        )

        if self._validation_result is None:
            self._summary_label.setText(self.translator.t("import_csv_flow.ready_to_validate"))

        self._refresh_deck_selector(select_deck_id=current_deck_id)
        self._refresh_manual_image_previews()

    def _apply_navigation_context(self) -> None:
        """Adjust heading + panel visibility for import/deck/question entry points."""
        context = self._navigation_context

        if context == "decks":
            self._title_label.setText(self.translator.t("pages.decks.title"))
            self._description_label.setText(self.translator.t("pages.decks.description"))
            self._context_hint_label.setText(self.translator.t("content_nav.decks_hint"))
        elif context == "questions":
            self._title_label.setText(self.translator.t("pages.questions.title"))
            self._description_label.setText(self.translator.t("pages.questions.description"))
            self._context_hint_label.setText(self.translator.t("content_nav.questions_hint"))
        else:
            self._title_label.setText(self.translator.t("pages.import_csv.title"))
            self._description_label.setText(self.translator.t("pages.import_csv.description"))
            self._context_hint_label.setText(self.translator.t("content_nav.import_hint"))

        # Keep only relevant surfaces visible so non-technical users can focus.
        is_import = context == "import"
        is_decks = context == "decks"
        is_questions = context == "questions"

        self._help_panel.setVisible(is_import)
        self._preview_panel.setVisible(is_import)
        self._manual_panel.setVisible(is_import or is_questions)
        self._controls_panel.setVisible(True)

        # In question mode we still keep deck controls visible because deck
        # selection remains the source-of-truth for list/create/edit/delete.
        if is_decks:
            self._manual_feedback_label.clear()
        elif is_questions:
            self._deck_manage_status_label.clear()

        self._apply_responsive_layout()

    def _populate_help_fields_table(self) -> None:
        """Render field-by-field CSV help from canonical parser headers.

        Field order comes from CsvImportService so help stays aligned with
        actual parser conventions and template generation.
        """
        headers = list(self.csv_import_service.template_headers())
        required = set(self.csv_validation_service.REQUIRED_COLUMNS)

        self._help_fields_table.setRowCount(len(headers))
        for row, field_name in enumerate(headers):
            required_label = self.translator.t(
                "import_csv_flow.help.required_yes"
                if field_name in required
                else "import_csv_flow.help.required_no"
            )
            values = (
                field_name,
                required_label,
                self.translator.t(f"import_csv_flow.help.fields.{field_name}"),
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(value)
                self._help_fields_table.setItem(row, col, item)

        self._help_fields_table.resizeRowsToContents()

    def _on_export_template(self, *, include_example_row: bool) -> None:
        dialog_title = self.translator.t(
            "import_csv_flow.help.save_dialog_example_title"
            if include_example_row
            else "import_csv_flow.help.save_dialog_blank_title"
        )
        default_name = (
            "ebbing_house_questions_template_example.csv"
            if include_example_row
            else "ebbing_house_questions_template_blank.csv"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            dialog_title,
            default_name,
            "CSV (*.csv)",
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"

        try:
            self.csv_import_service.save_template(
                file_path,
                include_example_row=include_example_row,
            )
        except Exception:
            self._template_status_label.setText(self.translator.t("import_csv_flow.help.save_error"))
            return

        self._template_status_label.setText(
            self.translator.t("import_csv_flow.help.save_success", path=file_path)
        )
        self.notify_toast(
            self.translator.t("import_csv_flow.help.save_success_short"),
            level="success",
        )

    def _on_choose_file(self) -> None:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.translator.t("import_csv_flow.file_dialog_title"),
            "",
            "CSV (*.csv);;All files (*)",
        )
        if not file_path:
            return

        self._selected_file_path = file_path
        self._selected_file_label.setText(self.translator.t("import_csv_flow.selected_file", path=file_path))

        # Reset old validation data when a new file is picked.
        self._validation_result = None
        self._preview_table.setRowCount(0)
        self._errors_list.clear()
        self._summary_label.setText(self.translator.t("import_csv_flow.ready_to_validate"))
        self._import_status_label.clear()
        self._set_feedback("", state="info")
        self._update_import_button_state()

    def _on_validate_file(self) -> None:
        if not self._selected_file_path:
            self._set_feedback(self.translator.t("import_csv_flow.error_choose_file_first"), state="error")
            return

        try:
            parsed = self.csv_import_service.parse_file(self._selected_file_path)
            result = self.csv_validation_service.validate(parsed)
        except Exception:
            self._set_feedback(self.translator.t("import_csv_flow.error_validation_exception"), state="error")
            return

        self._validation_result = result

        self._render_preview(result)
        self._render_issues(result.issues)

        self._summary_label.setText(
            self.translator.t(
                "import_csv_flow.summary",
                total=result.total_rows,
                valid=len(result.valid_rows),
                invalid=len(result.invalid_rows),
                warnings=result.warning_count,
            )
        )

        if result.is_valid:
            self._set_feedback(
                self.translator.t("import_csv_flow.validation_ok", count=len(result.valid_rows)),
                state="success",
            )
        else:
            self._set_feedback(
                self.translator.t("import_csv_flow.validation_failed", count=result.error_count),
                state="error",
            )

        self._update_import_button_state()

    def _on_create_deck(self) -> None:
        name = self._new_deck_name_input.text().strip()
        if not name:
            self._set_feedback(self.translator.t("import_csv_flow.error_deck_name_required"), state="error")
            return

        category = self._new_deck_category_input.text().strip() or None
        try:
            created = self.deck_service.create_deck(name=name, category=category)
        except Exception:
            self._set_feedback(self.translator.t("import_csv_flow.error_create_deck_failed"), state="error")
            return

        self._refresh_deck_selector(select_deck_id=created.id)

        self._new_deck_name_input.clear()
        self._new_deck_category_input.clear()

        self._set_feedback(
            self.translator.t("import_csv_flow.deck_created", name=created.name),
            state="success",
        )
        self._set_deck_manage_status(
            self.translator.t("import_csv_flow.deck_loaded_for_edit", name=created.name),
            state="success",
        )

    def _on_update_selected_deck(self) -> None:
        """Update metadata of the currently selected deck.

        Selection stays in the shared deck selector so import/manual/question
        workflows always point to the same deck context.
        """
        deck_id = self._deck_selector.currentData()
        if deck_id is None:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_select_deck_manage"),
                state="error",
            )
            return

        deck = self.deck_service.get_deck_by_id(int(deck_id))
        if deck is None:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_deck_not_found"),
                state="error",
            )
            return

        new_name = self._edit_deck_name_input.text().strip()
        if not new_name:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_deck_name_required"),
                state="error",
            )
            return

        deck.name = new_name
        deck.category = self._edit_deck_category_input.text().strip() or None
        deck.description = self._edit_deck_description_input.text().strip() or None

        try:
            updated = self.deck_service.update_deck(deck)
        except Exception:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_update_deck_failed"),
                state="error",
            )
            return

        if not updated:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_update_deck_failed"),
                state="error",
            )
            return

        self._refresh_deck_selector(select_deck_id=deck.id)
        self._set_deck_manage_status(
            self.translator.t("import_csv_flow.deck_updated", name=deck.name),
            state="success",
        )
        self.notify_toast(
            self.translator.t("import_csv_flow.deck_updated", name=deck.name),
            level="success",
        )

    def _on_delete_selected_deck(self) -> None:
        """Delete selected deck after explicit user confirmation.

        Deletion is destructive because linked questions are removed by
        SQLite ON DELETE CASCADE. We therefore always show a clear warning.
        """
        deck_id = self._deck_selector.currentData()
        if deck_id is None:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_select_deck_manage"),
                state="error",
            )
            return

        deck = self.deck_service.get_deck_by_id(int(deck_id))
        if deck is None:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_deck_not_found"),
                state="error",
            )
            return

        try:
            question_count = len(self.question_authoring_service.list_by_deck(int(deck_id)))
        except Exception:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_deck_question_count_failed"),
                state="error",
            )
            return
        confirm_message = self.translator.t(
            "import_csv_flow.delete_deck_confirm",
            name=deck.name,
            question_count=question_count,
        )
        confirmation = QMessageBox.question(
            self,
            self.translator.t("import_csv_flow.delete_deck_title"),
            confirm_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self.deck_service.delete_deck(int(deck_id))
        except Exception:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_delete_deck_failed"),
                state="error",
            )
            return

        if not deleted:
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_delete_deck_failed"),
                state="error",
            )
            return

        self._refresh_deck_selector(select_deck_id=None)
        self._set_deck_manage_status(
            self.translator.t("import_csv_flow.deck_deleted", name=deck.name),
            state="success",
        )
        self.notify_toast(
            self.translator.t("import_csv_flow.deck_deleted", name=deck.name),
            level="success",
        )

    def _on_import(self) -> None:
        if self._validation_result is None:
            self._set_feedback(self.translator.t("import_csv_flow.error_validate_first"), state="error")
            return

        if not self._validation_result.is_valid:
            self._set_feedback(self.translator.t("import_csv_flow.error_fix_validation"), state="error")
            return

        deck_id = self._deck_selector.currentData()
        if deck_id is None:
            self._set_feedback(self.translator.t("import_csv_flow.error_select_deck"), state="error")
            return

        try:
            imported_count = self.question_import_service.import_validated_rows(
                deck_id=int(deck_id),
                rows=self._validation_result.valid_rows,
            )
        except Exception:
            self._set_feedback(self.translator.t("import_csv_flow.error_import_failed"), state="error")
            return

        self._import_status_label.setText(
            self.translator.t("import_csv_flow.import_status", count=imported_count)
        )
        unlocked_names = self._unlock_import_trophies(imported_count)
        self._set_feedback(
            self._with_unlock_feedback(
                self.translator.t("import_csv_flow.import_success", count=imported_count),
                unlocked_names,
            ),
            state="success",
        )
        self.notify_toast(
            self.translator.t("import_csv_flow.import_success", count=imported_count),
            level="success",
        )
        if unlocked_names:
            self.notify_toast(
                self.translator.t(
                    "trophies_flow.feedback_unlocked",
                    names=", ".join(unlocked_names),
                ),
                level="success",
                duration_ms=3400,
            )

    def _refresh_deck_selector(self, select_deck_id: int | None = None) -> None:
        decks = self.deck_service.list_decks()

        self._deck_selector.blockSignals(True)
        self._deck_selector.clear()

        if not decks:
            self._deck_selector.addItem(self.translator.t("import_csv_flow.no_decks"), None)
        else:
            for deck in decks:
                deck_label = deck.name
                if deck.category:
                    deck_label = f"{deck.name} ({deck.category})"
                self._deck_selector.addItem(deck_label, deck.id)

        if select_deck_id is not None:
            index = self._deck_selector.findData(select_deck_id)
            if index >= 0:
                self._deck_selector.setCurrentIndex(index)

        self._deck_selector.blockSignals(False)
        self._load_selected_deck_for_edit()
        self._update_import_button_state()
        self._refresh_manual_questions()

    def _on_deck_selection_changed(self) -> None:
        self._update_import_button_state()
        self._editing_question_id = None
        self._manual_save_button.setText(self.translator.t("import_csv_flow.manual.save"))
        self._load_selected_deck_for_edit()
        self._refresh_manual_questions()

    def _load_selected_deck_for_edit(self) -> None:
        """Load selected deck metadata into the edit form.

        This keeps deck CRUD in one predictable place while the selector stays
        the source of truth across import/manual workflows.
        """
        deck_id = self._deck_selector.currentData()
        has_deck = deck_id is not None

        self._edit_deck_name_input.setEnabled(has_deck)
        self._edit_deck_category_input.setEnabled(has_deck)
        self._edit_deck_description_input.setEnabled(has_deck)
        self._update_deck_button.setEnabled(has_deck)
        self._delete_deck_button.setEnabled(has_deck)

        if not has_deck:
            self._edit_deck_name_input.clear()
            self._edit_deck_category_input.clear()
            self._edit_deck_description_input.clear()
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.manage_deck_empty"),
                state="info",
            )
            return

        deck = self.deck_service.get_deck_by_id(int(deck_id))
        if deck is None:
            self._edit_deck_name_input.clear()
            self._edit_deck_category_input.clear()
            self._edit_deck_description_input.clear()
            self._set_deck_manage_status(
                self.translator.t("import_csv_flow.error_deck_not_found"),
                state="error",
            )
            return

        self._edit_deck_name_input.setText(deck.name)
        self._edit_deck_category_input.setText(deck.category or "")
        self._edit_deck_description_input.setText(deck.description or "")
        try:
            question_count = len(self.question_authoring_service.list_by_deck(deck.id))
        except Exception:
            question_count = 0
        self._set_deck_manage_status(
            self.translator.t(
                "import_csv_flow.deck_loaded_for_edit_count",
                name=deck.name,
                question_count=question_count,
            ),
            state="info",
        )

    def _on_save_manual_question(self) -> None:
        deck_id = self._deck_selector.currentData()
        if deck_id is None:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_select_deck"),
                state="error",
            )
            return

        payload = self._manual_form_payload()
        try:
            if self._editing_question_id is None:
                saved = self.question_authoring_service.create_manual_question(
                    deck_id=int(deck_id),
                    **payload,
                )
                message_key = "import_csv_flow.manual.created"
            else:
                saved = self.question_authoring_service.update_manual_question(
                    question_id=self._editing_question_id,
                    deck_id=int(deck_id),
                    **payload,
                )
                message_key = "import_csv_flow.manual.updated"
        except ValueError:
            # Keep manual authoring feedback localized instead of exposing raw
            # service exceptions that may not be translated.
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_save_failed"),
                state="error",
            )
            return
        except Exception:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_save_failed"),
                state="error",
            )
            return

        self._refresh_manual_questions(select_question_id=saved.id)
        self._set_manual_feedback(
            self.translator.t(message_key),
            state="success",
        )
        self.notify_toast(
            self.translator.t(message_key),
            level="success",
        )
        self._reset_manual_form(clear_feedback=False)

    def _manual_form_payload(self) -> dict[str, object]:
        return {
            "category": self._manual_category_input.text().strip(),
            "question_text": self._editor_content(self._manual_question_input),
            "choice_a": self._manual_choice_a_input.text().strip(),
            "choice_b": self._manual_choice_b_input.text().strip(),
            "choice_c": self._manual_choice_c_input.text().strip(),
            "choice_d": self._manual_choice_d_input.text().strip(),
            "selected_answers": self._selected_correct_answers(),
            "mode": self._manual_mode_selector.currentData() or "single_choice",
            "explanation": self._editor_content(self._manual_explanation_input),
            "question_image_input": self._manual_question_image_source,
            "explanation_image_input": self._manual_explanation_image_source,
            "difficulty": int(self._manual_difficulty_spin.value()),
            "tags": self._manual_tags_input.text().strip(),
        }

    def _editor_content(self, editor: QTextEdit) -> str:
        text = editor.toPlainText().strip()
        if not text:
            return ""
        # We persist HTML to keep formatting/image-inline compatibility,
        # while plain-text questions still render correctly in card widget.
        return editor.toHtml().strip()

    def _selected_correct_answers(self) -> list[str]:
        selected: list[str] = []
        for letter in ("A", "B", "C", "D"):
            if self._manual_correct_checkboxes[letter].isChecked():
                selected.append(letter)
        return selected

    def _set_selected_correct_answers(self, answers: list[str]) -> None:
        normalized = {item.strip().upper() for item in answers}
        for letter, checkbox in self._manual_correct_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(letter in normalized)
            checkbox.blockSignals(False)

    def _on_correct_checkbox_toggled(self, selected_letter: str, checked: bool) -> None:
        # Single-choice authoring should remain explicit in the UI:
        # checking one answer unchecks the others automatically.
        if not checked:
            return
        if self._manual_mode_selector.currentData() != "single_choice":
            return
        for letter, checkbox in self._manual_correct_checkboxes.items():
            if letter == selected_letter:
                continue
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)

    def _refresh_manual_questions(self, select_question_id: int | None = None) -> None:
        deck_id = self._deck_selector.currentData()
        self._manual_questions_by_id.clear()
        self._manual_questions_table.setRowCount(0)
        self._manual_edit_button.setEnabled(False)
        self._manual_delete_button.setEnabled(False)

        has_deck = deck_id is not None
        self._manual_save_button.setEnabled(has_deck)
        self._manual_refresh_list_button.setEnabled(has_deck)

        if not has_deck:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_select_deck"),
                state="info",
            )
            return

        try:
            questions = self.question_authoring_service.list_by_deck(int(deck_id))
        except Exception:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_list_failed"),
                state="error",
            )
            return

        row_index = 0
        for question in questions:
            if question.id is None:
                continue
            self._manual_questions_by_id[question.id] = question
            self._manual_questions_table.insertRow(row_index)

            values = [
                str(question.id),
                self._plain_text_preview(question.question_text),
                self._plain_text_preview(question.explanation or "", max_length=120)
                or self.translator.t("import_csv_flow.manual.no_explanation"),
                question.mode,
                question.correct_answers,
                str(question.difficulty),
                question.tags or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, question.id)
                self._manual_questions_table.setItem(row_index, column, item)
            row_index += 1

        self._manual_questions_table.resizeRowsToContents()

        # Safety net:
        # If deck context changed (or a question was deleted elsewhere), an
        # old edit target may no longer exist. We reset to create mode so the
        # form cannot accidentally try to update a stale question id.
        if self._editing_question_id is not None and self._editing_question_id not in self._manual_questions_by_id:
            self._reset_manual_form(clear_feedback=False)

        if select_question_id is not None:
            self._select_manual_row_by_question_id(select_question_id)

    def _select_manual_row_by_question_id(self, question_id: int) -> None:
        for row in range(self._manual_questions_table.rowCount()):
            id_item = self._manual_questions_table.item(row, 0)
            if id_item is None:
                continue
            current_id = id_item.data(Qt.ItemDataRole.UserRole)
            if current_id == question_id:
                self._manual_questions_table.selectRow(row)
                self._on_manual_selection_changed()
                return

    def _on_manual_selection_changed(self) -> None:
        selected_id = self._selected_manual_question_id()
        has_selection = selected_id is not None
        self._manual_edit_button.setEnabled(has_selection)
        self._manual_delete_button.setEnabled(has_selection)

    def _selected_manual_question_id(self) -> int | None:
        rows = self._manual_questions_table.selectionModel().selectedRows()
        if not rows:
            return None
        id_item = self._manual_questions_table.item(rows[0].row(), 0)
        if id_item is None:
            return None
        question_id = id_item.data(Qt.ItemDataRole.UserRole)
        return question_id if isinstance(question_id, int) else None

    def _on_edit_selected_question(self) -> None:
        question_id = self._selected_manual_question_id()
        if question_id is None:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_select_question"),
                state="error",
            )
            return
        question = self._manual_questions_by_id.get(question_id)
        if question is None:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_question_not_found"),
                state="error",
            )
            return

        category, free_tags = self.question_authoring_service.split_category_and_tags(question.tags)
        self._editing_question_id = question.id
        self._manual_category_input.setText(category)
        self._set_editor_content(self._manual_question_input, question.question_text)
        self._manual_choice_a_input.setText(question.choice_a)
        self._manual_choice_b_input.setText(question.choice_b)
        self._manual_choice_c_input.setText(question.choice_c or "")
        self._manual_choice_d_input.setText(question.choice_d or "")
        self._set_editor_content(self._manual_explanation_input, question.explanation or "")
        self._manual_tags_input.setText(free_tags)
        self._manual_difficulty_spin.setValue(max(1, min(5, int(question.difficulty))))
        self._manual_question_image_source = question.question_image_path
        self._manual_explanation_image_source = question.explanation_image_path

        mode_index = self._manual_mode_selector.findData(question.mode)
        if mode_index >= 0:
            self._manual_mode_selector.setCurrentIndex(mode_index)

        selected_answers = [
            token.strip().upper()
            for token in (question.correct_answers or "").split("|")
            if token.strip()
        ]
        self._set_selected_correct_answers(selected_answers)
        self._refresh_manual_image_previews()

        self._manual_save_button.setText(self.translator.t("import_csv_flow.manual.update"))
        self._set_manual_feedback(self.translator.t("import_csv_flow.manual.editing"), state="info")

    def _on_delete_selected_question(self) -> None:
        question_id = self._selected_manual_question_id()
        if question_id is None:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_select_question"),
                state="error",
            )
            return

        question_preview = ""
        explanation_preview = ""
        question = self._manual_questions_by_id.get(question_id)
        if question is not None:
            question_preview = self._plain_text_preview(question.question_text, max_length=90)
            explanation_preview = self._plain_text_preview(question.explanation or "", max_length=90)

        # Delete dialog now mirrors CRUD scope more honestly by surfacing the
        # optional explanation too when present.
        detail_lines = [
            f"{self.translator.t('import_csv_flow.manual.columns.question')}: "
            f"{question_preview or self.translator.t('import_csv_flow.manual.columns.question')}"
        ]
        if explanation_preview:
            detail_lines.append(
                f"{self.translator.t('import_csv_flow.manual.columns.explanation')}: {explanation_preview}"
            )
        confirm_payload = "\n".join(detail_lines)

        confirmation = QMessageBox.question(
            self,
            self.translator.t("import_csv_flow.manual.delete_title"),
            self.translator.t(
                "import_csv_flow.manual.delete_confirm_with_preview",
                question=confirm_payload,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self.question_authoring_service.delete_question(question_id)
        except Exception:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_delete_failed"),
                state="error",
            )
            return

        if not deleted:
            self._set_manual_feedback(
                self.translator.t("import_csv_flow.manual.error_delete_failed"),
                state="error",
            )
            return

        if self._editing_question_id == question_id:
            self._reset_manual_form(clear_feedback=False)
        self._refresh_manual_questions()
        self._set_manual_feedback(
            self.translator.t("import_csv_flow.manual.deleted"),
            state="success",
        )
        self.notify_toast(self.translator.t("import_csv_flow.manual.deleted"), level="success")

    def _reset_manual_form(self, clear_feedback: bool = True) -> None:
        self._editing_question_id = None
        self._manual_category_input.clear()
        self._manual_question_input.clear()
        self._manual_choice_a_input.clear()
        self._manual_choice_b_input.clear()
        self._manual_choice_c_input.clear()
        self._manual_choice_d_input.clear()
        self._manual_explanation_input.clear()
        self._manual_tags_input.clear()
        self._manual_question_image_source = None
        self._manual_explanation_image_source = None
        self._manual_difficulty_spin.setValue(1)
        single_index = self._manual_mode_selector.findData("single_choice")
        if single_index >= 0:
            self._manual_mode_selector.setCurrentIndex(single_index)
        self._set_selected_correct_answers([])
        self._refresh_manual_image_previews()
        self._manual_save_button.setText(self.translator.t("import_csv_flow.manual.save"))
        if clear_feedback:
            self._set_manual_feedback("", state="info")

    def _toggle_rich_style(self, style: str) -> None:
        """Apply a tiny WYSIWYG subset to the currently focused editor.

        We intentionally keep only a few formatting actions so authoring stays
        practical and stable for everyday educational content.
        """
        editor = self._active_rich_editor()
        cursor = editor.textCursor()
        fmt = cursor.charFormat()

        if style == "bold":
            current = fmt.fontWeight()
            fmt.setFontWeight(
                QFont.Weight.Normal if current >= int(QFont.Weight.Bold) else QFont.Weight.Bold
            )
        elif style == "italic":
            fmt.setFontItalic(not fmt.fontItalic())
        elif style == "underline":
            fmt.setFontUnderline(not fmt.fontUnderline())
        else:
            return

        cursor.mergeCharFormat(fmt)
        editor.mergeCurrentCharFormat(fmt)
        editor.setFocus()

    def _insert_rich_bullets(self) -> None:
        """Insert a bullet list at cursor position.

        This gives enough structure for lesson prompts and explanations
        without building a full document editor.
        """
        editor = self._active_rich_editor()
        cursor = editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.Style.ListDisc)

        cursor.beginEditBlock()
        if cursor.currentList() is None:
            cursor.createList(list_format)
        else:
            # If already in a list, toggle back to a normal paragraph.
            block_format = cursor.blockFormat()
            block_format.setObjectIndex(-1)
            cursor.setBlockFormat(block_format)
        cursor.endEditBlock()
        editor.setFocus()

    def _active_rich_editor(self) -> QTextEdit:
        """Return the editor currently being authored.

        We prefer explanation when it has focus, otherwise question editor is
        the default target for formatting actions.
        """
        focused = self.focusWidget()
        if focused is not None:
            if focused is self._manual_explanation_input or self._manual_explanation_input.isAncestorOf(focused):
                return self._manual_explanation_input
            if focused is self._manual_question_input or self._manual_question_input.isAncestorOf(focused):
                return self._manual_question_input
        return self._manual_question_input

    def _pick_manual_image(self, kind: str) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator.t("import_csv_flow.manual.image_picker_title"),
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*)",
        )
        if not file_path:
            return

        if kind == "question":
            self._manual_question_image_source = file_path
        else:
            self._manual_explanation_image_source = file_path
        self._refresh_manual_image_previews()

    def _clear_manual_image(self, kind: str) -> None:
        if kind == "question":
            self._manual_question_image_source = None
        else:
            self._manual_explanation_image_source = None
        self._refresh_manual_image_previews()

    def _refresh_manual_image_previews(self) -> None:
        self._render_image_preview(
            label=self._manual_question_image_preview,
            source=self._manual_question_image_source,
            empty_message=self.translator.t("import_csv_flow.manual.no_image"),
        )
        self._render_image_preview(
            label=self._manual_explanation_image_preview,
            source=self._manual_explanation_image_source,
            empty_message=self.translator.t("import_csv_flow.manual.no_image"),
        )

    def _render_image_preview(self, *, label: QLabel, source: str | None, empty_message: str) -> None:
        """Render one preview label from a path or stored relative reference."""
        label.clear()
        label.setPixmap(QPixmap())
        label.setToolTip("")

        if not source:
            label.setText(empty_message)
            return

        resolved = resolve_media_reference(source)
        if resolved is None or not resolved.exists() or not resolved.is_file():
            label.setText(self.translator.t("import_csv_flow.manual.image_missing"))
            return

        pixmap = QPixmap(str(resolved))
        if pixmap.isNull():
            label.setText(self.translator.t("import_csv_flow.manual.image_invalid"))
            return

        # Keep image previews readable and lightweight.
        target_width = max(180, label.width() - 12)
        target_height = max(90, label.height() - 12)
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setToolTip(str(resolved))

    def _set_editor_content(self, editor: QTextEdit, value: str) -> None:
        if self._looks_like_html(value):
            editor.setHtml(value)
        else:
            editor.setPlainText(value)

    def _enforce_mode_answer_rules(self, _index: int | None = None) -> None:
        """Keep single-choice mode honest in the form itself."""
        if self._manual_mode_selector.currentData() != "single_choice":
            return

        selected = [
            letter for letter, checkbox in self._manual_correct_checkboxes.items() if checkbox.isChecked()
        ]
        if len(selected) <= 1:
            return

        keep = selected[0]
        for letter in selected[1:]:
            checkbox = self._manual_correct_checkboxes[letter]
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)

        self._set_manual_feedback(
            self.translator.t("import_csv_flow.manual.single_mode_hint", answer=keep),
            state="info",
        )

    def _plain_text_preview(self, value: str, max_length: int = 140) -> str:
        stripped = re.sub(r"<[^>]+>", " ", value or "")
        compact = " ".join(html.unescape(stripped).replace("\xa0", " ").split())
        if len(compact) <= max_length:
            return compact
        return f"{compact[: max_length - 1].rstrip()}…"

    def _looks_like_html(self, value: str) -> bool:
        if not value:
            return False
        return bool(
            re.search(r"<(?:p|div|span|br|strong|em|u|ul|ol|li|h[1-6]|img|table|blockquote)\b", value, re.IGNORECASE)
        )

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # Keep both responsive layout reflow and image preview scaling in sync
        # when users resize the window.
        self._apply_responsive_layout()
        self._refresh_manual_image_previews()

    def _set_manual_feedback(self, message: str, state: str = "info") -> None:
        self._manual_feedback_label.setText(message)
        set_feedback_visual(self._manual_feedback_label, state)

    def _set_deck_manage_status(self, message: str, state: str = "info") -> None:
        self._deck_manage_status_label.setText(message)
        set_feedback_visual(self._deck_manage_status_label, state)

    def _render_preview(self, result: CsvValidationResult) -> None:
        rows = result.preview_rows[: self.PREVIEW_LIMIT]
        self._preview_table.setRowCount(len(rows))

        for table_row, preview_row in enumerate(rows):
            normalized = preview_row.normalized_question
            question_text = (
                normalized.question_text
                if normalized
                else preview_row.raw_values.get("question", "")
            ).strip()

            mode = normalized.mode if normalized else preview_row.raw_values.get("mode", "")
            correct_answers = (
                normalized.correct_answers
                if normalized
                else preview_row.raw_values.get("correct_answers", "")
            )
            difficulty = str(normalized.difficulty) if normalized else preview_row.raw_values.get("difficulty", "")

            status_text = (
                self.translator.t("import_csv_flow.status_valid")
                if preview_row.is_valid
                else self.translator.t("import_csv_flow.status_invalid")
            )

            values = [
                str(preview_row.row_number),
                question_text,
                mode,
                correct_answers,
                difficulty,
                status_text,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(value)
                self._preview_table.setItem(table_row, column, item)

        # Dynamic row heights keep multi-line long content readable.
        self._preview_table.resizeRowsToContents()

    def _render_issues(self, issues: list[CsvValidationIssue]) -> None:
        self._errors_list.clear()

        if not issues:
            self._errors_list.addItem(self.translator.t("import_csv_flow.no_issues"))
            return

        for issue in issues:
            if issue.row_number is None:
                prefix = self.translator.t("import_csv_flow.issue_prefix_global")
            else:
                prefix = self.translator.t("import_csv_flow.issue_prefix_row", row=issue.row_number)

            level = "ERROR" if issue.is_error else "WARN"
            self._errors_list.addItem(f"[{level}] {prefix} - {issue.field}: {issue.message}")

    def _update_import_button_state(self) -> None:
        has_deck = self._deck_selector.currentData() is not None
        can_import = bool(self._validation_result and self._validation_result.is_valid and has_deck)
        self._import_button.setEnabled(can_import)

    def _set_feedback(self, message: str, state: str = "info") -> None:
        self._feedback_label.setText(message)
        set_feedback_visual(self._feedback_label, state)

    def _unlock_import_trophies(self, imported_count: int) -> list[str]:
        """Unlock import-related trophies for the current active profile.

        Import itself is global, but rewards are profile-based in this product.
        We therefore attribute the unlock to the active learner when available.
        """
        active_profile_id = self.profile_service.get_active_profile_id()
        unlocked = self.trophy_service.on_csv_import_completed(
            profile_id=active_profile_id,
            imported_count=imported_count,
        )
        return [item.display_name(self.translator.locale) for item in unlocked]

    def _with_unlock_feedback(self, base_message: str, unlocked_names: list[str]) -> str:
        if not unlocked_names:
            return base_message
        names = ", ".join(unlocked_names)
        return f"{base_message} {self.translator.t('trophies_flow.feedback_unlocked', names=names)}"
