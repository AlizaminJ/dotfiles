# Global agent instructions

- Write plainly and briefly. Comments explain why, not obvious code.
- Start with the simplest direct solution. Add machinery only for a demonstrated need.
- Stay within scope; flag unrelated issues instead of fixing them unasked.
- Reproduce bugs where practical, test changed behavior, and report verification gaps.
- Verify user claims before relying on them; correct them plainly when they're wrong.
- Ask before destructive actions or large/expensive subagent runs. Don't add agent co-author credits unasked.
- Keep credentials and private data out of logs, public files, and generated drafts.

## Mandatory dependency safety

- New packages and all dependencies require ≥7-day release age, verified provenance, pinned sources/versions, and retained lockfiles. Check effective settings for every installer.
- Disable lifecycle scripts where supported; avoid source builds unless explicitly approved. Existing installs aren't retroactively audited.
- If age, provenance, or dependencies cannot be verified, stop and ask for an explicit exception. Never silently weaken these safeguards.

## Workflows

- For installs, secrets, or security audits, read `~/.agents/skills/security-review/SKILL.md`.
- For code or PR reviews, read `~/.agents/skills/code-review/SKILL.md`.
- For blog posts, read `~/.agents/skills/essayist/SKILL.md`.

Keep this file tool-neutral and useful across projects. Prune repetition; point to authoritative code/commands. Repository conventions add context, not permission to weaken safety rules. Tool-specific instruction files should reference this file, not copy it.
