#!/bin/bash
# Configure uv without installing packages or running source builds.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SOURCE="$REPO_ROOT/uv/uv.toml"
TARGET="${XDG_CONFIG_HOME:-$HOME/.config}/uv/uv.toml"
[[ -f "$SOURCE" ]] || { echo "❌ Missing uv config: $SOURCE" >&2; exit 1; }
mkdir -p "$(dirname "$TARGET")"
if [[ -L "$TARGET" ]] && [[ "$(readlink "$TARGET")" == "$SOURCE" ]]; then
  echo "  ↪ uv preferences already linked"
  exit 0
fi
if [[ -e "$TARGET" || -L "$TARGET" ]]; then
  backup="$TARGET.bak"
  suffix=1
  while [[ -e "$backup" || -L "$backup" ]]; do
    backup="$TARGET.bak.$suffix"
    suffix=$((suffix + 1))
  done
  mv "$TARGET" "$backup"
  echo "  ↪ Backed up $TARGET to $backup"
fi
ln -s "$SOURCE" "$TARGET"
echo "✅ uv preferences linked (7-day minimum age; source builds disabled)."
