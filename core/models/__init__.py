"""Domain models used by the application."""

from core.models.deck import Deck
from core.models.connect4_game import (
    Connect4AnswerEvaluation,
    Connect4Cell,
    Connect4ChallengeState,
    Connect4ChallengeSummary,
    Connect4MoveRequest,
)
from core.models.maze_difficulty import (
    DEFAULT_MAZE_DIFFICULTY,
    MAZE_DIFFICULTY_PRESETS,
    MazeDifficultyCode,
    MazeDifficultyPreset,
)
from core.models.profile import Profile
from core.models.run_history import RunHistoryEntry, RunMode
from core.models.question_progress import QuestionProgress
from core.models.quiz_session import (
    QuestionAttempt,
    QuestionEvaluation,
    QuizSessionState,
    QuizSessionSummary,
)
from core.models.hangman_game import HangmanGameState, HangmanGameSummary
from core.models.memory_garden import MemoryGardenSnapshot, MemoryGardenTree
from core.models.maze_game import (
    MazeChallengeState,
    MazeChallengeSummary,
    MazeDirection,
    MazeGuardianTick,
    MazeLayout,
    MazeMoveEvaluation,
    MazeMoveRequest,
)
from core.models.question import Question
from core.models.settings import GlobalSettings
from core.models.trophy import Trophy
from core.models.profile_trophy import ProfileTrophy

__all__ = [
    "Deck",
    "Connect4Cell",
    "Connect4ChallengeState",
    "Connect4MoveRequest",
    "Connect4AnswerEvaluation",
    "Connect4ChallengeSummary",
    "Profile",
    "RunMode",
    "RunHistoryEntry",
    "Question",
    "QuestionProgress",
    "GlobalSettings",
    "Trophy",
    "ProfileTrophy",
    "QuestionAttempt",
    "QuestionEvaluation",
    "QuizSessionState",
    "QuizSessionSummary",
    "HangmanGameState",
    "HangmanGameSummary",
    "MazeDifficultyCode",
    "MazeDifficultyPreset",
    "DEFAULT_MAZE_DIFFICULTY",
    "MAZE_DIFFICULTY_PRESETS",
    "MazeDirection",
    "MazeLayout",
    "MazeMoveRequest",
    "MazeGuardianTick",
    "MazeChallengeState",
    "MazeMoveEvaluation",
    "MazeChallengeSummary",
    "MemoryGardenSnapshot",
    "MemoryGardenTree",
]
