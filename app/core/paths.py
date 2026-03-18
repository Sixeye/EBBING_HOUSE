"""Transitional compatibility shim for path helpers.

Phase 2A split path concerns into:
- `core.runtime.user_paths` (portable writable user data paths)
- `desktop_app.runtime.resource_paths` (desktop bundled resources / _MEIPASS)

This module intentionally re-exports the historical API so existing imports
continue to work during the incremental refactor.
"""

from core.runtime.user_paths import (
    get_app_data_dir,
    get_database_path,
    get_media_dir,
    resolve_media_reference,
)
from desktop_app.runtime.resource_paths import (
    PROJECT_ROOT,
    find_resource_path,
    get_app_asset_dir,
    get_locales_dir,
    get_project_asset_dir,
    get_resource_path,
    get_resource_root,
    is_bundled_runtime,
)

__all__ = [
    "PROJECT_ROOT",
    "is_bundled_runtime",
    "get_resource_root",
    "get_resource_path",
    "find_resource_path",
    "get_locales_dir",
    "get_app_asset_dir",
    "get_project_asset_dir",
    "get_app_data_dir",
    "get_database_path",
    "get_media_dir",
    "resolve_media_reference",
]

