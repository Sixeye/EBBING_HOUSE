# EBBING_HOUSE

Dark-mode-first bilingual desktop learning app foundation built with Python, PySide6, and SQLite.

## Tech stack

- Python 3.12+
- PySide6
- SQLite (`sqlite3` from Python stdlib)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Notes

- Local database is automatically created in your OS application data directory:
  - macOS: `~/Library/Application Support/EBBING_HOUSE/ebbing_house.db`
  - Windows: `%APPDATA%/EBBING_HOUSE/ebbing_house.db`
- Current MVP includes architecture scaffolding, dashboard, placeholders, translation layer, and schema bootstrap.
