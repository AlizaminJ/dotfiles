#!/bin/bash
# Verify the app without launching it or changing Gatekeeper policy.
set -euo pipefail
export LC_ALL=C

APP="${1:-/Applications/WezTerm.app}"
if [[ "$#" -gt 1 || ! -d "$APP" || "$(uname -s)" != Darwin ]]; then
  echo "❌ Usage on macOS: bash scripts/verify-wezterm.sh [path/to/WezTerm.app]" >&2
  exit 1
fi

# Reviewed 2026-11-09: stable 20240203-110809-5046fc22, released 2024-02-03.
# Archive SHA256: e77388cad55f2e9da95a220a89206a6c58f865874a629b7c3ea3c162f5692224
# Same checksum in Homebrew snapshot 6036456f4e329bd68fb5bed9f879df46e47892ba (2026-09-20).
# This app passed macOS signature/notarization checks; newer releases need a new review.
# Pin the developer identity checked against that official stable release.
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
