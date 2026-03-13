"""Lightweight startup splash animation for EBBING_HOUSE.

This splash keeps startup polish brief and elegant:
- central branded PNG
- subtle glasses glow/shimmer
- stylized upward sand motion in the hourglass area

The implementation is intentionally small and timer-driven to stay stable on
desktop environments without introducing heavy animation dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget

from app.themes.branding import (
    BRANDING_DIR,
    PRIMARY_BRANDING_DIR,
    PRIMARY_BRANDING_PATH,
    branding_source_path,
    load_brand_logo,
)


class StartupSplashWidget(QWidget):
    """Short startup splash with branded atmospheric micro-animation."""

    finished = Signal()

    def __init__(self, duration_ms: int = 1900, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._duration_ms = max(800, int(duration_ms))
        self._progress = 0.0
        self._elapsed = QElapsedTimer()

        self._pixmap, self._identity_source_path, self._is_canonical_identity = self._load_identity_pixmap()
        if self._pixmap.isNull():
            # Missing asset should not add startup friction; keep fallback brief.
            self._duration_ms = min(self._duration_ms, 1100)
        # Larger fallback keeps the splash readable if the branded PNG is absent.
        self._fallback_logo = load_brand_logo(520)

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS; light enough for a short splash.
        self._timer.timeout.connect(self._on_tick)

        self.setObjectName("StartupSplash")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.SplashScreen, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.resize(760, 760)
        self._center_on_primary_screen()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt naming convention)
        super().showEvent(event)
        self._elapsed.start()
        self._timer.start()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming convention)
        # Skip-safe behavior: any click finishes immediately.
        self._finish()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt naming convention)
        # Keep startup non-intrusive: Escape/Enter/Space can skip the splash.
        if event.key() in (
            Qt.Key.Key_Escape,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self._finish()
            return
        super().keyPressEvent(event)

    def _on_tick(self) -> None:
        elapsed_ms = self._elapsed.elapsed()
        self._progress = min(1.0, elapsed_ms / float(self._duration_ms))
        self.update()
        if self._progress >= 1.0:
            self._finish()

    def _finish(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self.isVisible():
            self.finished.emit()
            self.close()

    def is_using_provided_identity(self) -> bool:
        """Return True when canonical EBBING_HOUSE_APP.png is used."""
        return self._is_canonical_identity

    def identity_source_path(self) -> Path | None:
        """Expose loaded image path for diagnostics/manual verification."""
        return self._identity_source_path

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming convention)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        frame_rect = QRectF(self.rect()).adjusted(14, 14, -14, -14)

        # Dark atmospheric backdrop with a warm frame to keep retro tone.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(10, 11, 14, 236))
        painter.drawRoundedRect(frame_rect, 20, 20)
        painter.setPen(QPen(QColor(255, 138, 45, 118), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame_rect.adjusted(1, 1, -1, -1), 20, 20)

        content_rect = frame_rect.adjusted(18, 18, -18, -18)
        scene_opacity = self._scene_opacity(self._progress)
        base_pixmap = self._pixmap if not self._pixmap.isNull() else self._fallback_logo
        target_rect = self._fit_pixmap_rect(content_rect, base_pixmap)

        # Base branding image remains central and readable.
        painter.save()
        painter.setOpacity(scene_opacity)
        painter.drawPixmap(target_rect.toRect(), base_pixmap)
        painter.restore()

        # Subtle atmosphere glow over the whole artwork.
        self._paint_atmosphere(painter, target_rect, scene_opacity)
        if self._is_canonical_identity and not self._pixmap.isNull():
            # Requested branded effects are mapped to known art regions and work
            # best with the provided identity image.
            self._paint_glasses_glow(painter, target_rect, scene_opacity)
            self._paint_hourglass_upward_sand(painter, target_rect, scene_opacity)
        else:
            # Graceful fallback: keep startup elegant when asset is missing.
            self._paint_fallback_hint(painter, target_rect, scene_opacity)

    def _paint_atmosphere(self, painter: QPainter, target_rect: QRectF, scene_opacity: float) -> None:
        center = target_rect.center()
        radius = target_rect.width() * 0.58
        aura = QRadialGradient(center, radius)
        aura.setColorAt(0.0, QColor(255, 168, 86, int(58 * scene_opacity)))
        aura.setColorAt(0.55, QColor(255, 168, 86, int(24 * scene_opacity)))
        aura.setColorAt(1.0, QColor(255, 168, 86, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(aura)
        painter.drawEllipse(center, radius, radius)

    def _paint_glasses_glow(self, painter: QPainter, target_rect: QRectF, scene_opacity: float) -> None:
        """Add a soft pulse around the glasses and a tiny shimmer sweep."""
        phase_s = self._elapsed.elapsed() / 1000.0
        pulse = 0.55 + 0.45 * math.sin(phase_s * math.tau * 1.7)

        lens_centers = (
            self._map_point(target_rect, 0.455, 0.432),
            self._map_point(target_rect, 0.545, 0.432),
        )
        glow_radius = min(target_rect.width(), target_rect.height()) * 0.07

        painter.setPen(Qt.PenStyle.NoPen)
        for center in lens_centers:
            grad = QRadialGradient(center, glow_radius)
            grad.setColorAt(0.0, QColor(172, 228, 255, int(165 * pulse * scene_opacity)))
            grad.setColorAt(0.45, QColor(172, 228, 255, int(78 * pulse * scene_opacity)))
            grad.setColorAt(1.0, QColor(172, 228, 255, 0))
            painter.setBrush(grad)
            painter.drawEllipse(center, glow_radius, glow_radius)

        # Gentle shimmer bar crossing the glasses area.
        shimmer_rect = self._map_rect(target_rect, 0.395, 0.392, 0.22, 0.09)
        band_t = (phase_s % 1.35) / 1.35
        band_x = shimmer_rect.left() + band_t * shimmer_rect.width()
        band_width = max(6.0, target_rect.width() * 0.032)

        shimmer_grad = QLinearGradient(
            QPointF(band_x - band_width * 0.5, shimmer_rect.top()),
            QPointF(band_x + band_width * 0.5, shimmer_rect.bottom()),
        )
        shimmer_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        shimmer_grad.setColorAt(0.5, QColor(255, 255, 255, int(78 * scene_opacity)))
        shimmer_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(shimmer_grad)
        painter.drawRoundedRect(shimmer_rect, 8, 8)

    def _paint_hourglass_upward_sand(
        self,
        painter: QPainter,
        target_rect: QRectF,
        scene_opacity: float,
    ) -> None:
        """Stylized upward sand movement in the hourglass region.

        We intentionally keep this simple and readable:
        - one central stream
        - lightweight particles drifting upward
        """
        phase_s = self._elapsed.elapsed() / 1000.0
        hg_rect = self._map_rect(target_rect, 0.803, 0.556, 0.094, 0.165)

        # Central upward stream.
        painter.setBrush(Qt.BrushStyle.NoBrush)
        stream_pen = QPen(
            QColor(255, 196, 105, int(126 * scene_opacity)),
            max(1.2, target_rect.width() * 0.003),
        )
        painter.setPen(stream_pen)
        painter.drawLine(
            QPointF(hg_rect.center().x(), hg_rect.bottom() - hg_rect.height() * 0.10),
            QPointF(hg_rect.center().x(), hg_rect.top() + hg_rect.height() * 0.22),
        )

        # Upward particles from bottom to top.
        particle_count = 16
        painter.setPen(Qt.PenStyle.NoPen)
        for idx in range(particle_count):
            seed = idx / float(particle_count)
            travel = (phase_s * 0.92 + seed) % 1.0

            y = hg_rect.bottom() - hg_rect.height() * (0.10 + travel * 0.78)
            spread = max(0.24, 1.0 - abs(travel - 0.5) * 1.9)
            sway = math.sin((phase_s * 2.7 + seed * 11.0) * math.tau)
            x = hg_rect.center().x() + sway * hg_rect.width() * 0.20 * spread

            radius = max(1.5, target_rect.width() * 0.0036)
            alpha = int((95 + (1.0 - travel) * 150) * scene_opacity)
            color = QColor(255, 208, 124, max(0, min(255, alpha)))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), radius, radius)

    def _scene_opacity(self, progress: float) -> float:
        # Smooth fade-in/fade-out to avoid a harsh startup cut.
        if progress < 0.16:
            return max(0.0, min(1.0, progress / 0.16))
        if progress > 0.88:
            return max(0.0, min(1.0, (1.0 - progress) / 0.12))
        return 1.0

    def _paint_fallback_hint(self, painter: QPainter, target_rect: QRectF, scene_opacity: float) -> None:
        """Draw a minimal hint when branded PNG is unavailable.

        We keep this tiny and unobtrusive so startup still feels intentional
        without pretending to be the full branded splash.
        """
        hint_rect = QRectF(
            target_rect.left(),
            target_rect.bottom() + 8.0,
            target_rect.width(),
            min(32.0, self.height() * 0.06),
        )
        painter.setPen(QColor(193, 195, 202, int(170 * scene_opacity)))
        painter.drawText(
            hint_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "Brand image not found: assets/images/EBBING_HOUSE_APP.png",
        )

    def _load_identity_pixmap(self) -> tuple[QPixmap, Path | None, bool]:
        # Product requirement: splash should use the provided identity artwork
        # directly. We therefore prioritize the canonical filename first.
        direct_source = PRIMARY_BRANDING_PATH
        sources: list[Path] = []
        seen_resolved: set[Path] = set()

        def _add_source(path: Path | None) -> None:
            if path is None:
                return
            resolved = path.resolve()
            if resolved in seen_resolved:
                return
            seen_resolved.add(resolved)
            sources.append(path)

        if direct_source.exists():
            _add_source(direct_source)

        # If canonical asset is missing (or invalid), we still try other branding
        # files so startup keeps a coherent branded identity.
        _add_source(branding_source_path())

        for directory in (PRIMARY_BRANDING_DIR, BRANDING_DIR):
            if not directory.exists():
                continue
            for candidate in sorted(directory.iterdir()):
                if not candidate.is_file():
                    continue
                if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    continue
                _add_source(candidate)

        for source in sources:
            pixmap = QPixmap(str(source))
            if pixmap.isNull():
                continue
            return pixmap, source, source.resolve() == direct_source.resolve()

        return QPixmap(), None, False

    def _fit_pixmap_rect(self, container: QRectF, pixmap: QPixmap) -> QRectF:
        if pixmap.isNull():
            return container

        ratio = pixmap.width() / max(1.0, float(pixmap.height()))
        target_w = container.width()
        target_h = target_w / ratio
        if target_h > container.height():
            target_h = container.height()
            target_w = target_h * ratio

        x = container.left() + (container.width() - target_w) * 0.5
        y = container.top() + (container.height() - target_h) * 0.5
        return QRectF(x, y, target_w, target_h)

    def _map_point(self, target_rect: QRectF, nx: float, ny: float) -> QPointF:
        return QPointF(
            target_rect.left() + target_rect.width() * nx,
            target_rect.top() + target_rect.height() * ny,
        )

    def _map_rect(self, target_rect: QRectF, nx: float, ny: float, nw: float, nh: float) -> QRectF:
        return QRectF(
            target_rect.left() + target_rect.width() * nx,
            target_rect.top() + target_rect.height() * ny,
            target_rect.width() * nw,
            target_rect.height() * nh,
        )

    def _center_on_primary_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        center = rect.center() - QPoint(self.width() // 2, self.height() // 2)
        self.move(center)


__all__ = ["StartupSplashWidget"]
