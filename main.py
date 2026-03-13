"""Application entry point for EBBING_HOUSE."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config.settings import APP_NAME, APP_ORGANIZATION, APP_VERSION
from app.core.bootstrap import AppBootstrap
from app.themes.branding import build_window_icon
from app.themes.stylesheet import build_stylesheet
from app.ui.widgets.startup_splash import StartupSplashWidget


def create_application() -> QApplication:
    """Create and configure the Qt application object."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)
    # App-level icon keeps branding visible in dock/taskbar and window switchers.
    app.setWindowIcon(build_window_icon())
    app.setStyleSheet(build_stylesheet())
    return app


def main() -> int:
    """Boot the dependency container and run the main window."""
    app = create_application()

    bootstrap = AppBootstrap()
    bootstrap.initialize()

    window = bootstrap.create_main_window()
    settings = bootstrap.settings_service.get_settings()

    if settings.animations_enabled:
        # Startup splash remains short so app launch stays fast and non-intrusive.
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


if __name__ == "__main__":
    raise SystemExit(main())
