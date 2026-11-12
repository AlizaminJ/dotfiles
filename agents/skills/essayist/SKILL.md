---
name: essayist
description: 'Turn a troubleshooting session, a design decision, or a workflow/pattern from the current conversation into a short, clear blog post in markdown. Use when the user says "write a blog post about this", "turn this into an essay", "summarize this fix for others", "document this troubleshooting", or after a non-trivial bug/incident/setup is resolved and worth sharing.'
---

# Essayist

## Privacy and consent

- Before showing or saving any draft, remove credentials, private identities, internal URLs, and confidential details. Use anonymous placeholders while keeping the technical explanation accurate.
- Ask permission before searching past sessions; use only the approved topic and scope, never unrelated conversation history.
- Ask before overwriting an existing file. Do not publish or upload drafts unless explicitly requested.

## Procedure

1. **Gather the material.**
   - If it happened in this conversation, use it directly.
   - For older material, follow the history-consent rule above and use an available history tool.
   - If history tools are unavailable, permission is declined, or details are missing, ask for the situation, options/steps considered, and outcome.

2. **Read [the writing guidance](./references/writing-guide.md) in full.** Use it to make editorial choices, not to fill a fixed outline.

3. **Extract the core facts** before writing:
   - The problem or motivation, including symptoms/error text when relevant.
   - The key reasoning or investigation steps that mattered.
   - The root cause, or reasoning behind the chosen approach.
   - The fix, or concrete implementation/example.
   - What the reader can use or learn, including any limitations or unresolved tradeoffs.

4. **Clarify preferences if needed:**
   - Intended audience, tone, and depth/length; don't force a choice between preset styles or word counts.
   - Destination: print in chat, or save to a file? For a file, ask for its path/filename.

5. **Draft and check.** Choose structure and voice for this article, using the guidance. Check the technical facts and privacy rules before delivering.

6. **Output.** Print the markdown in chat or save it to the requested destination.
