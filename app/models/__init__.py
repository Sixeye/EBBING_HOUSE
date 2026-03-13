"""Domain models used by the application."""

from app.models.deck import Deck
from app.models.connect4_game import (
    Connect4AnswerEvaluation,
    Connect4Cell,
    Connect4ChallengeState,
    Connect4ChallengeSummary,
    Connect4MoveRequest,
)
from app.models.maze_difficulty import (
    DEFAULT_MAZE_DIFFICULTY,
    MAZE_DIFFICULTY_PRESETS,
    MazeDifficultyCode,
    MazeDifficultyPreset,
)
from app.models.profile import Profile
from app.models.run_history import RunHistoryEntry, RunMode
from app.models.question_progress import QuestionProgress
from app.models.quiz_session import (
    QuestionAttempt,
    QuestionEvaluation,
    QuizSessionState,
    QuizSessionSummary,
)
from app.models.hangman_game import HangmanGameState, HangmanGameSummary
from app.models.memory_garden import MemoryGardenSnapshot, MemoryGardenTree
from app.models.maze_game import (
    MazeChallengeState,
    MazeChallengeSummary,
    MazeDirection,
    MazeGuardianTick,
    MazeLayout,
    MazeMoveEvaluation,
    MazeMoveRequest,
)
from app.models.question import Question
from app.models.settings import GlobalSettings
from app.models.trophy import Trophy
from app.models.profile_trophy import ProfileTrophy

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
