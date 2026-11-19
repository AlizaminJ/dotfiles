#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$PATH"
[[ "$(uname -s)" == Darwin ]] || { echo "❌ Setup requires macOS." >&2; exit 1; }

if ! command -v brew >/dev/null 2>&1; then
  echo "⚙️ Installing Homebrew..."
  INSTALLER="$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  /bin/bash -c "$INSTALLER"
fi
command -v brew >/dev/null 2>&1 || { echo "❌ Homebrew is not available after installation." >&2; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
  echo "⚙️ Installing uv through Homebrew..."
  brew install uv
fi

echo "⚙️ Installing Python through uv..."
uv python install --default

echo "✅ Prerequisites ready."
