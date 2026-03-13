"""Calm background music controller with persistent mute state.

This controller is intentionally lightweight:
- one looped track selected from a small bundled catalog
- one persisted on/off preference (reusing global sounds setting)
- graceful fallback when multimedia backend or track is unavailable
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl

from app.services.settings_service import SettingsService

try:
    # Keep optional import so the app still runs in constrained environments.
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # pragma: no cover - safety fallback
    QSoundEffect = None  # type: ignore[assignment]


def _preferred_music_paths() -> list[Path]:
    """Return candidate calm loop tracks ordered by preference.

    Strategy:
    - first choice: longer calmer study loop for extended sessions
    - second choice: legacy calm loop kept for compatibility
    """
    sounds_dir = Path(__file__).resolve().parents[2] / "assets" / "sounds"
    return [
        sounds_dir / "background_8bit_serene_long.wav",
        sounds_dir / "background_8bit_calm.wav",
    ]


def _fallback_music_path() -> Path:
    """Return fallback track for environments where calm loop is not bundled yet."""
    return Path(__file__).resolve().parents[2] / "assets" / "sounds" / "game_start_8bit.wav"


class BackgroundMusicController(QObject):
    """Manage ambient 8-bit music playback and mute persistence.

    We reuse `settings_global.sounds_enabled` as the master audio toggle so:
    - the small speaker button has immediate persistent effect
    - Settings page and runtime controls stay in sync
    """

    def __init__(self, parent: QObject, settings_service: SettingsService) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._sound_effect = None
        self._track_path: Path | None = None
        self._using_fallback_track = False
        self._available = False
        # If start() is requested while asset is still loading, we defer play.
        self._pending_start = False

        self._track_path, self._using_fallback_track = self._resolve_track_path()

        if QSoundEffect is not None and self._track_path is not None:
            effect = QSoundEffect(parent)
            effect.setSource(QUrl.fromLocalFile(str(self._track_path)))
            # Some PySide builds expose `Infinite` as an enum, others as an int.
            # We normalize to int so loop playback stays portable.
            infinite_loop = QSoundEffect.Infinite
            if hasattr(infinite_loop, "value"):
                infinite_loop = infinite_loop.value
            effect.setLoopCount(int(infinite_loop))
            # Keep ambient level discreet for long study sessions.
            # The new long track is intentionally calmer, so we keep volume
            # low and stable to avoid listener fatigue over long sessions.
            effect.setVolume(0.07)
            effect.statusChanged.connect(self._on_status_changed)
            self._sound_effect = effect
            self._available = True

    def _resolve_track_path(self) -> tuple[Path | None, bool]:
        for preferred in _preferred_music_paths():
            if preferred.exists() and preferred.is_file():
                return preferred, False

        fallback = _fallback_music_path()
        if fallback.exists() and fallback.is_file():
            return fallback, True

        return None, False

    def is_available(self) -> bool:
        return self._available

    def using_fallback_track(self) -> bool:
        return self._using_fallback_track

    def track_path(self) -> Path | None:
        return self._track_path

    def is_enabled_preference(self) -> bool:
        return self._settings_service.get_settings().sounds_enabled

    def apply_settings(self) -> bool:
        """Apply persisted sound preference to current playback state."""
        enabled = self.is_enabled_preference()
        if enabled:
            self.start()
        else:
            self.stop()
        return enabled

    def set_enabled(self, enabled: bool) -> bool:
        """Persist mute/unmute and immediately apply playback state."""
        self._settings_service.set_sounds_enabled(enabled)
        if enabled:
            self.start()
        else:
            self.stop()
        return enabled

    def toggle_enabled(self) -> bool:
        return self.set_enabled(not self.is_enabled_preference())

    def start(self) -> None:
        if not self._available or self._sound_effect is None:
            return
        if self._sound_effect.isPlaying():
            return
        status = self._sound_effect.status()
        if self._is_status_ready(status):
            self._pending_start = False
            self._sound_effect.play()
            return

        # In some environments the sound is still loading when startup applies
        # settings. We mark intent and let status callback start playback once
        # the backend reports `Ready`.
        self._pending_start = True

    def stop(self) -> None:
        self._pending_start = False
        if self._sound_effect is None:
            return
        if self._sound_effect.isPlaying():
            self._sound_effect.stop()

    def _on_status_changed(self) -> None:
        if self._sound_effect is None:
            return
        if not self._pending_start:
            return
        if not self.is_enabled_preference():
            self._pending_start = False
            return
        if self._is_status_ready(self._sound_effect.status()):
            self._pending_start = False
            self._sound_effect.play()

    @staticmethod
    def _is_status_ready(status: object) -> bool:
        if QSoundEffect is None:
            return False
        ready = QSoundEffect.Status.Ready
        status_value = getattr(status, "value", status)
        ready_value = getattr(ready, "value", ready)
        return status_value == ready_value


__all__ = ["BackgroundMusicController"]
