# Dependency safety

Require **7 days minimum age** for newly selected packages and dependencies,
across all installers. Prefer immutable pins and retained lockfiles. No silent
exceptions. Age/signature checks are provenance evidence, not malware detection.
Existing installations are not retroactively audited.

## pnpm and uv

- pnpm 12+: `minimumReleaseAge=10080`, strict checks, reject missing timestamps,
  `trustLockfile=false`, `ignoreScripts=true`.
- uv: `exclude-newer="7 days"` and `no-build=true`, for both normal and `uv pip`
  interfaces. Requires a uv version supporting relative durations; uv is not installed.
- User/project/environment/CLI settings can override defaults. Verify the effective
  graph before installing; old lockfiles are not proof of current policy compliance.
- uv's cutoff uses distribution upload times. Missing provenance/timestamps need
  review. `no-build` prevents source builds, not execution of installed Python code.
- Existing differing uv config is backed up, not merged; retain reviewed index
  settings privately. Never track registry credentials.

## Homebrew

`scripts/brew-packages.py` checks missing Brewfile packages and declared runtime
dependencies. It requires official taps and an exact recipe hash matching immutable
upstream source unchanged for at least 7 days. It rejects disabled packages, source
builds, formula post-install hooks, and cask installer packages/hooks.

The check uses **recipe age**, a conservative proxy, not registry upload age.
Even harmless recent edits can block installation. Embedded binary dependencies
are not individually age-audited. No generic machine-wide Homebrew safeguard exists.

Before installation, versions/hashes are rechecked. Dependencies install first,
formulae use bottles and are pinned, and automatic upgrades/cleanup are disabled.
Selections are retained in `~/.local/state/dotfiles/brew-review.json`. Failures,
rate limits, unknown dependencies, and hooks stop setup; request explicit review
rather than bypassing them. Homebrew itself must already be reviewed/installed.

```bash
python3 scripts/brew-packages.py Brewfile  # Read-only preflight.
```

A fixed checker bug decoded GitHub source through base64 JSON instead of raw CLI
output, which had rendered escape bytes differently. Checksums remain enforced.

## Shell plugins

Antidote 2.3.0 was published on 2026-08-07. Its fetch/pin/load path and these
plugin sources were reviewed on 2026-11-09; no plugin install scripts or submodules
are required:

| Plugin | Commit | Commit date |
| --- | --- | --- |
| zsh-users/zsh-autosuggestions | `85919cd1ffa7d2d5412f6d3fe437ebdbeeec4fc5` | 2025-06-24 |
| zsh-users/zsh-syntax-highlighting | `e6683f20e5c38d3e5447f45845d04ddda75d0f23` | 2026-10-09 |

The installer rejects unknown/too-young pins, verifies clean checked-out revisions,
and rejects submodules before activating the cache. Git pins alone do not establish
trust. Startup never fetches plugins. New pins require deliberate code/age review.

## Neovim

A fresh editor uses core settings only. `vim.pack` loads only existing locked
plugins; missing/unlocked plugins, automatic build hooks, Mason startup installs,
and parser auto-installs are blocked/disabled. Review the lock's source revisions,
ages, dependencies, and any builds before preparing plugins/tools separately.
The current lockfile is retained, not claimed to be newly audited. See
[Neovim notes](../nvim/README.md). Manual install/update commands still need review;
this configuration is not a sandbox.

## WezTerm

Official stable release `20240203-110809-5046fc22` (published 2024-02-03) was checked
on 2026-11-09. Its archive SHA256 is
`e77388cad55f2e9da95a220a89206a6c58f865874a629b7c3ea3c162f5692224`, also recorded in
Homebrew commit `6036456f4e329bd68fb5bed9f879df46e47892ba` dated 2026-09-20.
Strict/deep signature checks passed for Developer ID `P4A6FU9KZ3`; Gatekeeper
reported `accepted`, `source=Notarized Developer ID`.

Bootstrap and doctor recheck the installed app with `scripts/verify-wezterm.sh`.
No quarantine removal or Gatekeeper exception. A changed signing identity needs
review. At review time, the recipe had changed on 2026-11-06 12:08:18 UTC, so its
separate age gate could not pass before 2026-11-13 12:08:18 UTC, assuming no new edits.
Use macOS Terminal while installation is blocked.

Other installers and direct downloads require their own full dependency/source
review. If verification is unavailable, stop and ask; do not claim universal
technical enforcement. CI's preinstalled runner tools are covered separately in
[CI notes](ci.md).
