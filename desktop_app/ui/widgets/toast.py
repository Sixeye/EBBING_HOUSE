"""Reusable non-blocking toast notifications.

Design intent:
- short, unobtrusive feedback for high-signal events
- queueing to avoid visual chaos during event bursts
- no modal dialogs, so learning flow remains uninterrupted
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ToastPayload:
    message: str
    level: str
    duration_ms: int
    title: str | None
    animations_enabled: bool


class ToastWidget(QFrame):
    """Single toast item with optional fade in/out."""

    closed = Signal(object)

    LEVEL_ICON = {
        "info": "i",
        "success": "✓",
        "warning": "!",
    }

    def __init__(
        self,
        message: str,
        *,
        level: str = "info",
        duration_ms: int = 2600,
        title: str | None = None,
        animations_enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ToastFrame")

        # Compatibility mapping: existing UI often uses "error" semantics.
        if level == "error":
            normalized_level = "warning"
        else:
            normalized_level = level if level in {"info", "success", "warning"} else "info"
        self.setProperty("toastLevel", normalized_level)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)

        self._animations_enabled = animations_enabled
        self._dismissed = False

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(9)

        self._icon_label = QLabel(self.LEVEL_ICON.get(normalized_level, "i"))
        self._icon_label.setObjectName("ToastIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(18, 18)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        self._title_label = QLabel(title or "")
        self._title_label.setObjectName("ToastTitle")
        self._title_label.setWordWrap(True)
        self._title_label.setVisible(bool(title))

        self._message_label = QLabel(message)
        self._message_label.setObjectName("ToastMessage")
        self._message_label.setWordWrap(True)

        text_col.addWidget(self._title_label)
        text_col.addWidget(self._message_label)

        root.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(text_col, 1)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.setInterval(max(1200, int(duration_ms)))
        self._dismiss_timer.timeout.connect(self.dismiss)

        self._opacity_effect: QGraphicsOpacityEffect | None = None
        self._fade_in: QPropertyAnimation | None = None
        self._fade_out: QPropertyAnimation | None = None

        if self._animations_enabled:
            self._opacity_effect = QGraphicsOpacityEffect(self)
            self._opacity_effect.setOpacity(0.0)
            self.setGraphicsEffect(self._opacity_effect)

            self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity", self)
            self._fade_in.setDuration(160)
            self._fade_in.setStartValue(0.0)
            self._fade_in.setEndValue(1.0)
            self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

            self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity", self)
            self._fade_out.setDuration(170)
            self._fade_out.setStartValue(1.0)
            self._fade_out.setEndValue(0.0)
            self._fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_out.finished.connect(lambda: self.closed.emit(self))

        self._dismiss_timer.start()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._animations_enabled and self._fade_in is not None:
            self._fade_in.start()

    def dismiss(self) -> None:
        """Request toast close (timer or manager)."""
        if self._dismissed:
            return
        self._dismissed = True
        self._dismiss_timer.stop()

        if self._animations_enabled and self._fade_out is not None:
            self._fade_out.start()
            return

        self.closed.emit(self)


class ToastManager(QWidget):
    """Overlay manager that queues and stacks toast notifications."""

    MAX_VISIBLE = 3
    STACK_SPACING = 8
    VIEW_MARGIN = 12

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ToastManager")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # The container should never block the learning UI.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

        self._queue: deque[ToastPayload] = deque()
        self._active: list[ToastWidget] = []

        parent.installEventFilter(self)
        self.setGeometry(parent.rect())

    def show_toast(
        self,
        message: str,
        *,
        level: str = "info",
        duration_ms: int = 2600,
        title: str | None = None,
        animations_enabled: bool = True,
    ) -> None:
        text = message.strip()
        if not text:
            return

        self._queue.append(
            ToastPayload(
                message=text,
                level=level,
                duration_ms=duration_ms,
                title=title,
                animations_enabled=animations_enabled,
            )
        )
        self._drain_queue()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if watched is self.parentWidget() and event.type() in {QEvent.Type.Resize, QEvent.Type.Show}:
            self.setGeometry(self.parentWidget().rect())
            self._relayout()
        return super().eventFilter(watched, event)

    def _drain_queue(self) -> None:
        while self._queue and len(self._active) < self.MAX_VISIBLE:
            payload = self._queue.popleft()
            toast = ToastWidget(
                payload.message,
                level=payload.level,
                duration_ms=payload.duration_ms,
                title=payload.title,
                animations_enabled=payload.animations_enabled,
                parent=self,
            )
            toast.closed.connect(self._on_toast_closed)
            toast.show()
            self._active.append(toast)

        if self._active:
            self.show()
            self.raise_()
            self._relayout()

    def _on_toast_closed(self, toast: object) -> None:
        if isinstance(toast, ToastWidget) and toast in self._active:
            self._active.remove(toast)
            toast.deleteLater()
        self._relayout()
        self._drain_queue()
        if not self._active and not self._queue:
            self.hide()

    def _relayout(self) -> None:
        if not self._active:
            return

        y = self.VIEW_MARGIN
        max_width = max(220, self.width() - (self.VIEW_MARGIN * 2))

        for toast in list(self._active):
            hint = toast.sizeHint()
            width = min(toast.maximumWidth(), max_width, max(220, hint.width()))
            if width >= self.width():
                width = max(160, self.width() - (self.VIEW_MARGIN * 2))
            height = max(hint.height(), 44)
            x = self.width() - width - self.VIEW_MARGIN
            toast.setGeometry(int(x), int(y), int(width), int(height))
            toast.raise_()
            y += height + self.STACK_SPACING


__all__ = ["ToastManager", "ToastWidget"]
