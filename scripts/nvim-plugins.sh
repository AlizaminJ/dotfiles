#!/bin/bash
# Install Neovim plugins only at the exact revisions pinned in nvim/nvim-pack-lock.json.
# Runs from bootstrap or on demand (dotfiles nvim-plugins); never from Neovim startup.
# No builds, Mason installs, or parser downloads happen here.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
LOCKFILE="${DOTFILES_NVIM_LOCK:-$REPO_ROOT/nvim/nvim-pack-lock.json}"
DEST_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/nvim/site/pack/core/opt"

command -v git >/dev/null 2>&1 || { echo "❌ git is required." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 is required." >&2; exit 1; }
[[ -f "$LOCKFILE" ]] || { echo "❌ Lockfile not found: $LOCKFILE" >&2; exit 1; }

# Same name and revision rules as nvim/lua/dotfiles/safety.lua; emits name, URL, revision.
PLUGINS="$(python3 - "$LOCKFILE" <<'PY'
import json, re, sys

plugins = json.load(open(sys.argv[1]))["plugins"]
for name, plugin in plugins.items():
    src, rev = plugin["src"], plugin["rev"]
    if not re.fullmatch(r"[\w.-]+", name) or name in (".", ".."):
        sys.exit(f"Invalid plugin name: {name!r}")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", rev):
        sys.exit(f"Invalid revision for {name}")
    url = re.sub(r"^ssh://git@github\.com/", "https://github.com/", src)
    url = re.sub(r"^git@github\.com:", "https://github.com/", url)
    if not url.startswith(("https://", "file://")):
        sys.exit(f"Unsupported source for {name}: {src}")
    print(f"{name} {url} {rev}")
PY
)"

echo "🔌 Installing pinned Neovim plugins..."
mkdir -p "$DEST_ROOT"
installed=0
while read -r name url rev; do
  dest="$DEST_ROOT/$name"
  if [[ -d "$dest/.git" && "$(git -C "$dest" rev-parse HEAD 2>/dev/null)" == "$rev" ]]; then
    echo "  ↪ $name already at ${rev:0:12}"
    continue
  fi
  if [[ -e "$dest" || -L "$dest" ]]; then
    echo "  ↪ $name exists with different content; leaving it untouched" >&2
    continue
  fi
  tmp="$(mktemp -d "$DEST_ROOT/.$name.XXXXXX")"
  if git clone --quiet --no-checkout "$url" "$tmp" \
      && git -C "$tmp" checkout --quiet --detach "$rev" \
      && [[ "$(git -C "$tmp" rev-parse HEAD)" == "$rev" ]]; then
    mv "$tmp" "$dest"
    installed=$((installed + 1))
    echo "  ↪ $name installed at ${rev:0:12}"
  else
    rm -rf "$tmp"
    echo "  ↪ $name failed; nothing was installed for it" >&2
    exit 1
  fi
done <<<"$PLUGINS"

echo "✅ Neovim plugins ready ($installed newly installed)."
