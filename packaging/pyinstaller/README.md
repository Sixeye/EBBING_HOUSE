PyInstaller preparation notes for EBBING_HOUSE
=============================================

This project now resolves bundled resources through `app/core/paths.py`.
That means the code expects packaged read-only assets to keep the same
relative structure they have in the repository.

Required bundled resource targets
---------------------------------

When building with PyInstaller, include these directories as data files:

- `assets/images` -> `assets/images`
- `app/assets` -> `app/assets`
- `app/i18n/locales` -> `app/i18n/locales`

Why these paths matter
----------------------

- `assets/images/EBBING_HOUSE_APP.png`
  Canonical branding image used by splash + dashboard hero + icons.
- `app/assets/sounds`
  Bundled music and short 8-bit sound effects.
- `app/assets/badges`
  Optional future PNG trophy badges.
- `app/i18n/locales`
  JSON locale files loaded at runtime.

Example PyInstaller data flags
------------------------------

macOS / Linux:

```bash
--add-data "assets/images:assets/images" \
--add-data "app/assets:app/assets" \
--add-data "app/i18n/locales:app/i18n/locales"
```

Windows:

```bash
--add-data "assets/images;assets/images" ^
--add-data "app/assets;app/assets" ^
--add-data "app/i18n/locales;app/i18n/locales"
```

Runtime split
-------------

- Read-only bundled resources:
  resolved from the runtime resource root (`sys._MEIPASS` in PyInstaller)
- Writable user data:
  stored under the OS application data directory via `get_app_data_dir()`

This split is intentional: packaged apps must not try to write into their own
bundle directory.

macOS flow
----------

For the actual macOS `.app` + `.dmg` workflow, see:

- `packaging/pyinstaller/EBBING_HOUSE.macos.spec`
- `packaging/macos/README.md`
- `packaging/macos/build_macos_app.sh`
- `packaging/macos/create_dmg.sh`

Windows flow
------------

For the Windows `.exe` GitHub Actions flow, see:

- `.github/workflows/windows-build.yml`
- `packaging/pyinstaller/EBBING_HOUSE.windows.spec`
- `packaging/windows/build_windows_exe.ps1`
- `packaging/windows/README.md`
