"""Minimal custom-painted hangman visualization widget."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.themes.palette import ACCENT_ORANGE, BORDER_SUBTLE, ERROR_RED, SUCCESS_GREEN


class HangmanWidget(QWidget):
    """Render gallows + body-part progression for wrong answers.

    Stages (max 6):
    1 head
    2 body
    3 left arm
    4 right arm
    5 left leg
    6 right leg
    """

    def __init__(self) -> None:
        super().__init__()
        self._wrong_answers = 0
        self._max_wrong_answers = 6
        self._pulse_strength = 0.0
        self._pulse_color = QColor(ACCENT_ORANGE)

        self._pulse_animation = QPropertyAnimation(self, b"pulseStrength", self)
        self._pulse_animation.setDuration(260)
        self._pulse_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        # Keep drawing space sufficient for clean silhouette readability.
        self.setMinimumWidth(300)
        self.setMinimumHeight(260)
        # Preferred vertical policy avoids overly tall stretch while preserving
        # full scene readability in compact windows.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        # Protect the scene from becoming a very tall column in resized layouts.
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        # Useful visual proportion for the gallows composition.
        target = int(width * 0.72)
        return max(self.minimumHeight(), min(target, 620))

    def sizeHint(self) -> QSize:  # type: ignore[override]
        base_width = 520
        return QSize(base_width, self.heightForWidth(base_width))

    def set_progress(self, wrong_answers: int, max_wrong_answers: int) -> None:
        self._wrong_answers = max(0, int(wrong_answers))
        self._max_wrong_answers = max(1, int(max_wrong_answers))
        self.update()

    def reset(self, max_wrong_answers: int = 6) -> None:
        self.set_progress(wrong_answers=0, max_wrong_answers=max_wrong_answers)

    def pulse_feedback(self, was_correct: bool) -> None:
        """Briefly pulse the scene after validation.

        We keep this effect short and transparent so it supports clarity
        (correct/wrong reinforcement) without turning into visual noise.
        """
        self._pulse_color = QColor(SUCCESS_GREEN if was_correct else ERROR_RED)
        self._pulse_animation.stop()
        self._pulse_animation.setStartValue(0.38)
        self._pulse_animation.setEndValue(0.0)
        self._pulse_animation.start()

    def _get_pulse_strength(self) -> float:
        return self._pulse_strength

    def _set_pulse_strength(self, value: float) -> None:
        self._pulse_strength = max(0.0, min(1.0, float(value)))
        self.update()

    pulseStrength = Property(float, _get_pulse_strength, _set_pulse_strength)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        # Calm backdrop keeps the visual readable and gives subtle depth.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 8))
        painter.drawRoundedRect(4, 4, max(0, w - 8), max(0, h - 8), 12, 12)

        # Keep drawing coordinates proportional to widget size so the component
        # scales cleanly on different desktop resolutions.
        base_y = int(h * 0.88)
        pole_x = int(w * 0.28)
        top_y = int(h * 0.12)
        beam_x = int(w * 0.62)
        rope_y = int(h * 0.22)

        structure_pen = QPen(
            QColor(BORDER_SUBTLE),
            6,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        painter.setPen(structure_pen)

        # Gallows structure stays static to frame danger progression.
        painter.drawLine(int(w * 0.12), base_y, int(w * 0.82), base_y)
        painter.drawLine(pole_x, base_y, pole_x, top_y)
        painter.drawLine(pole_x, top_y, beam_x, top_y)
        painter.drawLine(beam_x, top_y, beam_x, rope_y)

        ratio = min(1.0, self._wrong_answers / self._max_wrong_answers)
        if ratio >= 1.0:
            body_color = ERROR_RED
        elif ratio == 0.0:
            body_color = SUCCESS_GREEN
        else:
            body_color = ACCENT_ORANGE

        body_pen = QPen(
            QColor(body_color),
            5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        painter.setPen(body_pen)

        head_center_x = beam_x
        head_center_y = int(h * 0.31)
        head_radius = int(min(w, h) * 0.06)
        torso_top_y = head_center_y + head_radius
        torso_bottom_y = int(h * 0.58)

        stage = self._wrong_answers

        if stage >= 1:
            painter.drawEllipse(
                head_center_x - head_radius,
                head_center_y - head_radius,
                head_radius * 2,
                head_radius * 2,
            )
        if stage >= 2:
            painter.drawLine(head_center_x, torso_top_y, head_center_x, torso_bottom_y)
        if stage >= 3:
            painter.drawLine(head_center_x, int(h * 0.44), int(w * 0.50), int(h * 0.49))
        if stage >= 4:
            painter.drawLine(head_center_x, int(h * 0.44), int(w * 0.74), int(h * 0.49))
        if stage >= 5:
            painter.drawLine(head_center_x, torso_bottom_y, int(w * 0.52), int(h * 0.73))
        if stage >= 6:
            painter.drawLine(head_center_x, torso_bottom_y, int(w * 0.72), int(h * 0.73))

        if self._pulse_strength > 0.01:
            pulse_fill = QColor(self._pulse_color)
            pulse_fill.setAlpha(int(72 * self._pulse_strength))
            pulse_outline = QColor(self._pulse_color)
            pulse_outline.setAlpha(int(110 * self._pulse_strength))

            painter.setBrush(pulse_fill)
            painter.setPen(QPen(pulse_outline, 2))
            painter.drawRoundedRect(6, 6, max(0, w - 12), max(0, h - 12), 12, 12)


__all__ = ["HangmanWidget"]
