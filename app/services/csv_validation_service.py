"""Compatibility wrapper for ``CsvValidationService``.

Phase 4D.1 moved the canonical implementation to ``core.services``.
This shim keeps historical imports (`app.services.csv_validation_service`)
stable during the transition.
"""

from core.services.csv_validation_service import CsvValidationService

__all__ = ["CsvValidationService"]

