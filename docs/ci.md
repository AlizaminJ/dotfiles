# CI and publication checks

`.github/workflows/checks.yml` runs on pushes, pull requests, and manual dispatch.
It takes effect once committed/pushed; its first hosted execution is still pending.

| Job | Runner | Checks |
| --- | --- | --- |
| ShellCheck | Ubuntu 24.04 | Preinstalled ShellCheck, Bash scripts only |
| macOS | macOS 15 | Secrets, system Bash/zsh syntax, `dotfiles test` |

Ubuntu is lint infrastructure, not an additional supported dotfiles target.
No package installation or bootstrap runs. Tests use temporary homes, mocked
system commands, and isolated tmux sockets. Native tmux/Lua/Neovim tests skip if
not installed; native WezTerm validation requires `WEZTERM_TEST_BINARY` explicitly.
Real fresh-Mac testing is still required.

Permissions are `contents: read`. Ordinary PR events are used, not privileged
`pull_request_target`; no user secrets, retained checkout credentials, submodules,
LFS, cache, or deployment actions. Old runs are cancelled; jobs have time limits.

The only action is checkout at `d23441a48e516b6c34aea4fa41551a30e30af803`
(commit 2026-07-16). Metadata, entry point, fetch/auth/cleanup source, and bundled
runtime path were reviewed on 2026-11-09. It executes shipped Node 24 JavaScript,
not a fresh registry dependency resolution. Future changes need a new age/source
review. GitHub manages runner images and preinstalled tools; OS labels do not
pin immutable images, and those existing tools are not retroactively age-audited.

## Before publishing

```bash
./bin/dotfiles secrets
./bin/dotfiles test
git diff --check
```

The secret scan covers public Git candidates, the staged index, and available
reachable file/commit history. CI fetches full history for that check. Ignored
private files are not read; force-adding one is detected. Common credentials,
private keys, private state filenames, and personal home paths are flagged by
location only. **No matching values are printed.** Non-noreply Git contact
addresses produce a redacted privacy warning, not a credential failure; decide
whether they may remain public before pushing.

This lightweight scan is not proof that every possible secret is absent. Review
both staged/unstaged diffs, attachments, and Git author metadata before publishing.
Never commit `.env`, local settings, SSH keys, agent state, or private registry
credentials. If a real credential was committed, revoke it and review history
cleanup before publishing; ignoring the file later does not remove the leak.

Optional branch protection can require the two checks; repository settings are
not changed automatically. Local ShellCheck remains unavailable unless obtained
through a reviewed route; no linter was installed on this Mac for this change.
