---
name: code-review
description: Review code, diffs, pull requests, or review comments for actionable bugs, regressions, maintainability, and test gaps. Use when asked to review changes or decide whether a review suggestion is worth applying.
---

# Code review

1. Establish the intended behavior and read the diff plus surrounding callers/tests.
2. Look for correctness and performance problems, regressions, duplicate logic, unclear interfaces, and missing tests. Use `security-review` for security-specific checks.
3. Prefer an end-user reproduction using existing tools when practical. Don't introduce a heavy test framework just to reproduce a small bug.
4. Weigh each suggestion against complexity, maintenance, side effects, and risk. Only implement fixes when requested; explain why other suggestions aren't worth pursuing. Flag unrelated failures rather than expanding the task.
5. For changed behavior, expect regression tests, clear names, focused functions, and useful public API documentation. Update generated files through their source/generator, not by hand.
6. Report findings as `[CRITICAL]`, `[WARNING]`, or `[NIT]`, with file/line, concrete impact, and the smallest useful fix. Separate confirmed problems from assumptions; avoid speculative nits.
7. When addressing PR comments, reply in the original thread and match the comment's language. Explain what changed and leave resolution to the author. If posting isn't available or authorized, draft the reply instead. Write PR titles and descriptions in English.
8. End every review report, including reports with no findings, with a separate final line: `- <MODEL>`. Use the exact public model name/ID from trusted runtime/session metadata. If unavailable, write `- Model unknown`; never guess or expose private provider URLs/deployment details.

If no actionable issues are found, say so. State what was tested and what remains unverified; don't claim a clean bill of health from a partial review.
