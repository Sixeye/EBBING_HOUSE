"""Trophies page displaying unlocked/locked rewards for the active profile."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from app.services.profile_service import ProfileService
from app.services.trophy_service import TrophyService
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.widgets.motion import set_feedback_visual
from desktop_app.ui.widgets.trophy_badge_visuals import build_trophy_badge_icon


class TrophiesPage(BasePage):
    """Simple reward center focused on profile progress visibility.

    We intentionally keep this page lightweight:
    - one active profile context
    - unlocked list
    - locked list
    - compact completion summary
    """

    def __init__(
        self,
        translator,
        profile_service: ProfileService,
        trophy_service: TrophyService,
    ) -> None:
        super().__init__(translator)
        self.profile_service = profile_service
        self.trophy_service = trophy_service

        self._build_ui()
        self._connect_signals()
        self.update_texts()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        self._summary_panel = QFrame()
        self._summary_panel.setObjectName("HeroPanel")
        summary_layout = QVBoxLayout(self._summary_panel)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(6)

        self._active_profile_label = QLabel()
        self._active_profile_label.setObjectName("SectionTitle")

        self._completion_label = QLabel()
        self._completion_label.setObjectName("PageSubtitle")
        self._completion_label.setWordWrap(True)

        self._latest_label = QLabel()
        self._latest_label.setObjectName("PageSubtitle")
        self._latest_label.setWordWrap(True)

        summary_actions = QHBoxLayout()
        summary_actions.setSpacing(8)
        self._refresh_button = QPushButton()
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.setMinimumHeight(32)

        summary_actions.addWidget(self._refresh_button)
        summary_actions.addStretch(1)

        summary_layout.addWidget(self._active_profile_label)
        summary_layout.addWidget(self._completion_label)
        summary_layout.addWidget(self._latest_label)
        summary_layout.addLayout(summary_actions)

        self._unlocked_panel = QFrame()
        self._unlocked_panel.setObjectName("PlaceholderPanel")
        unlocked_layout = QVBoxLayout(self._unlocked_panel)
        unlocked_layout.setContentsMargins(14, 12, 14, 12)
        unlocked_layout.setSpacing(8)

        self._unlocked_title_label = QLabel()
        self._unlocked_title_label.setObjectName("SectionTitle")

        self._unlocked_list = QListWidget()
        self._unlocked_list.setObjectName("TrophyUnlockedList")
        self._unlocked_list.setIconSize(QSize(42, 42))
        self._unlocked_list.setSpacing(4)
        self._unlocked_list.setMouseTracking(True)

        unlocked_layout.addWidget(self._unlocked_title_label)
        unlocked_layout.addWidget(self._unlocked_list)

        self._locked_panel = QFrame()
        self._locked_panel.setObjectName("PlaceholderPanel")
        locked_layout = QVBoxLayout(self._locked_panel)
        locked_layout.setContentsMargins(14, 12, 14, 12)
        locked_layout.setSpacing(8)

        self._locked_title_label = QLabel()
        self._locked_title_label.setObjectName("SectionTitle")

        self._locked_list = QListWidget()
        self._locked_list.setObjectName("TrophyLockedList")
        self._locked_list.setIconSize(QSize(42, 42))
        self._locked_list.setSpacing(4)
        self._locked_list.setMouseTracking(True)

        locked_layout.addWidget(self._locked_title_label)
        locked_layout.addWidget(self._locked_list)

        lists_row = QHBoxLayout()
        lists_row.setSpacing(14)
        lists_row.addWidget(self._unlocked_panel, 1)
        lists_row.addWidget(self._locked_panel, 1)

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setProperty("feedbackState", "info")
        self._feedback_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(self._summary_panel)
        layout.addLayout(lists_row)
        layout.addWidget(self._feedback_label)

    def _connect_signals(self) -> None:
        self._refresh_button.clicked.connect(self.refresh_content)

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("pages.trophies.title"))
        self._description_label.setText(self.translator.t("pages.trophies.description"))
        self._refresh_button.setText(self.translator.t("trophies_flow.refresh_button"))
        self._unlocked_title_label.setText(self.translator.t("trophies_flow.unlocked_title"))
        self._locked_title_label.setText(self.translator.t("trophies_flow.locked_title"))
        self.refresh_content()

    def refresh_content(self) -> None:
        active_profile = self.profile_service.get_active_profile()

        self._unlocked_list.clear()
        self._locked_list.clear()

        if active_profile is None or active_profile.id is None:
            self._active_profile_label.setText(
                self.translator.t("trophies_flow.no_active_profile_title")
            )
            self._completion_label.setText(
                self.translator.t("trophies_flow.no_active_profile_hint")
            )
            self._latest_label.setText(self.translator.t("trophies_flow.no_active_profile_latest"))
            self._feedback_label.setText(self.translator.t("trophies_flow.no_active_profile_feedback"))
            set_feedback_visual(self._feedback_label, "info")
            return

        unlocked = self.trophy_service.list_unlocked_trophies(active_profile.id)
        locked = self.trophy_service.list_locked_trophies(active_profile.id)

        total_count = self.trophy_service.total_trophies_count()
        unlocked_count = len(unlocked)
        remaining_count = max(0, total_count - unlocked_count)

        self._active_profile_label.setText(
            self.translator.t(
                "trophies_flow.active_profile_value",
                name=active_profile.name,
            )
        )
        self._completion_label.setText(
            self.translator.t(
                "trophies_flow.completion_value",
                unlocked=unlocked_count,
                total=total_count,
                remaining=remaining_count,
            )
        )

        latest = unlocked[0] if unlocked else None
        if latest is None:
            self._latest_label.setText(self.translator.t("trophies_flow.latest_none"))
        else:
            unlocked_at = self._format_datetime(latest.unlocked_at)
            self._latest_label.setText(
                self.translator.t(
                    "trophies_flow.latest_value",
                    trophy=latest.display_name(self.translator.locale),
                    unlocked_at=unlocked_at,
                )
            )

        if unlocked:
            for trophy in unlocked:
                item = self._build_trophy_item(trophy=trophy, unlocked=True)
                self._unlocked_list.addItem(item)
        else:
            self._unlocked_list.addItem(self.translator.t("trophies_flow.none_unlocked"))

        if locked:
            for trophy in locked:
                item = self._build_trophy_item(trophy=trophy, unlocked=False)
                self._locked_list.addItem(item)
        else:
            self._locked_list.addItem(self.translator.t("trophies_flow.none_locked"))

        self._feedback_label.setText(self.translator.t("trophies_flow.profile_ready_feedback"))
        set_feedback_visual(self._feedback_label, "success" if unlocked_count > 0 else "info")

    def _build_unlocked_item_text(self, trophy) -> str:
        name = self._localized_trophy_name(trophy)
        description = self._localized_trophy_description(trophy)
        unlocked_at = self._format_datetime(trophy.unlocked_at)
        return self.translator.t(
            "trophies_flow.unlocked_item",
            name=name,
            description=description,
            unlocked_at=unlocked_at,
        )

    def _build_locked_item_text(self, trophy) -> str:
        name = self._localized_trophy_name(trophy)
        description = self._localized_trophy_description(trophy)
        return self.translator.t(
            "trophies_flow.locked_item",
            name=name,
            description=description,
        )

    def _build_trophy_item(self, trophy, unlocked: bool) -> QListWidgetItem:
        """Create one list item with icon + tooltip metadata.

        We keep list usage (simple and robust), while adding richer reward
        identity through icon visuals and hover explanations.
        """
        text = self._build_unlocked_item_text(trophy) if unlocked else self._build_locked_item_text(trophy)
        item = QListWidgetItem(text)
        item.setIcon(
            build_trophy_badge_icon(
                code=trophy.code,
                category=trophy.category,
                rarity=trophy.rarity,
                unlocked=unlocked,
                size=42,
            )
        )
        item.setToolTip(self._build_trophy_tooltip(trophy, unlocked))

        # Locked trophies stay readable but visually calmer than unlocked ones.
        if not unlocked:
            item.setForeground(QColor("#A6A9B0"))
        return item

    def _build_trophy_tooltip(self, trophy, unlocked: bool) -> str:
        """Build a concise hover tooltip describing trophy meaning/state."""
        name = self._localized_trophy_name(trophy)
        description = self._localized_trophy_description(trophy)
        unlocked_at = self._format_datetime(trophy.unlocked_at)

        state_label = self.translator.t(
            "trophies_flow.tooltip_state_unlocked"
            if unlocked
            else "trophies_flow.tooltip_state_locked"
        )
        lines = [
            name,
            description,
            self.translator.t("trophies_flow.tooltip_state", state=state_label),
            self.translator.t(
                "trophies_flow.tooltip_rarity",
                rarity=self._rarity_label(trophy.rarity),
            ),
        ]
        if unlocked:
            lines.append(
                self.translator.t(
                    "trophies_flow.tooltip_unlocked_on",
                    unlocked_at=unlocked_at,
                )
            )
        else:
            lines.append(self.translator.t("trophies_flow.tooltip_locked_hint"))
        return "\n".join(lines)

    def _rarity_label(self, rarity: str) -> str:
        normalized = (rarity or "").strip().lower()
        key = f"trophies_flow.rarity_{normalized}"
        translated = self.translator.t(key)
        # Translator returns the key itself if missing. Keep a readable fallback
        # so tooltips remain helpful even during future rarity experiments.
        if translated == key:
            return normalized.capitalize() if normalized else "-"
        return translated

    def _localized_trophy_name(self, trophy) -> str:
        """Resolve trophy name from i18n catalog with DB fallback.

        Why this layer exists:
        - built-in DB fields currently store EN/FR names
        - UI supports more locales (DE/ES/PT)
        - this hook allows full localization now without schema churn
        """
        key = f"trophies_catalog.{trophy.code}.name"
        translated = self.translator.t(key)
        if translated != key:
            return translated
        return trophy.display_name(self.translator.locale)

    def _localized_trophy_description(self, trophy) -> str:
        """Resolve trophy description from i18n catalog with DB fallback."""
        key = f"trophies_catalog.{trophy.code}.description"
        translated = self.translator.t(key)
        if translated != key:
            return translated
        return trophy.display_description(self.translator.locale)

    @staticmethod
    def _format_datetime(value: str | None) -> str:
        if not value:
            return "-"

        # Store format is UTC timestamp string. We keep display simple in V1.
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M")
