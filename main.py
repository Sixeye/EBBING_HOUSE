"""Backward-compatible root entry point.

Phase 1 keeps `python main.py` working while desktop startup logic
is moved under `desktop_app/`.
"""

from desktop_app.main import create_application, main

__all__ = ["create_application", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
