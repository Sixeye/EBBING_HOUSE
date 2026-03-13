#!/usr/bin/env bash
set -euo pipefail

# Generate a macOS .icns file from the canonical branding PNG.
# We keep this separate from the PyInstaller spec so icon creation stays
# understandable and can be rerun independently when branding changes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SOURCE_PNG="${PROJECT_ROOT}/assets/images/EBBING_HOUSE_APP.png"
OUTPUT_ICNS="${1:-${PROJECT_ROOT}/build/macos/icon/EBBING_HOUSE.icns}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This icon generator is macOS-only because it uses sips/iconutil." >&2
  exit 1
fi

for tool in sips iconutil; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "Missing required macOS tool: ${tool}" >&2
    exit 1
  fi
done

if [[ ! -f "${SOURCE_PNG}" ]]; then
  echo "Branding PNG not found: ${SOURCE_PNG}" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUTPUT_ICNS}")"
ICONSET_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ebh_iconset.XXXXXX")"
trap 'rm -rf "${ICONSET_DIR}"' EXIT

# `iconutil` expects a directory ending with `.iconset`.
ICONSET_PATH="${ICONSET_DIR}.iconset"
mv "${ICONSET_DIR}" "${ICONSET_PATH}"
ICONSET_DIR="${ICONSET_PATH}"

# macOS iconsets require several fixed sizes. We derive all of them from the
# canonical PNG so the dock/app-switcher branding stays consistent.
for size in 16 32 128 256 512; do
  retina_size=$((size * 2))
  sips -z "${size}" "${size}" "${SOURCE_PNG}" \
    --out "${ICONSET_DIR}/icon_${size}x${size}.png" >/dev/null
  sips -z "${retina_size}" "${retina_size}" "${SOURCE_PNG}" \
    --out "${ICONSET_DIR}/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "${ICONSET_DIR}" -o "${OUTPUT_ICNS}"
echo "Generated macOS icon: ${OUTPUT_ICNS}"
