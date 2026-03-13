"""Lightweight intro animation + optional 8-bit sound for mini-games."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, QUrl
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from app.core.paths import get_app_asset_dir
from app.services.settings_service import SettingsService

try:
    # QtMultimedia can be unavailable in some minimal environments. We keep
    # this optional so UI remains functional even without audio backend.
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # pragma: no cover - safety fallback for constrained runtimes
    QSoundEffect = None  # type: ignore[assignment]


def _default_sound_path() -> Path:
    # This intro cue ships with the app, so it has to come from bundled
    # resources instead of relying on source-tree-relative paths.
    return get_app_asset_dir("sounds", "game_start_8bit.wav")


class GameStartFxController:
    """Play subtle intro feedback governed by global settings flags."""

    def __init__(self, host: QWidget, settings_service: SettingsService) -> None:
        self._host = host
        self._settings_service = settings_service
        self._sound_effect = None
        if QSoundEffect is not None:
            self._sound_effect = QSoundEffect(host)
            self._sound_effect.setSource(QUrl.fromLocalFile(str(_default_sound_path())))
            self._sound_effect.setVolume(0.32)

    def play(self, message: str) -> None:
        settings = self._settings_service.get_settings()
        if settings.animations_enabled:
            self._play_banner(message)
        if settings.sounds_enabled:
            self._play_sound()

    def _play_banner(self, message: str) -> None:
        # The intro banner is intentionally short (under 1s) to create a
        # playful start cue without delaying the learning interaction.
        label = QLabel(message, self._host)
        label.setObjectName("FeedbackLabel")
        label.setProperty("feedbackState", "success")
        label.setStyleSheet(
            "font-weight: 700; padding: 8px 14px; "
            "background-color: rgba(57, 178, 106, 0.16);"
        )
        label.adjustSize()

        x = max(12, int((self._host.width() - label.width()) / 2))
        y = max(12, int(self._host.height() * 0.12))
        label.move(x, y + 8)
        label.show()
        label.raise_()

        opacity = QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(opacity)
        opacity.setOpacity(0.0)

        fade = QPropertyAnimation(opacity, b"opacity", label)
        fade.setDuration(780)
        fade.setStartValue(0.0)
        fade.setKeyValueAt(0.2, 1.0)
        fade.setKeyValueAt(0.72, 1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InOutCubic)

        slide = QPropertyAnimation(label, b"pos", label)
        slide.setDuration(780)
        slide.setStartValue(QPoint(x, y + 8))
        slide.setEndValue(QPoint(x, y))
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade.start()
        slide.start()

        # Keep Python references alive until animations complete.
        label._fx_fade = fade  # type: ignore[attr-defined]
        label._fx_slide = slide  # type: ignore[attr-defined]
        QTimer.singleShot(900, label.deleteLater)

    def _play_sound(self) -> None:
        if self._sound_effect is None:
            return
        if self._sound_effect.isPlaying():
            self._sound_effect.stop()
        self._sound_effect.play()


__all__ = ["GameStartFxController"]
