# Neovim

Kickstart-based config; upstream `LICENSE.md` retained. Requires `vim.pack`.
`scripts/nvim-plugins.sh` (run by bootstrap, or `dotfiles nvim-plugins`) installs the
plugins listed in `nvim-pack-lock.json` at exactly those revisions. Neovim startup
never installs anything; before the script runs you get core settings only.

[`lua/dotfiles/safety.lua`](lua/dotfiles/safety.lua) guards existing/listed plugins.
Existing plugin trees are trusted; startup doesn't verify their Git HEAD or local changes.
Before changing the lockfile, review source, immutable revisions, ≥7-day age, dependencies,
and builds. The retained lockfile isn't newly audited. No automatic builds,
Mason installs, or parser downloads; updates still need review.

Use `:checkhealth` to inspect an installation. Plugin keybindings live in the Lua
configuration and only work after the corresponding reviewed plugins are available.
