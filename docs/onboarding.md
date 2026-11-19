# Setup

From this checkout on macOS:

```bash
cp -n config.local.sh.example config.local.sh
chmod 600 config.local.sh
# Fill in personal/work names and emails.
bash bootstrap.sh
```

Setup installs Homebrew, uv, Python, and Brewfile packages. Approve prompts as needed.

Use GitHub noreply emails for commit privacy. Never store credentials in local config.
Setup asks for SSH passphrases, prints public-key copy commands, and restarts Finder/Dock.
Add each public key manually at https://github.com/settings/ssh/new in the matching account.
Open a fresh terminal, run `dotfiles doctor`, then see [daily use](usage.md).
Don't move or delete this dotfiles folder after setup: your configs point to it.
