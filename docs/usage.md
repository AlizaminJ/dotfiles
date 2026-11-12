# Daily use

- Run `tat` in a project to open/resume its tmux session.
- Press **Ctrl+B**, release, then `w` for windows, `s` for sessions, `c` for a new
  window, `%` / `"` to split, arrows to change panes, or `d` to detach.
- **Ctrl+R** searches shell history; `z` / `zi` jump to visited directories.
- Git shortcuts and explicit-argument helpers live in [aliases](../shell/aliases.zsh)
  and [functions](../shell/functions.zsh). Their CLIs must already be installed.
- Personal repos go under `~/workspace/personal`, work under `~/workspace/work`.
  Check `git whoami`. SSH clones use `git@github.com:ORG/repo.git` for work and
  `git@github.com-personal:USER/repo.git` for personal.
- `dotfiles ssh-keys` finishes key setup. New SSH profiles remember passphrases in
  macOS Keychain; existing marked SSH blocks aren't rewritten.
- Put private overrides in `~/.zshrc.local`. `sz` starts a fresh shell; `cz` edits that file.
- `dotfiles agents` links shared rules plus `code-review`, `security-review`, and
  `essayist`; Pi's `/reload` refreshes them. Other skills stay untouched.
- Use `dotfiles help` for tasks, `dotfiles doctor` for read-only checks, and
  `dotfiles plugins` if the shell reports missing/stale plugins.
- Before publishing: `dotfiles test`, `dotfiles secrets`, and `git diff --check`.
  Review staged changes/history too; a scanner cannot find every secret.

Broken shell? Open macOS Terminal, run `/bin/zsh -f`, and restore your `.zshrc.bak*`.
