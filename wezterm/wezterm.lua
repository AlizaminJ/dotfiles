local wezterm = require 'wezterm'

local config = {
  font = wezterm.font 'JetBrainsMono Nerd Font',
  font_size = 13,
  -- Matches Neovim's tokyonight-night so the padding has the same background as the editor.
  color_scheme = 'Tokyo Night',
  window_padding = { left = 8, right = 8, top = 8, bottom = 8 },
  scrollback_lines = 10000,
  -- Left Alt/Option acts as Meta for tmux and Neovim shortcuts; right Alt/AltGr composes characters (brackets, braces) on every OS.
  send_composed_key_when_left_alt_is_pressed = false,
  send_composed_key_when_right_alt_is_pressed = true,
  enable_tab_bar = false,
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
