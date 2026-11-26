# Daily use

- Run `tat` in a project to open/resume its tmux session.
- Press **Ctrl+B**, release, then `w` for windows, `s` for sessions, `c` for a new
  window, `%` / `"` to split, arrows to change panes, or `d` to detach.
- Open a project with `tz <name>` (zoxide match, then `tat`); it never moves the current
  shell. Switch between open projects by clicking a name in the second status line
  or with **Alt+S** for the session tree. Labels show each session's current folder.
- Dragging or double-clicking text in tmux copies it to the system clipboard through OSC 52 (paste with Cmd+V on macOS, Ctrl+Shift+V on Linux).
  `st` reloads the tmux config; `sz` restarts the shell.
- **Alt+Shift+F** in Neovim searches the repo (live grep) on macOS and Linux. Hold left Option on macOS.
- **Ctrl+R** searches shell history; `z` / `zi` jump to visited directories.
- Git shortcuts and explicit-argument helpers live in [aliases](../shell/aliases.zsh)
  and [functions](../shell/functions.zsh). Their CLIs must already be installed.
- Personal repos go under `~/workspace/personal`, work under `~/workspace/work`.
  Check `git whoami`. SSH clones use `git@github.com:ORG/repo.git` for work and
  `git@github.com-personal:USER/repo.git` for personal.
- `dotfiles ssh-keys` prepares keys and prints clipboard commands for your OS; add each public key
  to the matching GitHub account yourself. New SSH profiles also use the macOS
  Keychain when available; existing marked SSH blocks aren't rewritten.
- Put private overrides in `~/.zshrc.local`. `sz` starts a fresh shell; `cz` edits that file.
- `dotfiles agents` links shared rules (Pi, Claude, Copilot) plus `code-review`, `security-review`, and
  `essayist`; Pi's `/reload` refreshes them. Other skills stay untouched.
- Use `dotfiles help` for tasks, `dotfiles doctor` for read-only checks, and
  `dotfiles plugins` if the shell reports missing/stale plugins. `dotfiles nvim-plugins`
  installs the Neovim plugins pinned in `nvim/nvim-pack-lock.json`.
- Before publishing: `dotfiles test`, `dotfiles secrets`, and `git diff --check`.
  Review staged changes/history too; a scanner cannot find every secret.

Broken shell? Open your system terminal, run `/bin/zsh -f`, and restore your `.zshrc.bak*`.

## Linux notes

- Packages come from the same `Brewfile` through Homebrew on Linux; VS Code is the only shared GUI cask. Install other GUI apps (Docker, Bitwarden, Todoist, Obsidian) yourself; on Linux use Docker Engine from your distribution.
- `dotfiles linux-terminal` installs the latest stable WezTerm (AppImage, needs FUSE 2) to `~/.local/bin`
  and JetBrainsMono Nerd Font to `~/.local/share/fonts`. It checks each download against the
  project's published SHA-256, runs nothing from them, and skips what is already current.
  Run it again to update; these two apps follow the latest release, with no age delay.
- `clip` copies stdin to the clipboard (`pbcopy`, `wl-copy`, `xclip`, or OSC 52 over SSH).
- `dotfiles macos` does nothing on Linux.

### Differences from macOS

| Area | macOS | Linux |
|---|---|---|
| Paste in the terminal | Cmd+V | Ctrl+Shift+V (Ctrl+V stays free for Neovim) |
| Copy from tmux | Mouse selection, then Cmd+V anywhere | Same, through OSC 52 |
| Neovim live grep | Alt+Shift+F (left Option) | Alt+Shift+F (left Alt) |
| GUI apps | VS Code cask; WezTerm and the font via casks | VS Code cask; WezTerm and the font from `dotfiles linux-terminal` |
| WezTerm | Cask | AppImage, x86_64 only, needs `libfuse2` |
| System defaults | `dotfiles macos` | Not applicable |
| SSH passphrases | Remembered in the Keychain | Use `ssh-agent`; `UseKeychain` is ignored |
| Copy command for keys | `pbcopy` | `wl-copy` or `xclip` |
| VS Code prompts folder | `~/Library/Application Support/Code/User/prompts` | `~/.config/Code/User/prompts` |
| Setup prerequisites | Xcode Command Line Tools | `curl`, `git`, `zsh`, and a build toolchain |
