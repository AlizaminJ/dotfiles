# Shell and terminal — macOS

WezTerm renders, tmux manages sessions, zsh runs commands. Antidote loads selected
plugins; Starship draws the prompt; zoxide/fzf provide navigation and selection.
No shell framework, terminal AI layer, automatic tmux attach, or startup downloads.

## Files and private overrides

| Repository file | Installed path |
| --- | --- |
| `shell/zshrc` | `~/.zshrc` |
| `shell/starship.toml` | `~/.config/starship.toml` |
| `wezterm/wezterm.lua` | `~/.wezterm.lua` |
| `tmux/tmux.conf` | `~/.tmux.conf` |

XDG overrides are respected where supported. Setup backs up differing files to
`.bak` (numbered when necessary). Existing `.zprofile`, `.zshenv`, and
`.zshrc.local` are preserved. Move reviewed aliases/PATH/tool initialization from
old backups into `~/.zshrc.local`; do not reload an old framework or prompt.
Never copy credentials into Git. Use a fresh shell instead of sourcing `.zshrc` twice.

WezTerm launches `/bin/zsh -l`; only Cmd+C/V are bound. Tabs/default keyboard
bindings are disabled so tmux owns panes/sessions. `~/.wezterm.local.lua` can
return private overrides, for example `return { font_size = 14 }`.
[Signing and installation review](dependency-safety.md#wezterm).

## Everyday use

| Command / shortcut | Meaning |
| --- | --- |
| Tab | zsh completion |
| Right Arrow at the end | Accept a history suggestion without executing it |
| Ctrl+R | fzf command-history search |
| Ctrl+T | Insert selected file/directory paths |
| Alt+C | fzf directory picker; Option-key behavior may vary |
| `z dotfiles` | Jump to a previously visited matching folder |
| `zi` | Pick a known folder using fzf |
| `gs` / `gl` | Short Git status / recent commit graph |
| `..` / `...` | Up one/two directories |
| `$EDITOR` | Defaults to Neovim |

Zoxide learns visits: first use `cd ~/workspace/personal/dotfiles`, then `z dotfiles`.
The prompt shows directory, Git state, slow-command duration, and last-command
success/failure. Syntax colors are hints, not security checks. A leading space
omits a command from managed history, but other tools may still record it.

## Project tmux sessions

```bash
cd ~/workspace/work/backend
tat
tat ~/workspace/personal/dotfiles
```

`tat` uses the Git root, or the selected directory outside Git. A path hash keeps
same-named projects and worktrees separate; symlink paths reuse a session. Inside
tmux it switches clients rather than nesting. Moving a project creates a new
session name; old sessions are not deleted.

| Prefix Ctrl+B, then | Action |
| --- | --- |
| `d` | Detach, leaving work running |
| `%` | Left/right panes |
| `"` | Top/bottom panes |
| `c` | New window |

Panes/windows inherit the active directory. New servers load the config; explicitly
use `tmux source-file ~/.tmux.conf` for an existing server. Clipboard uses Cmd+C/V;
no extra tmux plugin or clipboard integration is installed.

## Plugins and rollback

`dotfiles plugins` uses Antidote **2.3.0** to prepare `shell/plugins.txt` pins.
Unknown pins require source/dependency review and a verified date at least 7 days
old before updating the allowlist in `scripts/shell-plugins.sh`. Review changes,
rebuild, then test in a fresh shell. Normal startup only loads the matching cache
under `~/.cache/dotfiles`; plugin code stays under `~/.local/share/antidote`.
Antidote manages loading, not compatibility or sandboxing. Never also load another
copy of the same plugin. Completions/tools initialize before plugins; highlighting
loads last. Missing/stale caches warn rather than download.

In `~/.zshrc.local`, set any of `DOTFILES_DISABLE_FZF=1`,
`DOTFILES_DISABLE_ZOXIDE=1`, or `DOTFILES_DISABLE_STARSHIP=1` to disable that piece.
To disable a plugin, remove its manifest line and rebuild the cache.

For recovery, open macOS Terminal and run `/bin/zsh -f`. Restore a reviewed
`.zshrc.bak*` only after checking its required tools; retain the backup.
