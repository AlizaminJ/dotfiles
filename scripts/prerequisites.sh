#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/usr/local/bin:/usr/local/sbin:$PATH"
case "$(uname -s)" in
  Darwin) ;;
  Linux)
    for tool in curl git; do
      command -v "$tool" >/dev/null 2>&1 || { echo "❌ Install $tool with your package manager first; Homebrew needs it." >&2; exit 1; }
    done
    ;;
  *) echo "❌ Setup requires macOS or Linux." >&2; exit 1 ;;
esac

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
