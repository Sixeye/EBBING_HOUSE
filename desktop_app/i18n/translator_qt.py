"""Qt-based translation service for desktop runtime.

Phase 2B isolates QObject/Signal behavior under `desktop_app` while keeping
locale JSON data shared in `app/i18n/locales`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from app.config.settings import SUPPORTED_LOCALES


class Translator(QObject):
    """Resolve translation keys and notify UI when language changes."""

    language_changed = Signal(str)

    def __init__(self, locales_dir: Path, default_locale: str) -> None:
        super().__init__()
        self._locales_dir = locales_dir
        self._translations: dict[str, dict[str, Any]] = {}
        self._locale = default_locale
        self._load_locales()

    @property
    def locale(self) -> str:
        return self._locale

    @property
    def supported_locales(self) -> tuple[str, ...]:
        return SUPPORTED_LOCALES

    def set_locale(self, locale: str) -> None:
        if locale not in self._translations:
            return
        if locale == self._locale:
            return

        self._locale = locale
        self.language_changed.emit(locale)

    def t(self, key: str, default: str = "", **kwargs: Any) -> str:
        """Translate `dot.separated.keys` with optional string formatting."""
        text = self._resolve(self._translations.get(self._locale, {}), key)
        if text is None:
            text = self._resolve(self._translations.get("en", {}), key)
        if text is None:
            text = default or key

        if kwargs:
            try:
                return str(text).format(**kwargs)
            except (KeyError, ValueError):
                return str(text)

        return str(text)

    def _load_locales(self) -> None:
        for locale in SUPPORTED_LOCALES:
            locale_file = self._locales_dir / f"{locale}.json"
            if not locale_file.exists():
                self._translations[locale] = {}
                continue

            self._translations[locale] = json.loads(locale_file.read_text(encoding="utf-8"))

    @staticmethod
    def _resolve(data: dict[str, Any], key: str) -> Any | None:
        current: Any = data
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current


__all__ = ["Translator"]

