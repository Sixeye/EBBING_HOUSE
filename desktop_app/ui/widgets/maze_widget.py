"""Voxel-inspired pseudo-3D maze renderer for Maze Challenge."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from desktop_app.themes.palette import ACCENT_ORANGE, ERROR_RED, SUCCESS_GREEN


class MazeWidget(QWidget):
    """Render a lightweight voxel-like maze scene.

    Rendering choice:
    - QPainter pseudo-3D instead of heavy real 3D engine
    - extruded blocks for walls/floor to keep a voxel mood
    - stable in offscreen and low-power environments
    """

    def __init__(self) -> None:
        super().__init__()
        self._layout_rows: tuple[str, ...] = tuple()
        self._player_pos: tuple[int, int] | None = None
        self._guardian_pos: tuple[int, int] | None = None
        self._start_pos: tuple[int, int] | None = None
        self._exit_pos: tuple[int, int] | None = None
        self._reachable_cells: set[tuple[int, int]] = set()

        self._pulse_strength = 0.0
        self._pulse_color = QColor(ACCENT_ORANGE)
        self._pulse_animation = QPropertyAnimation(self, b"pulseStrength", self)
        self._pulse_animation.setDuration(220)
        self._pulse_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Avoid over-compression of pseudo-3D tiles on tighter widths.
        self.setMinimumWidth(300)
        self.setMinimumHeight(320)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        # Maze scene should follow width and keep stable perspective density.
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        target = int(width * 0.78)
        return max(self.minimumHeight(), min(target, 700))

    def sizeHint(self) -> QSize:  # type: ignore[override]
        base_width = 620
        return QSize(base_width, self.heightForWidth(base_width))

    def set_scene(
        self,
        layout_rows: tuple[str, ...],
        player_pos: tuple[int, int],
        guardian_pos: tuple[int, int],
        start_pos: tuple[int, int],
        exit_pos: tuple[int, int],
        reachable_cells: set[tuple[int, int]] | None = None,
    ) -> None:
        self._layout_rows = layout_rows
        self._player_pos = player_pos
        self._guardian_pos = guardian_pos
        self._start_pos = start_pos
        self._exit_pos = exit_pos
        self._reachable_cells = reachable_cells or set()
        self.update()

    def pulse_move_feedback(self, moved: bool) -> None:
        """Short pulse after movement resolution.

        Green: successful move.
        Red: denied move (wrong answer or blocked attempt feedback).
        """
        self._pulse_color = QColor(SUCCESS_GREEN if moved else ERROR_RED)
        self._pulse_animation.stop()
        self._pulse_animation.setStartValue(0.35)
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
        # We disable antialiasing to keep edges crisp and blocky.
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        painter.fillRect(self.rect(), QColor("#11141A"))
        painter.setPen(QPen(QColor("#2A2F39"), 1))
        painter.drawRoundedRect(QRectF(4, 4, self.width() - 8, self.height() - 8), 10, 10)

        if not self._layout_rows or self._player_pos is None:
            return

        rows = len(self._layout_rows)
        cols = len(self._layout_rows[0]) if rows else 0
        if rows == 0 or cols == 0:
            return

        margin = 16.0
        usable_w = max(80.0, float(self.width()) - margin * 2)
        usable_h = max(80.0, float(self.height()) - margin * 2)

        cell_w = min(
            usable_w / (cols + rows * 0.22 + 1.1),
            usable_h / (rows * 0.74 + 2.1),
        )
        cell_h = cell_w * 0.56
        tilt_x = -cell_w * 0.42
        row_skew_x = cell_w * 0.13

        wall_depth = cell_w * 0.84
        floor_depth = cell_w * 0.18

        scene_w = cols * cell_w + rows * row_skew_x + abs(tilt_x) + cell_w
        scene_h = rows * cell_h + wall_depth + cell_w

        origin_x = (self.width() - scene_w) / 2.0 + abs(tilt_x)
        origin_y = (self.height() - scene_h) / 2.0 + cell_w * 0.28

        # Draw back-to-front for consistent overlap.
        for row_index, row in enumerate(self._layout_rows):
            for col_index, marker in enumerate(row):
                x = origin_x + col_index * cell_w + row_index * row_skew_x
                y = origin_y + row_index * cell_h
                top = self._cell_top_polygon(x, y, cell_w, cell_h, tilt_x)

                if marker == "#":
                    self._draw_block(
                        painter=painter,
                        top=top,
                        depth=wall_depth,
                        top_color=QColor("#4F5F53"),
                        front_color=QColor("#39443D"),
                        side_color=QColor("#323C36"),
                    )
                else:
                    tile_top = QColor("#1D232D")
                    if (row_index, col_index) == self._start_pos:
                        tile_top = QColor("#4A5470")
                    elif (row_index, col_index) == self._exit_pos:
                        tile_top = QColor("#1F6A48")

                    self._draw_block(
                        painter=painter,
                        top=top,
                        depth=floor_depth,
                        top_color=tile_top,
                        front_color=QColor(tile_top).darker(130),
                        side_color=QColor(tile_top).darker(145),
                    )

                    if (row_index, col_index) in self._reachable_cells:
                        painter.setPen(QPen(QColor("#FF9A3A"), 1))
                        painter.setBrush(QColor(255, 154, 58, 36))
                        painter.drawPolygon(top)

                    if (row_index, col_index) == self._exit_pos:
                        self._draw_exit_beacon(painter, top, cell_w)

        self._draw_player_marker(
            painter=painter,
            origin_x=origin_x,
            origin_y=origin_y,
            cell_w=cell_w,
            cell_h=cell_h,
            tilt_x=tilt_x,
            row_skew_x=row_skew_x,
            floor_depth=floor_depth,
        )
        self._draw_guardian_marker(
            painter=painter,
            origin_x=origin_x,
            origin_y=origin_y,
            cell_w=cell_w,
            cell_h=cell_h,
            tilt_x=tilt_x,
            row_skew_x=row_skew_x,
            floor_depth=floor_depth,
        )

        if self._pulse_strength > 0.01:
            pulse_fill = QColor(self._pulse_color)
            pulse_fill.setAlpha(int(72 * self._pulse_strength))
            pulse_outline = QColor(self._pulse_color)
            pulse_outline.setAlpha(int(110 * self._pulse_strength))

            painter.setBrush(pulse_fill)
            painter.setPen(QPen(pulse_outline, 2))
            painter.drawRoundedRect(QRectF(6, 6, self.width() - 12, self.height() - 12), 12, 12)

    def _cell_top_polygon(
        self,
        x: float,
        y: float,
        cell_w: float,
        cell_h: float,
        tilt_x: float,
    ) -> QPolygonF:
        return QPolygonF(
            [
                QPointF(x, y),
                QPointF(x + cell_w, y),
                QPointF(x + cell_w + tilt_x, y + cell_h),
                QPointF(x + tilt_x, y + cell_h),
            ]
        )

    def _draw_block(
        self,
        painter: QPainter,
        top: QPolygonF,
        depth: float,
        top_color: QColor,
        front_color: QColor,
        side_color: QColor,
    ) -> None:
        p1 = top[1]
        p2 = top[2]
        p3 = top[3]

        front = QPolygonF(
            [
                p3,
                p2,
                QPointF(p2.x(), p2.y() + depth),
                QPointF(p3.x(), p3.y() + depth),
            ]
        )
        right = QPolygonF(
            [
                p1,
                p2,
                QPointF(p2.x(), p2.y() + depth),
                QPointF(p1.x(), p1.y() + depth),
            ]
        )

        painter.setPen(QPen(QColor("#222831"), 1))
        painter.setBrush(top_color)
        painter.drawPolygon(top)

        painter.setBrush(front_color)
        painter.drawPolygon(front)

        painter.setBrush(side_color)
        painter.drawPolygon(right)

    def _draw_exit_beacon(self, painter: QPainter, top: QPolygonF, cell_w: float) -> None:
        center_x, center_y = self._center_of_polygon(top)
        cube_size = cell_w * 0.17

        body = QRectF(
            center_x - cube_size * 0.5,
            center_y - cube_size * 1.2,
            cube_size,
            cube_size,
        )
        painter.setPen(QPen(QColor("#0D2F22"), 1))
        painter.setBrush(QColor("#38B871"))
        painter.drawRect(body)

        painter.setBrush(QColor(56, 184, 113, 48))
        painter.setPen(QPen(QColor(56, 184, 113, 70), 1))
        painter.drawEllipse(
            QRectF(
                center_x - cube_size * 1.1,
                center_y - cube_size * 1.6,
                cube_size * 2.2,
                cube_size * 1.1,
            )
        )

    def _draw_player_marker(
        self,
        painter: QPainter,
        origin_x: float,
        origin_y: float,
        cell_w: float,
        cell_h: float,
        tilt_x: float,
        row_skew_x: float,
        floor_depth: float,
    ) -> None:
        if self._player_pos is None:
            return

        row, col = self._player_pos
        x = origin_x + col * cell_w + row * row_skew_x
        y = origin_y + row * cell_h
        top = self._cell_top_polygon(x, y, cell_w, cell_h, tilt_x)

        center_x, center_y = self._center_of_polygon(top)
        scale = cell_w * 0.22

        self._draw_actor_shadow(painter, center_x, center_y, scale, floor_depth)

        body = QRectF(center_x - scale * 0.5, center_y - scale * 0.25, scale, scale * 0.68)
        head = QRectF(center_x - scale * 0.32, center_y - scale * 0.72, scale * 0.64, scale * 0.38)

        painter.setPen(QPen(QColor("#5A2B05"), 1))
        painter.setBrush(QColor(ACCENT_ORANGE))
        painter.drawRect(body)

        painter.setPen(QPen(QColor("#7A3F0C"), 1))
        painter.setBrush(QColor("#FFC38E"))
        painter.drawRect(head)

    def _draw_guardian_marker(
        self,
        painter: QPainter,
        origin_x: float,
        origin_y: float,
        cell_w: float,
        cell_h: float,
        tilt_x: float,
        row_skew_x: float,
        floor_depth: float,
    ) -> None:
        if self._guardian_pos is None:
            return

        row, col = self._guardian_pos
        x = origin_x + col * cell_w + row * row_skew_x
        y = origin_y + row * cell_h
        top = self._cell_top_polygon(x, y, cell_w, cell_h, tilt_x)

        center_x, center_y = self._center_of_polygon(top)
        scale = cell_w * 0.24

        self._draw_actor_shadow(painter, center_x, center_y, scale, floor_depth)

        body = QRectF(center_x - scale * 0.5, center_y - scale * 0.26, scale, scale * 0.7)
        head = QRectF(center_x - scale * 0.34, center_y - scale * 0.76, scale * 0.68, scale * 0.4)

        painter.setPen(QPen(QColor("#3A0D0D"), 1))
        painter.setBrush(QColor("#D45A5A"))
        painter.drawRect(body)

        painter.setPen(QPen(QColor("#331010"), 1))
        painter.setBrush(QColor("#E99A9A"))
        painter.drawRect(head)

        # Minimal blocky axe silhouette: one handle + one blade rectangle.
        handle = QRectF(center_x + scale * 0.36, center_y - scale * 0.58, scale * 0.14, scale * 0.92)
        blade = QRectF(center_x + scale * 0.50, center_y - scale * 0.66, scale * 0.36, scale * 0.28)

        painter.setPen(QPen(QColor("#2F1F0E"), 1))
        painter.setBrush(QColor("#8A5B2C"))
        painter.drawRect(handle)

        painter.setPen(QPen(QColor("#2B2F34"), 1))
        painter.setBrush(QColor("#BBC2CC"))
        painter.drawRect(blade)

    def _draw_actor_shadow(
        self,
        painter: QPainter,
        center_x: float,
        center_y: float,
        scale: float,
        floor_depth: float,
    ) -> None:
        shadow_rect = QRectF(
            center_x - scale * 0.52,
            center_y + floor_depth * 0.25,
            scale * 1.04,
            scale * 0.28,
        )
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.drawEllipse(shadow_rect)

    @staticmethod
    def _center_of_polygon(poly: QPolygonF) -> tuple[float, float]:
        center_x = sum(point.x() for point in poly) / max(1, len(poly))
        center_y = sum(point.y() for point in poly) / max(1, len(poly))
        return center_x, center_y


__all__ = ["MazeWidget"]
