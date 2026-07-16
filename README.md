# X-LiveCast

**v1** — harness-agnostic agent skill: turn your X feed into an on-demand audio
brief, open a **real-time interruptible** Gemini Live voice room, continue
threads later, **Synthesize → review → confirm-publish** to X, and share a
portable **feed bundle**. Entry on the road is a link in your own X DMs.

Works with any agent: **Claude Code, Codex, Cursor, Gemini CLI, OpenClaw, …** —
each reads `AGENTS.md` / `CLAUDE.md` → `SKILL.md`. X auth is via `xurl`.

> **Needs:** free `GEMINI_API_KEY` + Python 3.9+ (stdlib only). **Optional:**
> `xurl` (live tools + DM + publish), always-on HTTPS host. **Never auto-posts**
> — publishing always requires an explicit confirm. Manual checklist: [`TESTING.md`](TESTING.md).

## Local vs cloud (how to operate)

**Full step-by-step checklists:** [`references/run-modes.md`](references/run-modes.md).

| | **Local** (start here) | **Cloud (Render)** |
| --- | --- | --- |
| Host | Your laptop | Render Web Service + Disk |
| UI | `http://localhost:8787` | `https://…onrender.com` |
| Setup | [Quick start](#quick-start-voice-room-demo) below | [`references/render.setup.md`](references/render.setup.md) |
| Always-on tunnel (non-Render) | — | [`references/always-on.setup.md`](references/always-on.setup.md) |

Sessions, briefs, and drafts live on the **host disk**, not on the phone.
Where each file goes: [`references/local-layout.md`](references/local-layout.md).

## Why it's different

- **Real-time barge-in voice** — interrupt mid-sentence (Gemini Live VAD).
- **On-demand, prompt-driven** — edit `prompt.md`, regenerate anytime.
- **Harness does the thinking** — your agent writes the brief; this skill owns
  X tools, format, and the voice layer.
- **Live X tools** mid-call (`search_x`, timeline, bookmarks, `get_post`, …).
- **Confirmed publish** — Synthesize → edit → Publish to X (threaded supported).
- **Feed bundles** — export/import `prompt.md` (+ taste) as JSON.
- **On the road** — ephemeral Gemini tokens only; prefer always-on HTTPS.

## Quick start (voice room demo)

```bash
cp .env.example .env      # set GEMINI_API_KEY
python3 scripts/voice_room.py
```

Browser → `http://localhost:8787` → **Start**. Hang up keeps the thread;
**Synthesize** builds a draft; **Publish to X** asks for confirm first.

Env: `XLC_PORT`, `XLC_GEMINI_MODEL` (Live voice), `XLC_SYNTH_MODEL` (Generate brief /
Synthesize text), `XLC_GEMINI_VOICE` — see `.env.example`.

### On the road: always-on URL (primary)

Set `XLC_PUBLIC_URL` to your named tunnel / reverse-proxy HTTPS origin, keep
`python3 scripts/voice_room.py --share` running on the host, then:

```bash
bash scripts/ensure_room.sh --dm
# or: python3 scripts/voice_room.py --dm-only
```

Full steps: [`references/always-on.setup.md`](references/always-on.setup.md).
Optional `XLC_ROOM_TOKEN` gates APIs; DM appends `?token=…`.

### Demo: temporary quick tunnel

```bash
brew install cloudflared
# unset XLC_PUBLIC_URL (or XLC_TUNNEL_MODE=quick)
python3 scripts/voice_room.py --share --dm
```

### Connect live X data

```bash
brew install --cask xdevplatform/tap/xurl
xurl auth apps add my-app --client-id YOUR_CLIENT_ID --client-secret YOUR_SECRET
xurl auth oauth2 --app my-app        # reads / DMs
# For publishing, app needs Read and Write — often also:
# xurl auth oauth1 --app my-app
python3 scripts/x_tools.py search "ai voice agents" 3
```

## Generate a brief

Ask your agent to run the recipe in `SKILL.md` (“Generating a daily brief”):
reads `prompt.md` (+ optional `memory/`), pulls X, writes `briefs/latest.json`.

## Synthesize → publish

1. In the room: **Synthesize** → edit the draft panel.
2. **Publish to X** → confirm → posts via `xurl` (`POST /publish` requires
   `"confirm": true`). Or CLI: `python3 scripts/publish.py publish --confirm`.
3. Harness recipe: “Publishing a draft (confirmed)” in `SKILL.md`.

## Feed bundles

```bash
python3 scripts/bundle_tools.py export
python3 scripts/bundle_tools.py import bundles/latest.json
```

Schema: `references/bundle.schema.example.json`. Host/CLI only (not in the room UI).

## How it works

```
Always-on host ──runs──> scripts/voice_room.py (XLC_PUBLIC_URL)
                                      ├─ web/ UI + sessions/ drafts/ bundles/
                                      ├─ GET /config → Gemini ephemeral token
                                      ├─ POST /publish (confirm required)
                                      └─ ensure_room / --dm-only → evergreen DM
Phone ── HTTPS ──> room ── access_token ──> Gemini Live (constrained WS)
```

## Project layout

```
x-livecast/
├── SKILL.md                 # source of truth + recipes
├── TESTING.md               # manual release checklist
├── AGENTS.md / CLAUDE.md
├── prompt.md / recap_template.md
├── memory/                  # USER.md + TASTE.md (optional)
├── scripts/
│   ├── voice_room.py
│   ├── ensure_room.sh
│   ├── publish.py
│   ├── bundle_tools.py
│   └── x_tools.py
├── web/
├── references/
│   ├── local-layout.md      # sessions / drafts / memory / .env vs docs
│   ├── always-on.setup.md
│   └── *.schema.example.json
├── briefs/ sessions/ drafts/ bundles/   # runtime JSON (gitignored)
│   ├── always-on.setup.md
│   ├── config.example.md
│   ├── brief.schema.example.json
│   ├── draft.schema.example.json
│   └── bundle.schema.example.json
├── briefs/ sessions/ drafts/ bundles/
└── .env.example
```

## Roadmap

| Phase | Scope | Status |
| --- | --- | --- |
| A–C.6 | Scaffold, voice room, brief, share, always-on, sessions, synthesize | done |
| D | Review + confirmed publish (single + thread) | done |
| E | Feed bundle export/import | done |
| Later | Richer evolving memory, ClawHub packaging polish | open |

## License

MIT — see `LICENSE`.
