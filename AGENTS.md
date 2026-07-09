# AGENTS.md

This project is the **x-livecast** agent skill (harness-agnostic).

**Read `SKILL.md` and follow it.** It is the single source of truth for what
this skill does and how to run it (generating a daily X brief, and the live
voice room).

Quick facts for the agent:

- Generate a brief: follow the "Generating a daily brief" recipe in `SKILL.md` —
  read `prompt.md`, pull X data (X MCP or `scripts/x_tools.py`), write
  `briefs/latest.json` (schema: `references/brief.schema.example.json`).
- Talk to it: `python3 scripts/voice_room.py` (needs `GEMINI_API_KEY` in `.env`).
  On the road: `python3 scripts/voice_room.py --share --dm` DMs a temporary
  HTTPS link to the user's own X account.
- After a session ends, follow "Generating a recap draft after a session" in
  `SKILL.md` — read `sessions/latest.json` + `recap_template.md`, write
  `drafts/latest.json`. Never auto-post.
- X access is via the `xurl` CLI (OAuth handled locally). Posting uses
  `xurl -X POST /2/tweets` (requires `tweet.write`); the hosted X MCP is read-only.
- Do not commit `.env`. Confirm before posting to X or other destructive actions.
