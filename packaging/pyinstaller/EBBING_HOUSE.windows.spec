# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows EBBING_HOUSE desktop build.

We package in one-folder mode for reliability with PySide6:
- startup is usually faster than one-file extraction
- fewer surprises with antivirus and large Qt payloads
- easier support when users report missing DLL/resource issues
"""

from __future__ import annotations

import os
from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[1]
main_script = project_root / "main.py"

# Keep runtime resource layout stable so `app/core/paths.py` resolves assets
# identically in dev and in packaged mode.
datas = [
    (str(project_root / "assets" / "images"), "assets/images"),
    (str(project_root / "app" / "assets"), "app/assets"),
    (str(project_root / "app" / "i18n" / "locales"), "app/i18n/locales"),
]

# Audio imports are optional in source code; explicit hidden import keeps the
# packaged .exe behavior deterministic without bundling unnecessary submodules.
hiddenimports = ["PySide6.QtMultimedia"]

# Optional .ico path for Windows executable icon.
icon_env = os.environ.get("EBBING_HOUSE_WINDOWS_ICON", "").strip()
icon_path = Path(icon_env) if icon_env else None
windows_icon = str(icon_path) if icon_path and icon_path.exists() else None

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EBBING_HOUSE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=windows_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="EBBING_HOUSE",
)
