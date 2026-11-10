# Global agent instructions

These rules apply in every repository. A repository's own AGENTS.md adds to them and wins on conflict, subject to the tool's higher-priority instructions.

## Comments and written explanations

Mandatory. Applies to code comments, docstrings, PR descriptions and commit messages.

- Write for a teammate who has never seen this code. Plain everyday words, no jargon.
- Explain why, not what. Never restate the next line of code.
- Keep it as short as possible.
- If a technical term is unavoidable, say what it means in plain words or use an everyday analogy. Example: "time.monotonic() is a stopwatch: it keeps counting even if the server clock is adjusted."
- Before finishing, re-read every comment you added. If a new teammate would need to look something up to understand it, rewrite it.

## Dependency safety

- Require a minimum release age of 7 days for newly selected packages and all dependencies, across every installer: pnpm, uv, Homebrew, plugin managers, and others.
- Disable dependency lifecycle scripts where supported. For uv, avoid source builds unless explicitly approved; installed packages can still execute when used.
- Prefer pinned versions, immutable source revisions, and retained lockfiles. Check effective project settings before installing; global settings can be overridden.
- pnpm settings do not protect other installers. Verify their full resolved dependency graph and source/release ages separately; do not assume equivalent safeguards exist.
- Review executable plugin code and its dependencies before installing. Git pins alone do not establish age or safety.
- If provenance, age, or dependencies cannot be verified, stop and ask for an explicit exception. Never silently weaken safeguards.
- Existing installations are not retroactively audited. Keep credentials out of logs and tracked files.

## Code reviews

- Before acting on a review suggestion, weigh its benefit against complexity, maintenance, and risk. Apply worthwhile changes; explain when a suggestion is not worth pursuing.
- Check surrounding code for side effects, duplicate logic, and existing patterns.
- Raise actionable issues that add real value. Challenge suggestions rather than applying them blindly.
- Prioritize security flaws, performance problems, missing tests, and unclear code.
- Expect tests for new behavior and bug fixes; clear names, focused functions, and useful public API documentation.
- Group findings as `[CRITICAL]`, `[WARNING]`, or `[NIT]`. Include the file and line, why it matters, and a minimal fix example when useful.
- When addressing review comments, reply in the original thread with what changed. Leave it open for the author to resolve.
- If no actionable issues are found, say so. Note any gaps in testing or verification.

## Maintaining this file

- This file is the single source of truth for shared rules. Keep it tool-neutral.
- On each machine, `~/.agents/AGENTS.md` links to this file in the dotfiles checkout.
- Edit shared rules here and sync this repository across machines.
- Tool-specific instruction files should only reference this file, not repeat its rules.
- Claude imports it from `~/.claude/CLAUDE.md` with `@~/.agents/AGENTS.md`.
- Copilot references it from a user-level `global.instructions.md` file.
- Pi's agent-directory `AGENTS.md` links to `~/.agents/AGENTS.md`; the directory defaults to `~/.pi/agent` and respects `PI_CODING_AGENT_DIR`.
- Keep repository-specific rules in each repository's own AGENTS.md.