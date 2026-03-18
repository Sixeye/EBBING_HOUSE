"""Desktop filesystem adapter for question media references.

This module keeps concrete local-file handling (copying to app data storage)
out of the authoring business service so the service can become portable.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from core.runtime.user_paths import get_app_data_dir, get_media_dir


class DesktopQuestionMediaStorage:
    """Persist question media files under app-managed desktop storage."""

    def normalize_media_reference(self, source: str | None) -> str | None:
        """Normalize media reference for stable cross-machine persistence.

        Strategy:
        - if reference is already relative (managed), keep it
        - if reference is absolute external path, copy into app media dir
        - if file no longer exists, drop reference safely
        """
        if source is None:
            return None
        raw = source.strip()
        if not raw:
            return None

        raw_path = Path(raw)
        if not raw_path.is_absolute():
            return raw.replace("\\", "/")

        if not raw_path.exists() or not raw_path.is_file():
            return None

        media_dir = get_media_dir("questions")
        suffix = raw_path.suffix or ".img"
        target_name = f"{uuid4().hex}{suffix.lower()}"
        target_path = media_dir / target_name
        shutil.copy2(raw_path, target_path)

        # Persist relative path so data remains portable across environments.
        return str(target_path.relative_to(get_app_data_dir())).replace("\\", "/")


__all__ = ["DesktopQuestionMediaStorage"]

