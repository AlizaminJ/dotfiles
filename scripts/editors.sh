#!/bin/bash
# Symlinks the Neovim and tmux configs from this repo into $HOME.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

backup_file() {
  local target="$1"
  local backup="$target.bak"
  local suffix=1

  while [[ -e "$backup" || -L "$backup" ]]; do
    backup="$target.bak.$suffix"
    suffix=$((suffix + 1))
  done
  mv "$target" "$backup"
  printf '  ↪ Backed up %s to %s\n' "$target" "$backup"
}

link() {
  local source="$1"
  local target="$2"

  [[ -e "$source" ]] || { printf 'Missing source: %s\n' "$source" >&2; exit 1; }
  mkdir -p "$(dirname "$target")"
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    printf '  ↪ %s already linked\n' "$target"
    return
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    backup_file "$target"
  fi
  ln -s "$source" "$target"
  printf '  ↪ Linked %s -> %s\n' "$target" "$source"
}

echo "⚙️ Linking Neovim and tmux configs..."
link "$REPO_ROOT/nvim" "$HOME/.config/nvim"
link "$REPO_ROOT/tmux/tmux.conf" "$HOME/.tmux.conf"

echo "✅ Editor and terminal configs linked!"
