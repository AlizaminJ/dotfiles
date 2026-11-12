#!/bin/bash
set -euo pipefail

export REPO_ROOT
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/config.sh
source "$REPO_ROOT/scripts/config.sh"

echo "🚀 Starting automated Mac setup..."

echo ""
echo "=== Shared agent instructions ==="
bash "$REPO_ROOT/scripts/agents.sh"

echo ""
echo "=== Homebrew & packages ==="
"$REPO_ROOT/scripts/homebrew.sh"

echo ""
echo "=== WezTerm signature & Gatekeeper ==="
bash "$REPO_ROOT/scripts/verify-wezterm.sh"

echo ""
echo "=== pnpm supply-chain defaults ==="
bash "$REPO_ROOT/scripts/pnpm.sh"

echo ""
echo "=== uv supply-chain defaults ==="
bash "$REPO_ROOT/scripts/uv.sh"

echo ""
echo "=== Neovim & tmux configs ==="
"$REPO_ROOT/scripts/editors.sh"

echo ""
echo "=== Modular zsh & terminal configs ==="
bash "$REPO_ROOT/scripts/shell-plugins.sh"
bash "$REPO_ROOT/scripts/shell.sh"

echo ""
echo "=== macOS defaults ==="
"$REPO_ROOT/scripts/macos-defaults.sh"

echo ""
echo "=== SSH keys & GitHub registration ==="
bash "$REPO_ROOT/scripts/ssh-keys.sh"

echo ""
echo "=== Git & SSH multi-profile ==="
"$REPO_ROOT/scripts/git-ssh.sh"

echo ""
echo "🎉 Mac setup complete! Safe to re-run bootstrap.sh anytime."
