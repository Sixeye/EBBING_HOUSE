"""Stacked widget with lightweight fade transition between pages."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize
from PySide6.QtWidgets import QGraphicsOpacityEffect, QSizePolicy, QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """A tiny UX polish layer: fade in page whenever selection changes."""

    def __init__(self) -> None:
        super().__init__()
        self._animation: QPropertyAnimation | None = None
        # Important for QScrollArea-based shell layout:
        # horizontal `Ignored` lets pages shrink to viewport width instead of
        # enforcing the widest page sizeHint (which can cause clipped content).
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setCurrentWidget(self, widget: QWidget) -> None:  # type: ignore[override]
        super().setCurrentWidget(widget)
        # Critical for QScrollArea shells:
        # force geometry recalculation when active page changes so the stack no
        # longer keeps the tallest hidden page height (which caused vertically
        # stretched game pages).
        self.updateGeometry()
        self._animate(widget)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        current = self.currentWidget()
        if current is not None:
            hint = current.sizeHint()
            if hint.isValid():
                return hint
        return super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        current = self.currentWidget()
        if current is not None:
            hint = current.minimumSizeHint()
            if hint.isValid():
                return hint
        return super().minimumSizeHint()

    def _animate(self, widget: QWidget) -> None:
        # Rapid page changes can overlap animations; stop previous transition so
        # we avoid dangling targets and keep transitions deterministic.
        if self._animation is not None:
            self._animation.stop()

        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(220)
        animation.setStartValue(0.35)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: widget.setGraphicsEffect(None))
        animation.start()

        # Keep a reference to avoid premature GC while animation is running.
        self._animation = animation
