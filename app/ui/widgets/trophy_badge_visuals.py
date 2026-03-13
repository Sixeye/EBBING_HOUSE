"""Trophy badge visual helpers.

This module gives us a clean bridge between:
- today's icon-based badges (generated with QPainter)
- future real PNG badge packs dropped in app/assets/badges

The page code only calls `build_trophy_badge_icon(...)`, so swapping
generated visuals for handcrafted PNG artwork later is straightforward.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap

# Future-ready location for real badge assets (one file per code/category).
BADGES_DIR = Path(__file__).resolve().parents[2] / "assets" / "badges"

# Short, readable glyphs used by the generated fallback icons.
_CODE_GLYPH_MAP: dict[str, str] = {
    "first_profile_created": "PR",
    "first_active_profile_set": "ACT",
    "first_csv_import": "CSV",
    "first_review_session_completed": "REV",
    "first_due_session_completed": "DUE",
    "five_correct_answers": "5+",
    "ten_correct_answers": "10+",
    "first_mastered_question": "M1",
    "ten_questions_tracked": "Q10",
    "all_caught_up_once": "ZERO",
    "first_hangman_win": "HM",
    "first_maze_completed": "MZ",
}

_RARITY_COLORS: dict[str, str] = {
    "common": "#FF8A2D",
    "uncommon": "#FFA95F",
    "rare": "#FFD073",
}


def build_trophy_badge_icon(
    *,
    code: str,
    category: str,
    rarity: str,
    unlocked: bool,
    size: int = 44,
) -> QIcon:
    """Return a visual badge icon for one trophy row.

    Resolution order:
    1) PNG badge from app/assets/badges (if available)
    2) generated vector-like icon fallback

    This keeps the reward UI usable today and ready for art upgrades later.
    """
    safe_size = max(24, int(size))
    return _build_trophy_badge_icon_cached(
        code.strip().lower(),
        category.strip().lower(),
        rarity.strip().lower(),
        bool(unlocked),
        safe_size,
    )


@lru_cache(maxsize=512)
def _build_trophy_badge_icon_cached(
    code: str,
    category: str,
    rarity: str,
    unlocked: bool,
    size: int,
) -> QIcon:
    pixmap = _load_png_badge(code=code, category=category, rarity=rarity, size=size)
    if pixmap is None:
        pixmap = _build_generated_badge(code=code, rarity=rarity, unlocked=unlocked, size=size)
    elif not unlocked:
        pixmap = _apply_locked_overlay(pixmap)
    return QIcon(pixmap)


def _load_png_badge(*, code: str, category: str, rarity: str, size: int) -> QPixmap | None:
    """Try loading a PNG badge from disk.

    Naming strategy stays explicit and beginner-friendly:
    - exact code first (best precision)
    - then category+rarity
    - then generic defaults
    """
    if not BADGES_DIR.exists():
        return None

    candidates = (
        BADGES_DIR / f"{code}.png",
        BADGES_DIR / f"{category}_{rarity}.png",
        BADGES_DIR / f"{category}.png",
        BADGES_DIR / "default.png",
    )
    for path in candidates:
        if not path.exists():
            continue
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            continue
        return pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    return None


def _build_generated_badge(*, code: str, rarity: str, unlocked: bool, size: int) -> QPixmap:
    """Generate an elegant fallback badge icon.

    We keep the look compact and legible:
    - rounded frame
    - subtle gradient body
    - centered glyph
    - lock overlay when locked
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    accent_hex = _RARITY_COLORS.get(rarity, _RARITY_COLORS["common"])
    accent = QColor(accent_hex)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    outer = QRectF(1.0, 1.0, size - 2.0, size - 2.0)
    inner = outer.adjusted(4.0, 4.0, -4.0, -4.0)

    # Frame + fill keep dark-mode coherence with orange-accent identity.
    frame_color = QColor(accent) if unlocked else QColor("#5D6068")
    painter.setPen(QPen(frame_color, 1.4))
    painter.setBrush(QColor("#1A1C20"))
    painter.drawRoundedRect(outer, 9.0, 9.0)

    grad = QLinearGradient(inner.topLeft(), inner.bottomRight())
    if unlocked:
        grad.setColorAt(0.0, QColor("#2D2F35"))
        grad.setColorAt(1.0, QColor("#1D1F24"))
    else:
        grad.setColorAt(0.0, QColor("#22242A"))
        grad.setColorAt(1.0, QColor("#17191E"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(grad)
    painter.drawRoundedRect(inner, 7.0, 7.0)

    # Tiny rarity strip gives quick visual distinction without noisy colors.
    rarity_strip = QRectF(inner.left(), inner.top(), inner.width(), max(4.0, size * 0.09))
    strip_color = QColor(accent) if unlocked else QColor("#666A73")
    painter.setBrush(strip_color)
    painter.drawRoundedRect(rarity_strip, 6.0, 6.0)

    glyph = _CODE_GLYPH_MAP.get(code, "XP")
    painter.setPen(QColor("#F4F4F5") if unlocked else QColor("#B0B3BB"))
    font = QFont("Avenir Next", max(8, int(size * 0.19)))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(inner.adjusted(2.0, size * 0.12, -2.0, -2.0), Qt.AlignmentFlag.AlignCenter, glyph)

    # Unlock sparkle in top-right. Locked badges receive a lock overlay.
    if unlocked:
        sparkle = QRectF(inner.right() - size * 0.20, inner.top() + size * 0.08, size * 0.12, size * 0.12)
        painter.setBrush(QColor("#FFD98A"))
        painter.drawEllipse(sparkle)
    else:
        painter.end()
        return _apply_locked_overlay(pixmap)

    painter.end()
    return pixmap


def _apply_locked_overlay(source: QPixmap) -> QPixmap:
    """Dim icon and draw a compact lock marker for locked state."""
    pixmap = source.copy()
    size = max(1, pixmap.width())
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.fillRect(pixmap.rect(), QColor(10, 10, 12, 115))

    body = QRectF(size * 0.66, size * 0.64, size * 0.22, size * 0.22)
    shackle = QRectF(size * 0.695, size * 0.56, size * 0.15, size * 0.14)

    painter.setPen(QPen(QColor("#CCCED3"), max(1.0, size * 0.02)))
    painter.setBrush(QColor(55, 58, 64, 220))
    painter.drawRoundedRect(body, 3.5, 3.5)
    painter.drawArc(shackle, 0, 180 * 16)
    painter.end()
    return pixmap


__all__ = ["build_trophy_badge_icon", "BADGES_DIR"]
