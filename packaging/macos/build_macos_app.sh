#!/usr/bin/env bash
set -euo pipefail

# Build the macOS .app bundle with PyInstaller.
# This script is intentionally explicit so non-specialists can rerun it and
# understand which resources and outputs are involved.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
SPEC_FILE="${PROJECT_ROOT}/packaging/pyinstaller/EBBING_HOUSE.macos.spec"
DIST_DIR="${PROJECT_ROOT}/dist/macos"
WORK_DIR="${PROJECT_ROOT}/build/pyinstaller/macos"
ICON_PATH="${PROJECT_ROOT}/build/macos/icon/EBBING_HOUSE.icns"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script targets macOS only." >&2
  exit 1
fi

if [[ ! -f "${SPEC_FILE}" ]]; then
  echo "PyInstaller spec file not found: ${SPEC_FILE}" >&2
  exit 1
fi

if ! "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import PyInstaller  # noqa: F401
PY
then
  echo "PyInstaller is not installed for ${PYTHON_BIN}." >&2
  echo "Install it first, for example: ${PYTHON_BIN} -m pip install pyinstaller" >&2
  exit 1
fi

# Best-effort icon generation. If icon tools are unavailable we keep building,
# because the app bundle still works with the default app icon.
if [[ -f "${PROJECT_ROOT}/assets/images/EBBING_HOUSE_APP.png" ]]; then
  if "${PROJECT_ROOT}/packaging/macos/generate_icns.sh" "${ICON_PATH}" >/dev/null 2>&1; then
    export EBBING_HOUSE_MAC_ICON="${ICON_PATH}"
    echo "Using generated icon: ${EBBING_HOUSE_MAC_ICON}"
  else
    echo "Warning: could not generate macOS .icns icon. Building without custom .icns." >&2
  fi
fi

mkdir -p "${DIST_DIR}" "${WORK_DIR}"

"${PYTHON_BIN}" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "${DIST_DIR}" \
  --workpath "${WORK_DIR}" \
  "${SPEC_FILE}"

APP_PATH="${DIST_DIR}/EBBING_HOUSE.app"
if [[ ! -d "${APP_PATH}" ]]; then
  echo "Build finished but expected app bundle was not found: ${APP_PATH}" >&2
  exit 1
fi

echo "macOS app bundle created:"
echo "  ${APP_PATH}"
