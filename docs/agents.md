# Shared instructions

`agents/AGENTS.md` is the source for writing style, dependency safety, and review
rules. `dotfiles agents` installs these macOS references:

| Tool | Reference |
| --- | --- |
| Shared | `~/.agents/AGENTS.md` → repository file |
| Pi | `~/.pi/agent/AGENTS.md` → shared link |
| Claude | `~/.claude/CLAUDE.md` imports the shared file |
| Copilot | VS Code user `prompts/global.instructions.md` references it |

Differing instructions are backed up to numbered `.bak` files. Review/merge any
rules worth keeping before reloading agents. Matching references are unchanged
on repeat runs. Repository-level instructions still supply project-specific rules.

Pi respects an absolute `PI_CODING_AGENT_DIR`; use the same value for setup and Pi.
An existing `AGENTS.override.md` stops setup because it would hide the shared file.
The doctor checks both conditions. SDK-specific `agentDir` options are not detected.
Use Pi's `/reload` or start a new session after changing instructions.

Only instruction files are managed. No agent CLI, extension, package, settings,
auth, sessions, trust state, models, MCP config, skills, or caches are copied or
installed. Never link a whole private agent directory into this public repo.
Instructions guide behavior; they do not enforce permissions or sandbox code.
