# AGENTS.md

This project is the **x-feed-loop** harness-agnostic agent skill.

Read `SKILL.md` and follow it. It is the single source of truth for composing
the official X skill with X Feed Loop's local state CLI.

Key constraints:

- Use the official X skill / `xurl` for every X read and write.
- Do not add X API calls, model calls, a chat runtime, or a web service here.
- Use `x-feed-loop` only for local posts, Reaction Cards, drafts, and memory.
- Preserve source URLs and the user's raw reactions.
- Never publish without showing the exact draft and receiving explicit approval.
- Run `python3 -m unittest discover -s tests -v` and the skill validator before release.
