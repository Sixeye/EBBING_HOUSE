Windows packaging flow for EBBING_HOUSE
======================================

This flow builds a Windows PyInstaller package on GitHub Actions.
The output is a downloadable ZIP containing `EBBING_HOUSE.exe` and all required
runtime files.

Why GitHub Actions on Windows
-----------------------------

The project is developed on macOS, but Windows executables should be built on
an actual Windows runner for better compatibility and fewer packaging issues.

Workflow file
-------------

- `.github/workflows/windows-build.yml`

Build script used by CI
-----------------------

- `packaging/windows/build_windows_exe.ps1`

PyInstaller spec used by CI
---------------------------

- `packaging/pyinstaller/EBBING_HOUSE.windows.spec`

Bundled resources
-----------------

The Windows build includes:

- `assets/images` (branding + splash identity)
- `app/assets` (audio, badges, internal assets)
- `app/i18n/locales` (FR/EN/DE/ES/PT locale JSON files)

Expected artifact
-----------------

The workflow uploads:

- artifact name: `EBBING_HOUSE-windows-x64`
- artifact file: `dist/windows/EBBING_HOUSE-windows-x64.zip`

When users download and extract this ZIP, they can run:

- `EBBING_HOUSE.exe`

Optional local Windows build
----------------------------

On a Windows machine, you can run:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
./packaging/windows/build_windows_exe.ps1
```
