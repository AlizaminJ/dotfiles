#!/bin/bash
# Linux only: install the latest WezTerm and JetBrainsMono Nerd Font, which macOS gets from casks.
# Resolves the latest stable release at install time; verifies the project's published SHA-256.
# User directories only: no sudo and no downloaded script is executed.
set -euo pipefail

if [[ "$(uname -s)" != Linux ]]; then
  echo "↪ Linux terminal apps skipped: not running on Linux."
  exit 0
fi
for tool in curl python3 tar; do
  command -v "$tool" >/dev/null 2>&1 || { echo "❌ $tool is required." >&2; exit 1; }
done

API="https://api.github.com/repos"
BIN_DIR="$HOME/.local/bin"
FONT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/JetBrainsMonoNerdFont"
STATE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dotfiles"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$BIN_DIR" "$STATE_DIR"

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# Print "tag asset-url checksum-url" for the latest stable release asset matching a regex.
latest_asset() {
  curl -fsSL "$API/$1/releases/latest" | python3 -c '
import json, re, sys
release = json.load(sys.stdin)
if release.get("prerelease") or release.get("draft"):
    sys.exit("Latest release is not stable")
assets = {a["name"]: a["browser_download_url"] for a in release["assets"]}
pattern, checksum = sys.argv[1], sys.argv[2]
names = [n for n in assets if re.fullmatch(pattern, n)]
if len(names) != 1:
    sys.exit("Expected exactly one matching asset, found %d" % len(names))
sums = checksum.replace("{name}", names[0])
if sums not in assets:
    sys.exit("No published checksum for " + names[0])
print(release["tag_name"], assets[names[0]], assets[sums])
' "$2" "$3"
}

# Download an asset and fail unless it matches the checksum the project published for it.
fetch_verified() {
  local url="$1" sums_url="$2" dest="$3" expected
  curl -fsSL -o "$dest" "$url"
  curl -fsSL -o "$dest.sums" "$sums_url"
  expected="$(awk -v n="$(basename "$url")" 'NF == 1 || $2 == n || $2 == "*" n {print $1; exit}' "$dest.sums")"
  [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || { echo "❌ No SHA-256 found for $(basename "$url")." >&2; return 1; }
  [[ "$(sha256 "$dest")" == "$(printf '%s' "$expected" | tr 'A-F' 'a-f')" ]] || { echo "❌ SHA-256 mismatch for $(basename "$url"); nothing installed." >&2; return 1; }
}

install_wezterm() {
  echo "⚙️ Checking WezTerm..."
  case "$(uname -m)" in
    x86_64) ;;
    *) echo "  ↪ WezTerm's official AppImage is x86_64 only; install WezTerm manually on $(uname -m)."; return 0 ;;
  esac
  local tag url sums_url found marker="$STATE_DIR/wezterm.version"
  found="$(latest_asset wezterm/wezterm '.*-Ubuntu20\.04\.AppImage' '{name}.sha256')"
  read -r tag url sums_url <<<"$found"
  if [[ -x "$BIN_DIR/wezterm" && -f "$marker" && "$(<"$marker")" == "$tag" ]]; then
    echo "  ↪ WezTerm $tag already installed"
    return 0
  fi
  fetch_verified "$url" "$sums_url" "$WORK/wezterm"
  chmod 755 "$WORK/wezterm"
  mv "$WORK/wezterm" "$BIN_DIR/wezterm"
  echo "$tag" > "$marker"
  echo "  ↪ WezTerm $tag installed to $BIN_DIR/wezterm (the AppImage needs FUSE 2, e.g. libfuse2)"
}

install_font() {
  echo "⚙️ Checking JetBrainsMono Nerd Font..."
  local tag url sums_url found marker="$STATE_DIR/jetbrains-mono-nerd-font.version"
  found="$(latest_asset ryanoasis/nerd-fonts 'JetBrainsMono\.tar\.xz' 'SHA-256.txt')"
  read -r tag url sums_url <<<"$found"
  if [[ -d "$FONT_DIR" && -f "$marker" && "$(<"$marker")" == "$tag" ]]; then
    echo "  ↪ JetBrainsMono Nerd Font $tag already installed"
    return 0
  fi
  fetch_verified "$url" "$sums_url" "$WORK/font.tar.xz"
  if tar -tf "$WORK/font.tar.xz" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
    echo "❌ Font archive contains unsafe paths; nothing installed." >&2
    return 1
  fi
  mkdir -p "$WORK/font"
  tar -xf "$WORK/font.tar.xz" -C "$WORK/font" --no-same-owner --no-same-permissions
  rm -rf "$FONT_DIR.new"
  mkdir -p "$FONT_DIR.new"
  find "$WORK/font" -type f \( -name '*.ttf' -o -name '*.otf' \) -exec cp {} "$FONT_DIR.new/" \;
  rm -rf "$FONT_DIR"
  mv "$FONT_DIR.new" "$FONT_DIR"
  echo "$tag" > "$marker"
  command -v fc-cache >/dev/null 2>&1 && fc-cache -f "$FONT_DIR" >/dev/null 2>&1 || true
  echo "  ↪ JetBrainsMono Nerd Font $tag installed to $FONT_DIR"
}

install_wezterm
install_font
echo "✅ Linux terminal apps ready."
