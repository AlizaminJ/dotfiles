#!/bin/bash
# Run key setup explicitly; private keys and passphrases never enter local config.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# shellcheck source=scripts/config.sh
source "$REPO_ROOT/scripts/config.sh"
command -v ssh-keygen >/dev/null 2>&1 || { echo "❌ ssh-keygen is required." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 is required." >&2; exit 1; }
exec python3 "$REPO_ROOT/scripts/ssh-keys.py"
