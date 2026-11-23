# Daily use

- Run `tat` in a project to open/resume its tmux session.
- Press **Ctrl+B**, release, then `w` for windows, `s` for sessions, `c` for a new
  window, `%` / `"` to split, arrows to change panes, or `d` to detach.
- Open a project with `tz <name>` (zoxide match, then `tat`); it never moves the current
  shell. Switch between open projects by clicking a name in the second status line
  or with **Alt+S** for the session tree. Labels show each session's current folder.
- Dragging or double-clicking text in tmux copies it to the macOS clipboard (Cmd+V pastes).
  `st` reloads the tmux config; `sz` restarts the shell.
- **Ctrl+R** searches shell history; `z` / `zi` jump to visited directories.
- Git shortcuts and explicit-argument helpers live in [aliases](../shell/aliases.zsh)
  and [functions](../shell/functions.zsh). Their CLIs must already be installed.
- Personal repos go under `~/workspace/personal`, work under `~/workspace/work`.
  Check `git whoami`. SSH clones use `git@github.com:ORG/repo.git` for work and
  `git@github.com-personal:USER/repo.git` for personal.
- `dotfiles ssh-keys` prepares keys and prints `pbcopy` commands; add each public key
  to the matching GitHub account yourself. New SSH profiles use macOS Keychain;
  existing marked SSH blocks aren't rewritten.
- Put private overrides in `~/.zshrc.local`. `sz` starts a fresh shell; `cz` edits that file.
- `dotfiles agents` links shared rules plus `code-review`, `security-review`, and
  `essayist`; Pi's `/reload` refreshes them. Other skills stay untouched.
- Use `dotfiles help` for tasks, `dotfiles doctor` for read-only checks, and
  `dotfiles plugins` if the shell reports missing/stale plugins.
- Before publishing: `dotfiles test`, `dotfiles secrets`, and `git diff --check`.
  Review staged changes/history too; a scanner cannot find every secret.

Broken shell? Open macOS Terminal, run `/bin/zsh -f`, and restore your `.zshrc.bak*`.
