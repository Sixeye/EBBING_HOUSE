"""Brand asset helpers for EBBING_HOUSE.

This module centralizes all identity loading logic:
- primary canonical asset: assets/images/EBBING_HOUSE_APP.png
- compatibility fallback: app/assets/branding/*
- internal pixel-style fallback when no image is available

Keeping this in one place prevents ad-hoc image handling in each page.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

from app.core.paths import PROJECT_ROOT as RUNTIME_PROJECT_ROOT
from app.core.paths import get_app_asset_dir, get_project_asset_dir

# Project-level canonical location required by product spec.
# These paths are resolved through `app.core.paths` so the same code works in
# development and inside a bundled app.
PROJECT_ROOT = RUNTIME_PROJECT_ROOT
PRIMARY_BRANDING_DIR = get_project_asset_dir("images")
PRIMARY_BRANDING_PATH = PRIMARY_BRANDING_DIR / "EBBING_HOUSE_APP.png"

# Compatibility folder used by earlier iterations of the project.
BRANDING_DIR = get_app_asset_dir("branding")
BRANDING_CANDIDATES = (
    "EBBING_HOUSE_APP.png",
    "ebbing_house_identity.png",
    "ebbing_house_app.png",
    "ebbing_house_identity.jpg",
    "ebbing_house_identity.jpeg",
)
SUPPORTED_BRANDING_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def branding_source_path() -> Path | None:
    """Return a usable branding image path.

    Resolution strategy:
    1) Prefer exact required file: assets/images/EBBING_HOUSE_APP.png
    2) Fallback to known names in assets/images
    3) Fallback to compatibility folder app/assets/branding
    This keeps onboarding simple when users drop an image with a custom name.
    """
    if PRIMARY_BRANDING_PATH.exists():
        return PRIMARY_BRANDING_PATH

    for filename in BRANDING_CANDIDATES:
        candidate = PRIMARY_BRANDING_DIR / filename
        if candidate.exists():
            return candidate

    for filename in BRANDING_CANDIDATES:
        candidate = BRANDING_DIR / filename
        if candidate.exists():
            return candidate

    for directory in (PRIMARY_BRANDING_DIR, BRANDING_DIR):
        if not directory.exists():
            continue
        for candidate in sorted(directory.iterdir()):
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_BRANDING_SUFFIXES:
                return candidate
    return None


@lru_cache(maxsize=24)
def load_brand_logo(size: int) -> QPixmap:
    """Return a square brand logo pixmap.

    We prefer the user-provided image for identity coherence. If it is not
    available, we render a tiny original pixel-style fallback so UI remains
    stable and branded.
    """
    safe_size = max(24, int(size))
    source_path = branding_source_path()
    if source_path is not None:
        source = QPixmap(str(source_path))
        if not source.isNull():
            return source.scaled(
                safe_size,
                safe_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                # Preserve pixel-art character for 8-bit style identity marks.
                Qt.TransformationMode.FastTransformation,
            )
    return _build_fallback_logo(safe_size)


def build_window_icon() -> QIcon:
    """Build window/app icon from branded artwork with fallback sizes."""
    source_path = branding_source_path()
    if source_path is not None:
        icon = QIcon(str(source_path))
        if not icon.isNull():
            return icon

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(load_brand_logo(size))
    return icon


@lru_cache(maxsize=48)
def load_brand_banner(width: int, height: int, focal_point: tuple[float, float] = (0.5, 0.5)) -> QPixmap:
    """Return an aspect-safe brand banner with optional focal-point crop.

    `focal_point` uses normalized coordinates in source-image space:
    - (0.5, 0.5) keeps classic center crop
    - lower y values shift crop upward to prioritize faces/heads

    This lets pages keep elegant framing when the meaningful subject is not
    exactly centered in the raw image bounds.
    """
    safe_width = max(120, int(width))
    safe_height = max(56, int(height))
    focal_x, focal_y = focal_point
    focal_x = min(1.0, max(0.0, float(focal_x)))
    focal_y = min(1.0, max(0.0, float(focal_y)))
    source_path = branding_source_path()
    if source_path is not None:
        source = QPixmap(str(source_path))
        if not source.isNull():
            # Keep aspect ratio (no stretch), then crop around focal point.
            scaled = source.scaled(
                safe_width,
                safe_height,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                # Keep retro/blocky edges readable instead of smoothing.
                Qt.TransformationMode.FastTransformation,
            )
            x = _focal_crop_start(
                full_size=scaled.width(),
                crop_size=safe_width,
                focal_ratio=focal_x,
            )
            y = _focal_crop_start(
                full_size=scaled.height(),
                crop_size=safe_height,
                focal_ratio=focal_y,
            )
            return scaled.copy(x, y, safe_width, safe_height)

    # Banner fallback keeps the same warm-orange / deep-blue retro direction.
    return _build_fallback_banner(safe_width, safe_height)


def _focal_crop_start(full_size: int, crop_size: int, focal_ratio: float) -> int:
    """Return a clamped crop start index around a focal point.

    Example:
    - full_size=520, crop_size=88, focal_ratio=0.38
    - focal pixel is around 197, crop starts near 153 (face-biased upper crop)
    """
    if full_size <= crop_size:
        return 0
    focal_px = full_size * focal_ratio
    start = int(round(focal_px - crop_size / 2.0))
    return max(0, min(full_size - crop_size, start))


def _build_fallback_logo(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    outer = QRectF(0, 0, size - 1, size - 1)
    painter.fillRect(outer, QColor("#0F1014"))

    frame_pen = QPen(QColor("#FF8A2D"), 2)
    painter.setPen(frame_pen)
    painter.drawRect(outer.adjusted(2, 2, -2, -2))

    cell = max(2, size // 20)
    center_x = size * 0.5
    center_y = size * 0.47

    # Simple blocky avatar silhouette aligned with retro educational identity.
    head = QRectF(center_x - cell * 3.0, center_y - cell * 4.0, cell * 6.0, cell * 5.0)
    beard = QRectF(center_x - cell * 3.2, center_y + cell * 0.8, cell * 6.4, cell * 3.3)
    glasses_left = QRectF(center_x - cell * 2.4, center_y - cell * 2.0, cell * 1.7, cell * 1.4)
    glasses_right = QRectF(center_x + cell * 0.7, center_y - cell * 2.0, cell * 1.7, cell * 1.4)

    painter.fillRect(head, QColor("#F2CFA6"))
    painter.fillRect(beard, QColor("#A85312"))
    painter.fillRect(glasses_left, QColor("#D9EEF8"))
    painter.fillRect(glasses_right, QColor("#D9EEF8"))
    painter.fillRect(QRectF(center_x - cell * 0.7, center_y - cell * 1.5, cell * 1.4, cell * 0.5), QColor("#1C2631"))

    # Tiny hourglass motif to keep memory/time symbolism.
    hg_x = size * 0.75
    hg_y = size * 0.63
    hg_w = cell * 3.0
    hg_h = cell * 4.0
    painter.fillRect(QRectF(hg_x, hg_y, hg_w, cell * 0.45), QColor("#FF8A2D"))
    painter.fillRect(QRectF(hg_x, hg_y + hg_h - cell * 0.45, hg_w, cell * 0.45), QColor("#FF8A2D"))
    hourglass = QPolygonF(
        [
            QPointF(hg_x + cell * 0.3, hg_y + cell * 0.55),
            QPointF(hg_x + hg_w - cell * 0.3, hg_y + cell * 0.55),
            QPointF(hg_x + hg_w * 0.57, hg_y + hg_h * 0.52),
            QPointF(hg_x + hg_w - cell * 0.3, hg_y + hg_h - cell * 0.55),
            QPointF(hg_x + cell * 0.3, hg_y + hg_h - cell * 0.55),
            QPointF(hg_x + hg_w * 0.43, hg_y + hg_h * 0.52),
        ]
    )
    painter.setBrush(QColor("#D9EEF8"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPolygon(hourglass)

    painter.end()
    return pixmap


def _build_fallback_banner(width: int, height: int) -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#101114"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    painter.fillRect(QRectF(0, 0, width, height), QColor("#101114"))
    painter.setPen(QPen(QColor("#FF8A2D"), 1))
    painter.drawRect(QRectF(1, 1, width - 2, height - 2))

    # Left panel (books).
    painter.fillRect(QRectF(width * 0.06, height * 0.28, width * 0.16, height * 0.48), QColor("#1B4F85"))
    painter.fillRect(QRectF(width * 0.06, height * 0.67, width * 0.16, height * 0.07), QColor("#FF8A2D"))

    # Center portrait block.
    center = QRectF(width * 0.36, height * 0.12, width * 0.28, height * 0.74)
    painter.fillRect(center, QColor("#224766"))
    painter.fillRect(QRectF(center.x() + center.width() * 0.24, center.y() + center.height() * 0.16, center.width() * 0.52, center.height() * 0.32), QColor("#F2CFA6"))
    painter.fillRect(QRectF(center.x() + center.width() * 0.20, center.y() + center.height() * 0.51, center.width() * 0.60, center.height() * 0.22), QColor("#A85312"))
    painter.fillRect(QRectF(center.x() + center.width() * 0.31, center.y() + center.height() * 0.28, center.width() * 0.12, center.height() * 0.10), QColor("#D9EEF8"))
    painter.fillRect(QRectF(center.x() + center.width() * 0.57, center.y() + center.height() * 0.28, center.width() * 0.12, center.height() * 0.10), QColor("#D9EEF8"))

    # Right panel (hourglass).
    hg = QRectF(width * 0.77, height * 0.30, width * 0.14, height * 0.44)
    painter.fillRect(hg.adjusted(0, 0, 0, -hg.height() * 0.84), QColor("#FF8A2D"))
    painter.fillRect(hg.adjusted(0, hg.height() * 0.84, 0, 0), QColor("#FF8A2D"))
    painter.fillRect(hg.adjusted(hg.width() * 0.23, hg.height() * 0.12, -hg.width() * 0.23, -hg.height() * 0.12), QColor("#D9EEF8"))

    painter.end()
    return pixmap


__all__ = [
    "PROJECT_ROOT",
    "PRIMARY_BRANDING_DIR",
    "PRIMARY_BRANDING_PATH",
    "BRANDING_DIR",
    "branding_source_path",
    "load_brand_logo",
    "load_brand_banner",
    "build_window_icon",
]
