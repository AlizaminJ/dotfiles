#!/bin/bash
# Configure pnpm's global supply-chain defaults without replacing unrelated settings.
set -euo pipefail

if ! command -v pnpm >/dev/null 2>&1; then
  echo "❌ pnpm is required. Install pnpm 12 or newer, then re-run this script." >&2
  exit 1
fi
VERSION="$(pnpm --version)"
if [[ "${VERSION%%.*}" -lt 12 ]]; then
  echo "❌ pnpm 12 or newer is required for these supply-chain settings (found $VERSION)." >&2
  exit 1
fi

echo "🔒 Configuring global pnpm supply-chain defaults..."
CONFIG="$(pnpm config get --global globalconfig)"
BACKED_UP=false

while read -r key value; do
  if [[ "$(pnpm config get --global "$key")" == "$value" ]]; then
    continue
  fi

  if [[ "$BACKED_UP" == false && -f "$CONFIG" ]]; then
    backup="$CONFIG.bak"
    suffix=1
    while [[ -e "$backup" || -L "$backup" ]]; do
      backup="$CONFIG.bak.$suffix"
      suffix=$((suffix + 1))
    done
    cp -p "$CONFIG" "$backup"
    echo "  ↪ Backed up $CONFIG to $backup"
    BACKED_UP=true
  fi

  pnpm config set --global "$key" "$value" --json
  echo "  ↪ $key=$value"
done << 'EOF'
minimumReleaseAge 10080
minimumReleaseAgeStrict true
minimumReleaseAgeIgnoreMissingTime false
trustLockfile false
ignoreScripts true
EOF

echo "✅ pnpm defaults configured (project settings can override global defaults)."
