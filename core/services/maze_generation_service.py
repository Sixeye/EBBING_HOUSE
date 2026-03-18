"""Procedural maze generation for Maze Challenge.

We keep algorithmic complexity intentionally low for V1:
- depth-first recursive backtracker carving
- one connected solvable maze
- farthest reachable cell chosen as exit
- shortest path length computed via BFS
"""

from __future__ import annotations

import random
import uuid
from collections import deque

from core.models.maze_game import MazeLayout


class MazeGenerationService:
    """Generate lightweight rectangular mazes with start/exit metadata."""

    def __init__(self, width: int = 15, height: int = 11) -> None:
        # Backtracker carving works best on odd dimensions so each corridor can
        # be separated by one-cell-thick walls.
        self.width = self._ensure_odd(max(7, width))
        self.height = self._ensure_odd(max(7, height))

    def generate_layout(self, seed: int | None = None) -> MazeLayout:
        rng = random.Random(seed)

        grid = [["#" for _ in range(self.width)] for _ in range(self.height)]

        start = (1, 1)
        grid[start[0]][start[1]] = "."

        self._carve_recursive_backtracker(grid, start=start, rng=rng)

        distances = self._distances_from(grid, start)
        if not distances:
            raise ValueError("Generated maze has no traversable cells.")

        # Exit at the farthest traversable cell creates meaningful path length.
        exit_pos = max(distances.items(), key=lambda item: item[1])[0]
        shortest_path_length = int(distances[exit_pos])

        grid[start[0]][start[1]] = "S"
        grid[exit_pos[0]][exit_pos[1]] = "E"

        rows = tuple("".join(row) for row in grid)
        return MazeLayout(
            key=f"proc_{uuid.uuid4().hex[:8]}",
            rows=rows,
            start_pos=start,
            exit_pos=exit_pos,
            shortest_path_length=shortest_path_length,
        )

    def shortest_distance(
        self,
        layout: MazeLayout,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> int:
        """Compute shortest walkable distance between two positions."""
        distances = self._distances_from([list(row) for row in layout.rows], start)
        return int(distances.get(end, -1))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _carve_recursive_backtracker(
        self,
        grid: list[list[str]],
        start: tuple[int, int],
        rng: random.Random,
    ) -> None:
        stack = [start]

        while stack:
            row, col = stack[-1]
            neighbors = self._unvisited_neighbors_two_steps(grid, row, col)
            if not neighbors:
                stack.pop()
                continue

            next_row, next_col = rng.choice(neighbors)

            # Carve the wall between current cell and next cell.
            wall_row = row + (next_row - row) // 2
            wall_col = col + (next_col - col) // 2
            grid[wall_row][wall_col] = "."
            grid[next_row][next_col] = "."

            stack.append((next_row, next_col))

    def _unvisited_neighbors_two_steps(
        self,
        grid: list[list[str]],
        row: int,
        col: int,
    ) -> list[tuple[int, int]]:
        candidates: list[tuple[int, int]] = []
        height = len(grid)
        width = len(grid[0]) if height else 0
        for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            nr, nc = row + dr, col + dc
            if nr <= 0 or nc <= 0 or nr >= height - 1 or nc >= width - 1:
                continue
            if grid[nr][nc] == "#":
                candidates.append((nr, nc))
        return candidates

    def _distances_from(
        self,
        grid: list[list[str]],
        source: tuple[int, int],
    ) -> dict[tuple[int, int], int]:
        height = len(grid)
        width = len(grid[0]) if height else 0
        queue: deque[tuple[int, int]] = deque([source])
        distances: dict[tuple[int, int], int] = {source: 0}

        while queue:
            row, col = queue.popleft()
            for nr, nc in self._neighbors4(row, col):
                if nr < 0 or nc < 0 or nr >= height or nc >= width:
                    continue
                if (nr, nc) in distances:
                    continue
                if grid[nr][nc] not in {".", "S", "E"}:
                    continue
                distances[(nr, nc)] = distances[(row, col)] + 1
                queue.append((nr, nc))

        return distances

    @staticmethod
    def _neighbors4(row: int, col: int) -> tuple[tuple[int, int], ...]:
        return (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        )

    @staticmethod
    def _ensure_odd(value: int) -> int:
        return value if value % 2 == 1 else value + 1


__all__ = ["MazeGenerationService"]
