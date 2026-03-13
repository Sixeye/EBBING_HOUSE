"""Left navigation sidebar for the main window."""

from __future__ import annotations

from collections import OrderedDict

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n.translator import Translator
from app.themes.branding import load_brand_logo


class SidebarWidget(QFrame):
    """Main app navigation with locale switcher."""

    navigation_requested = Signal(str)
    locale_changed = Signal(str)
    audio_toggle_requested = Signal()

    def __init__(self, translator: Translator) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        # Slightly narrower sidebar frees horizontal space for dense game
        # screens (maze/review/connect4) while still keeping labels readable.
        self.setMinimumWidth(204)
        self.setMaximumWidth(232)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.translator = translator
        self._buttons: OrderedDict[str, QPushButton] = OrderedDict()

        self._title_label = QLabel()
        self._title_label.setObjectName("AppTitle")

        self._tagline_label = QLabel()
        self._tagline_label.setObjectName("AppTagline")
        self._tagline_label.setWordWrap(True)

        self._brand_logo_label = QLabel()
        self._brand_logo_label.setObjectName("BrandLogo")
        self._brand_logo_label.setFixedSize(68, 68)
        self._brand_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brand_logo_label.setScaledContents(False)

        self._brand_note_label = QLabel()
        self._brand_note_label.setObjectName("BrandMiniCaption")
        self._brand_note_label.setWordWrap(True)

        self._language_label = QLabel()
        self._language_selector = QComboBox()
        self._language_selector.addItem("English", "en")
        self._language_selector.addItem("Francais", "fr")
        self._language_selector.addItem("Espanol", "es")
        self._language_selector.addItem("Portugues", "pt")
        self._language_selector.addItem("Deutsch", "de")
        self._language_selector.currentIndexChanged.connect(self._on_language_selected)

        self._audio_button = QToolButton()
        self._audio_button.setObjectName("SecondaryButton")
        self._audio_button.setAutoRaise(False)
        self._audio_button.setFixedSize(28, 28)
        self._audio_button.setIconSize(QSize(14, 14))
        self._audio_button.clicked.connect(self.audio_toggle_requested.emit)
        self._audio_enabled = True
        self._audio_available = True

        language_row = QWidget()
        language_layout = QHBoxLayout(language_row)
        language_layout.setContentsMargins(0, 0, 0, 0)
        language_layout.setSpacing(8)
        language_layout.addWidget(self._language_label)
        language_layout.addWidget(self._language_selector)
        language_layout.addWidget(self._audio_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(6)
        layout.addWidget(self._brand_logo_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._title_label)
        layout.addWidget(self._tagline_label)
        layout.addWidget(self._brand_note_label)
        layout.addSpacing(10)

        for page_key in (
            "dashboard",
            "memory_garden",
            "profiles",
            "decks",
            "questions",
            "import_csv",
            "review",
            "hangman",
            "connect4",
            "maze",
            "history",
            "trophies",
            "settings",
            "support",
        ):
            button = QPushButton()
            button.setObjectName("NavButton")
            button.setCheckable(True)
            # Bind `page_key` in the lambda default argument to avoid late-binding bugs.
            button.clicked.connect(lambda checked=False, key=page_key: self._on_nav_clicked(key))
            layout.addWidget(button)
            self._buttons[page_key] = button

        layout.addStretch(1)
        layout.addWidget(language_row)

        self.update_texts()
        self.set_active_page("dashboard")
        self._sync_locale_selector()

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("app.name"))
        self._tagline_label.setText(self.translator.t("app.tagline"))
        self._brand_note_label.setText(self.translator.t("branding.sidebar_note"))
        self._language_label.setText(self.translator.t("settings.language"))
        self._brand_logo_label.setPixmap(load_brand_logo(62))

        en_index = self._language_selector.findData("en")
        fr_index = self._language_selector.findData("fr")
        es_index = self._language_selector.findData("es")
        pt_index = self._language_selector.findData("pt")
        de_index = self._language_selector.findData("de")
        if en_index >= 0:
            self._language_selector.setItemText(en_index, self.translator.t("settings.language_en"))
        if fr_index >= 0:
            self._language_selector.setItemText(fr_index, self.translator.t("settings.language_fr"))
        if es_index >= 0:
            self._language_selector.setItemText(es_index, self.translator.t("settings.language_es"))
        if pt_index >= 0:
            self._language_selector.setItemText(pt_index, self.translator.t("settings.language_pt"))
        if de_index >= 0:
            self._language_selector.setItemText(de_index, self.translator.t("settings.language_de"))

        self._buttons["dashboard"].setText(self.translator.t("nav.dashboard"))
        self._buttons["memory_garden"].setText(self.translator.t("nav.memory_garden"))
        self._buttons["profiles"].setText(self.translator.t("nav.profiles"))
        self._buttons["decks"].setText(self.translator.t("nav.decks"))
        self._buttons["questions"].setText(self.translator.t("nav.questions"))
        self._buttons["import_csv"].setText(self.translator.t("nav.import_csv"))
        self._buttons["review"].setText(self.translator.t("nav.review"))
        self._buttons["hangman"].setText(self.translator.t("nav.hangman"))
        self._buttons["connect4"].setText(self.translator.t("nav.connect4"))
        self._buttons["maze"].setText(self.translator.t("nav.maze"))
        self._buttons["history"].setText(self.translator.t("nav.history"))
        self._buttons["trophies"].setText(self.translator.t("nav.trophies"))
        self._buttons["settings"].setText(self.translator.t("nav.settings"))
        self._buttons["support"].setText(self.translator.t("nav.support"))
        self._update_audio_button_visual()

    def set_audio_state(self, *, enabled: bool, available: bool) -> None:
        """Update compact speaker button based on runtime audio state."""
        self._audio_enabled = enabled
        self._audio_available = available
        self._update_audio_button_visual()

    def set_active_page(self, page_key: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page_key)

    def _sync_locale_selector(self) -> None:
        index = self._language_selector.findData(self.translator.locale)
        if index >= 0:
            self._language_selector.blockSignals(True)
            self._language_selector.setCurrentIndex(index)
            self._language_selector.blockSignals(False)

    def _on_nav_clicked(self, page_key: str) -> None:
        self.set_active_page(page_key)
        self.navigation_requested.emit(page_key)

    def _on_language_selected(self, index: int) -> None:
        locale = self._language_selector.itemData(index)
        if isinstance(locale, str):
            self.locale_changed.emit(locale)

    def _update_audio_button_visual(self) -> None:
        self._audio_button.setEnabled(self._audio_available)

        if not self._audio_available:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted)
            self._audio_button.setIcon(icon)
            self._audio_button.setToolTip(self.translator.t("audio_flow.unavailable_tooltip"))
            return

        if self._audio_enabled:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
            self._audio_button.setIcon(icon)
            self._audio_button.setToolTip(self.translator.t("audio_flow.mute_tooltip"))
        else:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted)
            self._audio_button.setIcon(icon)
            self._audio_button.setToolTip(self.translator.t("audio_flow.unmute_tooltip"))
