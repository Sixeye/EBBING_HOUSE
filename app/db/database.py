"""Low-level SQLite access and initialization."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.db.schema import initialize_schema


class DatabaseManager:
    """Centralized SQLite connection manager.

    This class keeps all SQLite setup details (path, row factory, foreign keys)
    in one place so repositories can stay focused on queries.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a transactional SQLite connection."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Initialize all required tables and apply simple migrations."""
        with self.connection() as conn:
            initialize_schema(conn)
