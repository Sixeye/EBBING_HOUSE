"""Compatibility wrapper for ``MazeGenerationService``.

Phase 4D.1 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.maze_generation_service`)
stable during the transition.
"""

from core.services.maze_generation_service import MazeGenerationService

__all__ = ["MazeGenerationService"]

