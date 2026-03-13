"""Lightweight UI motion helpers used across pages.

Design goals for this module:
- subtle effects only (no aggressive animation loops)
- centralized behavior (easy to tune globally)
- safe defaults for desktop performance
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QWidget,
)


def repolish(widget: QWidget) -> None:
    """Re-apply stylesheet after changing dynamic properties."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class _HoverLiftController(QObject):
    """Event-filter controller for tiny hover/press elevation cues.

    We animate only shadow blur + y-offset so interactions feel premium but
    remain calm and cheap to render.
    """

    def __init__(
        self,
        widget: QWidget,
        *,
        interactive: bool,
        base_blur: float,
        hover_blur: float,
        pressed_blur: float,
        base_offset: float,
        hover_offset: float,
        pressed_offset: float,
        shadow_alpha: int,
        duration_ms: int,
    ) -> None:
        super().__init__(widget)
        self._widget = widget
        self._interactive = interactive

        effect = QGraphicsDropShadowEffect(widget)
        effect.setColor(QColor(0, 0, 0, max(0, min(255, shadow_alpha))))
        effect.setBlurRadius(base_blur)
        effect.setOffset(0.0, base_offset)
        widget.setGraphicsEffect(effect)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._effect = effect

        self._base_blur = base_blur
        self._hover_blur = hover_blur
        self._pressed_blur = pressed_blur
        self._base_offset = base_offset
        self._hover_offset = hover_offset
        self._pressed_offset = pressed_offset
        self._duration_ms = max(90, duration_ms)

        self._blur_anim = QPropertyAnimation(self._effect, b"blurRadius", self)
        self._offset_anim = QPropertyAnimation(self._effect, b"yOffset", self)
        for anim in (self._blur_anim, self._offset_anim):
            anim.setDuration(self._duration_ms)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is not self._widget:
            return False

        if event.type() == QEvent.Type.Enter and self._widget.isEnabled():
            self._animate_to(self._hover_blur, self._hover_offset)
        elif event.type() == QEvent.Type.Leave:
            self._animate_to(self._base_blur, self._base_offset)
        elif (
            self._interactive
            and event.type() == QEvent.Type.MouseButtonPress
            and self._widget.isEnabled()
        ):
            self._animate_to(self._pressed_blur, self._pressed_offset)
        elif (
            self._interactive
            and event.type() == QEvent.Type.MouseButtonRelease
            and self._widget.isEnabled()
        ):
            if self._widget.underMouse():
                self._animate_to(self._hover_blur, self._hover_offset)
            else:
                self._animate_to(self._base_blur, self._base_offset)
        elif event.type() == QEvent.Type.EnabledChange and not self._widget.isEnabled():
            self._animate_to(self._base_blur, self._base_offset)

        return False

    def _animate_to(self, blur: float, y_offset: float) -> None:
        self._blur_anim.stop()
        self._blur_anim.setStartValue(self._effect.blurRadius())
        self._blur_anim.setEndValue(blur)
        self._blur_anim.start()

        self._offset_anim.stop()
        self._offset_anim.setStartValue(self._effect.yOffset())
        self._offset_anim.setEndValue(y_offset)
        self._offset_anim.start()


def install_hover_lift(
    widget: QWidget,
    *,
    interactive: bool = True,
    base_blur: float = 10.0,
    hover_blur: float = 18.0,
    pressed_blur: float = 9.0,
    base_offset: float = 1.0,
    hover_offset: float = 2.5,
    pressed_offset: float = 0.5,
    shadow_alpha: int = 70,
    duration_ms: int = 140,
) -> None:
    """Attach subtle hover/press lift to one widget.

    The controller is stored on the widget to avoid garbage collection while
    the event filter is active.
    """
    if bool(widget.property("_lift_installed")):
        return

    controller = _HoverLiftController(
        widget,
        interactive=interactive,
        base_blur=base_blur,
        hover_blur=hover_blur,
        pressed_blur=pressed_blur,
        base_offset=base_offset,
        hover_offset=hover_offset,
        pressed_offset=pressed_offset,
        shadow_alpha=shadow_alpha,
        duration_ms=duration_ms,
    )
    widget.installEventFilter(controller)
    widget.setProperty("_lift_installed", True)
    # Keep a Python reference so the controller is not garbage-collected.
    widget._lift_controller = controller  # type: ignore[attr-defined]


def apply_standard_micro_interactions(root: QWidget) -> None:
    """Apply consistent micro-interactions to common controls.

    We intentionally scope this to high-impact widgets:
    - navigation and action buttons
    - dashboard metric cards
    """
    for button in root.findChildren(QPushButton):
        name = button.objectName()
        if name == "PrimaryButton":
            install_hover_lift(
                button,
                interactive=True,
                base_blur=10.0,
                hover_blur=19.0,
                pressed_blur=9.0,
                base_offset=1.0,
                hover_offset=2.7,
                pressed_offset=0.6,
                shadow_alpha=90,
                duration_ms=130,
            )
        elif name == "SecondaryButton":
            install_hover_lift(
                button,
                interactive=True,
                base_blur=8.0,
                hover_blur=14.0,
                pressed_blur=7.0,
                base_offset=0.8,
                hover_offset=2.0,
                pressed_offset=0.4,
                shadow_alpha=66,
                duration_ms=130,
            )

    # We intentionally keep sidebar nav buttons static (CSS hover only) so
    # navigation feels calm and avoids unnecessary motion noise.
    # Metric cards already use an opacity effect for staggered reveal; we keep
    # that pipeline untouched to avoid conflicting graphics effects.


def flash_widget(
    widget: QWidget,
    *,
    start_opacity: float = 0.55,
    end_opacity: float = 1.0,
    duration_ms: int = 180,
) -> None:
    """Quick opacity pulse used for non-intrusive feedback emphasis."""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

    previous = getattr(widget, "_flash_animation", None)
    if isinstance(previous, QPropertyAnimation):
        previous.stop()

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(max(100, duration_ms))
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.setStartValue(start_opacity)
    anim.setEndValue(end_opacity)
    anim.start()
    widget._flash_animation = anim  # type: ignore[attr-defined]


def set_feedback_visual(label: QLabel, state: str) -> None:
    """Set feedback semantic state + subtle text pulse.

    Styling is handled in the global stylesheet using `feedbackState`.
    """
    normalized = state if state in {"info", "success", "error"} else "info"
    if label.property("feedbackState") != normalized:
        label.setProperty("feedbackState", normalized)
        repolish(label)
    flash_widget(label, start_opacity=0.6, end_opacity=1.0, duration_ms=190)
