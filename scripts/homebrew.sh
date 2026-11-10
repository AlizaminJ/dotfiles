#!/bin/bash
# Homebrew has no native release-age setting; check exact recipes before installing.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:?REPO_ROOT must be set}"

if ! command -v brew >/dev/null 2>&1; then
  echo "❌ Homebrew is missing. Its installer needs an immutable-source and age review first." >&2
  echo "  ↪ Do not bypass the 7-day policy with a floating curl | bash installer." >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 is required for Homebrew dependency age checks." >&2
  exit 1
fi

echo "🔒 Checking new Homebrew packages and runtime dependencies..."
python3 "$REPO_ROOT/scripts/brew-packages.py" "$REPO_ROOT/Brewfile" --install

echo "✅ Homebrew setup complete! Existing packages were not upgraded or removed."
