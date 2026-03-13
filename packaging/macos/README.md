macOS packaging flow for EBBING_HOUSE
====================================

This directory contains a practical macOS packaging flow that produces:

1. `EBBING_HOUSE.app`
2. `EBBING_HOUSE-macOS.dmg`

Files
-----

- `build_macos_app.sh`
  Builds the `.app` bundle with PyInstaller.
- `create_dmg.sh`
  Builds a drag-to-Applications DMG from an existing `.app`.
- `build_release.sh`
  Runs both steps in sequence.
- `generate_icns.sh`
  Generates a `.icns` icon from `assets/images/EBBING_HOUSE_APP.png`.

What gets bundled
-----------------

The PyInstaller spec bundles these runtime resources:

- `assets/images`
- `app/assets`
- `app/i18n/locales`

That covers:

- branding PNG and splash image
- dashboard branding image
- audio assets
- trophy badge PNGs if added later
- locale JSON files

Build outputs
-------------

- `.app`: `dist/macos/EBBING_HOUSE.app`
- `.dmg`: `dist/macos/EBBING_HOUSE-macOS.dmg`

Prerequisites
-------------

Required:

- macOS
- `python3`
- PyInstaller installed for that Python

Used if available:

- `sips`
- `iconutil`
- `hdiutil`

Notes:

- `sips`, `iconutil`, and `hdiutil` are standard macOS command-line tools.
- If `sips` or `iconutil` is unavailable, the `.app` can still be built, but
  it may not get the custom `.icns` icon.
- `hdiutil` is required to produce the `.dmg`.

Exact commands
--------------

Build the `.app` only:

```bash
./packaging/macos/build_macos_app.sh
```

Build the `.dmg` from an existing `.app`:

```bash
./packaging/macos/create_dmg.sh
```

Build both:

```bash
./packaging/macos/build_release.sh
```

Optional code signing note
--------------------------

For local testing or informal sharing, unsigned builds may be enough.

For broader macOS distribution, you will usually want:

1. code-sign the `.app`
2. notarize it with Apple
3. optionally sign the `.dmg`

That is intentionally left out here so the first packaging flow stays simple
and reproducible.
