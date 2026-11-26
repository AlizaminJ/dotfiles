#!/bin/bash
set -euo pipefail

export REPO_ROOT
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/config.sh
source "$REPO_ROOT/scripts/config.sh"

OS="$(uname -s)"

echo "🚀 Starting automated setup on $OS..."

echo ""
echo "=== Prerequisites ==="
bash "$REPO_ROOT/scripts/prerequisites.sh"
# Keep tools installed by the child script available to subsequent steps.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:/usr/local/bin:/usr/local/sbin:$PATH"

echo ""
echo "=== Shared agent instructions ==="
bash "$REPO_ROOT/scripts/agents.sh"

echo ""
echo "=== Homebrew & packages ==="
"$REPO_ROOT/scripts/homebrew.sh"

if [[ "$OS" == Linux ]]; then
  echo ""
  echo "=== WezTerm & Nerd Font (Linux) ==="
  bash "$REPO_ROOT/scripts/linux-terminal.sh"
fi

echo ""
echo "=== pnpm supply-chain defaults ==="
bash "$REPO_ROOT/scripts/pnpm.sh"

echo ""
echo "=== uv supply-chain defaults ==="
bash "$REPO_ROOT/scripts/uv.sh"

echo ""
echo "=== Neovim & tmux configs ==="
"$REPO_ROOT/scripts/editors.sh"
bash "$REPO_ROOT/scripts/nvim-plugins.sh"

echo ""
echo "=== Modular zsh & terminal configs ==="
bash "$REPO_ROOT/scripts/shell-plugins.sh"
bash "$REPO_ROOT/scripts/shell.sh"

if [[ "$OS" == Darwin ]]; then
  echo ""
  echo "=== macOS defaults ==="
  "$REPO_ROOT/scripts/macos-defaults.sh"
fi

echo ""
echo "=== SSH keys & manual GitHub registration ==="
bash "$REPO_ROOT/scripts/ssh-keys.sh"

echo ""
echo "=== Git & SSH multi-profile ==="
"$REPO_ROOT/scripts/git-ssh.sh"

echo ""
echo "🎉 Setup complete! Safe to re-run bootstrap.sh anytime."
