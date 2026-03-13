"""Reusable metric card used on the dashboard."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QLabel, QSizePolicy, QVBoxLayout


class MetricCard(QFrame):
    """Compact card to display one important progress metric."""

    def __init__(
        self,
        title: str = "",
        value: str = "",
        hint: str = "",
        animation_delay_ms: int = 0,
    ) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("MetricTitle")

        self._value_label = QLabel(value)
        self._value_label.setObjectName("MetricValue")

        self._hint_label = QLabel(hint)
        self._hint_label.setObjectName("MetricHint")
        self._hint_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        layout.addWidget(self._hint_label)

        self._animation_delay_ms = max(0, animation_delay_ms)

        # Simple fade-in animation gives a polished first-load impression.
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_animation.setDuration(360)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._played_once = False

    def update_content(self, title: str, value: str, hint: str) -> None:
        self._title_label.setText(title)
        self._value_label.setText(value)
        self._hint_label.setText(hint)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if not self._played_once:
            self._played_once = True

            # Delay is optional and lets the dashboard create a subtle stagger effect.
            QTimer.singleShot(self._animation_delay_ms, self._fade_animation.start)
