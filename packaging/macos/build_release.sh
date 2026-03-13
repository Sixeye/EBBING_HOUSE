#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper:
# 1) build the macOS .app
# 2) turn it into a drag-to-Applications .dmg

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/build_macos_app.sh"
"${SCRIPT_DIR}/create_dmg.sh"
