"""Compatibility wrapper for legacy ``app.db.schema`` imports.

This module mirrors ``app.db.database`` wrapper rationale:
it provides a concrete import target for packaged builds while canonical
implementation lives in ``core.persistence.sqlite.schema``.
"""

from core.persistence.sqlite.schema import initialize_schema

__all__ = ["initialize_schema"]

