"""Lightweight i18n consistency audit for EBBING_HOUSE.

Run:
    python3 app/i18n/audit_locales.py

What it checks:
- translation keys used in Python code must exist in every locale file
- non-English locales should not silently keep English values for used keys,
  except for explicit product/format exceptions
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LOCALES_DIR = ROOT_DIR / "app" / "i18n" / "locales"
APP_DIR = ROOT_DIR / "app"

LOCALES = ("en", "fr", "de", "es", "pt")

# Intentional cross-locale constants:
# - brand/product names
# - compact formatting tokens where translation adds little value
SAME_AS_EN_ALLOWED = {
    "app.name",
    "nav.connect4",
    "nav.questions",
    "connect4_flow.limit_label",
    "connect4_flow.progress_text",
    "hangman_flow.limit_label",
    "hangman_flow.progress_text",
    "maze_flow.limit_label",
    "maze_flow.progress_text",
    "review_flow.limit_label",
    "review_flow.mode_label",
    "review_flow.progress_text",
    "review_flow.summary_score_20",
    "review_flow.summary_score_100",
    "maze_flow.difficulty_normal",
    "profiles_flow.profile_row",
    "review_flow.summary_avg_time_value",
    "dashboard.recent_runs_row",
    "history_flow.columns.mode",
    "history_flow.columns.score",
    "import_csv_flow.help.columns.description",
    "import_csv_flow.manual.mode",
    "import_csv_flow.manual.columns.id",
    "import_csv_flow.manual.columns.question",
    "import_csv_flow.manual.columns.mode",
    "import_csv_flow.manual.columns.tags",
    "import_csv_flow.preview_columns.question",
    "import_csv_flow.preview_columns.mode",
    "import_csv_flow.preview_columns.status",
}


def _flatten(data: object, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            dotted = f"{prefix}.{key}" if prefix else key
            out.update(_flatten(value, dotted))
        return out
    out[prefix] = data
    return out


def _used_translation_keys() -> set[str]:
    pattern = re.compile(r"""translator\.t\(\s*['"]([^'"]+)['"]""")
    keys: set[str] = set()
    for py_file in APP_DIR.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        keys.update(match.group(1) for match in pattern.finditer(text))
    return keys


def main() -> int:
    locale_data: dict[str, dict[str, object]] = {}
    for locale in LOCALES:
        locale_path = LOCALES_DIR / f"{locale}.json"
        locale_data[locale] = _flatten(json.loads(locale_path.read_text(encoding="utf-8")))

    used_keys = _used_translation_keys()
    failed = False

    print("=== Missing keys by locale ===")
    for locale in LOCALES:
        missing = sorted(key for key in used_keys if key not in locale_data[locale])
        print(f"{locale}: {len(missing)}")
        if missing:
            failed = True
            for key in missing[:25]:
                print(f"  - {key}")

    print("\n=== Same-as-English used keys (non-en locales) ===")
    en_map = locale_data["en"]
    for locale in ("fr", "de", "es", "pt"):
        same = sorted(
            key
            for key in used_keys
            if key not in SAME_AS_EN_ALLOWED
            and isinstance(en_map.get(key), str)
            and isinstance(locale_data[locale].get(key), str)
            and locale_data[locale][key] == en_map[key]
        )
        print(f"{locale}: {len(same)}")
        if same:
            failed = True
            for key in same[:25]:
                print(f"  - {key}")

    if failed:
        print("\nAudit result: FAILED")
        return 1

    print("\nAudit result: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
