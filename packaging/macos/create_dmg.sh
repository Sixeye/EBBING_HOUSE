#!/usr/bin/env bash
set -euo pipefail

# Create a simple drag-to-Applications DMG from an existing .app bundle.
# We use `hdiutil`, which ships with macOS, to avoid an extra packaging
# dependency such as create-dmg.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

APP_PATH="${1:-${PROJECT_ROOT}/dist/macos/EBBING_HOUSE.app}"
DMG_PATH="${2:-${PROJECT_ROOT}/dist/macos/EBBING_HOUSE-macOS.dmg}"
VOLUME_NAME="${VOLUME_NAME:-EBBING_HOUSE}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "DMG creation is macOS-only." >&2
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "Missing required macOS tool: hdiutil" >&2
  exit 1
fi

if [[ ! -d "${APP_PATH}" ]]; then
  echo "App bundle not found: ${APP_PATH}" >&2
  echo "Build the .app first with packaging/macos/build_macos_app.sh" >&2
  exit 1
fi

mkdir -p "$(dirname "${DMG_PATH}")"
STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ebh_dmg.XXXXXX")"
trap 'rm -rf "${STAGING_DIR}"' EXIT

cp -R "${APP_PATH}" "${STAGING_DIR}/"
ln -s /Applications "${STAGING_DIR}/Applications"
rm -f "${DMG_PATH}"

hdiutil create \
  -volname "${VOLUME_NAME}" \
  -srcfolder "${STAGING_DIR}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"

echo "DMG created:"
echo "  ${DMG_PATH}"
