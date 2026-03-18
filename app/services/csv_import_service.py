"""Compatibility wrapper for ``CsvImportService``.

Phase 4D.1 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.csv_import_service`)
stable during the transition.
"""

from core.services.csv_import_service import CsvImportService

__all__ = ["CsvImportService"]

