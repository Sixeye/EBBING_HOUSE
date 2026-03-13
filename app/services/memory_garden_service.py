"""Data shaping service for the Memory Garden page."""

from __future__ import annotations

from datetime import datetime

from app.db.database import DatabaseManager
from app.models.memory_garden import MemoryGardenSnapshot, MemoryGardenTree


class MemoryGardenService:
    """Build profile-based garden snapshots from real SQLite progress data.

    We intentionally use a lightweight, explicit mapping instead of complex
    simulation. This keeps garden growth understandable for users and easy to
    evolve as new features (session history, mini-game effects) arrive.
    """

    MAX_TREES = 6

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def build_snapshot(self, profile_id: int | None) -> MemoryGardenSnapshot:
        if profile_id is None:
            return MemoryGardenSnapshot(
                profile_id=None,
                profile_name=None,
                trees=[],
                mood_key="memory_garden.mood.no_profile",
            )

        as_of = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        with self.database.connection() as conn:
            profile_row = conn.execute(
                "SELECT id, name FROM profiles WHERE id = ? LIMIT 1",
                (profile_id,),
            ).fetchone()
            if profile_row is None:
                return MemoryGardenSnapshot(
                    profile_id=None,
                    profile_name=None,
                    trees=[],
                    mood_key="memory_garden.mood.no_profile",
                )

            trophy_row = conn.execute(
                "SELECT COUNT(*) AS total FROM profile_trophies WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            trophies_unlocked = int(trophy_row["total"]) if trophy_row else 0

            rows = conn.execute(
                """
                SELECT
                    d.id AS deck_id,
                    d.name AS deck_name,
                    d.category AS category,
                    COUNT(q.id) AS total_questions,
                    COALESCE(SUM(CASE WHEN qp.id IS NOT NULL THEN 1 ELSE 0 END), 0) AS tracked_questions,
                    COALESCE(AVG(CASE WHEN qp.id IS NOT NULL THEN qp.mastery_score END), 0) AS average_mastery,
                    COALESCE(SUM(CASE WHEN qp.id IS NOT NULL AND qp.mastery_score >= 80 THEN 1 ELSE 0 END), 0) AS mastered_questions,
                    COALESCE(SUM(CASE WHEN qp.id IS NOT NULL AND qp.mastery_score < 40 THEN 1 ELSE 0 END), 0) AS weak_questions,
                    COALESCE(SUM(CASE WHEN qp.id IS NULL OR qp.next_due_at <= ? THEN 1 ELSE 0 END), 0) AS due_questions
                FROM decks d
                JOIN questions q ON q.deck_id = d.id
                LEFT JOIN question_progress qp
                    ON qp.question_id = q.id
                    AND qp.profile_id = ?
                GROUP BY d.id, d.name, d.category
                HAVING tracked_questions > 0
                ORDER BY tracked_questions DESC, average_mastery DESC, d.name ASC
                LIMIT ?
                """,
                (as_of, profile_id, self.MAX_TREES),
            ).fetchall()

        trees: list[MemoryGardenTree] = []
        for row in rows:
            tracked = int(row["tracked_questions"])
            mastered = int(row["mastered_questions"])
            weak = int(row["weak_questions"])
            due = int(row["due_questions"])
            avg_mastery = round(float(row["average_mastery"] or 0.0), 1)

            trunk_blocks = self._compute_trunk_blocks(tracked)
            foliage_blocks = self._compute_foliage_blocks(
                average_mastery=avg_mastery,
                tracked_questions=tracked,
                weak_questions=weak,
                due_questions=due,
            )
            health_state = self._compute_health_state(
                average_mastery=avg_mastery,
                tracked_questions=tracked,
                weak_questions=weak,
                due_questions=due,
            )
            accent_blocks = self._compute_accent_blocks(
                mastered_questions=mastered,
                average_mastery=avg_mastery,
                trophies_unlocked=trophies_unlocked,
            )

            trees.append(
                MemoryGardenTree(
                    deck_id=int(row["deck_id"]),
                    deck_name=str(row["deck_name"]),
                    category=str(row["category"]) if row["category"] else None,
                    tracked_questions=tracked,
                    mastered_questions=mastered,
                    weak_questions=weak,
                    due_questions=due,
                    average_mastery=avg_mastery,
                    trunk_blocks=trunk_blocks,
                    foliage_blocks=foliage_blocks,
                    accent_blocks=accent_blocks,
                    health_state=health_state,
                )
            )

        total_tracked = sum(item.tracked_questions for item in trees)
        total_due = sum(item.due_questions for item in trees)
        total_weak = sum(item.weak_questions for item in trees)
        avg_mastery = (
            round(sum(item.average_mastery for item in trees) / len(trees), 1)
            if trees
            else 0.0
        )

        return MemoryGardenSnapshot(
            profile_id=int(profile_row["id"]),
            profile_name=str(profile_row["name"]),
            trees=trees,
            total_tracked_questions=total_tracked,
            total_due_questions=total_due,
            total_weak_questions=total_weak,
            average_mastery_score=avg_mastery,
            trophies_unlocked=trophies_unlocked,
            mood_key=self._compute_mood_key(
                has_trees=bool(trees),
                total_due=total_due,
                total_tracked=total_tracked,
                average_mastery=avg_mastery,
            ),
        )

    def _compute_trunk_blocks(self, tracked_questions: int) -> int:
        # Trunk grows as tracking depth increases. We cap to keep trees readable
        # and avoid oversized drawings in compact desktop layouts.
        return max(2, min(8, 2 + tracked_questions // 5))

    def _compute_foliage_blocks(
        self,
        average_mastery: float,
        tracked_questions: int,
        weak_questions: int,
        due_questions: int,
    ) -> int:
        base = 1 + int(round(average_mastery / 20.0))  # 1..6 for mastery 0..100

        pressure_penalty = 0
        # Early trees (1-2 tracked questions) should not look punished too fast.
        if tracked_questions >= 3 and weak_questions > tracked_questions * 0.35:
            pressure_penalty += 1
        if tracked_questions >= 3 and due_questions > tracked_questions * 0.8:
            pressure_penalty += 1

        return max(1, min(7, base - pressure_penalty))

    def _compute_health_state(
        self,
        average_mastery: float,
        tracked_questions: int,
        weak_questions: int,
        due_questions: int,
    ) -> str:
        if tracked_questions <= 0:
            return "growing"
        if tracked_questions <= 2:
            return "growing"

        if average_mastery >= 75 and due_questions <= max(2, tracked_questions // 4):
            return "lush"

        if (
            average_mastery < 35
            or due_questions > tracked_questions * 1.2
            or weak_questions > tracked_questions * 0.5
        ):
            return "fragile"

        return "growing"

    def _compute_accent_blocks(
        self,
        mastered_questions: int,
        average_mastery: float,
        trophies_unlocked: int,
    ) -> int:
        accents = 0
        if average_mastery >= 75:
            accents += 1
        if mastered_questions >= 5:
            accents += 1
        if trophies_unlocked >= 5:
            accents += 1
        return max(0, min(3, accents))

    def _compute_mood_key(
        self,
        has_trees: bool,
        total_due: int,
        total_tracked: int,
        average_mastery: float,
    ) -> str:
        if not has_trees:
            return "memory_garden.mood.seed"
        if total_tracked < 3:
            return "memory_garden.mood.seed"

        if total_due == 0 and average_mastery >= 70:
            return "memory_garden.mood.flourishing"

        if total_tracked >= 6 and total_due > total_tracked * 0.6:
            return "memory_garden.mood.needs_care"

        return "memory_garden.mood.steady"


__all__ = ["MemoryGardenService"]
