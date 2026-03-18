"""Service layer for lightweight run history recording and reading."""

from __future__ import annotations

from datetime import datetime

from core.models.connect4_game import Connect4ChallengeSummary
from core.models.hangman_game import HangmanGameSummary
from core.models.maze_game import MazeChallengeSummary
from core.models.run_history import RunHistoryEntry, RunMode
from core.persistence.repositories.run_history_repository import RunHistoryRepository


class RunHistoryService:
    """Keep run history logic explicit and beginner-friendly.

    We only persist *completed* runs. This gives useful learner history
    without storing noisy partial gameplay telemetry.
    """

    def __init__(self, repository: RunHistoryRepository) -> None:
        self.repository = repository

    def list_recent_runs(
        self,
        *,
        limit: int = 20,
        profile_id: int | None = None,
        mode: RunMode | None = None,
    ) -> list[RunHistoryEntry]:
        return self.repository.list_recent(limit=limit, profile_id=profile_id, mode=mode)

    def record_hangman_completed(
        self,
        *,
        profile_id: int | None,
        deck_id: int | None,
        started_at: str | None,
        summary: HangmanGameSummary,
    ) -> RunHistoryEntry:
        ended_at = _utc_now_sql()
        return self.repository.create(
            profile_id=profile_id,
            mode="hangman",
            deck_id=deck_id,
            started_at=started_at or ended_at,
            ended_at=ended_at,
            did_win=summary.did_save,
            correct_count=summary.correct_answers_count,
            wrong_count=summary.wrong_answers_count,
            score_on_100=summary.score_on_100,
            summary_text=(
                f"{'saved' if summary.did_save else 'failed'};"
                f"danger={summary.wrong_answers_used};"
                f"remaining={summary.wrong_answers_remaining}"
            ),
        )

    def record_connect4_completed(
        self,
        *,
        profile_id: int | None,
        deck_id: int | None,
        started_at: str | None,
        summary: Connect4ChallengeSummary,
    ) -> RunHistoryEntry:
        ended_at = _utc_now_sql()
        result_label = "draw" if summary.did_draw else ("win" if summary.did_win else "loss")
        return self.repository.create(
            profile_id=profile_id,
            mode="connect4",
            deck_id=deck_id,
            started_at=started_at or ended_at,
            ended_at=ended_at,
            did_win=summary.did_win,
            correct_count=summary.correct_answers_count,
            wrong_count=summary.wrong_answers_count,
            score_on_100=summary.score_on_100,
            summary_text=(
                f"{result_label};"
                f"player={summary.player_moves};"
                f"opponent={summary.opponent_moves}"
            ),
        )

    def record_maze_completed(
        self,
        *,
        profile_id: int | None,
        deck_id: int | None,
        started_at: str | None,
        summary: MazeChallengeSummary,
    ) -> RunHistoryEntry:
        ended_at = _utc_now_sql()
        return self.repository.create(
            profile_id=profile_id,
            mode="maze",
            deck_id=deck_id,
            started_at=started_at or ended_at,
            ended_at=ended_at,
            did_win=summary.did_win,
            correct_count=summary.correct_answers_count,
            wrong_count=summary.wrong_answers_count,
            score_on_100=summary.score_on_100,
            summary_text=(
                f"{'win' if summary.did_win else 'loss'};"
                f"moves={summary.successful_moves};"
                f"mistakes={summary.mistakes_count};"
                f"walls={summary.wall_hits_count};"
                f"restarts={summary.guardian_restart_count}"
            ),
        )


def _utc_now_sql() -> str:
    """Return UTC timestamp in SQLite-friendly TEXT format."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


__all__ = ["RunHistoryService"]
