tap "databricks/tap"

brew "git"
brew "gh"
brew "jq"
brew "pnpm"
brew "uv"
brew "neovim"
brew "tmux"
brew "ripgrep"
brew "fd"
brew "tree-sitter-cli"
brew "antidote"
brew "starship"
brew "zoxide"
brew "fzf"
brew "bitwarden-cli"
brew "direnv"
brew "awscli"
brew "tfenv"
brew "nvm"
brew "databricks/tap/databricks"

# Clipboard tools for Neovim and the clip helper on Linux; macOS ships pbcopy.
if OS.linux?
  brew "wl-clipboard"
  brew "xclip"
end

# Only apps that install the same way on macOS and Linux belong here.
cask "visual-studio-code"

# Other GUI apps (Docker, Bitwarden, Todoist, Obsidian...) are installed manually.
# Linux gets WezTerm and the font from scripts/linux-terminal.sh.
if OS.mac?
  cask "wezterm"
  cask "font-jetbrains-mono-nerd-font"
end
