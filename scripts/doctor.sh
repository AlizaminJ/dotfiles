#!/bin/bash
# Report setup problems without applying configuration or installing anything.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TARGET="${1:-$PWD}"
ISSUES=0

pass() { printf '✅ %s\n' "$1"; }
warn() { printf '⚠️ %s\n' "$1"; }
fail() { printf '❌ %s\n' "$1"; ISSUES=1; }

if [[ "$#" -gt 1 || ! -d "$TARGET" ]]; then
  printf 'Usage: bash scripts/doctor.sh [existing-directory]\n' >&2
  exit 2
fi
TARGET="$(cd "$TARGET" && pwd -P)"

echo "🩺 Checking dotfiles setup (no changes will be made)..."
if [[ "$(uname -s)" == Darwin ]]; then
  pass "macOS ($(uname -m))"
  if xcode-select -p >/dev/null 2>&1; then
    pass "Xcode Command Line Tools available"
  else
    fail "Xcode Command Line Tools missing"
  fi
else
  warn "This setup targets macOS; macOS-only checks skipped"
fi

for tool in brew git gh nvim tmux rg fd tree-sitter pnpm starship zoxide fzf; do
  if command -v "$tool" >/dev/null 2>&1; then
    pass "$tool available"
  else
    fail "$tool missing"
  fi
done

if command -v pnpm >/dev/null 2>&1; then
  version="$(pnpm --version 2>/dev/null || true)"
  major="${version%%.*}"
  if [[ "$major" =~ ^[0-9]+$ ]] && [[ "$major" -ge 12 ]]; then
    pass "pnpm supports the required safeguards"
  else
    fail "pnpm 12 or newer required"
  fi

  echo "  ↪ Checking effective pnpm settings in $TARGET"
  age="$(cd "$TARGET" && pnpm config get minimumReleaseAge 2>/dev/null)" || age=""
  if [[ "$age" =~ ^[0-9]+$ ]] && [[ "$age" -ge 10080 ]]; then
    pass "Minimum package release age is at least 7 days"
  else
    fail "Minimum package release age is below 7 days or not configured"
  fi
  while read -r key expected; do
    actual="$(cd "$TARGET" && pnpm config get "$key" 2>/dev/null)" || actual=""
    if [[ "$actual" == "$expected" ]]; then
      pass "pnpm $key=$expected"
    else
      fail "pnpm $key must be $expected (check global and project settings)"
    fi
  done << 'EOF'
minimumReleaseAgeStrict true
minimumReleaseAgeIgnoreMissingTime false
trustLockfile false
ignoreScripts true
EOF
  exclusions="$(cd "$TARGET" && pnpm config get minimumReleaseAgeExclude 2>/dev/null)" || exclusions=""
  case "$exclusions" in
    undefined|null|'[]') pass "No pnpm release-age exclusions" ;;
    *) fail "pnpm release-age exclusions exist or could not be checked" ;;
  esac
fi

check_link() {
  local target="$1" source="$2" label="$3"
  if [[ -L "$target" && -e "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    pass "$label linked to this checkout"
  else
    fail "$label missing, broken, or not linked to this checkout"
  fi
}
check_link "$HOME/.config/nvim" "$REPO_ROOT/nvim" "Neovim config"
check_link "$HOME/.tmux.conf" "$REPO_ROOT/tmux/tmux.conf" "tmux config"
check_link "$HOME/.agents/AGENTS.md" "$REPO_ROOT/agents/AGENTS.md" "Shared agent instructions"
for skill in code-review security-review essayist; do
  check_link "$HOME/.agents/skills/$skill/SKILL.md" "$REPO_ROOT/agents/skills/$skill/SKILL.md" "Shared $skill skill"
done
check_link "$HOME/.agents/skills/essayist/references/writing-guide.md" \
  "$REPO_ROOT/agents/skills/essayist/references/writing-guide.md" "Essayist writing guide"
PI_DIR="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
if [[ "$PI_DIR" != /* ]]; then
  fail "PI_CODING_AGENT_DIR must be an absolute path"
elif [[ -e "$PI_DIR/AGENTS.override.md" || -L "$PI_DIR/AGENTS.override.md" ]]; then
  fail "Pi AGENTS.override.md hides the shared instructions; review it manually"
else
  check_link "$PI_DIR/AGENTS.md" "$HOME/.agents/AGENTS.md" "Pi shared-instructions reference"
fi
check_link "$HOME/.zshrc" "$REPO_ROOT/shell/zshrc" "Modular zsh config"
check_link "${XDG_CONFIG_HOME:-$HOME/.config}/starship.toml" "$REPO_ROOT/shell/starship.toml" "Starship config"
check_link "$HOME/.wezterm.lua" "$REPO_ROOT/wezterm/wezterm.lua" "WezTerm config"
check_link "${XDG_CONFIG_HOME:-$HOME/.config}/uv/uv.toml" "$REPO_ROOT/uv/uv.toml" "uv preferences"
PLUGIN_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/plugins.zsh"
if [[ -r "$PLUGIN_CACHE" && -r "$PLUGIN_CACHE.manifest" ]] &&
   [[ "$(cksum < "$REPO_ROOT/shell/plugins.txt")" == "$(< "$PLUGIN_CACHE.manifest")" ]]; then
  pass "Shell plugin cache matches the reviewed manifest"
else
  fail "Shell plugin cache missing or stale; run scripts/shell-plugins.sh"
fi
if command -v wezterm >/dev/null 2>&1; then
  pass "WezTerm available"
else
  fail "WezTerm missing"
fi
if [[ "$(uname -s)" == Darwin ]]; then
  if bash "$REPO_ROOT/scripts/verify-wezterm.sh" >/dev/null 2>&1; then
    pass "WezTerm developer signature and notarization verified"
  else
    fail "WezTerm signature/notarization check failed; run scripts/verify-wezterm.sh for details"
  fi
fi

if [[ -f "$HOME/.claude/CLAUDE.md" ]] && grep -qFx '@~/.agents/AGENTS.md' "$HOME/.claude/CLAUDE.md"; then
  pass "Claude references shared instructions"
else
  fail "Claude shared-instructions reference missing"
fi
COPILOT="$HOME/Library/Application Support/Code/User/prompts/global.instructions.md"
if [[ -f "$COPILOT" ]] && grep -qF "$HOME/.agents/AGENTS.md" "$COPILOT"; then
  pass "Copilot references shared instructions"
else
  fail "Copilot shared-instructions reference missing"
fi

# A subshell lets invalid local configuration fail without hiding other checks.
check_profiles() (
  local profile_issues=0
  fail() { printf '❌ %s\n' "$1"; profile_issues=1; }
  # shellcheck source=scripts/config.sh
  source "$REPO_ROOT/scripts/config.sh"
  pass "Local settings complete and workspace paths valid"

  check_identity() {
    local root="$1" name="$2" email="$3" label="$4"
    if [[ ! -d "$root" ]]; then
      fail "$label workspace folder missing"
      return
    fi
    root="$(cd "$root" && pwd -P)"
    local actual_name actual_email repo="" candidate
    if [[ "$TARGET/" == "$root/"* ]] && git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      repo="$TARGET"
    else
      # Look only near the workspace root, rather than scanning entire projects.
      for candidate in "$root/.git" "$root"/*/.git "$root"/*/*/.git; do
        if [[ -d "$candidate" || -f "$candidate" ]]; then
          repo="${candidate%/.git}"
          break
        fi
      done
    fi
    if [[ -z "$repo" ]]; then
      warn "No repository found within two levels of $label workspace; identity not verified"
      return
    fi
    actual_name="$(git -C "$repo" config --get user.name 2>/dev/null || true)"
    actual_email="$(git -C "$repo" config --get user.email 2>/dev/null || true)"
    if [[ "$actual_name" == "$name" && "$actual_email" == "$email" ]]; then
      pass "$label identity matches in $repo"
    else
      fail "Repository overrides or does not select the expected $label identity: $repo"
    fi
  }

  if command -v git >/dev/null 2>&1; then
    check_identity "$PERSONAL_ROOT" "$PERSONAL_NAME" "$PERSONAL_EMAIL" "Personal"
    check_identity "$WORK_ROOT" "$WORK_NAME" "$WORK_EMAIL" "Work"
    if [[ "$(git config --global --get user.useConfigOnly 2>/dev/null || true)" == true ]] &&
       ! git config --global --get user.name >/dev/null 2>&1 &&
       ! git config --global --get user.email >/dev/null 2>&1; then
      pass "No global fallback Git identity; explicit identity required outside workspaces"
    else
      fail "Global Git settings do not enforce the outside-workspace identity safeguard"
    fi
    warn "Other repositories may have local overrides; pass a repository directory to check it"
    if [[ -n "${GIT_AUTHOR_NAME:-}${GIT_AUTHOR_EMAIL:-}${GIT_COMMITTER_NAME:-}${GIT_COMMITTER_EMAIL:-}${EMAIL:-}" ]]; then
      warn "Git identity environment overrides are set; their values are not displayed"
    fi
  fi

  for key in "$PERSONAL_KEY_NAME" "$WORK_KEY_NAME"; do
    if [[ -f "$HOME/.ssh/$key" && -r "$HOME/.ssh/$key" ]]; then
      pass "Configured SSH key file exists and is readable (contents not inspected)"
    else
      fail "A configured SSH key file is missing or unreadable"
    fi
  done
  warn "SSH checks only cover key-file presence, not GitHub authentication"
  exit "$profile_issues"
)
if ! check_profiles; then
  fail "Local settings or Git/SSH checks need attention"
fi

if [[ "$ISSUES" -eq 0 ]]; then
  echo "✅ All checked settings passed. Nothing was changed."
else
  echo "⚠️ Setup needs attention. Nothing was changed."
fi
exit "$ISSUES"
