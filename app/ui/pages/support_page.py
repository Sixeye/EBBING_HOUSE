"""Support page with a discreet external donation link."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.themes.branding import load_brand_logo
from app.ui.pages.base_page import BasePage
from app.ui.widgets.motion import repolish, set_feedback_visual


class SupportPage(BasePage):
    """Calm, optional support screen.

    We intentionally keep support in a dedicated page so learning flows are not
    interrupted by popups. Users can choose to support the project when they
    want, with one clear external button.
    """

    SUPPORT_URL = "https://pay.sumup.com/b2c/Q4L1VF5Q"

    def __init__(self, translator) -> None:
        super().__init__(translator)

        # We keep a translation key instead of raw text so locale changes can
        # re-render feedback state consistently.
        self._feedback_key = "support_flow.status_idle"
        self._feedback_state = "info"

        self._build_ui()
        self.update_texts()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._subtitle_label = QLabel()
        self._subtitle_label.setObjectName("PageSubtitle")
        self._subtitle_label.setWordWrap(True)

        self._panel = QFrame()
        self._panel.setObjectName("HeroPanel")
        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        self._brand_logo_label = QLabel()
        self._brand_logo_label.setObjectName("BrandLogo")
        self._brand_logo_label.setFixedSize(58, 58)
        self._brand_logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._brand_badge_label = QLabel()
        self._brand_badge_label.setObjectName("BrandTitle")
        self._brand_badge_label.setWordWrap(True)

        brand_row.addWidget(self._brand_logo_label)
        brand_row.addWidget(self._brand_badge_label, 1)

        self._intro_label = QLabel()
        self._intro_label.setObjectName("HeroTitle")
        self._intro_label.setWordWrap(True)

        self._amount_note_label = QLabel()
        self._amount_note_label.setObjectName("PageSubtitle")
        self._amount_note_label.setWordWrap(True)

        self._browser_note_label = QLabel()
        self._browser_note_label.setObjectName("PageSubtitle")
        self._browser_note_label.setWordWrap(True)

        self._url_label = QLabel()
        self._url_label.setObjectName("PageSubtitle")
        self._url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._url_label.setWordWrap(True)

        self._thank_you_label = QLabel()
        self._thank_you_label.setObjectName("PageSubtitle")
        self._thank_you_label.setWordWrap(True)

        self._open_button = QPushButton()
        self._open_button.setObjectName("PrimaryButton")
        self._open_button.setMinimumHeight(34)
        self._open_button.clicked.connect(self._open_support_link)

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setProperty("feedbackState", "info")

        panel_layout.addLayout(brand_row)
        panel_layout.addWidget(self._intro_label)
        panel_layout.addWidget(self._amount_note_label)
        panel_layout.addWidget(self._browser_note_label)
        panel_layout.addWidget(self._url_label)
        panel_layout.addWidget(self._thank_you_label)
        panel_layout.addSpacing(6)
        panel_layout.addWidget(self._open_button, alignment=Qt.AlignmentFlag.AlignLeft)
        panel_layout.addWidget(self._feedback_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        layout.addWidget(self._subtitle_label)
        layout.addWidget(self._panel)

    def _open_support_link(self) -> None:
        """Open SumUp support link in the user's default browser."""
        opened = QDesktopServices.openUrl(QUrl(self.SUPPORT_URL))
        if opened:
            self._feedback_key = "support_flow.status_opened"
            self._feedback_state = "success"
            self.notify_toast(
                self.translator.t("support_flow.status_opened"),
                level="success",
            )
        else:
            # We keep this friendly and actionable without intrusive dialogs.
            self._feedback_key = "support_flow.status_failed"
            self._feedback_state = "error"
            self.notify_toast(
                self.translator.t("support_flow.status_failed"),
                level="warning",
                duration_ms=3200,
            )

        self._feedback_label.setText(self._build_feedback_text())
        set_feedback_visual(self._feedback_label, self._feedback_state)

    def _build_feedback_text(self) -> str:
        text = self.translator.t(self._feedback_key)
        if self._feedback_key == "support_flow.status_failed":
            return f"{text}\n{self.SUPPORT_URL}"
        return text

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("pages.support.title"))
        self._subtitle_label.setText(self.translator.t("pages.support.description"))
        self._brand_badge_label.setText(self.translator.t("branding.support_badge"))
        self._brand_logo_label.setPixmap(load_brand_logo(52))
        self._intro_label.setText(self.translator.t("support_flow.intro"))
        self._amount_note_label.setText(self.translator.t("support_flow.amount_note"))
        self._browser_note_label.setText(self.translator.t("support_flow.browser_note"))
        self._url_label.setText(
            f"{self.translator.t('support_flow.url_label')} {self.SUPPORT_URL}"
        )
        self._thank_you_label.setText(self.translator.t("support_flow.thanks"))
        self._open_button.setText(self.translator.t("support_flow.open_button"))
        self._feedback_label.setText(self._build_feedback_text())
        # Locale refresh should keep feedback semantics but avoid re-triggering
        # motion effects unless the user performed a new action.
        self._feedback_label.setProperty("feedbackState", self._feedback_state)
        repolish(self._feedback_label)
