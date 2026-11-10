# macOS dotfiles

A small Mac setup: one tool per job, reviewed dependencies, repeatable scripts.
Targets Apple Silicon and Intel Macs; fresh-machine testing is still required.
No other OS setup is maintained.

## Setup

Requires Command Line Tools, Python 3.9+, and an already-reviewed Homebrew install.
The bootstrap does not download a Homebrew installer.

```bash
cp -n config.local.sh.example config.local.sh
chmod 600 config.local.sh
# Fill in names, emails, and SSH key filenames in config.local.sh.
bash bootstrap.sh
```

Local settings are ignored by Git and sourced as trusted shell code. Never put
credentials in them. Differing user configs are backed up; correct links are
left alone on repeat runs. Existing packages are not upgraded or removed.

Installation stops on missing age/provenance evidence, unsupported hooks, or
failed signing checks. Do not bypass those stops. Open a fresh zsh session after
setup. Move only reviewed private settings into `~/.zshrc.local`; the old shell
configuration is backed up, not executed automatically.

## Tools and special configuration

| Tool | Purpose / repository choices |
| --- | --- |
| Homebrew | Checked Brewfile installs; 7-day recipe-age gate, bottles only, no automatic upgrades |
| Git | Personal/work identities by folder; explicit identity elsewhere; `git whoami`; new repositories use `main` |
| GitHub CLI (`gh`) | GitHub access and authenticated public-metadata lookups; account state stays local |
| WezTerm | `/bin/zsh -l`, JetBrains Mono Nerd Font, Cmd+C/V; no tab bar or default pane/session shortcuts; signature/notarization required |
| tmux | Sessions/panes; `tat` resumes a project; new panes/windows keep the working directory |
| zsh | History, completion, `EDITOR=nvim`, small aliases; no shell framework |
| Antidote | Two reviewed commit pins: autosuggestions and syntax highlighting; no startup downloads |
| Starship | Directory, Git status, slow-command duration, success/failure prompt |
| zoxide | `z` learns folders; `zi` opens an interactive picker |
| fzf | Ctrl+R history, Ctrl+T paths, Alt+C directories |
| Neovim | Kickstart-based Lua config; retained lockfile and existing-only `vim.pack` loading; core-only startup until plugins are reviewed/installed |
| ripgrep (`rg`), fd | Fast text/file search, including Neovim's search tools |
| tree-sitter CLI | Tooling for reviewed parser builds; no automatic parser installation |
| pnpm 12+ | Strict 7-day age checks, reject missing timestamps, recheck lockfile ages, disable lifecycle scripts |
| uv (configured, not installed) | 7-day upload-age cutoff; source builds disabled |
| VS Code | App plus shared Copilot instruction reference; no managed settings, shortcuts, or extension installs |
| JetBrains Mono Nerd Font | Terminal/editor glyphs; installed through the Brewfile |
| Pi / Claude / Copilot | Shared instructions only; no agent CLI, credentials, sessions, or extensions installed |

macOS preferences: hidden files and filename extensions, Finder path/status bars,
fast key repeat, Dock autohide, screenshots in `~/Screenshots`, and no smart
quotes/dashes. Applying them restarts Finder/Dock; apps may override text settings.

## Commands

The managed shell adds `bin/` to PATH. Before setup, use `./bin/dotfiles`.

```bash
dotfiles help
dotfiles doctor                 # Check this directory; optional project path.
dotfiles secrets                # Check public files, index, and available history.
dotfiles agents
dotfiles shell                  # Link configs only.
dotfiles plugins                # Explicitly prepare reviewed plugin pins.
dotfiles test
dotfiles --dry-run setup         # Print the command; do not run it.
```

Also: `editors`, `pnpm`, `uv`, `git-ssh`, `macos`, `homebrew`,
`verify-wezterm [app]`, and `setup`. These call existing scripts. Preview is not
a file diff or package resolution. Only explicit commands install/apply anything.

```bash
cd ~/workspace/work/backend
tat                             # Create/resume this project; Ctrl+B, D detaches.
git whoami                      # Show the effective author identity.
```

Personal/work roots default to `~/workspace/personal` and `~/workspace/work`.
They must not overlap. For this public checkout, optionally set
`PUBLIC_GIT_NAME` to your public GitHub handle and `PUBLIC_GIT_EMAIL` to your GitHub
noreply address in ignored `config.local.sh`. `dotfiles git-ssh` applies that pair
only to this checkout's local Git config; other repositories keep their workspace
identities. This protects future commits, not existing history.

SSH authentication is separate from commit identity:
clone work projects with `git@github.com-work:org/repo.git`. Existing marked SSH
blocks are not rewritten; update them manually if key filenames change.

## Checks and publication

```bash
./bin/dotfiles secrets
./bin/dotfiles test
```

CI checks Bash/zsh syntax, ShellCheck, secrets, and tests on pushes/PRs. It never
runs bootstrap. Tests use temporary homes and mocked system commands; optional
native tools may be skipped. Hosted CI has not run until this workflow is pushed.

Before publishing, review both staged and unstaged changes. The scanner never
prints matching values, but cannot detect every secret. Git author metadata is
public too; use a GitHub noreply address if desired. No private machine config
or agent state belongs in this repository.

## Details

- [Shell usage, plugins, and rollback](docs/shell.md)
- [Dependency safety and limitations](docs/dependency-safety.md)
- [Shared agent instructions](docs/agents.md)
- [CI and publication checks](docs/ci.md)
- [Neovim safety and shortcuts](nvim/README.md)
- [Reviewed ideas and decisions](docs/dotfiles-inspirations.md)
