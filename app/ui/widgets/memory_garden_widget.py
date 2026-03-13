"""Custom painter widget for the Memory Garden blocky scene."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, Property, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.models.memory_garden import MemoryGardenSnapshot, MemoryGardenTree


class MemoryGardenWidget(QWidget):
    """Render a lightweight 2.5D block-inspired garden scene.

    Why QPainter and not full 3D for V1:
    - stable cross-platform desktop rendering
    - no extra engine dependency
    - easy to evolve with richer visual metaphors later
    """

    # Emitting an int keeps page-side handlers simple and explicit.
    tree_selected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._snapshot = MemoryGardenSnapshot(profile_id=None, profile_name=None)
        self._selected_deck_id: int | None = None
        self._hovered_deck_id: int | None = None
        self._tree_slots: list[tuple[int, QRectF]] = []
        self._selection_emphasis = 1.0
        self._selection_animation = QPropertyAnimation(self, b"selectionEmphasis", self)
        self._selection_animation.setDuration(180)
        self._selection_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumHeight(320)
        self.setMouseTracking(True)

    def set_snapshot(self, snapshot: MemoryGardenSnapshot) -> None:
        self._snapshot = snapshot
        current_ids = {tree.deck_id for tree in snapshot.trees}
        if self._selected_deck_id not in current_ids:
            self._selected_deck_id = None
        if self._hovered_deck_id not in current_ids:
            self._hovered_deck_id = None
        self.update()

    def set_selected_deck_id(self, deck_id: int | None) -> None:
        """Set selected tree by deck id (used by the page layer)."""
        if deck_id is not None:
            valid_ids = {tree.deck_id for tree in self._snapshot.trees}
            if deck_id not in valid_ids:
                deck_id = None
        if self._selected_deck_id == deck_id:
            return
        self._selected_deck_id = deck_id
        if deck_id is not None:
            # Selection gets a short emphasis pulse to guide the eye without
            # adding continuous animation.
            self._selection_animation.stop()
            self._selection_animation.setStartValue(0.45)
            self._selection_animation.setEndValue(1.0)
            self._selection_animation.start()
        else:
            self._selection_emphasis = 1.0
        self.update()

    def selected_deck_id(self) -> int | None:
        return self._selected_deck_id

    def _get_selection_emphasis(self) -> float:
        return self._selection_emphasis

    def _set_selection_emphasis(self, value: float) -> None:
        self._selection_emphasis = max(0.0, min(1.0, float(value)))
        self.update()

    selectionEmphasis = Property(float, _get_selection_emphasis, _set_selection_emphasis)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        self._draw_background(painter)
        self._draw_ground(painter)

        trees = self._snapshot.trees
        if not trees:
            self._tree_slots = []
            self._draw_empty_scene_hint(painter)
            return

        self._draw_trees(painter, trees)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return

        deck_id = self._deck_id_at_pos(event.position().toPoint())
        if deck_id is None:
            return

        self.set_selected_deck_id(deck_id)
        self.tree_selected.emit(deck_id)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        super().mouseMoveEvent(event)
        deck_id = self._deck_id_at_pos(event.position().toPoint())
        if deck_id == self._hovered_deck_id:
            return

        self._hovered_deck_id = deck_id
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if deck_id is not None
            else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        super().leaveEvent(event)
        self._hovered_deck_id = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def _draw_background(self, painter: QPainter) -> None:
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#121318"))
        gradient.setColorAt(1.0, QColor("#1A1C22"))
        painter.fillRect(self.rect(), gradient)

    def _draw_ground(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()

        ground_top = int(h * 0.73)
        painter.fillRect(QRectF(0, ground_top, w, h - ground_top), QColor("#23262E"))

        # Subtle tile grid to evoke a block/voxel field without heavy geometry.
        tile_w = 28
        tile_h = 16
        pen = QPen(QColor("#2C303A"), 1)
        painter.setPen(pen)

        y = ground_top
        row = 0
        while y < h:
            x_offset = 0 if row % 2 == 0 else tile_w // 2
            x = -x_offset
            while x < w + tile_w:
                painter.drawRect(QRectF(x, y, tile_w, tile_h))
                x += tile_w
            y += tile_h
            row += 1

    def _draw_empty_scene_hint(self, painter: QPainter) -> None:
        text = "..."
        painter.setPen(QColor("#646A78"))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            text,
        )

    def _draw_trees(self, painter: QPainter, trees: list[MemoryGardenTree]) -> None:
        width = self.width()
        height = self.height()

        top_margin = 24
        bottom_margin = int(height * 0.24)
        left_margin = 20
        right_margin = 20

        row_count = 1 if len(trees) <= 3 else 2
        cols = min(3, len(trees)) if row_count == 1 else 3

        scene_w = max(120, width - left_margin - right_margin)
        scene_h = max(120, height - top_margin - bottom_margin)
        slot_w = scene_w / cols
        slot_h = scene_h / row_count

        self._tree_slots = []
        for index, tree in enumerate(trees):
            row = 0 if row_count == 1 else index // 3
            col = index if row_count == 1 else index % 3

            slot_rect = QRectF(
                left_margin + col * slot_w + 2,
                top_margin + row * slot_h + 2,
                slot_w - 4,
                slot_h - 4,
            )
            self._tree_slots.append((tree.deck_id, slot_rect))

            is_selected = self._selected_deck_id == tree.deck_id
            is_hovered = self._hovered_deck_id == tree.deck_id
            self._draw_slot_highlight(painter, slot_rect, is_selected=is_selected, is_hovered=is_hovered)

            origin_x = left_margin + col * slot_w + slot_w * 0.28
            ground_y = top_margin + row * slot_h + slot_h * 0.72

            block_size = max(11.0, min(19.0, min(slot_w, slot_h) / 6.0))
            self._draw_tree(
                painter,
                tree,
                origin_x,
                ground_y,
                block_size,
                is_selected=is_selected,
                is_hovered=is_hovered,
            )

            label_rect = QRectF(left_margin + col * slot_w, ground_y + block_size * 1.6, slot_w, 24)
            self._draw_tree_label(painter, label_rect, tree.deck_name, is_selected=is_selected)

    def _draw_slot_highlight(
        self,
        painter: QPainter,
        rect: QRectF,
        is_selected: bool,
        is_hovered: bool,
    ) -> None:
        if not is_selected and not is_hovered:
            return

        painter.save()
        if is_selected:
            fill = QColor("#FF8A2D")
            fill.setAlpha(int(18 + (16 * self._selection_emphasis)))
            outline = QPen(QColor("#FF8A2D"), 1.8)
        else:
            fill = QColor("#FFFFFF")
            fill.setAlpha(10)
            outline = QPen(QColor("#AAAAAE"), 1.0)

        painter.setPen(outline)
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 8, 8)
        painter.restore()

    def _draw_tree(
        self,
        painter: QPainter,
        tree: MemoryGardenTree,
        x: float,
        ground_y: float,
        block: float,
        is_selected: bool,
        is_hovered: bool,
    ) -> None:
        trunk_front = QColor("#6B4E3D")
        if is_selected:
            trunk_front = trunk_front.lighter(108 + int(8 * self._selection_emphasis))
        elif is_hovered:
            trunk_front = trunk_front.lighter(108)

        # Trunk = vertical block stack controlled by tracked question volume.
        for i in range(tree.trunk_blocks):
            y = ground_y - (i + 1) * (block * 0.88)
            self._draw_voxel_block(painter, x, y, block, trunk_front)

        canopy_origin_y = ground_y - tree.trunk_blocks * (block * 0.88) - block * 0.4
        foliage_color = self._foliage_color(tree.health_state)
        if is_selected:
            foliage_color = foliage_color.lighter(112 + int(10 * self._selection_emphasis))
        elif is_hovered:
            foliage_color = foliage_color.lighter(110)

        # Foliage cluster pattern stays deterministic to avoid flicker.
        offsets = [
            (0, 0),
            (-1, 0),
            (1, 0),
            (0, -1),
            (-1, -1),
            (1, -1),
            (0, 1),
        ]

        for i in range(min(tree.foliage_blocks, len(offsets))):
            ox, oy = offsets[i]
            bx = x + ox * (block * 0.8)
            by = canopy_origin_y + oy * (block * 0.72)
            self._draw_voxel_block(painter, bx, by, block, foliage_color)

        # Accent blocks represent milestone achievements (mastery/trophies).
        for i in range(tree.accent_blocks):
            bx = x + (i - 1) * (block * 0.55)
            by = canopy_origin_y - block * 1.1 - (i % 2) * (block * 0.15)
            self._draw_voxel_block(painter, bx, by, block * 0.45, QColor("#FF9A3C"))

        if is_selected:
            marker_x = x + block * 0.32
            marker_y = ground_y + block * 0.18
            marker = QColor("#FF8A2D")
            marker.setAlpha(int(190 + (45 * self._selection_emphasis)))
            self._draw_voxel_block(painter, marker_x, marker_y, block * 0.35, marker)

    def _draw_tree_label(self, painter: QPainter, rect: QRectF, text: str, is_selected: bool) -> None:
        painter.save()
        painter.setPen(QColor("#FFB06A") if is_selected else QColor("#B1B6C3"))

        fm = QFontMetrics(painter.font())
        clipped = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(rect.width()) - 6)
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            clipped,
        )
        painter.restore()

    def _draw_voxel_block(
        self,
        painter: QPainter,
        x: float,
        y: float,
        size: float,
        color: QColor,
    ) -> None:
        front = QRectF(x, y, size, size)

        top = [
            QPointF(x, y),
            QPointF(x + size * 0.22, y - size * 0.20),
            QPointF(x + size * 1.22, y - size * 0.20),
            QPointF(x + size, y),
        ]
        side = [
            QPointF(x + size, y),
            QPointF(x + size * 1.22, y - size * 0.20),
            QPointF(x + size * 1.22, y + size * 0.80),
            QPointF(x + size, y + size),
        ]

        outline = QColor("#2C2F38")
        painter.setPen(QPen(outline, 1))

        painter.setBrush(color)
        painter.drawRect(front)

        top_color = QColor(color)
        top_color = top_color.lighter(125)
        painter.setBrush(top_color)
        painter.drawPolygon(top)

        side_color = QColor(color)
        side_color = side_color.darker(120)
        painter.setBrush(side_color)
        painter.drawPolygon(side)

    def _foliage_color(self, health_state: str) -> QColor:
        if health_state == "lush":
            return QColor("#5B8F66")
        if health_state == "fragile":
            return QColor("#6D6658")
        return QColor("#7B7A5F")

    def _deck_id_at_pos(self, pos: QPoint) -> int | None:
        # Hit detection is intentionally simple and stable: each tree owns a
        # slot rectangle in the scene, so clicks map cleanly to deck ids.
        for deck_id, rect in self._tree_slots:
            if rect.contains(QPointF(pos)):
                return deck_id
        return None


__all__ = ["MemoryGardenWidget"]
