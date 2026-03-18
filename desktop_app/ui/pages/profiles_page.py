"""Profiles page with minimal CRUD and active profile selection."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.services.profile_service import ProfileService
from app.services.trophy_service import TrophyService
from desktop_app.ui.pages.base_page import BasePage
from desktop_app.ui.widgets.motion import set_feedback_visual


class ProfilesPage(BasePage):
    """Manage learner profiles and choose one active learner for the app."""

    profile_state_changed = Signal()

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

        # Profiles list panel
        list_panel = QFrame()
        list_panel.setObjectName("PlaceholderPanel")
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(14, 12, 14, 12)
        list_layout.setSpacing(8)

        self._list_title_label = QLabel()
        self._list_title_label.setObjectName("SectionTitle")

        self._profiles_list = QListWidget()
        self._profiles_list.setMinimumHeight(210)

        self._empty_label = QLabel()
        self._empty_label.setObjectName("PageSubtitle")
        self._empty_label.setWordWrap(True)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self._set_active_button = QPushButton()
        self._set_active_button.setObjectName("SecondaryButton")
        self._set_active_button.setMinimumHeight(32)
        self._set_active_button.setEnabled(False)

        self._delete_button = QPushButton()
        self._delete_button.setObjectName("SecondaryButton")
        self._delete_button.setMinimumHeight(32)
        self._delete_button.setEnabled(False)

        self._feedback_label = QLabel()
        self._feedback_label.setObjectName("FeedbackLabel")
        self._feedback_label.setProperty("feedbackState", "info")
        self._feedback_label.setWordWrap(True)

        actions_row.addWidget(self._set_active_button)
        actions_row.addWidget(self._delete_button)
        actions_row.addStretch(1)

        list_layout.addWidget(self._list_title_label)
        list_layout.addWidget(self._profiles_list)
        list_layout.addWidget(self._empty_label)
        list_layout.addLayout(actions_row)
        list_layout.addWidget(self._feedback_label)

        # Create panel
        create_panel = QFrame()
        create_panel.setObjectName("PlaceholderPanel")
        create_layout = QVBoxLayout(create_panel)
        create_layout.setContentsMargins(14, 12, 14, 12)
        create_layout.setSpacing(8)

        self._create_title_label = QLabel()
        self._create_title_label.setObjectName("SectionTitle")

        self._name_input = QLineEdit()
        self._name_input.setMinimumHeight(32)

        self._create_button = QPushButton()
        self._create_button.setObjectName("PrimaryButton")
        self._create_button.setMinimumHeight(34)

        create_layout.addWidget(self._create_title_label)
        create_layout.addWidget(self._name_input)
        create_layout.addWidget(self._create_button, alignment=Qt.AlignmentFlag.AlignLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        layout.addWidget(self._description_label)
        layout.addWidget(list_panel)
        layout.addWidget(create_panel)

    def _connect_signals(self) -> None:
        self._profiles_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._create_button.clicked.connect(self._on_create_profile)
        self._set_active_button.clicked.connect(self._on_set_active_profile)
        self._delete_button.clicked.connect(self._on_delete_profile)

    def update_texts(self) -> None:
        self._title_label.setText(self.translator.t("pages.profiles.title"))
        self._description_label.setText(self.translator.t("pages.profiles.description"))
        self._list_title_label.setText(self.translator.t("profiles_flow.list_title"))
        self._create_title_label.setText(self.translator.t("profiles_flow.create_title"))
        self._name_input.setPlaceholderText(self.translator.t("profiles_flow.name_placeholder"))
        self._create_button.setText(self.translator.t("profiles_flow.create_button"))
        self._set_active_button.setText(self.translator.t("profiles_flow.set_active_button"))
        self._delete_button.setText(self.translator.t("profiles_flow.delete_button"))
        self._empty_label.setText(self.translator.t("profiles_flow.empty_state"))
        self._refresh_profiles(select_profile_id=self._selected_profile_id())

    def _refresh_profiles(self, select_profile_id: int | None = None) -> None:
        profiles = self.profile_service.list_profiles()
        active_profile_id = self.profile_service.get_active_profile_id()

        self._profiles_list.blockSignals(True)
        self._profiles_list.clear()

        for profile in profiles:
            label = self.translator.t(
                "profiles_flow.profile_row",
                name=profile.name,
                language=profile.language.upper(),
            )
            if profile.id == active_profile_id:
                label = self.translator.t("profiles_flow.profile_row_active", value=label)

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, profile.id)
            self._profiles_list.addItem(item)

        if profiles:
            self._empty_label.hide()
            target_id = select_profile_id or active_profile_id or profiles[0].id
            target_row = self._find_row_for_profile_id(target_id)
            if target_row >= 0:
                self._profiles_list.setCurrentRow(target_row)
        else:
            self._empty_label.show()

        self._profiles_list.blockSignals(False)
        self._on_selection_changed()

    def _on_create_profile(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            self._set_feedback(self.translator.t("profiles_flow.error_name_required"), "error")
            return

        profile = self.profile_service.create_profile(name=name, language=self.translator.locale)
        unlocked_names = self._unlock_profile_created_trophies(profile.id)
        self._name_input.clear()
        self._refresh_profiles(select_profile_id=profile.id)
        created_message = self.translator.t("profiles_flow.created_message", name=profile.name)
        self._set_feedback(self._with_unlock_feedback(created_message, unlocked_names), "success")
        self._notify_unlock_toast(unlocked_names)
        self.profile_state_changed.emit()

    def _on_set_active_profile(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id is None:
            self._set_feedback(self.translator.t("profiles_flow.error_select_profile"), "error")
            return

        profile = self.profile_service.set_active_profile(profile_id)
        unlocked = self.trophy_service.on_active_profile_set(profile_id)
        unlocked_names = [item.display_name(self.translator.locale) for item in unlocked]
        self._refresh_profiles(select_profile_id=profile_id)
        active_message = self.translator.t(
            "profiles_flow.active_set_message",
            name=profile.name if profile else "",
        )
        self._set_feedback(self._with_unlock_feedback(active_message, unlocked_names), "success")
        self._notify_unlock_toast(unlocked_names)
        self.profile_state_changed.emit()

    def _on_delete_profile(self) -> None:
        profile_id = self._selected_profile_id()
        if profile_id is None:
            self._set_feedback(self.translator.t("profiles_flow.error_select_profile"), "error")
            return

        profile = self.profile_service.get_profile_by_id(profile_id)
        profile_name = profile.name if profile else ""
        confirmation = QMessageBox.question(
            self,
            self.translator.t("profiles_flow.delete_confirm_title"),
            self.translator.t("profiles_flow.delete_confirm_message", name=profile_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        deleted = self.profile_service.delete_profile(profile_id)
        if not deleted:
            self._set_feedback(self.translator.t("profiles_flow.error_delete_failed"), "error")
            return

        self._refresh_profiles()
        self._set_feedback(
            self.translator.t("profiles_flow.deleted_message", name=profile_name),
            "info",
        )
        self.profile_state_changed.emit()

    def _on_selection_changed(self) -> None:
        has_selection = self._selected_profile_id() is not None
        self._set_active_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)

    def _selected_profile_id(self) -> int | None:
        item = self._profiles_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        if value is None:
            return None
        return int(value)

    def _find_row_for_profile_id(self, profile_id: int | None) -> int:
        if profile_id is None:
            return -1
        for row in range(self._profiles_list.count()):
            item = self._profiles_list.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == profile_id:
                return row
        return -1

    def _set_feedback(self, message: str, state: str) -> None:
        self._feedback_label.setText(message)
        set_feedback_visual(self._feedback_label, state)

    def _unlock_profile_created_trophies(self, profile_id: int) -> list[str]:
        """Handle onboarding trophies triggered by profile creation."""
        unlocked = self.trophy_service.on_profile_created(profile_id)

        # If this new profile became active automatically (first profile case),
        # we can unlock the active-profile onboarding trophy as well.
        if self.profile_service.get_active_profile_id() == profile_id:
            unlocked.extend(self.trophy_service.on_active_profile_set(profile_id))

        return [item.display_name(self.translator.locale) for item in unlocked]

    def _with_unlock_feedback(self, base_message: str, unlocked_names: list[str]) -> str:
        if not unlocked_names:
            return base_message
        names = ", ".join(unlocked_names)
        return f"{base_message} {self.translator.t('trophies_flow.feedback_unlocked', names=names)}"

    def _notify_unlock_toast(self, unlocked_names: list[str]) -> None:
        if not unlocked_names:
            return
        self.notify_toast(
            self.translator.t("trophies_flow.feedback_unlocked", names=", ".join(unlocked_names)),
            level="success",
            duration_ms=3400,
        )
