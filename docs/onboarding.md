# Setup

From this checkout on macOS or Linux. Linux needs `curl`, `git`, `zsh`, and a build
toolchain from your distro first; every other tool comes from Homebrew, as on macOS.

```bash
cp -n config.local.sh.example config.local.sh
chmod 600 config.local.sh
# Fill in personal/work names and emails.
bash bootstrap.sh
source ~/.zshrc
```

Setup installs Homebrew, uv, Python, and Brewfile packages. Approve prompts as needed.
On Linux, setup also installs the latest WezTerm and JetBrainsMono Nerd Font into your home
directory; macOS defaults are skipped (see [daily use](usage.md#linux-notes)).

Use GitHub noreply emails for commit privacy. Never store credentials in local config.
Setup asks for SSH passphrases, prints public-key copy commands, and, on macOS, restarts Finder/Dock.
Add each public key manually at https://github.com/settings/ssh/new in the matching account.
Open a fresh terminal, run `dotfiles doctor`, then see [daily use](usage.md).
Don't move or delete this dotfiles folder after setup: your configs point to it.
