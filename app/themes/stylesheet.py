"""Qt stylesheet builder for the EBBING_HOUSE visual identity."""

from __future__ import annotations

from app.themes.palette import (
    ACCENT_ORANGE,
    ACCENT_ORANGE_HOVER,
    ACCENT_ORANGE_PRESSED,
    BACKGROUND_CARD,
    BACKGROUND_CARD_HOVER,
    ERROR_RED,
    SUCCESS_GREEN,
    BACKGROUND_PRIMARY,
    BACKGROUND_SECONDARY,
    BORDER_SUBTLE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def build_stylesheet() -> str:
    """Return the application-wide stylesheet.

    Styles stay centralized so future themes (light mode, seasonal skins)
    can be added without touching every widget class.
    """
    return f"""
    QWidget {{
        background-color: {BACKGROUND_PRIMARY};
        color: {TEXT_PRIMARY};
        font-family: "Avenir Next", "SF Pro Text", "Segoe UI";
        font-size: 14px;
    }}

    QWidget#AppRoot {{
        background-color: {BACKGROUND_PRIMARY};
    }}

    QWidget#ContentHost {{
        background-color: {BACKGROUND_PRIMARY};
    }}

    QScrollArea#PageScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollArea#PageScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    QFrame#Sidebar {{
        background-color: {BACKGROUND_SECONDARY};
        border-right: 1px solid {BORDER_SUBTLE};
    }}

    QLabel#AppTitle {{
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }}

    QLabel#AppTagline {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QLabel#BrandLogo {{
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 138, 45, 0.38);
        border-radius: 10px;
        padding: 3px;
    }}

    QLabel#BrandMiniCaption {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
        line-height: 1.15em;
    }}

    QLabel#BrandTitle {{
        font-size: 15px;
        font-weight: 650;
        color: {TEXT_PRIMARY};
    }}

    QLabel#BrandSubtitle {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QLabel#BrandBanner {{
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 138, 45, 0.34);
        border-radius: 12px;
        padding: 4px;
    }}

    QPushButton#NavButton {{
        text-align: left;
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 7px 10px;
        color: {TEXT_PRIMARY};
        background-color: transparent;
        font-weight: 500;
    }}

    QPushButton#NavButton:hover {{
        background-color: {BACKGROUND_CARD_HOVER};
        border: 1px solid rgba(255, 138, 45, 0.32);
    }}

    QPushButton#NavButton:checked {{
        background-color: rgba(255, 138, 45, 0.18);
        border: 1px solid rgba(255, 138, 45, 0.45);
    }}

    QFrame#MetricCard {{
        background-color: {BACKGROUND_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 14px;
    }}

    QFrame#MetricCard:hover {{
        background-color: {BACKGROUND_CARD_HOVER};
        border: 1px solid rgba(255, 138, 45, 0.45);
    }}

    QLabel#MetricTitle {{
        color: {TEXT_SECONDARY};
        font-size: 12px;
    }}

    QLabel#MetricValue {{
        color: {TEXT_PRIMARY};
        font-size: 24px;
        font-weight: 700;
    }}

    QLabel#MetricHint {{
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}

    QLabel#PageTitle {{
        font-size: 24px;
        font-weight: 700;
    }}

    QLabel#PageSubtitle {{
        font-size: 14px;
        color: {TEXT_SECONDARY};
    }}

    QLabel#SectionTitle {{
        font-size: 17px;
        font-weight: 600;
    }}

    QFrame#HeroPanel {{
        background-color: {BACKGROUND_CARD};
        border: 1px solid rgba(255, 138, 45, 0.35);
        border-radius: 16px;
    }}

    QFrame#HeroPanel:hover {{
        border: 1px solid rgba(255, 138, 45, 0.48);
        background-color: {BACKGROUND_CARD_HOVER};
    }}

    QLabel#HeroTitle {{
        font-size: 18px;
        font-weight: 650;
    }}

    QLabel#HeroSubtitle {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}

    QPushButton#PrimaryButton {{
        background-color: {ACCENT_ORANGE};
        color: #0F0F10;
        border: none;
        border-radius: 12px;
        padding: 8px 13px;
        min-height: 30px;
        font-weight: 700;
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: {ACCENT_ORANGE_HOVER};
        border: 1px solid rgba(255, 239, 224, 0.34);
    }}

    QPushButton#PrimaryButton:pressed {{
        background-color: {ACCENT_ORANGE_PRESSED};
    }}

    QPushButton#PrimaryButton:disabled {{
        background-color: #6E5D4D;
        color: rgba(15, 15, 16, 0.65);
    }}

    QPushButton#SecondaryButton {{
        background-color: {BACKGROUND_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 10px;
        padding: 7px 11px;
        min-height: 28px;
        font-weight: 600;
    }}

    QToolButton#SecondaryButton {{
        background-color: {BACKGROUND_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        padding: 3px 7px;
        min-height: 26px;
        min-width: 28px;
        font-weight: 700;
    }}

    QPushButton#DirectionButton {{
        background-color: {BACKGROUND_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 9px;
        min-width: 28px;
        min-height: 28px;
        max-width: 32px;
        max-height: 32px;
        font-size: 15px;
        font-weight: 700;
        padding: 1px;
    }}

    QPushButton#DirectionButton:hover {{
        border: 1px solid rgba(255, 138, 45, 0.60);
        background-color: {BACKGROUND_CARD_HOVER};
    }}

    QPushButton#DirectionButton:pressed {{
        background-color: {BACKGROUND_SECONDARY};
    }}

    QPushButton#DirectionButton:disabled {{
        color: #7D7F87;
        border: 1px solid #2A2C31;
        background-color: #1A1B1F;
    }}

    QPushButton#SecondaryButton:hover {{
        border: 1px solid rgba(255, 138, 45, 0.55);
        background-color: {BACKGROUND_CARD_HOVER};
    }}

    QToolButton#SecondaryButton:hover {{
        border: 1px solid rgba(255, 138, 45, 0.55);
        background-color: {BACKGROUND_CARD_HOVER};
    }}

    QPushButton#SecondaryButton:pressed {{
        background-color: {BACKGROUND_SECONDARY};
    }}

    QToolButton#SecondaryButton:pressed {{
        background-color: {BACKGROUND_SECONDARY};
    }}

    QPushButton#SecondaryButton:disabled {{
        color: #7D7F87;
        border: 1px solid #2A2C31;
        background-color: #1A1B1F;
    }}

    QToolButton#SecondaryButton:disabled {{
        color: #7D7F87;
        border: 1px solid #2A2C31;
        background-color: #1A1B1F;
    }}

    QPushButton#NavButton:disabled {{
        color: #7D7F87;
    }}

    QPushButton#PrimaryButton:focus,
    QPushButton#SecondaryButton:focus,
    QToolButton#SecondaryButton:focus,
    QPushButton#NavButton:focus {{
        outline: none;
        border: 1px solid rgba(255, 138, 45, 0.55);
    }}

    QTextEdit {{
        background-color: {BACKGROUND_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 10px;
        padding: 8px 9px;
        color: {TEXT_PRIMARY};
    }}

    QTextEdit:focus {{
        border: 1px solid rgba(255, 138, 45, 0.55);
    }}

    QFrame#PlaceholderPanel {{
        background-color: {BACKGROUND_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 14px;
    }}

    QFrame#PlaceholderPanel:hover {{
        border: 1px solid rgba(255, 138, 45, 0.38);
        background-color: {BACKGROUND_CARD_HOVER};
    }}

    QScrollArea#QuestionScrollArea {{
        border: none;
        background: transparent;
    }}

    QComboBox {{
        background-color: {BACKGROUND_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        padding: 4px 9px;
        min-width: 110px;
        min-height: 28px;
    }}

    QComboBox:hover,
    QComboBox:focus {{
        border: 1px solid rgba(255, 138, 45, 0.45);
    }}

    QComboBox::drop-down {{
        border: none;
        width: 16px;
    }}

    QLineEdit {{
        background-color: {BACKGROUND_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        padding: 4px 9px;
        color: {TEXT_PRIMARY};
        min-height: 28px;
    }}

    QLineEdit:focus {{
        border: 1px solid rgba(255, 138, 45, 0.55);
    }}

    QTableWidget {{
        background-color: {BACKGROUND_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 10px;
        gridline-color: {BORDER_SUBTLE};
        alternate-background-color: rgba(255, 255, 255, 0.02);
    }}

    QHeaderView::section {{
        background-color: {BACKGROUND_CARD};
        color: {TEXT_PRIMARY};
        border: none;
        border-bottom: 1px solid {BORDER_SUBTLE};
        padding: 6px 8px;
        font-weight: 600;
    }}

    QListWidget {{
        background-color: {BACKGROUND_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 10px;
        padding: 6px;
    }}

    QListWidget::item {{
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 8px;
        padding: 7px;
        margin: 3px 0;
    }}

    QListWidget::item:selected {{
        border: 1px solid rgba(255, 138, 45, 0.5);
        background-color: rgba(255, 138, 45, 0.14);
    }}

    QListWidget#TrophyUnlockedList::item {{
        border: 1px solid rgba(57, 178, 106, 0.38);
        background-color: rgba(57, 178, 106, 0.09);
    }}

    QListWidget#TrophyUnlockedList::item:hover {{
        border: 1px solid rgba(57, 178, 106, 0.62);
        background-color: rgba(57, 178, 106, 0.15);
    }}

    QListWidget#TrophyLockedList::item {{
        border: 1px solid rgba(170, 170, 174, 0.20);
        background-color: rgba(255, 255, 255, 0.02);
    }}

    QListWidget#TrophyLockedList::item:hover {{
        border: 1px solid rgba(255, 138, 45, 0.38);
        background-color: rgba(255, 138, 45, 0.08);
    }}

    QLabel#FeedbackLabel {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
        border: 1px solid rgba(170, 170, 174, 0.18);
        border-radius: 10px;
        padding: 5px 9px;
        background-color: rgba(255, 255, 255, 0.02);
    }}

    QLabel#FeedbackLabel[feedbackState="info"] {{
        color: {TEXT_SECONDARY};
        border: 1px solid rgba(170, 170, 174, 0.22);
        background-color: rgba(255, 255, 255, 0.03);
    }}

    QLabel#FeedbackLabel[feedbackState="success"] {{
        color: {SUCCESS_GREEN};
        border: 1px solid rgba(57, 178, 106, 0.42);
        background-color: rgba(57, 178, 106, 0.10);
    }}

    QLabel#FeedbackLabel[feedbackState="error"] {{
        color: {ERROR_RED};
        border: 1px solid rgba(217, 91, 91, 0.45);
        background-color: rgba(217, 91, 91, 0.10);
    }}

    QLabel#ImagePreview {{
        border: 1px dashed rgba(170, 170, 174, 0.30);
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.02);
        color: {TEXT_SECONDARY};
        padding: 6px;
    }}

    QLabel#DueValueLabel {{
        font-size: 36px;
        font-weight: 700;
        letter-spacing: 0.3px;
        color: {ACCENT_ORANGE};
    }}

    QLabel#DueValueLabel[dueState="idle"] {{
        color: #AAAAAE;
    }}

    QLabel#DueValueLabel[dueState="clear"] {{
        color: {SUCCESS_GREEN};
    }}

    QLabel#DueValueLabel[dueState="due"] {{
        color: {ACCENT_ORANGE};
    }}

    QLabel#DangerValueLabel {{
        font-size: 28px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: {ACCENT_ORANGE};
    }}

    QLabel#DangerValueLabel[dangerState="idle"] {{
        color: #AAAAAE;
    }}

    QLabel#DangerValueLabel[dangerState="safe"] {{
        color: {SUCCESS_GREEN};
    }}

    QLabel#DangerValueLabel[dangerState="warning"] {{
        color: {ACCENT_ORANGE};
    }}

    QLabel#DangerValueLabel[dangerState="critical"] {{
        color: {ERROR_RED};
    }}

    QFrame#ToastFrame {{
        background-color: rgba(22, 24, 29, 0.95);
        border: 1px solid rgba(170, 170, 174, 0.34);
        border-radius: 12px;
    }}

    QFrame#ToastFrame[toastLevel="info"] {{
        border: 1px solid rgba(170, 170, 174, 0.40);
    }}

    QFrame#ToastFrame[toastLevel="success"] {{
        border: 1px solid rgba(57, 178, 106, 0.62);
    }}

    QFrame#ToastFrame[toastLevel="warning"] {{
        border: 1px solid rgba(255, 138, 45, 0.66);
    }}

    QLabel#ToastIcon {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(170, 170, 174, 0.38);
        border-radius: 9px;
        font-size: 11px;
        font-weight: 700;
    }}

    QFrame#ToastFrame[toastLevel="success"] QLabel#ToastIcon {{
        color: {SUCCESS_GREEN};
        border: 1px solid rgba(57, 178, 106, 0.55);
        background-color: rgba(57, 178, 106, 0.10);
    }}

    QFrame#ToastFrame[toastLevel="warning"] QLabel#ToastIcon {{
        color: {ACCENT_ORANGE};
        border: 1px solid rgba(255, 138, 45, 0.58);
        background-color: rgba(255, 138, 45, 0.11);
    }}

    QFrame#ToastFrame[toastLevel="info"] QLabel#ToastIcon {{
        color: {TEXT_SECONDARY};
    }}

    QLabel#ToastTitle {{
        color: {TEXT_PRIMARY};
        font-size: 12px;
        font-weight: 650;
    }}

    QLabel#ToastMessage {{
        color: {TEXT_PRIMARY};
        font-size: 12px;
    }}

    QProgressBar {{
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        text-align: center;
        background-color: {BACKGROUND_CARD};
        color: {TEXT_PRIMARY};
        min-height: 16px;
    }}

    QProgressBar::chunk {{
        border-radius: 7px;
        background-color: {ACCENT_ORANGE};
    }}
    """
