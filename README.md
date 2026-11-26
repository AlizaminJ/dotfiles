# Dotfiles

Personal/work setup for macOS and Linux, with one shared toolchain and configuration.
WezTerm renders, tmux manages sessions, zsh runs commands, and Neovim edits files.

- [Start here](docs/onboarding.md): configure and set up a Mac or Linux machine.
- [Daily use](docs/usage.md): shortcuts, Git accounts, customization, recovery.

## Source of truth

- [`Brewfile`](Brewfile): packages (Homebrew on macOS and Linux; VS Code on both; other GUI apps are installed manually; WezTerm and the font via cask on macOS, via `scripts/linux-terminal.sh` on Linux).
- [`bin/dotfiles`](bin/dotfiles): tasks; run `./bin/dotfiles help`.
- [`bootstrap.sh`](bootstrap.sh) / [`scripts/`](scripts): setup steps.
- [`shell/`](shell), [`wezterm/`](wezterm), [`tmux/`](tmux), [`nvim/`](nvim): configuration.
- [`agents/`](agents): shared instructions and skills.
- [CI](.github/workflows/checks.yml): syntax, lint, tests, and secret checks; no provisioning.
