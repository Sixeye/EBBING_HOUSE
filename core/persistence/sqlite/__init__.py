"""SQLite persistence layer (canonical namespace in phase 4B)."""

from core.persistence.sqlite.database import DatabaseManager
from core.persistence.sqlite.schema import initialize_schema

__all__ = ["DatabaseManager", "initialize_schema"]
