# Neovim — macOS

Lua configuration based on [kickstart.nvim](https://github.com/nvim-lua/kickstart.nvim).
Upstream license is retained in `LICENSE.md`. Requires Neovim with `vim.pack`.

## First launch and dependency safety

A fresh Mac gets core editor settings only until the lockfile's plugins are
reviewed and present under Neovim's data directory. No automatic clone, build,
Mason tool install, or Treesitter parser install runs during startup.

`lua/dotfiles/safety.lua` checks the retained lockfile/cache and blocks missing or
unlisted additions. It does not re-audit cached revisions or verify every installed
HEAD against the lock on startup. Before preparing any plugin/tool, verify immutable revisions, release age
(at least 7 days), dependencies, and executable code. Do not use floating install
commands to bypass this. Parser/native-plugin builds need separate approval.
Existing plugin code can execute when loaded; this guard is not a sandbox.

`nvim-pack-lock.json` is retained, not regenerated or newly audited by setup.
Keep its updates deliberate and review diffs. Manual `vim.pack`/Mason/update
commands remain subject to the same policy. On a fresh Mac, `nvim` stays usable
without those extras; `:checkhealth` can help diagnose an existing installation.

## Configured features once reviewed plugins are available

| Feature | Choice |
| --- | --- |
| Leader | Space; Nerd Font enabled |
| UI | Tokyonight, which-key, TODO markers, mini modules |
| Git | Gitsigns; hunk actions under Space+h |
| Search | Telescope using ripgrep/fd |
| File tree | Neo-tree; `\` reveals current file |
| Completion | blink.cmp Lua matcher and LuaSnip; no Rust binary download |
| Language tools | Lua language server; StyLua formatter, not an LSP |
| Formatting | Space+f; Lua uses externally reviewed StyLua; format-on-save off |
| Syntax | Existing Treesitter parsers only; no build/update hooks |

Useful keys: Space+sf files, Space+sg text search, Space+sh help,
Space+Space buffers, Space+f format. Language servers/formatters must be installed
separately through reviewed sources. Optional debug/lint examples are disabled
unless explicitly enabled; they are not permission to install unreviewed tools.
