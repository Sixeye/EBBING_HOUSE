"""Thin service layer for profile-oriented use cases."""

from __future__ import annotations

from app.models.profile import Profile
from app.repositories.profile_repository import ProfileRepository
from app.repositories.settings_repository import SettingsRepository


class ProfileService:
    """Orchestrates profile operations.

    Keeping this class lightweight helps beginners see where business rules
    would be added later without duplicating SQL in UI code.
    """

    def __init__(
        self,
        repository: ProfileRepository,
        settings_repository: SettingsRepository | None = None,
    ) -> None:
        self.repository = repository
        self.settings_repository = settings_repository

    def create_profile(
        self,
        name: str,
        language: str = "en",
        theme: str = "dark",
        grading_mode: str = "score_20",
    ) -> Profile:
        profile = self.repository.create(
            name=name,
            language=language,
            theme=theme,
            grading_mode=grading_mode,
        )
        # First-created profile becomes active automatically, which reduces
        # onboarding friction before the user visits the Profiles page.
        if self.get_active_profile_id() is None:
            self._persist_active_profile_id(profile.id)
        return profile

    def list_profiles(self) -> list[Profile]:
        return self.repository.list_all()

    def get_profile_by_id(self, profile_id: int) -> Profile | None:
        return self.repository.get_by_id(profile_id)

    def update_profile(self, profile: Profile) -> bool:
        return self.repository.update(profile)

    def delete_profile(self, profile_id: int) -> bool:
        active_profile_id = self.get_active_profile_id()
        deleted = self.repository.delete(profile_id)
        if not deleted:
            return False

        if active_profile_id == profile_id:
            # If the active learner is removed, we switch to another available
            # profile to keep dashboard/review flows usable.
            remaining_profiles = self.repository.list_all()
            fallback_profile_id = remaining_profiles[0].id if remaining_profiles else None
            self._persist_active_profile_id(fallback_profile_id)
        return True

    def get_active_profile_id(self) -> int | None:
        """Return active profile id and self-heal stale values if needed."""
        if self.settings_repository is None:
            return None

        settings = self.settings_repository.get_settings()
        active_profile_id = settings.active_profile_id
        if active_profile_id is None:
            return None

        # Defensive consistency check for legacy/manual DB edits.
        if self.repository.get_by_id(active_profile_id) is None:
            settings.active_profile_id = None
            self.settings_repository.save_or_update(settings)
            return None

        return active_profile_id

    def get_active_profile(self) -> Profile | None:
        active_profile_id = self.get_active_profile_id()
        if active_profile_id is None:
            return None
        return self.repository.get_by_id(active_profile_id)

    def set_active_profile(self, profile_id: int | None) -> Profile | None:
        """Persist the selected active learner.

        Passing None clears active profile selection.
        """
        if profile_id is None:
            self._persist_active_profile_id(None)
            return None

        profile = self.repository.get_by_id(profile_id)
        if profile is None:
            raise ValueError("Selected profile does not exist.")

        self._persist_active_profile_id(profile_id)
        return profile

    def _persist_active_profile_id(self, profile_id: int | None) -> None:
        if self.settings_repository is None:
            return
        settings = self.settings_repository.get_settings()
        settings.active_profile_id = profile_id
        self.settings_repository.save_or_update(settings)
