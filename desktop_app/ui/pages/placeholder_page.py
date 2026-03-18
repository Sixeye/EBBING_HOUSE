"""Reusable placeholder page for not-yet-implemented sections."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from desktop_app.ui.pages.base_page import BasePage


class PlaceholderPage(BasePage):
    """Simple page template to keep navigation complete in MVP."""

    def __init__(self, translator, title_key: str, description_key: str) -> None:
        super().__init__(translator)
        self._title_key = title_key
        self._description_key = description_key

        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        self._panel = QFrame()
        self._panel.setObjectName("PlaceholderPanel")

        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(8)

        self._coming_soon_label = QLabel()
        self._coming_soon_label.setWordWrap(True)
        panel_layout.addWidget(self._coming_soon_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(self._panel)
        layout.addStretch(1)

        self.update_texts()

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t(self._title_key))
        self._description_label.setText(self.translator.t(self._description_key))
        self._coming_soon_label.setText(self.translator.t("common.coming_soon"))
