# macOS dotfiles

Personal/work setup for Apple Macs.
WezTerm renders, tmux manages sessions, zsh runs commands, and Neovim edits files.

- [Start here](docs/onboarding.md): configure and set up a Mac.
- [Daily use](docs/usage.md): shortcuts, Git accounts, customization, recovery.

## Source of truth

- [`Brewfile`](Brewfile): packages.
- [`bin/dotfiles`](bin/dotfiles): tasks; run `./bin/dotfiles help`.
- [`bootstrap.sh`](bootstrap.sh) / [`scripts/`](scripts): setup steps.
- [`shell/`](shell), [`wezterm/`](wezterm), [`tmux/`](tmux), [`nvim/`](nvim): configuration.
- [`agents/`](agents): shared instructions and skills.
- [CI](.github/workflows/checks.yml): syntax, lint, tests, and secret checks; no provisioning.
