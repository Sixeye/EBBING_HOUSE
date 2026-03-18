"""Reusable widgets for the EBBING_HOUSE UI."""

from desktop_app.ui.widgets.question_card import QuestionCardWidget
from desktop_app.ui.widgets.session_summary_card import SessionSummaryCardWidget
from desktop_app.ui.widgets.background_music_controller import BackgroundMusicController
from desktop_app.ui.widgets.connect4_widget import Connect4Widget
from desktop_app.ui.widgets.game_start_fx import GameStartFxController
from desktop_app.ui.widgets.hangman_widget import HangmanWidget
from desktop_app.ui.widgets.maze_widget import MazeWidget
from desktop_app.ui.widgets.memory_garden_widget import MemoryGardenWidget
from desktop_app.ui.widgets.toast import ToastManager, ToastWidget
from desktop_app.ui.widgets.startup_splash import StartupSplashWidget

__all__ = [
    "QuestionCardWidget",
    "SessionSummaryCardWidget",
    "BackgroundMusicController",
    "Connect4Widget",
    "GameStartFxController",
    "HangmanWidget",
    "MazeWidget",
    "MemoryGardenWidget",
    "ToastManager",
    "ToastWidget",
    "StartupSplashWidget",
]
