"""Settings page for language and experience preferences."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QLabel,
    QVBoxLayout,
)

from app.services.settings_service import SettingsService
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.widgets.motion import set_feedback_visual


class SettingsPage(BasePage):
    """Editable global settings page.

    We keep this page intentionally small:
    - language
    - animations on/off
    - sounds on/off
    This gives immediate product value without adding heavy preferences logic.
    """

    language_change_requested = Signal(str)
    sounds_changed = Signal(bool)

    def __init__(self, translator, settings_service: SettingsService) -> None:
        super().__init__(translator)
        self.settings_service = settings_service
        self._updating_widgets = False

        self._build_ui()
        self.update_texts()
        self.refresh_settings()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        panel = QFrame()
        panel.setObjectName("PlaceholderPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(10)

        self._language_label = QLabel()
        self._language_selector = QComboBox()
        self._language_selector.setMinimumHeight(32)
        self._language_selector.currentIndexChanged.connect(self._on_language_changed)

        self._theme_label = QLabel()
        self._theme_selector = QComboBox()
        self._theme_selector.setMinimumHeight(32)
        self._theme_selector.currentIndexChanged.connect(self._on_theme_changed)

        self._animations_checkbox = QCheckBox()
        self._animations_checkbox.stateChanged.connect(self._on_animations_toggled)

        self._sounds_checkbox = QCheckBox()
        self._sounds_checkbox.stateChanged.connect(self._on_sounds_toggled)

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setProperty("feedbackState", "info")
        self._feedback_label.setWordWrap(True)

        panel_layout.addWidget(self._language_label)
        panel_layout.addWidget(self._language_selector)
        panel_layout.addWidget(self._theme_label)
        panel_layout.addWidget(self._theme_selector)
        panel_layout.addWidget(self._animations_checkbox)
        panel_layout.addWidget(self._sounds_checkbox)
        panel_layout.addWidget(self._feedback_label)

        content = QVBoxLayout(self)
        content.setContentsMargins(22, 18, 22, 18)
        content.setSpacing(12)
        content.addWidget(self._title_label)
        content.addWidget(self._description_label)
        content.addWidget(panel)

    def refresh_settings(self) -> None:
        """Load persisted settings and reflect them in controls."""
        settings = self.settings_service.get_settings()
        self._updating_widgets = True
        try:
            self._set_combo_value(self._language_selector, settings.app_language)
            self._set_combo_value(self._theme_selector, settings.default_theme)
            self._animations_checkbox.setChecked(settings.animations_enabled)
            self._sounds_checkbox.setChecked(settings.sounds_enabled)
        finally:
            self._updating_widgets = False

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("pages.settings.title"))
        self._description_label.setText(self.translator.t("pages.settings.description"))
        self._language_label.setText(self.translator.t("settings_flow.language_label"))
        self._theme_label.setText(self.translator.t("settings_flow.theme_label"))
        self._animations_checkbox.setText(self.translator.t("settings_flow.animations_label"))
        self._sounds_checkbox.setText(self.translator.t("settings_flow.sounds_label"))

        self._language_selector.blockSignals(True)
        self._language_selector.clear()
        self._language_selector.addItem(self.translator.t("settings.language_en"), "en")
        self._language_selector.addItem(self.translator.t("settings.language_fr"), "fr")
        self._language_selector.addItem(self.translator.t("settings.language_es"), "es")
        self._language_selector.addItem(self.translator.t("settings.language_pt"), "pt")
        self._language_selector.addItem(self.translator.t("settings.language_de"), "de")
        self._language_selector.blockSignals(False)

        # Theme is intentionally constrained to dark for now. We still expose a
        # selector so the architecture is ready for a future light mode.
        self._theme_selector.blockSignals(True)
        self._theme_selector.clear()
        self._theme_selector.addItem(self.translator.t("settings_flow.theme_dark"), "dark")
        self._theme_selector.blockSignals(False)

        self.refresh_settings()
        self._set_feedback(self.translator.t("settings_flow.ready"), "info")

    def _on_language_changed(self, index: int) -> None:
        if self._updating_widgets:
            return
        locale = self._language_selector.itemData(index)
        if not isinstance(locale, str):
            return
        # MainWindow remains the single place that applies + persists locale so
        # sidebar and page selectors stay synchronized through one signal path.
        self.language_change_requested.emit(locale)
        self._set_feedback(self.translator.t("settings_flow.saved_language"), "success")

    def _on_theme_changed(self, index: int) -> None:
        if self._updating_widgets:
            return
        theme = self._theme_selector.itemData(index)
        if not isinstance(theme, str):
            return
        self.settings_service.set_default_theme(theme)
        self._set_feedback(self.translator.t("settings_flow.saved_theme"), "success")

    def _on_animations_toggled(self) -> None:
        if self._updating_widgets:
            return
        self.settings_service.set_animations_enabled(self._animations_checkbox.isChecked())
        self._set_feedback(self.translator.t("settings_flow.saved_animations"), "success")

    def _on_sounds_toggled(self) -> None:
        if self._updating_widgets:
            return
        enabled = self._sounds_checkbox.isChecked()
        self.settings_service.set_sounds_enabled(enabled)
        # Let shell-level UI controls (speaker button + music controller)
        # react immediately without coupling this page to those widgets.
        self.sounds_changed.emit(enabled)
        self._set_feedback(self.translator.t("settings_flow.saved_sounds"), "success")

    def _set_feedback(self, message: str, state: str) -> None:
        self._feedback_label.setText(message)
        set_feedback_visual(self._feedback_label, state)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)


__all__ = ["SettingsPage"]
