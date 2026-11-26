#!/bin/bash
# Applies common macOS system preferences. `defaults write` is idempotent (safe to re-run).
set -euo pipefail

[[ "$(uname -s)" == Darwin ]] || { echo "↪ macOS defaults skipped: not running on macOS."; exit 0; }

echo "🖥️ Applying macOS defaults..."

echo "  ↪ Finder: show hidden files"
defaults write com.apple.finder AppleShowAllFiles -bool true

echo "  ↪ Finder: show filename extensions, path bar, and status bar"
defaults write NSGlobalDomain AppleShowAllExtensions -bool true
defaults write com.apple.finder ShowPathbar -bool true
defaults write com.apple.finder ShowStatusBar -bool true

echo "  ↪ Text input: disable smart quotes and dashes"
defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false

echo "  ↪ Keyboard: faster key repeat"
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

echo "  ↪ Dock: autohide"
defaults write com.apple.dock autohide -bool true

echo "  ↪ Screenshots: save to ~/Screenshots"
mkdir -p ~/Screenshots
defaults write com.apple.screencapture location -string "$HOME/Screenshots"

echo "  ↪ Restarting Finder and Dock to apply changes..."
killall Finder >/dev/null 2>&1 || true
killall Dock >/dev/null 2>&1 || true

echo "✅ macOS defaults applied!"
