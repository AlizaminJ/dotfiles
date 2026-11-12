#!/bin/bash
# Select Git identities by workspace; SSH account selection remains separate.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# shellcheck source=scripts/config.sh
source "$REPO_ROOT/scripts/config.sh"

# Existing links can redirect setup into unrelated files; check before any writes.
for target in "$HOME/.gitconfig" "$HOME/.gitconfig-personal" "$HOME/.gitconfig-work" \
              "$HOME/.gitignore_global" "$HOME/.ssh" "$HOME/.ssh/config"; do
  if [[ -L "$target" ]]; then
    printf '❌ Refusing symlinked Git/SSH path: %s. Review it manually before setup.\n' "$target" >&2
    exit 1
  fi
done

# Writes $1 with content from stdin, backing up any existing differing file to $1.bak first.
write_file() {
  local target="$1"
  local content
  content="$(cat)"
  if [[ -f "$target" ]] && [[ "$(cat "$target")" == "$content" ]]; then
    return
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    local backup="$target.bak"
    local suffix=1
    while [[ -e "$backup" || -L "$backup" ]]; do
      backup="$target.bak.$suffix"
      suffix=$((suffix + 1))
    done
    cp -p "$target" "$backup"
    echo "  ↪ backed up existing $target to $backup"
  fi
  printf '%s\n' "$content" > "$target"
}

# Let Git quote values correctly, including names and paths containing spaces.
TEMP_CONFIG="$(mktemp)"
trap 'rm -f "$TEMP_CONFIG"' EXIT
write_git_config() {
  local target="$1"
  shift
  : > "$TEMP_CONFIG"
  while [[ "$#" -gt 0 ]]; do
    git config --file "$TEMP_CONFIG" --add "$1" "$2"
    shift 2
  done
  write_file "$target" < "$TEMP_CONFIG"
}

echo "📁 Creating workspace folders..."
mkdir -p "$PERSONAL_ROOT" "$WORK_ROOT"
# Git checks real paths, which can differ when a parent folder is a symlink.
PERSONAL_ROOT="$(cd "$PERSONAL_ROOT" && pwd -P)"
WORK_ROOT="$(cd "$WORK_ROOT" && pwd -P)"
if [[ "$PERSONAL_ROOT/" == "$WORK_ROOT/"* || "$WORK_ROOT/" == "$PERSONAL_ROOT/"* ]]; then
  echo "❌ Workspace roots resolve to overlapping folders." >&2
  exit 1
fi

echo "⚙️ Configuring workspace Git identities..."
write_git_config "$HOME/.gitconfig-personal" \
  user.name "$PERSONAL_NAME" user.email "$PERSONAL_EMAIL"
write_git_config "$HOME/.gitconfig-work" \
  user.name "$WORK_NAME" user.email "$WORK_EMAIL"

echo "⚙️ Requiring an explicit Git identity outside managed workspaces..."
write_git_config "$HOME/.gitconfig" \
  user.useConfigOnly true \
  init.defaultBranch main \
  alias.whoami '!f() { identity=$(git var GIT_AUTHOR_IDENT) || return; printf "%s>\n" "${identity%>*}"; }; f' \
  "includeIf.gitdir:$PERSONAL_ROOT/.path" "$HOME/.gitconfig-personal" \
  "includeIf.gitdir:$WORK_ROOT/.path" "$HOME/.gitconfig-work" \
  core.excludesfile "$HOME/.gitignore_global"

echo "🙈 Creating global gitignore for macOS system files..."
write_file ~/.gitignore_global << EOF
.DS_Store
EOF

echo "🔒 Configuring SSH profiles..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh
if [[ ! -e "$HOME/.ssh/config" ]]; then
  touch "$HOME/.ssh/config"
fi

MARKER="# --- dotfiles:git-ssh multi-account setup ---"
if grep -qF "$MARKER" ~/.ssh/config 2>/dev/null; then
  echo "  ↪ Existing SSH block kept; review it manually if account defaults or key names changed."
else
  cat << EOF >> ~/.ssh/config

$MARKER
# Work GitHub Profile (Default)
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/$WORK_KEY_NAME
    IdentitiesOnly yes
    AddKeysToAgent yes
    UseKeychain yes

# Personal GitHub Profile
Host github.com-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/$PERSONAL_KEY_NAME
    IdentitiesOnly yes
    AddKeysToAgent yes
    UseKeychain yes
EOF
fi

chmod 600 ~/.ssh/config

echo "✅ Git/SSH setup complete!"
echo "--------------------------------------------------------"
echo "Next Steps:"
echo "1. Run dotfiles ssh-keys if key generation/GitHub registration was skipped."
echo "2. First SSH use can remember passphrases in the macOS Keychain."
echo "3. Work SSH clones use github.com; personal SSH clones use github.com-personal."
echo "--------------------------------------------------------"
