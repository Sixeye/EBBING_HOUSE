"""Compact page showing recent completed game runs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.profile_service import ProfileService
from app.services.run_history_service import RunHistoryService
from desktop_app.ui.pages.base_page import BasePage


class HistoryPage(BasePage):
    """Show lightweight personal history for the active profile."""

    _COLUMN_TIME = 0
    _COLUMN_MODE = 1
    _COLUMN_DECK = 2
    _COLUMN_RESULT = 3
    _COLUMN_SCORE = 4
    _COLUMN_COUNTS = 5

    def __init__(
        self,
        translator,
        profile_service: ProfileService,
        run_history_service: RunHistoryService,
    ) -> None:
        super().__init__(translator)
        self.profile_service = profile_service
        self.run_history_service = run_history_service

        self._build_ui()
        self.update_texts()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._subtitle_label = QLabel()
        self._subtitle_label.setObjectName("PageSubtitle")
        self._subtitle_label.setWordWrap(True)

        controls_panel = QFrame()
        controls_panel.setObjectName("PlaceholderPanel")
        controls_layout = QHBoxLayout(controls_panel)
        controls_layout.setContentsMargins(14, 10, 14, 10)
        controls_layout.setSpacing(8)

        self._profile_status_label = QLabel()
        self._profile_status_label.setObjectName("PageSubtitle")
        self._profile_status_label.setWordWrap(True)

        self._refresh_button = QPushButton()
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.setMinimumHeight(32)
        self._refresh_button.clicked.connect(self.refresh_runs)

        controls_layout.addWidget(self._profile_status_label, 1)
        controls_layout.addWidget(self._refresh_button)

        self._table = QTableWidget(0, 6)
        self._table.setObjectName("HistoryTable")
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setMinimumHeight(300)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("PageSubtitle")
        self._empty_label.setWordWrap(True)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)
        layout.addWidget(controls_panel)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._empty_label)

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("pages.history.title"))
        self._subtitle_label.setText(self.translator.t("pages.history.description"))
        self._refresh_button.setText(self.translator.t("history_flow.refresh"))
        self._table.setHorizontalHeaderLabels(
            [
                self.translator.t("history_flow.columns.time"),
                self.translator.t("history_flow.columns.mode"),
                self.translator.t("history_flow.columns.deck"),
                self.translator.t("history_flow.columns.result"),
                self.translator.t("history_flow.columns.score"),
                self.translator.t("history_flow.columns.counts"),
            ]
        )
        self.refresh_runs()

    def refresh_runs(self) -> None:
        """Reload rows for the active profile.

        We keep filtering by active profile to stay aligned with the app's
        "one learner context at a time" UX principle.
        """
        active_profile = self.profile_service.get_active_profile()
        if active_profile is None or active_profile.id is None:
            self._profile_status_label.setText(self.translator.t("history_flow.no_profile"))
            self._table.hide()
            self._empty_label.setText(self.translator.t("history_flow.no_profile_hint"))
            self._empty_label.show()
            return

        self._profile_status_label.setText(
            self.translator.t("history_flow.active_profile", name=active_profile.name)
        )
        runs = self.run_history_service.list_recent_runs(
            profile_id=active_profile.id,
            limit=25,
        )
        self._table.setRowCount(0)

        if not runs:
            self._table.hide()
            self._empty_label.setText(self.translator.t("history_flow.empty"))
            self._empty_label.show()
            return

        self._table.show()
        self._empty_label.hide()

        for run in runs:
            row = self._table.rowCount()
            self._table.insertRow(row)

            # Datetimes are persisted in a SQLite-friendly format. We keep
            # display simple and localizable later if needed.
            self._table.setItem(row, self._COLUMN_TIME, QTableWidgetItem(run.ended_at))
            self._table.setItem(
                row,
                self._COLUMN_MODE,
                QTableWidgetItem(self._mode_label(run.mode)),
            )
            self._table.setItem(
                row,
                self._COLUMN_DECK,
                QTableWidgetItem(run.deck_name or self.translator.t("history_flow.deck_unknown")),
            )
            self._table.setItem(
                row,
                self._COLUMN_RESULT,
                QTableWidgetItem(
                    self._result_label(run.did_win, run.summary_text)
                ),
            )
            self._table.setItem(
                row,
                self._COLUMN_SCORE,
                QTableWidgetItem(
                    f"{run.score_on_100:.1f}" if run.score_on_100 is not None else "-"
                ),
            )
            counts_text = self.translator.t(
                "history_flow.counts_value",
                correct=run.correct_count if run.correct_count is not None else 0,
                wrong=run.wrong_count if run.wrong_count is not None else 0,
            )
            self._table.setItem(row, self._COLUMN_COUNTS, QTableWidgetItem(counts_text))

        self._table.resizeColumnsToContents()

    def _mode_label(self, mode: str) -> str:
        key = f"history_flow.mode.{mode}"
        resolved = self.translator.t(key)
        if resolved == key:
            return mode
        return resolved

    def _result_label(self, did_win: bool, summary_text: str | None) -> str:
        if summary_text and summary_text.startswith("draw"):
            return self.translator.t("history_flow.result_draw")
        return self.translator.t("history_flow.result_win") if did_win else self.translator.t(
            "history_flow.result_loss"
        )


__all__ = ["HistoryPage"]
