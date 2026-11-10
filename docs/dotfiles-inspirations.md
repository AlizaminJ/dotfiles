# Reviewed dotfiles ideas

Reviewed 2026-11-09. Counts were checked through GitHub's API; popularity is not a
security audit. The scope is now macOS only.

| # | Idea | Decision |
| --- | --- | --- |
| 1 | Machine-local configuration | Implemented; ignored file plus example, separate personal/work roots |
| 2 | Read-only doctor | Implemented; tools, safeguards, links, identities, keys, signing |
| 3 | Small shell setup | Implemented; plain zsh, Antidote pins, Starship, zoxide, fzf |
| 4 | Reliable Git identities | Implemented; scoped identities, `whoami`, `main`; signing deferred |
| 5 | Project tmux sessions | Implemented; `tat` and current-directory panes/windows; clipboard extras deferred |
| 6 | Portable agent rules | Implemented for Pi/Claude/Copilot; private state and optional UI excluded |
| 7 | VS Code preferences/extensions | Skipped; app and Copilot instruction reference only |
| 8 | Targeted macOS preferences | Implemented; extensions, Finder bars, no smart quotes/dashes |
| 9 | Selective task command | Implemented as `dotfiles`; preview, no updater/cleanup |
| 10 | Automatic safety checks | Tests and pinned CI workflow implemented; hosted run awaits push |

WezTerm replaced the initial terminal proposal after verifying the official
stable app's signature/notarization. It leaves sessions/panes to tmux. No Nix
migration, shell framework, or new dotfile manager was added.

## Source snapshots

All repositories exceeded 500 stars at review time:

| Repository | Stars | Snapshot |
| --- | ---: | --- |
| mathiasbynens/dotfiles | 31,514 | [b7c7894](https://github.com/mathiasbynens/dotfiles/tree/b7c7894e7bb2de5d60bfb9a2f5e46d01a61300ea) |
| thoughtbot/dotfiles | 8,168 | [939a270](https://github.com/thoughtbot/dotfiles/tree/939a27005b2dd4ac1556e104fc91122f3aea0a6c) |
| holman/dotfiles | 7,778 | [9a90082](https://github.com/holman/dotfiles/tree/9a90082b61fa5659789b9d41544c19098825a3ca) |
| paulirish/dotfiles | 4,359 | [d7607a4](https://github.com/paulirish/dotfiles/tree/d7607a4c2383bf7300032b2c7b89da87d6f9dcc5) |
| jessfraz/dotfiles | 3,563 | [840bf82](https://github.com/jessfraz/dotfiles/tree/840bf82166079aba320050eed0917d115356b7fb) |
| driesvints/dotfiles | 2,729 | [3204920](https://github.com/driesvints/dotfiles/tree/32049202c70c13445af8ea74c649b909696323ad) |
| alrra/dotfiles | 1,540 | [a810a23](https://github.com/alrra/dotfiles/tree/a810a2393aa8987e36e251b83fb79590f1382adc) |
| webpro/dotfiles | 1,243 | [acddce2](https://github.com/webpro/dotfiles/tree/acddce218937d94c76760562393d202b15cb3c6d) |
| kunchenguid/dotfiles | 690 | [9a4a638](https://github.com/kunchenguid/dotfiles/tree/9a4a6387d0dd6f4bf9b8a5a732b406916bbbf95d) |

Main influences: thoughtbot's local overrides/`tat`, holman's small topic-based
shell files, mathiasbynens' Git/macOS defaults, webpro's selective commands/CI,
and kunchenguid's selective shared-agent configuration. Ideas were adapted, not
installed wholesale; permission bypasses and aggressive cleanup were excluded.
