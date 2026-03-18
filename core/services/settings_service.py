"""Thin service layer for global settings use cases."""

from __future__ import annotations

from core.models.settings import GlobalSettings
from core.persistence.repositories.settings_repository import SettingsRepository


class SettingsService:
    """Coordinates global settings updates."""

    def __init__(self, repository: SettingsRepository) -> None:
        self.repository = repository

    def get_settings(self) -> GlobalSettings:
        return self.repository.get_settings()

    def set_app_language(self, locale: str) -> GlobalSettings:
        settings = self.repository.get_settings()
        settings.app_language = locale
        return self.repository.save_or_update(settings)

    def set_default_theme(self, theme: str) -> GlobalSettings:
        settings = self.repository.get_settings()
        settings.default_theme = theme
        return self.repository.save_or_update(settings)

    def set_animations_enabled(self, enabled: bool) -> GlobalSettings:
        settings = self.repository.get_settings()
        settings.animations_enabled = enabled
        return self.repository.save_or_update(settings)

    def set_sounds_enabled(self, enabled: bool) -> GlobalSettings:
        settings = self.repository.get_settings()
        settings.sounds_enabled = enabled
        return self.repository.save_or_update(settings)

    def get_active_profile_id(self) -> int | None:
        """Return globally selected learner profile id, if any."""
        return self.repository.get_settings().active_profile_id

    def set_active_profile_id(self, profile_id: int | None) -> GlobalSettings:
        """Persist active learner selection used by dashboard/review defaults."""
        settings = self.repository.get_settings()
        settings.active_profile_id = profile_id
        return self.repository.save_or_update(settings)
