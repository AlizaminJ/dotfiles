#!/bin/bash
# Prepare plugins during setup, never during shell startup.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MANIFEST="$REPO_ROOT/shell/plugins.txt"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/plugins.zsh"
export ANTIDOTE_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/antidote"

command -v zsh >/dev/null 2>&1 || { echo "❌ Required tool missing: zsh" >&2; exit 1; }
if [[ -z "${ANTIDOTE_ZSH:-}" ]]; then
  ANTIDOTE_ZSH="$(brew --prefix antidote)/share/antidote/antidote.zsh"
fi
[[ -r "$ANTIDOTE_ZSH" ]] || { echo "❌ Antidote not found: $ANTIDOTE_ZSH" >&2; exit 1; }

mkdir -p "$(dirname "$CACHE")"
TEMP="$(mktemp "${CACHE}.new.XXXXXX")"
trap 'rm -f "$TEMP" "$TEMP.manifest"' EXIT

echo "⚙️ Preparing shell plugins with Antidote..."
# bundle prints a load script; unlike load, it does not execute plugin code.
GIT_TERMINAL_PROMPT=0 zsh -f -c '
  source "$1"
  antidote bundle < "$2"
' -- "$ANTIDOTE_ZSH" "$MANIFEST" > "$TEMP"

cksum < "$MANIFEST" > "$TEMP.manifest"
if [[ -f "$CACHE" ]] && cmp -s "$TEMP" "$CACHE"; then
  rm "$TEMP"
else
  mv "$TEMP" "$CACHE"
fi
if [[ -f "$CACHE.manifest" ]] && cmp -s "$TEMP.manifest" "$CACHE.manifest"; then
  rm "$TEMP.manifest"
else
  mv "$TEMP.manifest" "$CACHE.manifest"
fi
echo "✅ Shell plugin cache prepared; no startup downloads."
