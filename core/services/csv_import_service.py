"""Low-level CSV parsing service used before semantic validation."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from core.models.csv_preview import CsvParsedData, CsvRawRow, CsvValidationIssue


class CsvImportService:
    """Read CSV files robustly and normalize headers/values.

    This service intentionally does *not* decide if data is pedagogically valid.
    It only parses, normalizes common formatting issues, and surfaces parse-level
    warnings/errors.
    """

    CANONICAL_FIELDS = (
        "id",
        "category",
        "question",
        "choice_a",
        "choice_b",
        "choice_c",
        "choice_d",
        "correct_answers",
        "mode",
        "explanation",
        "difficulty",
        "tags",
    )

    HEADER_ALIASES = {
        "id": {"id", "external_id", "question_id"},
        "category": {"category", "topic", "theme"},
        "question": {"question", "question_text", "prompt"},
        "choice_a": {"choice_a", "a", "option_a", "answer_a"},
        "choice_b": {"choice_b", "b", "option_b", "answer_b"},
        "choice_c": {"choice_c", "c", "option_c", "answer_c"},
        "choice_d": {"choice_d", "d", "option_d", "answer_d"},
        "correct_answers": {"correct_answers", "correct", "answer", "answers"},
        "mode": {"mode", "type", "question_type"},
        "explanation": {"explanation", "explain", "note"},
        "difficulty": {"difficulty", "level"},
        "tags": {"tags", "tag", "labels"},
    }

    def template_headers(self) -> tuple[str, ...]:
        """Expose canonical CSV headers used by parser+validator.

        Keeping headers centralized avoids drift between:
        - help/template generation
        - actual import parser expectations
        """
        return self.CANONICAL_FIELDS

    def save_template(
        self,
        file_path: str,
        *,
        include_example_row: bool = False,
        delimiter: str = ",",
    ) -> None:
        """Write a CSV template file with canonical headers.

        `include_example_row=True` adds one small valid demo row to help
        non-technical users start quickly.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, delimiter=delimiter)
            writer.writerow(self.template_headers())

            if include_example_row:
                # Example intentionally mirrors validator conventions:
                # - mode: single_choice / multiple_choice
                # - correct_answers separator: A|C
                writer.writerow(
                    [
                        "demo_001",
                        "general",
                        "Which options are vowels?",
                        "A",
                        "B",
                        "E",
                        "",
                        "A|C",
                        "multiple_choice",
                        "A and E are vowels.",
                        "1",
                        "demo,vowels",
                    ]
                )

    def parse_file(self, file_path: str) -> CsvParsedData:
        path = Path(file_path)
        if not path.exists():
            return CsvParsedData(
                file_path=file_path,
                source_headers=[],
                detected_delimiter=",",
                issues=[
                    CsvValidationIssue(
                        row_number=None,
                        field="file",
                        message="File does not exist.",
                        level="error",
                    )
                ],
            )

        try:
            text, encoding = self._read_with_fallback(path)
        except RuntimeError as exc:
            return CsvParsedData(
                file_path=file_path,
                source_headers=[],
                detected_delimiter=",",
                issues=[
                    CsvValidationIssue(
                        row_number=None,
                        field="file",
                        message=str(exc),
                        level="error",
                    )
                ],
            )

        delimiter = self._detect_delimiter(text)

        # StringIO keeps csv.reader behavior close to real files and preserves
        # accurate line counting via `reader.line_num` even with empty lines.
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        source_headers = [header.strip() for header in (reader.fieldnames or []) if header]
        mapped_headers = self._map_headers(source_headers)

        result = CsvParsedData(
            file_path=file_path,
            source_headers=source_headers,
            detected_delimiter=delimiter,
            detected_fields=sorted({value for value in mapped_headers.values() if value}),
        )

        if encoding != "utf-8-sig":
            result.issues.append(
                CsvValidationIssue(
                    row_number=None,
                    field="file",
                    message=f"File decoded using {encoding}.",
                    level="warning",
                )
            )

        if not source_headers:
            result.issues.append(
                CsvValidationIssue(
                    row_number=None,
                    field="header",
                    message="CSV header is missing.",
                    level="error",
                )
            )
            return result

        # Report duplicated canonical mappings, e.g. both `question` and `prompt`.
        duplicates = self._find_duplicate_mappings(mapped_headers)
        for canonical_name, incoming_names in duplicates.items():
            joined = ", ".join(incoming_names)
            result.issues.append(
                CsvValidationIssue(
                    row_number=None,
                    field=canonical_name,
                    message=f"Multiple columns map to '{canonical_name}': {joined}.",
                    level="warning",
                )
            )

        unknown_headers = [name for name, canonical in mapped_headers.items() if not canonical]
        for unknown in unknown_headers:
            result.issues.append(
                CsvValidationIssue(
                    row_number=None,
                    field=unknown,
                    message="Unknown column ignored.",
                    level="warning",
                )
            )

        try:
            for raw_row in reader:
                row_number = reader.line_num
                normalized_row = {field: "" for field in self.CANONICAL_FIELDS}

                for incoming_header, raw_value in raw_row.items():
                    if incoming_header is None:
                        continue

                    canonical_header = mapped_headers.get(incoming_header.strip(), "")
                    if not canonical_header:
                        continue

                    value = str(raw_value or "").strip()
                    if normalized_row[canonical_header]:
                        # Merge repeated mapped values gracefully instead of losing data.
                        normalized_row[canonical_header] = (
                            f"{normalized_row[canonical_header]} {value}".strip()
                        )
                    else:
                        normalized_row[canonical_header] = value

                # Skip visually empty lines so users can keep spacing in CSV files.
                if all(not value for value in normalized_row.values()):
                    continue

                result.rows.append(CsvRawRow(row_number=row_number, values=normalized_row))
        except csv.Error as exc:
            # Keep parser errors in the same issue pipeline shown by the UI.
            result.issues.append(
                CsvValidationIssue(
                    row_number=reader.line_num or None,
                    field="csv",
                    message=f"CSV parsing error: {exc}",
                    level="error",
                )
            )

        return result

    def _read_with_fallback(self, path: Path) -> tuple[str, str]:
        """Try common encodings because CSV files often come from Excel exports."""
        encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

        last_error: Exception | None = None
        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding), encoding
            except UnicodeDecodeError as exc:
                last_error = exc

        raise RuntimeError(f"Could not decode CSV file '{path}'.") from last_error

    def _detect_delimiter(self, text: str) -> str:
        sample = "\n".join(text.splitlines()[:5])
        if not sample.strip():
            return ","

        try:
            detected = csv.Sniffer().sniff(sample, delimiters=",;|\t")
            return detected.delimiter
        except csv.Error:
            # Comma remains the safest fallback for most CSV files.
            return ","

    def _map_headers(self, source_headers: list[str]) -> dict[str, str]:
        mapped: dict[str, str] = {}
        for header in source_headers:
            normalized = self._normalize_header(header)
            canonical = self._canonical_for(normalized)
            mapped[header] = canonical
        return mapped

    def _find_duplicate_mappings(self, mapped_headers: dict[str, str]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for original, canonical in mapped_headers.items():
            if not canonical:
                continue
            grouped.setdefault(canonical, []).append(original)

        return {key: value for key, value in grouped.items() if len(value) > 1}

    def _canonical_for(self, normalized_header: str) -> str:
        for canonical, aliases in self.HEADER_ALIASES.items():
            if normalized_header in aliases:
                return canonical
        return ""

    def _normalize_header(self, header: str) -> str:
        cleaned = header.strip().lower().replace("-", "_").replace(" ", "_")
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        return cleaned
