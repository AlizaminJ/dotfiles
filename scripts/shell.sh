#!/bin/bash
# Link portable shell settings while leaving existing private settings local.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

link_config() {
  local source="$1" target="$2" backup suffix=1
  [[ -f "$source" ]] || { echo "❌ Missing config: $source" >&2; exit 1; }
  mkdir -p "$(dirname "$target")"
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    echo "  ↪ $target already linked"
    return
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    backup="$target.bak"
    while [[ -e "$backup" || -L "$backup" ]]; do
      backup="$target.bak.$suffix"
      suffix=$((suffix + 1))
    done
    mv "$target" "$backup"
    echo "  ↪ Backed up $target to $backup"
  fi
  ln -s "$source" "$target"
}

echo "⚙️ Linking modular shell and terminal settings..."
link_config "$REPO_ROOT/shell/zshrc" "$HOME/.zshrc"
link_config "$REPO_ROOT/shell/starship.toml" "${XDG_CONFIG_HOME:-$HOME/.config}/starship.toml"
link_config "$REPO_ROOT/wezterm/wezterm.lua" "$HOME/.wezterm.lua"

echo "✅ Configs linked. Existing .zprofile, .zshenv, and .zshrc.local were left alone."
echo "  ↪ Move reviewed private aliases and environment setup from your .zshrc backup to ~/.zshrc.local."
echo "  ↪ Read docs/usage.md before opening a new shell; the old framework is not sourced automatically."
