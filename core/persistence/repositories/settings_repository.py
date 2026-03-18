"""Repository for global app settings."""

from __future__ import annotations

from app.db.database import DatabaseManager
from app.models.settings import GlobalSettings


class SettingsRepository:
    """Persist and retrieve singleton global settings.

    This repository intentionally keeps one row in `settings_global` (id=1).
    """

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def ensure_defaults(self) -> None:
        """Guarantee that the singleton settings row exists."""
        self.get_settings()

    def get_settings(self) -> GlobalSettings:
        """Load global settings from SQLite, creating defaults if missing."""
        with self.database.connection() as conn:
            row = conn.execute("SELECT * FROM settings_global WHERE id = 1").fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO settings_global (
                        id,
                        app_language,
                        default_theme,
                        animations_enabled,
                        sounds_enabled,
                        active_profile_id
                    )
                    VALUES (1, 'en', 'dark', 1, 1, NULL)
                    """
                )
                row = conn.execute("SELECT * FROM settings_global WHERE id = 1").fetchone()

        return GlobalSettings.from_row(row)

    def save_or_update(self, settings: GlobalSettings) -> GlobalSettings:
        """Insert/update global settings using an upsert statement."""
        with self.database.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings_global (
                    id,
                    app_language,
                    default_theme,
                    animations_enabled,
                    sounds_enabled,
                    active_profile_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    app_language = excluded.app_language,
                    default_theme = excluded.default_theme,
                    animations_enabled = excluded.animations_enabled,
                    sounds_enabled = excluded.sounds_enabled,
                    active_profile_id = excluded.active_profile_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    1,
                    settings.app_language,
                    settings.default_theme,
                    int(settings.animations_enabled),
                    int(settings.sounds_enabled),
                    settings.active_profile_id,
                ),
            )

            row = conn.execute("SELECT * FROM settings_global WHERE id = 1").fetchone()

        return GlobalSettings.from_row(row)

    # ---------------------------------------------------------------------
    # Compatibility helpers:
    # These methods keep existing UI/bootstrap code working while we migrate
    # toward explicit `get_settings()` + `save_or_update()` usage.
    # ---------------------------------------------------------------------
    def set_value(self, key: str, value: str) -> None:
        settings = self.get_settings()

        if key == "language":
            settings.app_language = value
        elif key == "theme":
            settings.default_theme = value
        elif key == "animations_enabled":
            settings.animations_enabled = self._as_bool(value)
        elif key == "sounds_enabled":
            settings.sounds_enabled = self._as_bool(value)
        elif key == "active_profile_id":
            settings.active_profile_id = self._as_optional_int(value)
        else:
            # Unknown keys are intentionally ignored to keep this layer strict.
            return

        self.save_or_update(settings)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        settings = self.get_settings()
        mapping = {
            "language": settings.app_language,
            "theme": settings.default_theme,
            "animations_enabled": "1" if settings.animations_enabled else "0",
            "sounds_enabled": "1" if settings.sounds_enabled else "0",
            "active_profile_id": (
                str(settings.active_profile_id) if settings.active_profile_id is not None else None
            ),
        }
        return mapping.get(key, default)

    @staticmethod
    def _as_bool(value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "on"}

    @staticmethod
    def _as_optional_int(value: str) -> int | None:
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return int(normalized)
        except ValueError:
            return None
