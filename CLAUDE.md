# CLAUDE.md

This project is the **x-livecast** agent skill (harness-agnostic).

**Read `SKILL.md` and follow it** — it is the source of truth. See also
`AGENTS.md` for a quick summary. Key points:

- Generate a brief via the "Generating a daily brief" recipe in `SKILL.md`
  (read `prompt.md` → pull X data → write `briefs/latest.json`).
- Voice room: `python3 scripts/voice_room.py` (needs `GEMINI_API_KEY`). Always-on:
  `XLC_PUBLIC_URL` + `scripts/ensure_room.sh --dm` (same URL daily). Demo:
  `--share --dm` quick tunnel. See `references/always-on.setup.md`.
- After a session: Synthesize → `drafts/latest.json`. Publish only with explicit
  confirm (`scripts/publish.py publish --confirm` or room UI). Never auto-post.
- Bundles: `scripts/bundle_tools.py export|import`.
- X access via `xurl`; posting via `xurl -X POST /2/tweets` (needs `tweet.write`).
- Never commit `.env`; confirm before posting to X. Checklist: `TESTING.md`.
