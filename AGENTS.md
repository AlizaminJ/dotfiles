# AGENTS.md

Instructions for AI coding agents (Copilot, etc.) working in this repository.

## Purpose

This repo automates setting up a new Mac: Homebrew + packages, macOS system
defaults, and multi-profile Git/SSH config (personal vs. work GitHub identity).
Entry point: `bash bootstrap.sh`.

## Layout

- `bootstrap.sh` — thin orchestrator. Loads `scripts/config.sh` before running
  each setup script in order.
- `config.local.sh.example` — tracked template for the ignored `config.local.sh`.
  Holds personal/work names, emails, SSH key filenames, and workspace roots.
- `scripts/config.sh` — loads, validates, and exports local settings. Shared by
  bootstrap and standalone Git/SSH setup; missing identity values stop setup.
- `scripts/prerequisites.sh` — installs Homebrew, uv, and Python.
- `scripts/homebrew.sh` — installs/updates Brewfile packages with `brew bundle`.
- `scripts/shell.sh` — backs up and links zsh, Starship, and WezTerm configs.
- `scripts/shell-plugins.sh` — prepares shell plugins through Antidote.
  Startup must not download plugins or run an automatic updater.
- `shell/`, `wezterm/` — macOS settings; generic helpers require explicit targets.
  Keep private aliases, profiles, locations, and project paths out of Git.
  WezTerm handles rendering only; leave pane/session shortcuts to tmux.
- `scripts/uv.sh`, `uv/uv.toml` — user uv age/build preferences; does not install uv.
- `docs/onboarding.md`, `docs/usage.md` — setup, everyday commands, and recovery.
  Safety policy lives in shared rules/skills; installer evidence stays with its code.
- `scripts/macos-defaults.sh` — `defaults write` tweaks for Finder/Dock/keyboard.
- `scripts/doctor.sh` — read-only health check, run manually with an optional
  project directory. Reports issues without installing or repairing anything.
- `scripts/ssh-keys.sh` / `scripts/ssh-keys.py` — interactive missing-key generation
  and printed public-key clipboard commands for manual GitHub registration.
  Never overwrite existing keys, create empty passphrases automatically, print key
  contents, or contact accounts/change the clipboard. Tests use fake keygen only.
- `scripts/git-ssh.sh` — writes `~/.gitconfig`, `~/.gitconfig-personal`,
  `~/.gitconfig-work`, and `~/.gitignore_global`, and appends the SSH account block.
  Git identities apply only inside `PERSONAL_ROOT` and `WORK_ROOT`; outside those
  roots Git requires an explicitly configured identity.
- `scripts/editors.sh` — symlinks `nvim/` to `~/.config/nvim` and
  `tmux/tmux.conf` to `~/.tmux.conf` (backs up existing files first).
- `nvim/` — kickstart-based config with guarded, existing-only plugin loading.
  Plugins are installed only by `scripts/nvim-plugins.sh` (run from bootstrap or
  `dotfiles nvim-plugins`) at the exact lockfile revisions. Neovim startup must not
  clone, build, run Mason installs, or download parsers.
  `tmux/` — session/pane config.
- `scripts/check-secrets.py` — redact-by-location scan of public files, index,
  and reachable history. Never print matching values or read ignored private files.
- `.github/workflows/checks.yml` — pinned checkout, Ubuntu lint infrastructure,
  macOS syntax/tests/secrets. No package installs or bootstrap in CI.
- `bin/dotfiles` — thin task dispatcher; calls existing scripts from any directory.
  Preserve the caller directory for doctor checks; run tests from the checkout.
  `--dry-run` prints commands only, without sourcing configuration or running tasks.
- `bin/tat` — create/resume a project tmux session, or switch clients inside tmux.
  Managed zsh adds `bin/` to PATH. Keep tests on an isolated tmux socket.
- `Brewfile` — package list consumed by `scripts/homebrew.sh`.
- `agents/AGENTS.md` — minimal shared, tool-neutral rules; `agents/skills/` holds
  code-review, security-review, and essayist workflows. Keep this root file repository-specific.
- `scripts/agents.sh` — links the shared file at `~/.agents/AGENTS.md` and
  installs Pi, Claude, and VS Code Copilot references. Pi respects
  `PI_CODING_AGENT_DIR`; only its instruction file is managed, never runtime state.
  Only the named skill files and essayist's writing guide are linked under `~/.agents/skills/`;
  unrelated skills and backups stay untouched.
  See `docs/usage.md` (Agents). Run with
  `bash scripts/agents.sh` to configure agents without running full setup.

## Conventions for new/changed scripts

- One script per concern under `scripts/`, invoked from `bootstrap.sh` — don't
  grow `bootstrap.sh` itself beyond the orchestrator role.
- Start every script with `set -euo pipefail`.
- **Idempotency is required.** Every step must be safe to re-run on a machine
  that already ran it:
  - Check before installing (`command -v <tool>`) rather than reinstalling blindly.
  - Before overwriting a file the user may have customized, back it up
    (`<file>.bak`) only if the new content differs — see `write_file()` in
    `scripts/git-ssh.sh`.
  - When appending to a file (e.g. `~/.ssh/config`), guard with a marker
    comment and skip if already present — don't append duplicate blocks.
  - `defaults write` is naturally idempotent.
- Keep the existing progress-echo style: short emoji-prefixed status lines
  (`🚀`, `⚙️`, `🔒`, `✅`, etc.), with `↪` for sub-steps/details.
- Do not commit secrets (SSH keys, tokens). `PERSONAL_EMAIL`/`WORK_EMAIL` etc.
  are non-sensitive placeholders meant to be edited by the user; don't add
  actual credentials to any script.

## Verification before suggesting a change is done

1. Parse each Bash file separately: `for f in bootstrap.sh bin/* scripts/*.sh; do /bin/bash -n "$f"; done`.
2. Parse zsh files separately; run ShellCheck on Bash files if available.
3. Run `./bin/dotfiles test` and `./bin/dotfiles secrets`.
4. Check repeat-run safety: no duplicate config or loss of un-backed-up data.
5. Preserve the macOS-only scope. Keep examples anonymous and never publish
   local settings, agent state, credentials, or personal absolute paths.
