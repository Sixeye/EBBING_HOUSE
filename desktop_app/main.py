"""Desktop application entry point.

This module is the new desktop-specific startup location introduced in
phase 1. Keeping it isolated makes later extraction of portable `core/`
logic safer, while preserving the old root `main.py` as a compatibility
wrapper for existing launch scripts.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config.settings import APP_NAME, APP_ORGANIZATION, APP_VERSION
from desktop_app.themes.branding import build_window_icon
from desktop_app.themes.stylesheet import build_stylesheet
from desktop_app.bootstrap_desktop import DesktopAppBootstrap
from desktop_app.ui.widgets.startup_splash import StartupSplashWidget


def create_application() -> QApplication:
    """Create and configure the Qt application object."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)
    # App-level icon keeps branding visible in dock/taskbar and switchers.
    app.setWindowIcon(build_window_icon())
    app.setStyleSheet(build_stylesheet())
    return app


def main() -> int:
    """Boot the desktop dependency container and run the main window."""
    app = create_application()

    bootstrap = DesktopAppBootstrap()
    bootstrap.initialize()

    window = bootstrap.create_main_window()
    settings = bootstrap.settings_service.get_settings()

    if settings.animations_enabled:
        # Startup splash remains short so launch stays fast and non-intrusive.
        splash = StartupSplashWidget(duration_ms=1900)

        def _show_main_window() -> None:
            window.show()
            window.raise_()
            window.activateWindow()

        splash.finished.connect(_show_main_window)
        splash.show()
    else:
        # Respect accessibility/performance preference when animations are off.
        window.show()
        window.raise_()
        window.activateWindow()

    return app.exec()


__all__ = ["create_application", "main"]
