#!/bin/bash
# Verify the app without launching it or changing Gatekeeper policy.
set -euo pipefail
export LC_ALL=C

APP="${1:-/Applications/WezTerm.app}"
if [[ "$#" -gt 1 || ! -d "$APP" || "$(uname -s)" != Darwin ]]; then
  echo "❌ Usage on macOS: bash scripts/verify-wezterm.sh [path/to/WezTerm.app]" >&2
  exit 1
fi

# Pin the developer identity checked against the official stable release.
codesign --verify --deep --strict \
  --test-requirement='=anchor apple generic and certificate leaf[subject.OU] = "P4A6FU9KZ3"' \
  "$APP"

if ! assessment="$(spctl --assess --type execute --verbose=4 "$APP" 2>&1)"; then
  printf '❌ WezTerm failed Gatekeeper assessment:\n%s\n' "$assessment" >&2
  exit 1
fi
if ! grep -q '^source=Notarized Developer ID$' <<< "$assessment"; then
  echo "❌ WezTerm was not accepted as a notarized Developer ID app." >&2
  exit 1
fi
echo "✅ WezTerm signature matches the reviewed developer and Gatekeeper accepts its notarization."
