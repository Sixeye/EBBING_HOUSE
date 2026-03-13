"""Reusable question card widget for quiz/review sessions."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.paths import resolve_media_reference
from app.models.question import Question


class QuestionCardWidget(QFrame):
    """Render one question with dynamic single/multiple answer controls."""

    selection_changed = Signal()

    def __init__(self, translator) -> None:
        super().__init__()
        self.translator = translator
        self.setObjectName("PlaceholderPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._answer_buttons: dict[str, QCheckBox | QRadioButton] = {}
        self._answer_rows: dict[str, QFrame] = {}
        self._answer_labels: dict[str, QLabel] = {}
        self._radio_group = QButtonGroup(self)
        self._radio_group.setExclusive(True)
        self._current_question: Question | None = None
        self._explanation_media_visible = False

        self._title_label = QLabel()
        self._title_label.setObjectName("SectionTitle")

        self._question_text_label = QLabel()
        self._question_text_label.setWordWrap(True)
        self._question_text_label.setTextFormat(Qt.TextFormat.PlainText)
        self._question_text_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._question_text_label.setStyleSheet("font-size: 18px; font-weight: 600;")

        self._question_image_label = QLabel()
        self._question_image_label.setObjectName("ImagePreview")
        self._question_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._question_image_label.setWordWrap(True)
        self._question_image_label.setMinimumHeight(110)
        self._question_image_label.setMaximumHeight(220)
        self._question_image_label.hide()

        self._mode_label = QLabel()
        self._mode_label.setObjectName("PageSubtitle")

        self._answers_container = QWidget()
        self._answers_layout = QVBoxLayout(self._answers_container)
        self._answers_layout.setContentsMargins(0, 0, 0, 0)
        self._answers_layout.setSpacing(6)

        self._explanation_title = QLabel()
        self._explanation_title.setObjectName("SectionTitle")
        self._explanation_title.hide()

        self._explanation_label = QLabel()
        self._explanation_label.setWordWrap(True)
        self._explanation_label.setTextFormat(Qt.TextFormat.PlainText)
        self._explanation_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._explanation_label.setObjectName("PageSubtitle")
        self._explanation_label.hide()

        self._explanation_image_label = QLabel()
        self._explanation_image_label.setObjectName("ImagePreview")
        self._explanation_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._explanation_image_label.setWordWrap(True)
        self._explanation_image_label.setMinimumHeight(96)
        self._explanation_image_label.setMaximumHeight(200)
        self._explanation_image_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        layout.addWidget(self._title_label)
        layout.addWidget(self._question_text_label)
        layout.addWidget(self._question_image_label)
        layout.addWidget(self._mode_label)
        layout.addWidget(self._answers_container)
        layout.addWidget(self._explanation_title)
        layout.addWidget(self._explanation_label)
        layout.addWidget(self._explanation_image_label)

        self.update_texts()

    def update_texts(self) -> None:
        self._explanation_title.setText(self.translator.t("review_flow.explanation_title"))

    def set_question(self, question: Question, question_number: int, total_questions: int) -> None:
        """Render a fresh question and reset previous visual feedback."""
        self._current_question = question
        self._answer_buttons = {}
        self._answer_rows = {}
        self._answer_labels = {}

        self._title_label.setText(
            self.translator.t(
                "review_flow.question_counter",
                current=question_number,
                total=total_questions,
            )
        )
        self._set_rich_or_plain_text(self._question_text_label, question.question_text)
        self._set_optional_image(
            self._question_image_label,
            question.question_image_path,
        )
        self._mode_label.setText(
            self.translator.t("review_flow.mode_single")
            if question.mode == "single_choice"
            else self.translator.t("review_flow.mode_multiple")
        )

        self._clear_answers_layout()
        self._build_answer_controls(question)
        self._explanation_title.hide()
        self._explanation_label.hide()
        self._explanation_label.clear()
        self._explanation_image_label.hide()
        self._explanation_image_label.clear()
        self._explanation_image_label.setPixmap(QPixmap())
        self._explanation_media_visible = False

    def has_selection(self) -> bool:
        return len(self.selected_answers()) > 0

    def selected_answers(self) -> list[str]:
        selected: list[str] = []
        for letter, button in self._answer_buttons.items():
            if button.isChecked():
                selected.append(letter)
        return selected

    def lock_answers(self, locked: bool) -> None:
        for button in self._answer_buttons.values():
            button.setEnabled(not locked)
        for label in self._answer_labels.values():
            label.setEnabled(not locked)

    def show_feedback(
        self,
        selected_answers: list[str],
        correct_answers: list[str],
        explanation: str | None,
    ) -> None:
        """Apply immediate visual feedback after validation."""
        selected_set = set(selected_answers)
        correct_set = set(correct_answers)

        for letter, button in self._answer_buttons.items():
            state = "neutral"
            if letter in correct_set:
                state = "correct"
            elif letter in selected_set and letter not in correct_set:
                state = "wrong"

            row = self._answer_rows.get(letter)
            if row is not None:
                row.setStyleSheet(self._style_for_state(state))

        if explanation:
            self._set_rich_or_plain_text(self._explanation_label, explanation)
            self._explanation_label.show()
        else:
            self._explanation_label.hide()
            self._explanation_label.clear()

        explanation_image_visible = False
        if self._current_question is not None:
            explanation_image_visible = self._set_optional_image(
                self._explanation_image_label,
                self._current_question.explanation_image_path,
            )
        else:
            self._explanation_image_label.hide()

        if explanation or explanation_image_visible:
            self._explanation_title.show()
        else:
            self._explanation_title.hide()
        self._explanation_media_visible = explanation_image_visible

    def _clear_answers_layout(self) -> None:
        # QButtonGroup keeps references to radio buttons; clear old mappings so
        # single-choice exclusivity resets cleanly between questions.
        for button in self._radio_group.buttons():
            self._radio_group.removeButton(button)

        while self._answers_layout.count():
            item = self._answers_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _build_answer_controls(self, question: Question) -> None:
        options = self._question_options(question)
        for letter, text in options:
            if question.mode == "single_choice":
                button: QCheckBox | QRadioButton = QRadioButton()
                self._radio_group.addButton(button)
            else:
                button = QCheckBox()

            # Root cause fixed:
            # Native radio/checkbox text does not wrap robustly for very long
            # educational content. We therefore separate indicator + label so
            # answer text can wrap naturally with dynamic height.
            row = QFrame()
            row.setObjectName("AnswerOptionRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(9, 7, 9, 7)
            row_layout.setSpacing(8)

            text_label = QLabel(f"{letter}. {text}")
            text_label.setObjectName("AnswerOptionText")
            text_label.setWordWrap(True)
            text_label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            row_layout.addWidget(button, 0)
            row_layout.addWidget(text_label, 1)

            # Qt sends `checked: bool`; we expose a cleaner no-arg signal to page code.
            button.toggled.connect(lambda _checked=False: self.selection_changed.emit())
            row.setStyleSheet(self._style_for_state("neutral"))

            # Make the row and label clickable, not only the tiny indicator.
            row.mousePressEvent = self._build_row_click_handler(button)  # type: ignore[assignment]
            text_label.mousePressEvent = self._build_row_click_handler(button)  # type: ignore[assignment]

            self._answers_layout.addWidget(row)
            self._answer_buttons[letter] = button
            self._answer_rows[letter] = row
            self._answer_labels[letter] = text_label

        self._answers_layout.addStretch(1)

    def _question_options(self, question: Question) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        if question.choice_a:
            options.append(("A", question.choice_a))
        if question.choice_b:
            options.append(("B", question.choice_b))
        if question.choice_c:
            options.append(("C", question.choice_c))
        if question.choice_d:
            options.append(("D", question.choice_d))
        return options

    def _style_for_state(self, state: str) -> str:
        if state == "correct":
            return (
                "QFrame#AnswerOptionRow {"
                "border: 1px solid #39B26A; border-radius: 10px;"
                "background-color: rgba(57, 178, 106, 0.12); }"
                "QLabel#AnswerOptionText { color: #39B26A; font-weight: 600; }"
            )
        if state == "wrong":
            return (
                "QFrame#AnswerOptionRow {"
                "border: 1px solid #D95B5B; border-radius: 10px;"
                "background-color: rgba(217, 91, 91, 0.12); }"
                "QLabel#AnswerOptionText { color: #D95B5B; font-weight: 600; }"
            )
        return (
            "QFrame#AnswerOptionRow {"
            "border: 1px solid #32343A; border-radius: 10px;"
            "background-color: rgba(255, 255, 255, 0.01); }"
            "QFrame#AnswerOptionRow:hover {"
            "border: 1px solid rgba(255, 138, 45, 0.56);"
            "background-color: rgba(255, 138, 45, 0.10); }"
            "QLabel#AnswerOptionText { color: #F3F3F4; }"
        )

    def _build_row_click_handler(self, button: QCheckBox | QRadioButton):
        def _handler(_event) -> None:
            if button.isEnabled():
                button.click()

        return _handler

    def _set_rich_or_plain_text(self, label: QLabel, content: str) -> None:
        """Render saved question content safely for both plain and rich text.

        Manual authoring can save HTML while CSV import usually stores plain
        text. This helper keeps both formats compatible in session pages.
        """
        if self._looks_like_html(content):
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText(content)
        else:
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setText(content)

    def _set_optional_image(self, label: QLabel, image_reference: str | None) -> bool:
        """Render optional question/explanation image if available."""
        label.clear()
        label.setPixmap(QPixmap())
        label.setToolTip("")

        if not image_reference:
            label.hide()
            return False

        resolved = resolve_media_reference(image_reference)
        if resolved is None or not resolved.exists() or not resolved.is_file():
            label.hide()
            return False

        pixmap = QPixmap(str(resolved))
        if pixmap.isNull():
            label.hide()
            return False

        target_width = max(160, label.width() - 10)
        target_height = max(90, label.height() - 10)
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)
        label.setToolTip(str(resolved))
        label.show()
        return True

    def _looks_like_html(self, content: str) -> bool:
        if not content:
            return False
        return bool(
            re.search(
                r"<(?:p|div|span|br|strong|em|u|ul|ol|li|h[1-6]|img|table|blockquote)\b",
                content,
                re.IGNORECASE,
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming convention)
        super().resizeEvent(event)
        if self._current_question is None:
            return
        self._set_optional_image(self._question_image_label, self._current_question.question_image_path)
        if self._explanation_media_visible:
            self._set_optional_image(
                self._explanation_image_label,
                self._current_question.explanation_image_path,
            )
