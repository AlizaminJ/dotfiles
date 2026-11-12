#!/bin/bash
# Fetch reviewed plugin pins with Antidote; never run this from shell startup.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MANIFEST="$REPO_ROOT/shell/plugins.txt"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/plugins.zsh"
export ANTIDOTE_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/antidote"

for tool in zsh git python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "❌ Required tool missing: $tool" >&2; exit 1; }
done
if [[ -z "${ANTIDOTE_ZSH:-}" ]]; then
  command -v brew >/dev/null 2>&1 || { echo "❌ Install reviewed Antidote first." >&2; exit 1; }
  ANTIDOTE_ZSH="$(brew --prefix antidote)/share/antidote/antidote.zsh"
fi
[[ -r "$ANTIDOTE_ZSH" ]] || { echo "❌ Antidote not found: $ANTIDOTE_ZSH" >&2; exit 1; }

# Reviewed 2026-11-09; Antidote 2.3.0 was published 2026-08-07.
# These dates were verified against upstream GitHub commits during code review.
python3 - "$MANIFEST" << 'PY'
import datetime, pathlib, sys
reviewed = {
    ('zsh-users/zsh-autosuggestions', '85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5'): '2025-06-24T16:15:03+00:00',
    ('zsh-users/zsh-syntax-highlighting', 'e6683f20e5c38d3e5447f45845d04ddda75d0f23'): '2026-10-09T17:16:49+00:00',
}
cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    if not line.strip() or line.lstrip().startswith('#'):
        continue
    parts = line.split()
    if len(parts) != 2 or not parts[1].startswith('pin:'):
        sys.exit('Unpinned plugin: review and pin an immutable commit before installing.')
    key = parts[0], parts[1][4:]
    if key not in reviewed or datetime.datetime.fromisoformat(reviewed[key]) > cutoff:
        sys.exit('Plugin pin has not passed source review and the 7-day minimum age.')
PY

mkdir -p "$(dirname "$CACHE")"
TEMP="$(mktemp "${CACHE}.new.XXXXXX")"
trap 'rm -f "$TEMP" "$TEMP.manifest"' EXIT

echo "🔒 Preparing pinned shell plugins with Antidote..."
# bundle prints a load script; unlike load, it does not execute plugin code.
GIT_TERMINAL_PROMPT=0 zsh -f -c '
  source "$1"
  [[ $(antidote --version) == "antidote version 2.3.0"* ]] || {
    print -u2 "Antidote version needs review; this setup was checked with 2.3.0."
    exit 1
  }
  zstyle ":antidote:bundle:*" shallow yes
  zstyle ":antidote:bundle:*" min-age 7
  antidote bundle < "$2"
' -- "$ANTIDOTE_ZSH" "$MANIFEST" > "$TEMP"

# Verify the downloaded trees before making their load script active.
while read -r repo pin extra; do
  [[ -z "$repo" || "$repo" == \#* ]] && continue
  [[ -z "${extra:-}" ]] || exit 1
  revision="${pin#pin:}"
  plugin_dir="$(zsh -f -c 'source "$1"; antidote path "$2"' -- "$ANTIDOTE_ZSH" "$repo")"
  [[ "$(git -C "$plugin_dir" rev-parse HEAD)" == "$revision" ]] || { echo "❌ Plugin revision mismatch" >&2; exit 1; }
  [[ -z "$(git -C "$plugin_dir" status --porcelain)" ]] || { echo "❌ Plugin has local modifications" >&2; exit 1; }
  [[ ! -e "$plugin_dir/.gitmodules" ]] || { echo "❌ Plugin submodules require a separate review" >&2; exit 1; }
done < "$MANIFEST"

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
echo "✅ Shell plugin cache prepared; no plugin code is stored in the dotfiles repo."
