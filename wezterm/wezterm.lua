local wezterm = require 'wezterm'

local config = {
  font = wezterm.font 'JetBrainsMono Nerd Font',
  font_size = 13,
  window_padding = { left = 8, right = 8, top = 8, bottom = 8 },
  scrollback_lines = 10000,
  default_prog = { '/bin/zsh', '-l' },
  enable_tab_bar = false,
  -- Leave session and pane shortcuts to tmux instead of binding them twice.
  disable_default_key_bindings = true,
}

config.keys = {
  { key = 'c', mods = 'CMD', action = wezterm.action.CopyTo 'Clipboard' },
  { key = 'v', mods = 'CMD', action = wezterm.action.PasteFrom 'Clipboard' },
}

-- Keep machine-specific preferences outside Git.
local local_path = wezterm.home_dir .. '/.wezterm.local.lua'
local file = io.open(local_path, 'r')
if file then
  file:close()
  local overrides = assert(loadfile(local_path))()
  assert(type(overrides) == 'table', 'Expected a table from ~/.wezterm.local.lua')
  for key, value in pairs(overrides) do
    config[key] = value
  end
end

return config
