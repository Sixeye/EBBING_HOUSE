"""Semantic validation and normalization for parsed CSV question rows."""

from __future__ import annotations

import re

from core.models.csv_preview import (
    CsvNormalizedQuestion,
    CsvParsedData,
    CsvPreviewRow,
    CsvValidationIssue,
    CsvValidationResult,
)


class CsvValidationService:
    """Validate parsed CSV rows and normalize data for safe import."""

    # Canonical conventions used everywhere in the app:
    # - mode: single_choice / multiple_choice
    # - correct_answers separator: A|C
    MODE_SINGLE = "single_choice"
    MODE_MULTIPLE = "multiple_choice"
    CORRECT_ANSWERS_SEPARATOR = "|"

    REQUIRED_COLUMNS = {"question", "choice_a", "choice_b", "correct_answers"}
    OPTIONAL_COLUMNS = {"id", "category", "choice_c", "choice_d", "mode", "explanation", "difficulty", "tags"}
    ALLOWED_ANSWER_LETTERS = {"A", "B", "C", "D"}

    def validate(self, parsed: CsvParsedData) -> CsvValidationResult:
        result = CsvValidationResult(
            file_path=parsed.file_path,
            source_headers=parsed.source_headers,
        )

        # Carry parser issues forward so UI shows one consolidated report.
        result.issues.extend(parsed.issues)

        found_columns = self._detected_columns(parsed)
        missing_required = sorted(self.REQUIRED_COLUMNS.difference(found_columns))
        missing_optional = sorted(self.OPTIONAL_COLUMNS.difference(found_columns))

        for column in missing_required:
            result.issues.append(
                CsvValidationIssue(
                    row_number=None,
                    field=column,
                    message="Required column is missing from the CSV header.",
                    level="error",
                )
            )

        if missing_optional:
            joined = ", ".join(missing_optional)
            result.issues.append(
                CsvValidationIssue(
                    row_number=None,
                    field="header",
                    message=f"Optional columns missing ({joined}); defaults will be used.",
                    level="warning",
                )
            )

        # If required columns are absent, row-level validation is not reliable.
        if missing_required:
            return result

        for raw_row in parsed.rows:
            row_issues: list[CsvValidationIssue] = []
            normalized = self._validate_one_row(raw_row.values, raw_row.row_number, row_issues)

            preview_row = CsvPreviewRow(
                row_number=raw_row.row_number,
                raw_values=raw_row.values,
                normalized_question=normalized if not any(issue.is_error for issue in row_issues) else None,
                issues=row_issues,
            )

            result.preview_rows.append(preview_row)
            result.issues.extend(row_issues)

            if preview_row.is_valid and normalized is not None:
                result.valid_rows.append(normalized)
            else:
                result.invalid_rows.append(preview_row)

        return result

    def _validate_one_row(
        self,
        row: dict[str, str],
        row_number: int,
        issues: list[CsvValidationIssue],
    ) -> CsvNormalizedQuestion | None:
        question_text = row.get("question", "").strip()
        choice_a = row.get("choice_a", "").strip()
        choice_b = row.get("choice_b", "").strip()
        choice_c = row.get("choice_c", "").strip() or None
        choice_d = row.get("choice_d", "").strip() or None
        raw_correct_answers = row.get("correct_answers", "").strip()
        raw_mode = row.get("mode", "").strip()

        # We require A and B. C and D are optional to support true/false and
        # compact 2-choice questions while keeping A-D compatibility.
        if not question_text:
            issues.append(self._error(row_number, "question", "Question text cannot be empty."))
        if not choice_a:
            issues.append(self._error(row_number, "choice_a", "Choice A is required."))
        if not choice_b:
            issues.append(self._error(row_number, "choice_b", "Choice B is required."))

        normalized_answers = self._normalize_answers(raw_correct_answers)
        if not normalized_answers:
            issues.append(
                self._error(
                    row_number,
                    "correct_answers",
                    "At least one correct answer letter is required (A-D).",
                )
            )

        if any(letter not in self.ALLOWED_ANSWER_LETTERS for letter in normalized_answers):
            issues.append(
                self._error(
                    row_number,
                    "correct_answers",
                    "Only A, B, C, D are allowed in correct_answers.",
                )
            )

        available_letters = {"A", "B"}
        if choice_c:
            available_letters.add("C")
        if choice_d:
            available_letters.add("D")

        for letter in normalized_answers:
            if letter not in available_letters:
                issues.append(
                    self._error(
                        row_number,
                        "correct_answers",
                        f"Answer '{letter}' has no matching non-empty choice.",
                    )
                )

        mode = self._normalize_mode(raw_mode, normalized_answers, row_number, issues)
        if mode == self.MODE_SINGLE and len(normalized_answers) != 1:
            issues.append(
                self._error(
                    row_number,
                    "correct_answers",
                    "single_choice mode requires exactly one correct answer.",
                )
            )
        if mode == self.MODE_MULTIPLE and len(normalized_answers) < 1:
            issues.append(
                self._error(
                    row_number,
                    "correct_answers",
                    "multiple_choice mode requires at least one correct answer.",
                )
            )

        difficulty = self._normalize_difficulty(row.get("difficulty", ""), row_number, issues)

        if any(issue.is_error for issue in issues):
            return None

        return CsvNormalizedQuestion(
            row_number=row_number,
            external_id=row.get("id", "").strip() or None,
            category=row.get("category", "").strip() or None,
            question_text=question_text,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c,
            choice_d=choice_d,
            correct_answers=self.CORRECT_ANSWERS_SEPARATOR.join(normalized_answers),
            mode=mode,
            explanation=row.get("explanation", "").strip() or None,
            difficulty=difficulty,
            tags=row.get("tags", "").strip() or None,
        )

    def _normalize_mode(
        self,
        raw_mode: str,
        answers: list[str],
        row_number: int,
        issues: list[CsvValidationIssue],
    ) -> str:
        value = raw_mode.strip().lower().replace("-", "_").replace(" ", "_")
        single_aliases = {"single", "single_choice", "one", "unique", "solo"}
        multiple_aliases = {"multiple", "multiple_choice", "multi", "many", "checkbox"}

        if value in single_aliases:
            return self.MODE_SINGLE
        if value in multiple_aliases:
            return self.MODE_MULTIPLE

        # If mode is missing, infer it from number of answers and warn the user.
        if not value:
            inferred = self.MODE_MULTIPLE if len(answers) > 1 else self.MODE_SINGLE
            issues.append(
                CsvValidationIssue(
                    row_number=row_number,
                    field="mode",
                    message=f"Mode missing; inferred '{inferred}'.",
                    level="warning",
                )
            )
            return inferred

        issues.append(
            self._error(
                row_number,
                "mode",
                "Unsupported mode. Use single_choice/single or multiple_choice/multiple.",
            )
        )
        return self.MODE_SINGLE

    def _normalize_difficulty(
        self,
        raw_value: str,
        row_number: int,
        issues: list[CsvValidationIssue],
    ) -> int:
        value = raw_value.strip()
        if not value:
            return 1

        try:
            parsed = int(value)
        except ValueError:
            issues.append(self._error(row_number, "difficulty", "Difficulty must be an integer."))
            return 1

        if parsed < 1:
            issues.append(
                CsvValidationIssue(
                    row_number=row_number,
                    field="difficulty",
                    message="Difficulty below 1 was clamped to 1.",
                    level="warning",
                )
            )
            return 1
        if parsed > 5:
            issues.append(
                CsvValidationIssue(
                    row_number=row_number,
                    field="difficulty",
                    message="Difficulty above 5 was clamped to 5.",
                    level="warning",
                )
            )
            return 5
        return parsed

    def _normalize_answers(self, raw_value: str) -> list[str]:
        if not raw_value.strip():
            return []

        # Accept several separators so human-edited CSV files still work.
        tokens = [token.strip().upper() for token in re.split(r"[|,;/\s]+", raw_value.strip()) if token.strip()]

        # Preserve order while removing duplicates.
        seen: set[str] = set()
        normalized: list[str] = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            normalized.append(token)
        return normalized

    def _detected_columns(self, parsed: CsvParsedData) -> set[str]:
        return set(parsed.detected_fields)

    def _error(self, row_number: int, field: str, message: str) -> CsvValidationIssue:
        return CsvValidationIssue(row_number=row_number, field=field, message=message, level="error")
