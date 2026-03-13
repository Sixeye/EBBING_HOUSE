# Branding asset placement

Primary branding path (required):
- `assets/images/EBBING_HOUSE_APP.png`

Compatibility path (legacy, still supported):
- this folder (`app/assets/branding`)
- preferred names below

- `EBBING_HOUSE_APP.png`
- `ebbing_house_identity.png`

Custom names also work (`.png`, `.jpg`, `.jpeg`, `.webp`), but the preferred
name above keeps the project convention explicit.

The app automatically uses it for:

- sidebar/header logo
- dashboard brand banner
- support page brand mark
- window/app icon
- startup splash animation

Important for splash identity:
- `assets/images/EBBING_HOUSE_APP.png` is the canonical filename.
- When this exact file exists, the splash uses it as the primary identity asset
  (glasses shimmer + hourglass sand overlays are mapped for this artwork).

If the file is missing, the UI falls back to an internal pixel-style mark so
the app remains coherent and runnable.
