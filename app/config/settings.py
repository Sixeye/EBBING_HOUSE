"""Static application settings and runtime constants."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "EBBING_HOUSE"
APP_VERSION = "0.1.0"
APP_ORGANIZATION = "Ebbing House"

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "fr", "es", "pt", "de")

# Centralized local data folder used for SQLite and future exports/backups.
APP_DATA_DIRNAME = "EBBING_HOUSE"
DATABASE_FILENAME = "ebbing_house.db"

# Locale files are bundled with the app package.
LOCALES_DIR = Path(__file__).resolve().parent.parent / "i18n" / "locales"
