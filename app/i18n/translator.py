"""Transitional compatibility shim for the desktop Qt translator.

Phase 2B moves the Qt-specific implementation to `desktop_app.i18n` while
preserving historical imports from `app.i18n.translator`.
"""

from desktop_app.i18n.translator_qt import Translator as _DesktopQtTranslator


class Translator(_DesktopQtTranslator):
    """Compatibility wrapper preserving the historical import path."""


__all__ = ["Translator"]

