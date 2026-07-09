# CLAUDE.md

This project is the **x-livecast** agent skill (harness-agnostic).

**Read `SKILL.md` and follow it** — it is the source of truth. See also
`AGENTS.md` for a quick summary. Key points:

- Generate a brief via the "Generating a daily brief" recipe in `SKILL.md`
  (read `prompt.md` → pull X data → write `briefs/latest.json`).
- Voice room: `python3 scripts/voice_room.py` (needs `GEMINI_API_KEY`). On the
  road: `--share --dm` DMs a temporary HTTPS link to the user's X account.
- After a session ends: "Generating a recap draft" recipe in `SKILL.md` —
  read `sessions/latest.json` + `recap_template.md`, write `drafts/latest.json`.
- X access via `xurl`; posting via `xurl -X POST /2/tweets` (needs `tweet.write`).
- Never commit `.env`; confirm before posting to X.
