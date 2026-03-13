"""Session summary card shown when a quiz/review session is complete."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout

from app.models.quiz_session import QuizSessionSummary


class SessionSummaryCardWidget(QFrame):
    """Display end-of-session metrics in a compact card."""

    def __init__(self, translator) -> None:
        super().__init__()
        self.translator = translator
        self.setObjectName("PlaceholderPanel")

        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._deck_label = QLabel()
        self._deck_label.setObjectName("PageSubtitle")
        self._deck_label.setWordWrap(True)
        self._deck_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._grid_layout = QGridLayout()
        self._grid_layout.setHorizontalSpacing(20)
        self._grid_layout.setVerticalSpacing(10)

        self._metric_labels: dict[str, QLabel] = {}
        self._metric_values: dict[str, QLabel] = {}
        for row_index, key in enumerate(
            (
                "total",
                "correct",
                "wrong",
                "percentage",
                "score_20",
                "score_100",
                "avg_time",
            )
        ):
            label = QLabel()
            label.setObjectName("MetricTitle")
            value = QLabel()
            value.setObjectName("MetricValue")
            value.setStyleSheet("font-size: 20px;")
            self._grid_layout.addWidget(label, row_index, 0)
            self._grid_layout.addWidget(value, row_index, 1)
            self._metric_labels[key] = label
            self._metric_values[key] = value

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        layout.addWidget(self._deck_label)
        layout.addLayout(self._grid_layout)

        self.update_texts()

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("review_flow.summary_title"))
        self._metric_labels["total"].setText(self.translator.t("review_flow.summary_total"))
        self._metric_labels["correct"].setText(self.translator.t("review_flow.summary_correct"))
        self._metric_labels["wrong"].setText(self.translator.t("review_flow.summary_wrong"))
        self._metric_labels["percentage"].setText(self.translator.t("review_flow.summary_percentage"))
        self._metric_labels["score_20"].setText(self.translator.t("review_flow.summary_score_20"))
        self._metric_labels["score_100"].setText(self.translator.t("review_flow.summary_score_100"))
        self._metric_labels["avg_time"].setText(self.translator.t("review_flow.summary_avg_time"))

    def set_summary(self, summary: QuizSessionSummary) -> None:
        self._deck_label.setText(self.translator.t("review_flow.summary_deck", deck=summary.deck_name))
        self._metric_values["total"].setText(str(summary.total_questions))
        self._metric_values["correct"].setText(str(summary.correct_answers_count))
        self._metric_values["wrong"].setText(str(summary.wrong_answers_count))
        self._metric_values["percentage"].setText(f"{summary.percentage:.2f}%")
        self._metric_values["score_20"].setText(f"{summary.score_on_20:.2f}")
        self._metric_values["score_100"].setText(f"{summary.score_on_100:.2f}")
        if summary.average_response_time_seconds is None:
            self._metric_values["avg_time"].setText("-")
        else:
            self._metric_values["avg_time"].setText(
                self.translator.t(
                    "review_flow.summary_avg_time_value",
                    seconds=f"{summary.average_response_time_seconds:.2f}",
                )
            )
