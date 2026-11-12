# Neovim

Kickstart-based config; upstream `LICENSE.md` retained. Requires `vim.pack`.
Fresh Macs start with core settings, not automatic plugin installation.

[`lua/dotfiles/safety.lua`](lua/dotfiles/safety.lua) guards existing/listed plugins.
Existing plugin trees are trusted; startup doesn't verify their Git HEAD or local changes.
Before preparing plugins, review source, immutable revisions, ≥7-day age, dependencies,
and builds. The retained lockfile isn't newly audited. No automatic builds,
Mason installs, or parser downloads; manual installs/updates still need review.

Use `:checkhealth` to inspect an installation. Plugin keybindings live in the Lua
configuration and only work after the corresponding reviewed plugins are available.
