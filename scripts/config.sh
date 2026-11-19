#!/bin/bash
# Source this file so setup steps share the same machine-specific settings.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
if [[ ! -f "$REPO_ROOT/config.local.sh" ]]; then
  echo "❌ Copy config.local.sh.example to config.local.sh and fill in your details first." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$REPO_ROOT/config.local.sh"

for key in PERSONAL_NAME PERSONAL_EMAIL PERSONAL_KEY_NAME PERSONAL_ROOT WORK_NAME WORK_EMAIL WORK_KEY_NAME WORK_ROOT; do
  if [[ -z "${!key:-}" ]]; then
    echo "❌ Set $key in config.local.sh before running setup." >&2
    exit 1
  fi
done

for variable in PERSONAL_KEY_NAME WORK_KEY_NAME; do
  value="${!variable}"
  lower="$(printf '%s' "$value" | LC_ALL=C tr '[:upper:]' '[:lower:]')"
  if [[ ! "$value" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ || "${#value}" -gt 200 ]]; then
    echo "❌ SSH key names must be ordinary filenames, not paths." >&2
    exit 1
  fi
  case "$lower" in
    config|known_hosts|known_hosts.old|authorized_keys|environment|rc|*.pub)
      echo "❌ SSH key names must not name public keys or SSH configuration files." >&2
      exit 1
      ;;
  esac
done
if [[ "$(printf '%s' "$PERSONAL_KEY_NAME" | LC_ALL=C tr '[:upper:]' '[:lower:]')" == "$(printf '%s' "$WORK_KEY_NAME" | LC_ALL=C tr '[:upper:]' '[:lower:]')" ]]; then
  echo "❌ Personal and work keys must use different filenames." >&2
  exit 1
fi

PERSONAL_ROOT="${PERSONAL_ROOT%/}"
WORK_ROOT="${WORK_ROOT%/}"
for root in "$PERSONAL_ROOT" "$WORK_ROOT"; do
  if [[ "$root" != /* || "$root" == / || -z "$root" || "$root" == *$'\n'* || "$root" == *$'\r'* ||
        "$root" == *'*'* || "$root" == *'?'* || "$root" == *'['* || "$root" == *']'* || "$root" == *\\* ]]; then
    echo "❌ Workspace roots must be absolute, non-root paths without Git pattern characters." >&2
    exit 1
  fi
  case "$root/" in
    */../*|*/./*|*//*)
      echo "❌ Workspace roots must not contain '.', '..', or repeated slashes." >&2
      exit 1
      ;;
  esac
done
if [[ "$PERSONAL_ROOT/" == "$WORK_ROOT/"* || "$WORK_ROOT/" == "$PERSONAL_ROOT/"* ]]; then
  echo "❌ Personal and work roots must be separate, non-overlapping folders." >&2
  exit 1
fi

export REPO_ROOT PERSONAL_NAME PERSONAL_EMAIL PERSONAL_KEY_NAME PERSONAL_ROOT
export WORK_NAME WORK_EMAIL WORK_KEY_NAME WORK_ROOT
