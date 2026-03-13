"""Services that prepare dashboard-level data for the UI."""

from __future__ import annotations

from datetime import datetime

from app.db.database import DatabaseManager
from app.models.dashboard import DashboardMetrics, DueDeckStat


class DashboardService:
    """Provide dashboard metrics.

    Dashboard is treated as the app's home base, so values here should be grounded
    in actual learner data. We intentionally keep these metrics simple and honest
    until richer session-history analytics are introduced.
    """

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def get_metrics(self) -> DashboardMetrics:
        with self.database.connection() as conn:
            settings_row = conn.execute(
                "SELECT active_profile_id FROM settings_global WHERE id = 1"
            ).fetchone()
            active_profile_id = (
                int(settings_row["active_profile_id"])
                if settings_row and settings_row["active_profile_id"] is not None
                else None
            )

            active_profile_name: str | None = None
            if active_profile_id is not None:
                profile_row = conn.execute(
                    "SELECT id, name FROM profiles WHERE id = ?",
                    (active_profile_id,),
                ).fetchone()
                if profile_row is None:
                    # Self-heal stale setting when profile was deleted externally.
                    conn.execute(
                        """
                        UPDATE settings_global
                        SET active_profile_id = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                        """
                    )
                    active_profile_id = None
                else:
                    active_profile_name = str(profile_row["name"])

            if active_profile_id is None:
                return DashboardMetrics(
                    active_profile_id=None,
                    active_profile_name=None,
                    due_today_count=0,
                    tracked_questions_count=0,
                    average_mastery_score=0.0,
                    mastered_questions_count=0,
                    weak_questions_count=0,
                    total_reviews_count=0,
                    reviewed_today_count=0,
                    encouragement_key="dashboard.encouragement.no_profile",
                    top_due_decks=[],
                )

            due_now = self._count_due_questions_for_profile(conn, active_profile_id)
            stats = conn.execute(
                """
                SELECT
                    COUNT(*) AS tracked_questions,
                    COALESCE(AVG(mastery_score), 0) AS average_mastery,
                    COALESCE(SUM(CASE WHEN mastery_score >= 80 THEN 1 ELSE 0 END), 0) AS mastered_questions,
                    COALESCE(SUM(CASE WHEN mastery_score > 0 AND mastery_score < 40 THEN 1 ELSE 0 END), 0) AS weak_questions,
                    COALESCE(SUM(review_count), 0) AS total_reviews,
                    -- We count unique tracked questions touched today (not raw attempts),
                    -- because V1 stores only one progress row per question/profile.
                    COALESCE(SUM(CASE WHEN DATE(last_reviewed_at) = DATE('now') THEN 1 ELSE 0 END), 0) AS reviewed_today
                FROM question_progress
                WHERE profile_id = ?
                """,
                (active_profile_id,),
            ).fetchone()

            tracked_questions_count = int(stats["tracked_questions"]) if stats else 0
            average_mastery_score = round(float(stats["average_mastery"] or 0.0), 1) if stats else 0.0
            mastered_questions_count = int(stats["mastered_questions"]) if stats else 0
            weak_questions_count = int(stats["weak_questions"]) if stats else 0
            total_reviews_count = int(stats["total_reviews"]) if stats else 0
            reviewed_today_count = int(stats["reviewed_today"]) if stats else 0

            top_due_decks = self._list_top_due_decks(conn, active_profile_id, limit=3)
            encouragement_key = self._build_encouragement_key(
                due_today_count=due_now,
                total_reviews_count=total_reviews_count,
                reviewed_today_count=reviewed_today_count,
            )

        return DashboardMetrics(
            active_profile_id=active_profile_id,
            active_profile_name=active_profile_name,
            due_today_count=due_now,
            tracked_questions_count=tracked_questions_count,
            average_mastery_score=average_mastery_score,
            mastered_questions_count=mastered_questions_count,
            weak_questions_count=weak_questions_count,
            total_reviews_count=total_reviews_count,
            reviewed_today_count=reviewed_today_count,
            encouragement_key=encouragement_key,
            top_due_decks=top_due_decks,
        )

    def _count_due_questions_for_profile(self, conn, profile_id: int) -> int:
        as_of_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row = conn.execute(
            """
            SELECT COUNT(*) AS due_count
            FROM questions q
            LEFT JOIN question_progress qp
                ON qp.question_id = q.id
                AND qp.profile_id = ?
            WHERE qp.id IS NULL OR qp.next_due_at <= ?
            """,
            (profile_id, as_of_timestamp),
        ).fetchone()
        return int(row["due_count"]) if row else 0

    def _list_top_due_decks(
        self,
        conn,
        profile_id: int,
        limit: int = 3,
    ) -> list[DueDeckStat]:
        # This powers a lightweight urgency section on the dashboard without
        # introducing heavy analytics tables at this stage.
        as_of_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            """
            SELECT
                d.id AS deck_id,
                d.name AS deck_name,
                COUNT(*) AS due_count
            FROM questions q
            JOIN decks d ON d.id = q.deck_id
            LEFT JOIN question_progress qp
                ON qp.question_id = q.id
                AND qp.profile_id = ?
            WHERE qp.id IS NULL OR qp.next_due_at <= ?
            GROUP BY d.id, d.name
            HAVING due_count > 0
            ORDER BY due_count DESC, d.name ASC
            LIMIT ?
            """,
            (profile_id, as_of_timestamp, limit),
        ).fetchall()

        return [
            DueDeckStat(
                deck_id=int(row["deck_id"]),
                deck_name=str(row["deck_name"]),
                due_count=int(row["due_count"]),
            )
            for row in rows
        ]

    def _build_encouragement_key(
        self,
        due_today_count: int,
        total_reviews_count: int,
        reviewed_today_count: int,
    ) -> str:
        if total_reviews_count == 0:
            return "dashboard.encouragement.fresh_start"
        if due_today_count == 0 and reviewed_today_count > 0:
            return "dashboard.encouragement.caught_up_today"
        if due_today_count == 0:
            return "dashboard.encouragement.all_caught_up"
        if due_today_count <= 5:
            return "dashboard.encouragement.light_queue"
        if due_today_count <= 15:
            return "dashboard.encouragement.regular_queue"
        return "dashboard.encouragement.heavy_queue"
