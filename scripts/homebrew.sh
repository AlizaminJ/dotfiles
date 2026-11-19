#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:?REPO_ROOT must be set}"
command -v brew >/dev/null 2>&1 || { echo "❌ Run bash scripts/prerequisites.sh first." >&2; exit 1; }

echo "⚙️ Installing Brewfile packages with Homebrew..."
brew bundle --file="$REPO_ROOT/Brewfile"
echo "✅ Homebrew setup complete!"
