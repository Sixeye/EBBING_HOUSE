"""Memory Garden page: calm visual progression tied to real learning data."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.models.memory_garden import MemoryGardenSnapshot, MemoryGardenTree
from app.services.memory_garden_service import MemoryGardenService
from app.services.profile_service import ProfileService
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.widgets.memory_garden_widget import MemoryGardenWidget
from desktop_app.ui.widgets.motion import flash_widget


class MemoryGardenPage(BasePage):
    """Profile-aware garden view with blocky trees driven by progress metrics."""

    open_review_due_requested = Signal()
    open_review_due_for_deck_requested = Signal(int)

    def __init__(
        self,
        translator,
        profile_service: ProfileService,
        memory_garden_service: MemoryGardenService,
    ) -> None:
        super().__init__(translator)
        self.profile_service = profile_service
        self.memory_garden_service = memory_garden_service

        self._snapshot = MemoryGardenSnapshot(profile_id=None, profile_name=None)
        self._selected_deck_id: int | None = None

        self._build_ui()
        self._connect_signals()
        self.update_texts()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        # Refresh on show keeps profile-dependent visuals current even when
        # progress changed in other pages while this page was hidden.
        self.refresh_garden()

    def _build_ui(self) -> None:
        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")

        self._description_label = QLabel()
        self._description_label.setObjectName("PageSubtitle")
        self._description_label.setWordWrap(True)

        self._header_panel = QFrame()
        self._header_panel.setObjectName("HeroPanel")
        header_layout = QVBoxLayout(self._header_panel)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(5)

        self._active_profile_label = QLabel()
        self._active_profile_label.setObjectName("SectionTitle")

        self._mood_label = QLabel()
        self._mood_label.setObjectName("PageSubtitle")
        self._mood_label.setWordWrap(True)

        self._empty_state_label = QLabel()
        self._empty_state_label.setObjectName("PageSubtitle")
        self._empty_state_label.setWordWrap(True)

        header_layout.addWidget(self._active_profile_label)
        header_layout.addWidget(self._mood_label)
        header_layout.addWidget(self._empty_state_label)

        self._garden_panel = QFrame()
        self._garden_panel.setObjectName("PlaceholderPanel")
        garden_layout = QVBoxLayout(self._garden_panel)
        garden_layout.setContentsMargins(10, 10, 10, 10)
        garden_layout.setSpacing(8)

        self._garden_widget = MemoryGardenWidget()
        garden_layout.addWidget(self._garden_widget)

        stats_panel = QFrame()
        stats_panel.setObjectName("PlaceholderPanel")
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(14, 10, 14, 10)
        stats_layout.setSpacing(12)

        self._stats_tracked_label = QLabel()
        self._stats_tracked_label.setObjectName("PageSubtitle")

        self._stats_mastery_label = QLabel()
        self._stats_mastery_label.setObjectName("PageSubtitle")

        self._stats_due_label = QLabel()
        self._stats_due_label.setObjectName("PageSubtitle")

        self._stats_trophies_label = QLabel()
        self._stats_trophies_label.setObjectName("PageSubtitle")

        stats_layout.addWidget(self._stats_tracked_label)
        stats_layout.addWidget(self._stats_mastery_label)
        stats_layout.addWidget(self._stats_due_label)
        stats_layout.addWidget(self._stats_trophies_label)
        stats_layout.addStretch(1)

        legend_panel = QFrame()
        legend_panel.setObjectName("PlaceholderPanel")
        legend_layout = QVBoxLayout(legend_panel)
        legend_layout.setContentsMargins(14, 10, 14, 10)
        legend_layout.setSpacing(4)

        self._legend_title_label = QLabel()
        self._legend_title_label.setObjectName("SectionTitle")

        self._legend_lush_label = QLabel()
        self._legend_lush_label.setObjectName("PageSubtitle")

        self._legend_growing_label = QLabel()
        self._legend_growing_label.setObjectName("PageSubtitle")

        self._legend_fragile_label = QLabel()
        self._legend_fragile_label.setObjectName("PageSubtitle")

        legend_layout.addWidget(self._legend_title_label)
        legend_layout.addWidget(self._legend_lush_label)
        legend_layout.addWidget(self._legend_growing_label)
        legend_layout.addWidget(self._legend_fragile_label)

        self._detail_panel = QFrame()
        self._detail_panel.setObjectName("PlaceholderPanel")
        detail_layout = QVBoxLayout(self._detail_panel)
        detail_layout.setContentsMargins(14, 10, 14, 10)
        detail_layout.setSpacing(5)

        self._detail_title_label = QLabel()
        self._detail_title_label.setObjectName("SectionTitle")

        self._detail_deck_name_label = QLabel()
        self._detail_deck_name_label.setObjectName("MetricValue")
        self._detail_deck_name_label.setStyleSheet("font-size: 22px;")

        self._detail_metrics_label = QLabel()
        self._detail_metrics_label.setObjectName("PageSubtitle")
        self._detail_metrics_label.setWordWrap(True)

        self._detail_status_label = QLabel()
        self._detail_status_label.setObjectName("PageSubtitle")
        self._detail_status_label.setWordWrap(True)

        self._detail_review_button = QPushButton()
        self._detail_review_button.setObjectName("PrimaryButton")
        self._detail_review_button.setMinimumHeight(34)

        detail_layout.addWidget(self._detail_title_label)
        detail_layout.addWidget(self._detail_deck_name_label)
        detail_layout.addWidget(self._detail_metrics_label)
        detail_layout.addWidget(self._detail_status_label)
        detail_layout.addWidget(self._detail_review_button)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self._refresh_button = QPushButton()
        self._refresh_button.setObjectName("SecondaryButton")
        self._refresh_button.setMinimumHeight(32)

        self._review_due_button = QPushButton()
        self._review_due_button.setObjectName("PrimaryButton")
        self._review_due_button.setMinimumHeight(34)

        actions_row.addWidget(self._refresh_button)
        actions_row.addWidget(self._review_due_button)
        actions_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(self._header_panel)
        layout.addWidget(self._garden_panel, 1)
        layout.addWidget(stats_panel)
        layout.addWidget(legend_panel)
        layout.addWidget(self._detail_panel)
        layout.addLayout(actions_row)

    def _connect_signals(self) -> None:
        self._refresh_button.clicked.connect(self.refresh_garden)
        self._review_due_button.clicked.connect(self._on_open_review_due_general)
        self._detail_review_button.clicked.connect(self._on_open_review_for_selected_deck)
        self._garden_widget.tree_selected.connect(self._on_tree_selected)

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("pages.memory_garden.title"))
        self._description_label.setText(self.translator.t("pages.memory_garden.description"))

        self._refresh_button.setText(self.translator.t("memory_garden.refresh_button"))
        self._review_due_button.setText(self.translator.t("memory_garden.review_due_button"))

        self._legend_title_label.setText(self.translator.t("memory_garden.legend_title"))
        self._legend_lush_label.setText(self.translator.t("memory_garden.legend_lush"))
        self._legend_growing_label.setText(self.translator.t("memory_garden.legend_growing"))
        self._legend_fragile_label.setText(self.translator.t("memory_garden.legend_fragile"))
        self._detail_title_label.setText(self.translator.t("memory_garden.detail_title"))
        self._detail_review_button.setText(self.translator.t("memory_garden.detail_review_button"))

        self.refresh_garden()

    def refresh_garden(self) -> None:
        """Rebuild and render garden snapshot for the active profile."""
        active_profile = self.profile_service.get_active_profile()
        active_profile_id = active_profile.id if active_profile and active_profile.id is not None else None

        snapshot = self.memory_garden_service.build_snapshot(active_profile_id)
        self._snapshot = snapshot
        self._garden_widget.set_snapshot(snapshot)
        flash_widget(self._garden_widget, start_opacity=0.86, duration_ms=170)

        valid_deck_ids = {tree.deck_id for tree in snapshot.trees}
        if self._selected_deck_id not in valid_deck_ids:
            self._selected_deck_id = None
        self._garden_widget.set_selected_deck_id(self._selected_deck_id)

        if not snapshot.has_active_profile:
            self._active_profile_label.setText(self.translator.t("memory_garden.no_profile_title"))
            self._empty_state_label.setText(self.translator.t("memory_garden.no_profile_hint"))
            self._empty_state_label.show()
            self._review_due_button.setEnabled(False)
            self._detail_review_button.setEnabled(False)
        else:
            self._active_profile_label.setText(
                self.translator.t("memory_garden.active_profile", name=snapshot.profile_name or "-")
            )
            if snapshot.has_growth:
                self._empty_state_label.clear()
                self._empty_state_label.hide()
            else:
                self._empty_state_label.setText(self.translator.t("memory_garden.no_growth_hint"))
                self._empty_state_label.show()

            self._review_due_button.setEnabled(True)
            self._detail_review_button.setEnabled(self._selected_deck_id is not None)

        self._mood_label.setText(self.translator.t(snapshot.mood_key))

        self._stats_tracked_label.setText(
            self.translator.t(
                "memory_garden.stats_tracked",
                value=snapshot.total_tracked_questions,
            )
        )
        self._stats_mastery_label.setText(
            self.translator.t(
                "memory_garden.stats_mastery",
                value=f"{snapshot.average_mastery_score:.1f}",
            )
        )
        self._stats_due_label.setText(
            self.translator.t(
                "memory_garden.stats_due",
                value=snapshot.total_due_questions,
            )
        )
        self._stats_trophies_label.setText(
            self.translator.t(
                "memory_garden.stats_trophies",
                value=snapshot.trophies_unlocked,
            )
        )

        self._render_selected_tree_details()

    def _on_tree_selected(self, deck_id: int) -> None:
        self._selected_deck_id = deck_id
        self._garden_widget.set_selected_deck_id(deck_id)
        self._render_selected_tree_details()

    def _render_selected_tree_details(self) -> None:
        selected = self._selected_tree()
        if selected is None:
            self._detail_deck_name_label.setText(self.translator.t("memory_garden.detail_no_selection"))
            self._detail_metrics_label.setText(self.translator.t("memory_garden.detail_no_selection_hint"))
            self._detail_status_label.clear()
            self._detail_review_button.setEnabled(False)
            flash_widget(self._detail_panel, start_opacity=0.86, duration_ms=150)
            return

        self._detail_deck_name_label.setText(selected.deck_name)
        self._detail_metrics_label.setText(
            self.translator.t(
                "memory_garden.detail_metrics",
                tracked=selected.tracked_questions,
                mastery=f"{selected.average_mastery:.1f}",
                due=selected.due_questions,
                weak=selected.weak_questions,
            )
        )

        status_key = {
            "lush": "memory_garden.health_lush",
            "growing": "memory_garden.health_growing",
            "fragile": "memory_garden.health_fragile",
        }.get(selected.health_state, "memory_garden.health_growing")

        extra_key = (
            "memory_garden.detail_due_none"
            if selected.due_questions == 0
            else "memory_garden.detail_due_has_items"
        )
        self._detail_status_label.setText(
            f"{self.translator.t(status_key)} {self.translator.t(extra_key)}"
        )
        self._detail_review_button.setEnabled(self._snapshot.has_active_profile)
        flash_widget(self._detail_panel, start_opacity=0.84, duration_ms=150)

    def _selected_tree(self) -> MemoryGardenTree | None:
        if self._selected_deck_id is None:
            return None
        for tree in self._snapshot.trees:
            if tree.deck_id == self._selected_deck_id:
                return tree
        return None

    def _on_open_review_due_general(self) -> None:
        """Fallback CTA: open due review with active profile defaults."""
        # We keep this button for quick access from the garden page.
        if not self._snapshot.has_active_profile:
            return
        # Reuse selected tree when possible to reduce user clicks.
        if self._selected_deck_id is not None:
            self.open_review_due_for_deck_requested.emit(self._selected_deck_id)
            return
        # If no tree is selected we still open due mode with active profile
        # defaults so the main CTA remains useful as a generic "review now".
        self.open_review_due_requested.emit()

    def _on_open_review_for_selected_deck(self) -> None:
        if self._selected_deck_id is None:
            return
        self.open_review_due_for_deck_requested.emit(self._selected_deck_id)


__all__ = ["MemoryGardenPage"]
