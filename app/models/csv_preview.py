"""Typed models used by CSV parsing, validation, and preview workflows."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CsvRawRow:
    """One raw row parsed from the CSV file."""

    row_number: int
    values: dict[str, str]


@dataclass
class CsvValidationIssue:
    """A validation issue surfaced to the user with row+field context."""

    row_number: int | None
    field: str
    message: str
    level: str = "error"  # Allowed: "error" or "warning"

    @property
    def is_error(self) -> bool:
        return self.level == "error"

    @property
    def is_warning(self) -> bool:
        return self.level == "warning"


@dataclass
class CsvParsedData:
    """Result of low-level CSV parsing (before semantic validation)."""

    file_path: str
    source_headers: list[str]
    detected_delimiter: str
    detected_fields: list[str] = field(default_factory=list)
    rows: list[CsvRawRow] = field(default_factory=list)
    issues: list[CsvValidationIssue] = field(default_factory=list)


@dataclass
class CsvNormalizedQuestion:
    """Validated+normalized question payload ready for DB insertion."""

    row_number: int
    external_id: str | None
    category: str | None
    question_text: str
    choice_a: str
    choice_b: str
    choice_c: str | None
    choice_d: str | None
    correct_answers: str
    mode: str
    explanation: str | None
    difficulty: int
    tags: str | None


@dataclass
class CsvPreviewRow:
    """UI-facing preview row with validation status."""

    row_number: int
    raw_values: dict[str, str]
    normalized_question: CsvNormalizedQuestion | None
    issues: list[CsvValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(not issue.is_error for issue in self.issues)


@dataclass
class CsvValidationResult:
    """Complete validation output used by preview and import actions."""

    file_path: str
    source_headers: list[str]
    preview_rows: list[CsvPreviewRow] = field(default_factory=list)
    valid_rows: list[CsvNormalizedQuestion] = field(default_factory=list)
    invalid_rows: list[CsvPreviewRow] = field(default_factory=list)
    issues: list[CsvValidationIssue] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.preview_rows)

    @property
    def error_count(self) -> int:
        return len([issue for issue in self.issues if issue.is_error])

    @property
    def warning_count(self) -> int:
        return len([issue for issue in self.issues if issue.is_warning])

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0 and len(self.valid_rows) > 0
