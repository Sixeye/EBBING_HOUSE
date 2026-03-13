"""Profile-based trophy/badge service.

This module keeps reward logic explicit and lightweight on purpose:
- fixed built-in trophy definitions
- deterministic eligibility checks from real data
- idempotent unlock operations

We avoid a generic rule engine in V1 to keep behavior easy to read and teach.
"""

from __future__ import annotations

from app.models.quiz_session import QuizSessionSummary
from app.models.trophy import Trophy
from app.repositories.profile_trophy_repository import ProfileTrophyRepository
from app.repositories.question_progress_repository import QuestionProgressRepository
from app.repositories.trophy_repository import TrophyRepository


class TrophyService:
    """Coordinate trophy definition seeding and profile unlock logic."""

    DUE_SESSION_SOURCE = "due_today"
    MASTERED_THRESHOLD = 80.0

    def __init__(
        self,
        trophy_repository: TrophyRepository,
        profile_trophy_repository: ProfileTrophyRepository,
        progress_repository: QuestionProgressRepository,
    ) -> None:
        self.trophy_repository = trophy_repository
        self.profile_trophy_repository = profile_trophy_repository
        self.progress_repository = progress_repository

    def ensure_builtins(self) -> None:
        """Upsert fixed trophy definitions.

        Safe to call on every launch. Using upsert means we can tweak labels later
        without duplicating rows.
        """
        for definition in self._built_in_definitions():
            self.trophy_repository.upsert(definition)

    def list_unlocked_trophies(self, profile_id: int) -> list[Trophy]:
        return self.profile_trophy_repository.list_unlocked_trophies(profile_id)

    def list_locked_trophies(self, profile_id: int) -> list[Trophy]:
        return self.profile_trophy_repository.list_locked_trophies(profile_id)

    def unlocked_count(self, profile_id: int) -> int:
        return self.profile_trophy_repository.count_unlocked(profile_id)

    def total_trophies_count(self) -> int:
        return self.trophy_repository.count_all()

    def latest_unlocked_trophy(self, profile_id: int) -> Trophy | None:
        return self.profile_trophy_repository.latest_unlocked_trophy(profile_id)

    # ------------------------------------------------------------------
    # Event handlers used by UI/service workflows
    # ------------------------------------------------------------------
    def on_profile_created(self, profile_id: int) -> list[Trophy]:
        return self._unlock_codes(profile_id, ["first_profile_created"])

    def on_active_profile_set(self, profile_id: int | None) -> list[Trophy]:
        if profile_id is None:
            return []
        return self._unlock_codes(profile_id, ["first_active_profile_set"])

    def on_csv_import_completed(self, profile_id: int | None, imported_count: int) -> list[Trophy]:
        if profile_id is None or imported_count <= 0:
            return []
        return self._unlock_codes(profile_id, ["first_csv_import"])

    def on_due_answer_recorded(
        self,
        profile_id: int | None,
        question_id: int,
        was_correct: bool,
    ) -> list[Trophy]:
        """Evaluate per-answer trophy milestones in due mode.

        `question_id` is currently informational, but kept in the API for future
        question-specific trophies (for example "difficult question mastered").
        """
        if profile_id is None:
            return []
        _ = question_id

        codes: list[str] = []

        # Tracked/mastery milestones come from question_progress rows.
        tracked_questions = self.progress_repository.count_tracked_questions(profile_id)
        if tracked_questions >= 10:
            codes.append("ten_questions_tracked")

        mastered_questions = self.progress_repository.count_mastered_questions(
            profile_id,
            mastery_threshold=self.MASTERED_THRESHOLD,
        )
        if mastered_questions >= 1:
            codes.append("first_mastered_question")

        # Correct-answer milestones use persisted cumulative correct counters.
        # We check only after correct attempts to avoid unnecessary SQL calls.
        if was_correct:
            total_correct = self.progress_repository.sum_correct_answers(profile_id)
            if total_correct >= 5:
                codes.append("five_correct_answers")
            if total_correct >= 10:
                codes.append("ten_correct_answers")

        return self._unlock_codes(profile_id, codes)

    def on_review_session_completed(
        self,
        profile_id: int | None,
        summary: QuizSessionSummary,
        session_source: str,
    ) -> list[Trophy]:
        """Evaluate session-level trophies when summary is finalized."""
        if profile_id is None or summary.total_questions <= 0:
            return []

        codes = ["first_review_session_completed"]

        if session_source == self.DUE_SESSION_SOURCE:
            codes.append("first_due_session_completed")

            # "All caught up" should reflect true due state after the session,
            # based on profile-wide due counts (not just one deck).
            due_now = self.progress_repository.count_due_questions_for_profile(profile_id)
            if due_now == 0:
                codes.append("all_caught_up_once")

        # Re-check progression milestones at summary time as a safety net.
        # This keeps unlocks reliable even if per-answer hooks are skipped.
        tracked_questions = self.progress_repository.count_tracked_questions(profile_id)
        if tracked_questions >= 10:
            codes.append("ten_questions_tracked")

        mastered_questions = self.progress_repository.count_mastered_questions(
            profile_id,
            mastery_threshold=self.MASTERED_THRESHOLD,
        )
        if mastered_questions >= 1:
            codes.append("first_mastered_question")

        total_correct = self.progress_repository.sum_correct_answers(profile_id)
        if total_correct >= 5:
            codes.append("five_correct_answers")
        if total_correct >= 10:
            codes.append("ten_correct_answers")

        return self._unlock_codes(profile_id, codes)

    def on_hangman_session_completed(self, profile_id: int | None, did_win: bool) -> list[Trophy]:
        """Unlock hangman trophies from mini-game completion events."""
        if profile_id is None or not did_win:
            return []
        return self._unlock_codes(profile_id, ["first_hangman_win"])

    def on_maze_session_completed(self, profile_id: int | None, did_win: bool) -> list[Trophy]:
        """Unlock maze trophies from challenge completion events."""
        if profile_id is None or not did_win:
            return []
        return self._unlock_codes(profile_id, ["first_maze_completed"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _unlock_codes(self, profile_id: int, codes: list[str]) -> list[Trophy]:
        """Unlock multiple trophies safely and return newly unlocked ones only."""
        unlocked: list[Trophy] = []
        seen_codes: set[str] = set()

        for code in codes:
            normalized_code = code.strip()
            if not normalized_code or normalized_code in seen_codes:
                continue
            seen_codes.add(normalized_code)

            trophy = self._unlock_by_code(profile_id, normalized_code)
            if trophy is not None:
                unlocked.append(trophy)

        return unlocked

    def _unlock_by_code(self, profile_id: int, code: str) -> Trophy | None:
        trophy = self.trophy_repository.get_by_code(code)

        # Defensive self-heal: if schema was freshly migrated and seed has not
        # run yet, we seed once and retry lookup.
        if trophy is None:
            self.ensure_builtins()
            trophy = self.trophy_repository.get_by_code(code)

        if trophy is None or trophy.id is None:
            return None

        inserted = self.profile_trophy_repository.unlock(profile_id, trophy.id)
        if not inserted:
            return None

        # Return the latest unlocked row variant so UI can display unlocked_at.
        latest = self.profile_trophy_repository.latest_unlocked_trophy(profile_id)
        if latest and latest.code == code:
            return latest
        return trophy

    def _built_in_definitions(self) -> list[Trophy]:
        """Return fixed V1 trophy catalog.

        Names/descriptions are stored in DB as EN/FR fields so the same catalog
        can be displayed even outside JSON translation files.
        """
        return [
            Trophy(
                id=None,
                code="first_profile_created",
                name_en="First Learner",
                name_fr="Premier profil",
                description_en="Create your first learner profile.",
                description_fr="Creer ton premier profil apprenant.",
                category="onboarding",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_active_profile_set",
                name_en="Learner Selected",
                name_fr="Profil actif defini",
                description_en="Set a learner as the active profile.",
                description_fr="Definir un apprenant comme profil actif.",
                category="onboarding",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_csv_import",
                name_en="First Deck Imported",
                name_fr="Premier import CSV",
                description_en="Import your first CSV question set.",
                description_fr="Importer ton premier fichier CSV de questions.",
                category="content",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_review_session_completed",
                name_en="Session Starter",
                name_fr="Premiere session terminee",
                description_en="Complete your first review session.",
                description_fr="Terminer ta premiere session de revision.",
                category="sessions",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_due_session_completed",
                name_en="Due Queue Cleared Once",
                name_fr="Premiere session due terminee",
                description_en="Complete your first due-today session.",
                description_fr="Terminer ta premiere session due aujourd'hui.",
                category="sessions",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="five_correct_answers",
                name_en="5 Correct Answers",
                name_fr="5 bonnes reponses",
                description_en="Reach 5 correct answers in tracked due reviews.",
                description_fr="Atteindre 5 bonnes reponses en revisions dues suivies.",
                category="accuracy",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="ten_correct_answers",
                name_en="10 Correct Answers",
                name_fr="10 bonnes reponses",
                description_en="Reach 10 correct answers in tracked due reviews.",
                description_fr="Atteindre 10 bonnes reponses en revisions dues suivies.",
                category="accuracy",
                rarity="uncommon",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_mastered_question",
                name_en="First Mastered Question",
                name_fr="Premiere question maitrisee",
                description_en="Bring one question to mastery score 80+.",
                description_fr="Amener une question a un score de maitrise de 80+.",
                category="mastery",
                rarity="uncommon",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="ten_questions_tracked",
                name_en="10 Questions Tracked",
                name_fr="10 questions suivies",
                description_en="Track progress for 10 distinct questions.",
                description_fr="Suivre la progression de 10 questions distinctes.",
                category="mastery",
                rarity="uncommon",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="all_caught_up_once",
                name_en="All Caught Up",
                name_fr="Tout est a jour",
                description_en="Reach zero due questions once in due mode.",
                description_fr="Atteindre zero question due au moins une fois.",
                category="consistency",
                rarity="rare",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_hangman_win",
                name_en="First Hangman Win",
                name_fr="Premier defi pendu gagne",
                description_en="Win your first Hangman Challenge session.",
                description_fr="Gagner ta premiere session Defi Pendu.",
                category="mini_game",
                rarity="common",
                created_at=None,
            ),
            Trophy(
                id=None,
                code="first_maze_completed",
                name_en="First Maze Completed",
                name_fr="Premier labyrinthe termine",
                description_en="Reach the maze exit in Maze Challenge.",
                description_fr="Atteindre la sortie dans le Defi Labyrinthe.",
                category="mini_game",
                rarity="common",
                created_at=None,
            ),
        ]


__all__ = ["TrophyService"]
