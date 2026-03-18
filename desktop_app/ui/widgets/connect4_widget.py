"""Custom-painted Connect Four board widget."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from desktop_app.themes.palette import ACCENT_ORANGE, BACKGROUND_SECONDARY, BORDER_SUBTLE, ERROR_RED


class Connect4Widget(QWidget):
    """Render a clean Connect Four board in the app's dark visual language."""

    def __init__(self) -> None:
        super().__init__()
        self._board: list[list[int]] = [[0 for _ in range(7)] for _ in range(6)]
        # Protect readability when parent layouts get tight while keeping the
        # board large enough to remain a primary game surface.
        self.setMinimumWidth(360)
        self.setMinimumHeight(300)
        # Preferred vertical policy keeps the board central without forcing
        # very tall page growth on stacked/small layouts.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        # Board should scale mostly by width; this avoids giant vertical growth.
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        # Base board ratio is 7x6 plus a little padding for frame aesthetics.
        target = int((width * 6 / 7) + 34)
        return max(self.minimumHeight(), min(target, 640))

    def sizeHint(self) -> QSize:  # type: ignore[override]
        base_width = 560
        return QSize(base_width, self.heightForWidth(base_width))

    def set_board(self, board: list[list[int]]) -> None:
        self._board = [list(row) for row in board] if board else []
        self.update()

    def reset(self, rows: int = 6, cols: int = 7) -> None:
        self._board = [[0 for _ in range(cols)] for _ in range(rows)]
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        width = self.width()
        height = self.height()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 8))
        painter.drawRoundedRect(4, 4, max(0, width - 8), max(0, height - 8), 12, 12)

        rows = len(self._board)
        cols = len(self._board[0]) if rows else 0
        if rows == 0 or cols == 0:
            return

        padding = 18
        available_w = max(10, width - (padding * 2))
        available_h = max(10, height - (padding * 2))

        # Keep a consistent board proportion (7 columns / 6 rows). Without
        # this, tall layouts can stretch discs and reduce gameplay readability.
        target_ratio = cols / rows
        if available_w / available_h > target_ratio:
            board_h = available_h
            board_w = int(board_h * target_ratio)
        else:
            board_w = available_w
            board_h = int(board_w / target_ratio)

        board_x = int((width - board_w) / 2)
        board_y = int((height - board_h) / 2)

        painter.setBrush(QColor(BACKGROUND_SECONDARY))
        painter.setPen(QColor(BORDER_SUBTLE))
        painter.drawRoundedRect(board_x, board_y, board_w, board_h, 14, 14)

        cell_w = board_w / cols
        cell_h = board_h / rows
        disc_diameter = int(min(cell_w, cell_h) * 0.68)

        for row in range(rows):
            for col in range(cols):
                cx = board_x + (col + 0.5) * cell_w
                cy = board_y + (row + 0.5) * cell_h
                x = int(cx - disc_diameter / 2)
                y = int(cy - disc_diameter / 2)

                value = self._board[row][col]
                if value == 1:
                    fill = QColor(ACCENT_ORANGE)
                elif value == 2:
                    fill = QColor(ERROR_RED)
                else:
                    fill = QColor(32, 34, 38)

                painter.setPen(QColor(BORDER_SUBTLE))
                painter.setBrush(fill)
                painter.drawEllipse(x, y, disc_diameter, disc_diameter)


__all__ = ["Connect4Widget"]
