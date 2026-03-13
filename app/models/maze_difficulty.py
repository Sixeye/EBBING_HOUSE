"""Maze Challenge difficulty presets.

The goal is to keep balancing explicit and readable:
- Easy / Normal / Hard are fixed presets
- each preset controls maze size and guardian pressure
- quiz rules remain unchanged regardless of difficulty
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MazeDifficultyCode = Literal["easy", "normal", "hard"]
DEFAULT_MAZE_DIFFICULTY: MazeDifficultyCode = "normal"


@dataclass(frozen=True)
class MazeDifficultyPreset:
    """Explicit preset values used by maze session orchestration."""

    code: MazeDifficultyCode
    maze_width: int
    maze_height: int
    guardian_tick_ms: int
    guardian_patrol_radius: int


MAZE_DIFFICULTY_PRESETS: dict[MazeDifficultyCode, MazeDifficultyPreset] = {
    # Easy: smaller navigation space and slower guardian pacing.
    "easy": MazeDifficultyPreset(
        code="easy",
        maze_width=13,
        maze_height=11,
        guardian_tick_ms=1200,
        guardian_patrol_radius=2,
    ),
    # Normal preserves the current baseline behavior.
    "normal": MazeDifficultyPreset(
        code="normal",
        maze_width=17,
        maze_height=13,
        guardian_tick_ms=900,
        guardian_patrol_radius=2,
    ),
    # Hard increases exploration depth and guardian pressure.
    "hard": MazeDifficultyPreset(
        code="hard",
        maze_width=21,
        maze_height=15,
        guardian_tick_ms=650,
        guardian_patrol_radius=3,
    ),
}


def get_maze_difficulty_preset(code: str | None) -> MazeDifficultyPreset:
    """Resolve incoming code safely with `normal` fallback."""
    if code in MAZE_DIFFICULTY_PRESETS:
        return MAZE_DIFFICULTY_PRESETS[code]
    return MAZE_DIFFICULTY_PRESETS[DEFAULT_MAZE_DIFFICULTY]


__all__ = [
    "MazeDifficultyCode",
    "MazeDifficultyPreset",
    "DEFAULT_MAZE_DIFFICULTY",
    "MAZE_DIFFICULTY_PRESETS",
    "get_maze_difficulty_preset",
]
