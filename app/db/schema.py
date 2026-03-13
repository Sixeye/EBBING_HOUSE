"""SQLite schema bootstrap and lightweight migration helpers.

The goal of this module is to keep persistence simple today while making
future expansions (spaced repetition, session history, trophies) easy later.
"""

from __future__ import annotations

import sqlite3


# We keep table creation SQL close to migration helpers so schema changes
# remain easy to reason about in one place.
CREATE_PROFILES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    theme TEXT NOT NULL DEFAULT 'dark',
    grading_mode TEXT NOT NULL DEFAULT 'score_20',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_DECKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NULL,
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
);
"""

CREATE_SETTINGS_GLOBAL_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS settings_global (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    app_language TEXT NOT NULL DEFAULT 'en',
    default_theme TEXT NOT NULL DEFAULT 'dark',
    animations_enabled INTEGER NOT NULL DEFAULT 1,
    sounds_enabled INTEGER NOT NULL DEFAULT 1,
    active_profile_id INTEGER NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (active_profile_id) REFERENCES profiles(id) ON DELETE SET NULL
);
"""

CREATE_QUESTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    external_id TEXT,
    question_text TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT,
    choice_d TEXT,
    correct_answers TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'single_choice',
    explanation TEXT,
    question_image_path TEXT,
    explanation_image_path TEXT,
    difficulty INTEGER NOT NULL DEFAULT 1,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
);
"""

CREATE_QUESTION_PROGRESS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS question_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 0,
    consecutive_correct INTEGER NOT NULL DEFAULT 0,
    mastery_score REAL NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at TEXT,
    next_due_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, question_id),
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
"""

CREATE_TROPHIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trophies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name_en TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    description_en TEXT NOT NULL,
    description_fr TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    rarity TEXT NOT NULL DEFAULT 'common',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PROFILE_TROPHIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profile_trophies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    trophy_id INTEGER NOT NULL,
    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, trophy_id),
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (trophy_id) REFERENCES trophies(id) ON DELETE CASCADE
);
"""

CREATE_GAME_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS game_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NULL,
    mode TEXT NOT NULL,
    deck_id INTEGER NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    did_win INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER,
    wrong_count INTEGER,
    score_on_100 REAL,
    summary_text TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL,
    FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE SET NULL
);
"""


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create or migrate the minimal schema used by the app.

    We explicitly keep this migration style small and transparent.
    For this stage of the project we avoid adding external migration frameworks.
    """
    # During table rebuild operations we briefly disable FK checks. They are
    # re-enabled immediately after migration tasks complete.
    conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        _ensure_profiles_table(conn)
        _ensure_decks_table(conn)
        _ensure_settings_global_table(conn)
        _ensure_questions_table(conn)
        _ensure_question_progress_table(conn)
        _ensure_trophies_table(conn)
        _ensure_profile_trophies_table(conn)
        _ensure_game_runs_table(conn)
        _ensure_indexes(conn)
        _ensure_default_settings_row(conn)
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")


def _ensure_profiles_table(conn: sqlite3.Connection) -> None:
    required_columns = {
        "id",
        "name",
        "language",
        "theme",
        "grading_mode",
        "created_at",
        "updated_at",
    }
    columns = _table_columns(conn, "profiles")

    if not columns:
        conn.execute(CREATE_PROFILES_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    # Legacy table is automatically upgraded to the current shape.
    language_expr = _column_or_default(columns, ("language", "preferred_language"), "'en'")
    name_expr = _column_or_default(columns, ("name",), "'Profile'")
    theme_expr = _column_or_default(columns, ("theme",), "'dark'")
    grading_expr = _column_or_default(columns, ("grading_mode",), "'score_20'")
    created_expr = _column_or_default(columns, ("created_at",), "CURRENT_TIMESTAMP")
    updated_expr = _column_or_default(columns, ("updated_at",), "CURRENT_TIMESTAMP")

    conn.execute("ALTER TABLE profiles RENAME TO profiles_legacy;")
    conn.execute(CREATE_PROFILES_TABLE_SQL)
    conn.execute(
        f"""
        INSERT INTO profiles (
            id, name, language, theme, grading_mode, created_at, updated_at
        )
        SELECT
            id,
            {name_expr},
            {language_expr},
            {theme_expr},
            {grading_expr},
            {created_expr},
            {updated_expr}
        FROM profiles_legacy
        """
    )
    conn.execute("DROP TABLE profiles_legacy;")


def _ensure_decks_table(conn: sqlite3.Connection) -> None:
    required_columns = {
        "id",
        "profile_id",
        "name",
        "category",
        "description",
        "created_at",
        "updated_at",
    }
    columns = _table_columns(conn, "decks")

    if not columns:
        conn.execute(CREATE_DECKS_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    profile_expr = _column_or_default(columns, ("profile_id",), "NULL")
    name_expr = _column_or_default(columns, ("name", "title"), "'Untitled deck'")
    category_expr = _column_or_default(columns, ("category",), "'General'")
    description_expr = _column_or_default(columns, ("description",), "NULL")
    created_expr = _column_or_default(columns, ("created_at",), "CURRENT_TIMESTAMP")
    updated_expr = _column_or_default(columns, ("updated_at",), "CURRENT_TIMESTAMP")

    conn.execute("ALTER TABLE decks RENAME TO decks_legacy;")
    conn.execute(CREATE_DECKS_TABLE_SQL)
    conn.execute(
        f"""
        INSERT INTO decks (
            id, profile_id, name, category, description, created_at, updated_at
        )
        SELECT
            id,
            {profile_expr},
            {name_expr},
            {category_expr},
            {description_expr},
            {created_expr},
            {updated_expr}
        FROM decks_legacy
        """
    )
    conn.execute("DROP TABLE decks_legacy;")


def _ensure_settings_global_table(conn: sqlite3.Connection) -> None:
    required_columns = {
        "id",
        "app_language",
        "default_theme",
        "animations_enabled",
        "sounds_enabled",
        "active_profile_id",
        "created_at",
        "updated_at",
    }
    columns = _table_columns(conn, "settings_global")

    if not columns:
        conn.execute(CREATE_SETTINGS_GLOBAL_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    app_language = "en"
    default_theme = "dark"
    animations_enabled = 1
    sounds_enabled = 1
    active_profile_id: int | None = None

    # Support migration from the previous key/value settings table.
    if {"key", "value"}.issubset(columns):
        app_language = _read_legacy_setting(conn, "language", app_language)
        default_theme = _read_legacy_setting(conn, "theme", default_theme)
        animations_enabled = _as_sqlite_bool(
            _read_legacy_setting(conn, "animations_enabled", "1"), default=1
        )
        sounds_enabled = _as_sqlite_bool(
            _read_legacy_setting(conn, "sounds_enabled", "1"), default=1
        )
        active_profile_id = _coerce_optional_int(
            _read_legacy_setting(conn, "active_profile_id", "")
        )
    else:
        if "app_language" in columns:
            row = conn.execute("SELECT app_language FROM settings_global LIMIT 1").fetchone()
            if row and row[0]:
                app_language = str(row[0])
        if "default_theme" in columns:
            row = conn.execute("SELECT default_theme FROM settings_global LIMIT 1").fetchone()
            if row and row[0]:
                default_theme = str(row[0])
        if "active_profile_id" in columns:
            row = conn.execute("SELECT active_profile_id FROM settings_global LIMIT 1").fetchone()
            if row and row[0] is not None:
                active_profile_id = _coerce_optional_int(row[0])

    # Migration safety: clear stale ids if profile row no longer exists.
    if active_profile_id is not None:
        exists = conn.execute(
            "SELECT 1 FROM profiles WHERE id = ? LIMIT 1",
            (active_profile_id,),
        ).fetchone()
        if exists is None:
            active_profile_id = None

    conn.execute("ALTER TABLE settings_global RENAME TO settings_global_legacy;")
    conn.execute(CREATE_SETTINGS_GLOBAL_TABLE_SQL)
    conn.execute(
        """
        INSERT INTO settings_global (
            id, app_language, default_theme, animations_enabled, sounds_enabled, active_profile_id
        )
        VALUES (1, ?, ?, ?, ?, ?)
        """,
        (app_language, default_theme, animations_enabled, sounds_enabled, active_profile_id),
    )
    conn.execute("DROP TABLE settings_global_legacy;")


def _ensure_questions_table(conn: sqlite3.Connection) -> None:
    required_columns = {
        "id",
        "deck_id",
        "external_id",
        "question_text",
        "choice_a",
        "choice_b",
        "choice_c",
        "choice_d",
        "correct_answers",
        "mode",
        "explanation",
        "question_image_path",
        "explanation_image_path",
        "difficulty",
        "tags",
        "created_at",
        "updated_at",
    }
    columns = _table_columns(conn, "questions")

    if not columns:
        conn.execute(CREATE_QUESTIONS_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    # If question schema changes in future, this block keeps backward data safe.
    deck_expr = _column_or_default(columns, ("deck_id",), "NULL")
    external_expr = _column_or_default(columns, ("external_id",), "NULL")
    text_expr = _column_or_default(columns, ("question_text",), "''")
    a_expr = _column_or_default(columns, ("choice_a",), "''")
    b_expr = _column_or_default(columns, ("choice_b",), "''")
    c_expr = _column_or_default(columns, ("choice_c",), "NULL")
    d_expr = _column_or_default(columns, ("choice_d",), "NULL")
    correct_expr = _column_or_default(columns, ("correct_answers",), "''")
    mode_expr = _column_or_default(columns, ("mode",), "'single_choice'")
    explanation_expr = _column_or_default(columns, ("explanation",), "NULL")
    question_image_expr = _column_or_default(columns, ("question_image_path",), "NULL")
    explanation_image_expr = _column_or_default(columns, ("explanation_image_path",), "NULL")
    difficulty_expr = _column_or_default(columns, ("difficulty",), "1")
    tags_expr = _column_or_default(columns, ("tags",), "NULL")
    created_expr = _column_or_default(columns, ("created_at",), "CURRENT_TIMESTAMP")
    updated_expr = _column_or_default(columns, ("updated_at",), "CURRENT_TIMESTAMP")

    conn.execute("ALTER TABLE questions RENAME TO questions_legacy;")
    conn.execute(CREATE_QUESTIONS_TABLE_SQL)
    conn.execute(
        f"""
        INSERT INTO questions (
            id,
            deck_id,
            external_id,
            question_text,
            choice_a,
            choice_b,
            choice_c,
            choice_d,
            correct_answers,
            mode,
            explanation,
            question_image_path,
            explanation_image_path,
            difficulty,
            tags,
            created_at,
            updated_at
        )
        SELECT
            id,
            {deck_expr},
            {external_expr},
            {text_expr},
            {a_expr},
            {b_expr},
            {c_expr},
            {d_expr},
            {correct_expr},
            {mode_expr},
            {explanation_expr},
            {question_image_expr},
            {explanation_image_expr},
            {difficulty_expr},
            {tags_expr},
            {created_expr},
            {updated_expr}
        FROM questions_legacy
        WHERE {deck_expr} IS NOT NULL
        """
    )
    conn.execute("DROP TABLE questions_legacy;")


def _ensure_question_progress_table(conn: sqlite3.Connection) -> None:
    """Create/migrate per-profile per-question progress state.

    This table is the first persistence brick for spaced repetition.
    It stays intentionally small while providing due-date scheduling hooks.
    """
    required_columns = {
        "id",
        "profile_id",
        "question_id",
        "interval_days",
        "consecutive_correct",
        "mastery_score",
        "review_count",
        "correct_count",
        "last_reviewed_at",
        "next_due_at",
        "created_at",
        "updated_at",
    }
    columns = _table_columns(conn, "question_progress")

    if not columns:
        conn.execute(CREATE_QUESTION_PROGRESS_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    # Defensive migration: preserve common data and fill missing fields with
    # deterministic defaults. This keeps the migration idempotent and safe.
    profile_expr = _column_or_default(columns, ("profile_id",), "NULL")
    question_expr = _column_or_default(columns, ("question_id",), "NULL")
    interval_expr = _column_or_default(columns, ("interval_days",), "0")
    consecutive_expr = _column_or_default(columns, ("consecutive_correct",), "0")
    mastery_expr = _column_or_default(columns, ("mastery_score",), "0")
    review_expr = _column_or_default(columns, ("review_count",), "0")
    correct_expr = _column_or_default(columns, ("correct_count",), "0")
    last_reviewed_expr = _column_or_default(columns, ("last_reviewed_at",), "NULL")
    next_due_expr = _column_or_default(columns, ("next_due_at",), "CURRENT_TIMESTAMP")
    created_expr = _column_or_default(columns, ("created_at",), "CURRENT_TIMESTAMP")
    updated_expr = _column_or_default(columns, ("updated_at",), "CURRENT_TIMESTAMP")

    conn.execute("ALTER TABLE question_progress RENAME TO question_progress_legacy;")
    conn.execute(CREATE_QUESTION_PROGRESS_TABLE_SQL)
    conn.execute(
        f"""
        INSERT INTO question_progress (
            id,
            profile_id,
            question_id,
            interval_days,
            consecutive_correct,
            mastery_score,
            review_count,
            correct_count,
            last_reviewed_at,
            next_due_at,
            created_at,
            updated_at
        )
        SELECT
            id,
            {profile_expr},
            {question_expr},
            {interval_expr},
            {consecutive_expr},
            {mastery_expr},
            {review_expr},
            {correct_expr},
            {last_reviewed_expr},
            {next_due_expr},
            {created_expr},
            {updated_expr}
        FROM question_progress_legacy
        WHERE {profile_expr} IS NOT NULL AND {question_expr} IS NOT NULL
        """
    )
    conn.execute("DROP TABLE question_progress_legacy;")


def _ensure_trophies_table(conn: sqlite3.Connection) -> None:
    """Create/migrate trophy definition table.

    We keep a fixed set of built-in trophies for V1, so a simple table with
    localized labels is enough and easy to maintain.
    """
    required_columns = {
        "id",
        "code",
        "name_en",
        "name_fr",
        "description_en",
        "description_fr",
        "category",
        "rarity",
        "created_at",
    }
    columns = _table_columns(conn, "trophies")

    if not columns:
        conn.execute(CREATE_TROPHIES_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    id_expr = _column_or_default(columns, ("id",), "NULL")
    code_expr = _column_or_default(columns, ("code",), "''")
    name_en_expr = _column_or_default(columns, ("name_en", "name"), "'Trophy'")
    name_fr_expr = _column_or_default(columns, ("name_fr",), name_en_expr)
    description_en_expr = _column_or_default(columns, ("description_en", "description"), "''")
    description_fr_expr = _column_or_default(columns, ("description_fr",), description_en_expr)
    category_expr = _column_or_default(columns, ("category",), "'general'")
    rarity_expr = _column_or_default(columns, ("rarity",), "'common'")
    created_expr = _column_or_default(columns, ("created_at",), "CURRENT_TIMESTAMP")

    conn.execute("ALTER TABLE trophies RENAME TO trophies_legacy;")
    conn.execute(CREATE_TROPHIES_TABLE_SQL)
    conn.execute(
        f"""
        INSERT OR IGNORE INTO trophies (
            id,
            code,
            name_en,
            name_fr,
            description_en,
            description_fr,
            category,
            rarity,
            created_at
        )
        SELECT
            {id_expr},
            {code_expr},
            {name_en_expr},
            {name_fr_expr},
            {description_en_expr},
            {description_fr_expr},
            {category_expr},
            {rarity_expr},
            {created_expr}
        FROM trophies_legacy
        WHERE TRIM({code_expr}) <> ''
        """
    )
    conn.execute("DROP TABLE trophies_legacy;")


def _ensure_profile_trophies_table(conn: sqlite3.Connection) -> None:
    """Create/migrate profile trophy unlock table.

    Unlock rows are profile-scoped so achievements remain learner-specific.
    """
    required_columns = {
        "id",
        "profile_id",
        "trophy_id",
        "unlocked_at",
    }
    columns = _table_columns(conn, "profile_trophies")

    if not columns:
        conn.execute(CREATE_PROFILE_TROPHIES_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    id_expr = _column_or_default(columns, ("id",), "NULL")
    profile_expr = _column_or_default(columns, ("profile_id",), "NULL")
    trophy_expr = _column_or_default(columns, ("trophy_id",), "NULL")
    unlocked_expr = _column_or_default(columns, ("unlocked_at",), "CURRENT_TIMESTAMP")

    conn.execute("ALTER TABLE profile_trophies RENAME TO profile_trophies_legacy;")
    conn.execute(CREATE_PROFILE_TROPHIES_TABLE_SQL)
    # `INSERT OR IGNORE` keeps migration idempotent if duplicate unlock rows
    # existed before we added the UNIQUE(profile_id, trophy_id) constraint.
    conn.execute(
        f"""
        INSERT OR IGNORE INTO profile_trophies (
            id,
            profile_id,
            trophy_id,
            unlocked_at
        )
        SELECT
            {id_expr},
            {profile_expr},
            {trophy_expr},
            {unlocked_expr}
        FROM profile_trophies_legacy
        WHERE {profile_expr} IS NOT NULL
          AND {trophy_expr} IS NOT NULL
          AND EXISTS (SELECT 1 FROM profiles p WHERE p.id = {profile_expr})
          AND EXISTS (SELECT 1 FROM trophies t WHERE t.id = {trophy_expr})
        """
    )
    conn.execute("DROP TABLE profile_trophies_legacy;")


def _ensure_game_runs_table(conn: sqlite3.Connection) -> None:
    """Create/migrate lightweight game run history rows.

    We only store completed runs for personal learning history. This keeps
    schema compact now while still enabling future analytics.
    """
    required_columns = {
        "id",
        "profile_id",
        "mode",
        "deck_id",
        "started_at",
        "ended_at",
        "did_win",
        "correct_count",
        "wrong_count",
        "score_on_100",
        "summary_text",
        "created_at",
    }
    columns = _table_columns(conn, "game_runs")

    if not columns:
        conn.execute(CREATE_GAME_RUNS_TABLE_SQL)
        return
    if required_columns.issubset(columns):
        return

    id_expr = _column_or_default(columns, ("id",), "NULL")
    profile_expr = _column_or_default(columns, ("profile_id",), "NULL")
    mode_expr = _column_or_default(columns, ("mode",), "'unknown'")
    deck_expr = _column_or_default(columns, ("deck_id",), "NULL")
    started_expr = _column_or_default(columns, ("started_at",), "CURRENT_TIMESTAMP")
    ended_expr = _column_or_default(columns, ("ended_at",), "CURRENT_TIMESTAMP")
    did_win_expr = _column_or_default(columns, ("did_win",), "0")
    correct_expr = _column_or_default(columns, ("correct_count",), "NULL")
    wrong_expr = _column_or_default(columns, ("wrong_count",), "NULL")
    score_expr = _column_or_default(columns, ("score_on_100",), "NULL")
    summary_expr = _column_or_default(columns, ("summary_text",), "NULL")
    created_expr = _column_or_default(columns, ("created_at",), "CURRENT_TIMESTAMP")
    safe_profile_expr = (
        f"CASE WHEN {profile_expr} IS NOT NULL "
        f"AND EXISTS (SELECT 1 FROM profiles p WHERE p.id = {profile_expr}) "
        f"THEN {profile_expr} ELSE NULL END"
    )
    safe_deck_expr = (
        f"CASE WHEN {deck_expr} IS NOT NULL "
        f"AND EXISTS (SELECT 1 FROM decks d WHERE d.id = {deck_expr}) "
        f"THEN {deck_expr} ELSE NULL END"
    )

    conn.execute("ALTER TABLE game_runs RENAME TO game_runs_legacy;")
    conn.execute(CREATE_GAME_RUNS_TABLE_SQL)
    conn.execute(
        f"""
        INSERT INTO game_runs (
            id,
            profile_id,
            mode,
            deck_id,
            started_at,
            ended_at,
            did_win,
            correct_count,
            wrong_count,
            score_on_100,
            summary_text,
            created_at
        )
        SELECT
            {id_expr},
            {safe_profile_expr},
            {mode_expr},
            {safe_deck_expr},
            {started_expr},
            {ended_expr},
            {did_win_expr},
            {correct_expr},
            {wrong_expr},
            {score_expr},
            {summary_expr},
            {created_expr}
        FROM game_runs_legacy
        WHERE TRIM({mode_expr}) <> ''
        """
    )
    conn.execute("DROP TABLE game_runs_legacy;")


def _ensure_default_settings_row(conn: sqlite3.Connection) -> None:
    """Keep exactly one settings row for global app preferences."""
    conn.execute(
        """
        INSERT OR IGNORE INTO settings_global (
            id, app_language, default_theme, animations_enabled, sounds_enabled, active_profile_id
        )
        VALUES (1, 'en', 'dark', 1, 1, NULL)
        """
    )


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    """Create minimal indexes that support current query patterns."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decks_profile_id ON decks(profile_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_questions_deck_id ON questions(deck_id);")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_questions_external_id ON questions(external_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_qp_profile_due ON question_progress(profile_id, next_due_at);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_qp_question_id ON question_progress(question_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_profile_trophies_profile_id ON profile_trophies(profile_id);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_profile_trophies_unlocked_at ON profile_trophies(unlocked_at);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_runs_profile_mode_ended ON game_runs(profile_id, mode, ended_at DESC);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_runs_ended_at ON game_runs(ended_at DESC);"
    )


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    return {str(row[1]) for row in rows}


def _column_or_default(columns: set[str], candidates: tuple[str, ...], default: str) -> str:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return default


def _read_legacy_setting(conn: sqlite3.Connection, key: str, default: str) -> str:
    row = conn.execute("SELECT value FROM settings_global WHERE key = ? LIMIT 1", (key,)).fetchone()
    if not row or row[0] is None:
        return default
    return str(row[0])


def _as_sqlite_bool(value: str, default: int = 1) -> int:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return 1
    if normalized in {"0", "false", "no", "off"}:
        return 0
    return default


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
