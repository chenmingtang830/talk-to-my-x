# AGENTS.md

This project is the **x-livecast** agent skill (harness-agnostic).

**Read `SKILL.md` and follow it.** It is the single source of truth for what
this skill does and how to run it (generating a daily X brief, and the live
voice room).

Quick facts for the agent:

- Generate a brief: `python3 scripts/generate_brief.py`, room **Generate today’s
  brief** (`POST /brief/generate`), or the harness recipe in `SKILL.md` —
  read `prompt.md` (and optional `memory/USER.md` / `memory/TASTE.md`), pull X
  data (X MCP or `scripts/x_tools.py`), write `briefs/latest.json` (schema:
  `references/brief.schema.example.json`). Cloud: `references/render.setup.md`.
- Talk to it: `python3 scripts/voice_room.py` (needs `GEMINI_API_KEY` in `.env`).
  Always-on: set `XLC_PUBLIC_URL`, keep the room up, then
  `bash scripts/ensure_room.sh --dm` or `python3 scripts/voice_room.py --dm-only`
  (same evergreen URL daily). Demo-only: `--share --dm` quick tunnel.
  Setup: `references/always-on.setup.md`.
- After a session: Synthesize in-room or "Generating a recap draft" in `SKILL.md`
  → `drafts/latest.json`. **Never auto-post.**
- Publish only after explicit user confirm: room **Publish to X**, or
  `python3 scripts/publish.py publish --confirm`, or `POST /publish` with
  `"confirm": true`. Needs `tweet.write`. See "Publishing a draft (confirmed)".
- Bundles: `python3 scripts/bundle_tools.py export|import` (see SKILL "Feed bundles").
- X access is via the `xurl` CLI. Posting uses `xurl -X POST /2/tweets`.
- Do not commit `.env`. Confirm before posting to X or other destructive actions.
- Manual checklist: `TESTING.md`.
