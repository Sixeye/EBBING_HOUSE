"""Base class for pages that need translation updates."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.i18n.translator import Translator


class BasePage(QWidget):
    """Shared base class for localized pages."""

    def __init__(self, translator: Translator) -> None:
        super().__init__()
        self.translator = translator

    def update_texts(self) -> None:
        """Called by the main window when locale changes."""
        raise NotImplementedError

    def notify_toast(
        self,
        message: str,
        *,
        level: str = "info",
        duration_ms: int = 2600,
        title: str | None = None,
    ) -> None:
        """Forward a toast request to MainWindow when available.

        Pages stay decoupled from concrete toast-manager wiring. They only
        express intent ("show short non-blocking feedback"), and MainWindow
        decides how to render/queue it.
        """
        host_window = self.window()
        show_toast = getattr(host_window, "show_toast", None)
        if callable(show_toast):
            show_toast(
                message,
                level=level,
                duration_ms=duration_ms,
                title=title,
            )
