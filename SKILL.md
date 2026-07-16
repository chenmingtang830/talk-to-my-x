---
name: x-livecast
description: >-
  Turn the user's X feed into a personalized audio brief on demand (any time, as
  often as they want) and open a real-time, interruptible voice room hosted by
  Gemini Live — landed as a link in the user's own X DMs so they can open it on
  their phone and listen/interrupt on the road. The brief is driven by the
  user's editable prompt.md; the agent harness pulls X data and writes the
  brief, then the voice room reads it and the user can barge in to ask
  questions and pull fresh X data live. Use when the user asks for their
  daily/X brief, wants to talk to their feed, or says things like "start my
  livecast" / "生成我的简报" / "早上的直播简报".
version: 0.1.0
homepage: https://github.com/richardtang/live-x-podcast
license: MIT
---

# X-LiveCast

A **harness-agnostic agent skill** that runs **entirely on the user's local
machine**. It turns the user's X feed into a personalized audio brief **on
demand** and opens a real-time, interruptible voice room hosted by the **Gemini
Live API** (native audio, automatic-VAD barge-in, free developer tier).

## Works with any agent harness

This is just `SKILL.md` (instructions) + `scripts/` + `prompt.md`. Nothing here
is tied to a specific agent. Any harness that can read instructions, run shell,
and call tools works — **Claude Code, Codex, Cursor, Gemini CLI, OpenClaw, …**.
Each harness just needs its usual entry file pointing here:

| Harness | Entry file (points to this SKILL.md) |
| --- | --- |
| Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Cursor | `AGENTS.md` / `.cursor/rules` |
| Gemini CLI | `GEMINI.md` |
| OpenClaw | `SKILL.md` |

X auth is handled by `xurl` (independent of the harness), so no harness-specific
integration is required.

## Division of labor (important)

The **agent harness** is the outer brain: it already has an LLM, tool-calling,
and scheduling, so it does the text work — read `prompt.md`, pull X data (via the
X MCP or `scripts/x_tools.py`), and write the brief. This skill provides the
**X tools, the prompt/brief format, and the voice layer** (the part a text
harness can't do). Text = harness's model. Voice = Gemini Live.

## What this skill does

1. **Generate a brief on demand** (any time, as often as the user wants): the
   harness runs the recipe below — read `prompt.md` → pull X data → write
   `briefs/latest.json`. Optionally scheduled via cron; not tied to "morning".
2. **Live voice room**: `python3 scripts/voice_room.py` opens the room; the host
   reads `briefs/latest.json` and the user can **interrupt any time** to ask
   follow-ups. During the call the host calls X tools (`search_x`,
   `get_home_timeline`) for fresh data.
3. **Regenerate to X** (Phase D): after the call, the harness turns the brief +
   conversation into a polished post and publishes via `xurl -X POST /2/tweets`
   (the hosted X MCP is read-only; posting uses direct `xurl` + `tweet.write`).

## Architecture: always-on host, phone is the remote

The server (`scripts/voice_room.py`) runs on the **harness host** — ideally an
always-on box (OpenClaw on a Mac Mini / VPS, etc.). Briefs, sessions, and drafts
live on that host's disk. The phone only opens an HTTPS URL.

Primary design:

1. **`XLC_PUBLIC_URL`** — one evergreen HTTPS origin (named Cloudflare tunnel or
   reverse proxy). Daily cron regenerates the brief and DMs **the same URL**.
2. **The real `GEMINI_API_KEY` never reaches the browser.** The server mints a
   short-lived Gemini **ephemeral token** per session (`/v1alpha/auth_tokens`).
3. **Mobile needs HTTPS** for mic access — localhost is fine on the host
   machine; phones need the public HTTPS origin (not a bare LAN HTTP IP).

```
Always-on host ── voice_room.py (XLC_PUBLIC_URL)
                    ├─ briefs/  sessions/  drafts/  memory/
                    ├─ GET /config → Gemini ephemeral token
                    └─ cron: brief → ensure_room → --dm-only (same URL)
Phone ── HTTPS ──> room UI ── access_token ──> Gemini Live (constrained WS)
```

Demo-only: `--share` with `XLC_TUNNEL_MODE=quick` spins a temporary
`*.trycloudflare.com` link (dies when the process stops; URL changes every run).

Modes:

```bash
# Always-on (set XLC_PUBLIC_URL + named tunnel / reverse proxy first):
python3 scripts/voice_room.py --share          # bind; do not invent a new URL
python3 scripts/voice_room.py --dm-only        # DM evergreen URL; room already up
bash scripts/ensure_room.sh --dm               # health-check, start if needed, DM

# Local laptop demo:
python3 scripts/voice_room.py                  # http://localhost:8787
python3 scripts/voice_room.py --share --dm     # quick tunnel demo (if no XLC_PUBLIC_URL)
```

Optional: set `XLC_ROOM_TOKEN` so `/config` and session/tool APIs require
`X-XLC-Token` / `?token=` (the DM helper appends the token to the shared URL).

## Prerequisites

- A free Gemini API key: https://aistudio.google.com/apikey (no billing needed).
  Set `GEMINI_API_KEY` (see `.env.example`).
- Python 3.9+ (the local server uses only the standard library — no pip install).
- `xurl` for X access (see below). No specific agent harness is required.
- **Always-on:** a stable HTTPS front (`XLC_PUBLIC_URL`) — named Cloudflare
  tunnel or any reverse proxy. Quick tunnels are demo-only.
- (Optional, demo) `cloudflared` — `brew install cloudflared`.
- (Optional) any scheduler for recurring briefs — your harness's cron, system
  `cron`, or e.g. `openclaw cron`.

## Usage

### Try the voice room locally (no X credentials needed)

```bash
export GEMINI_API_KEY=...          # or put it in .env
python3 scripts/voice_room.py      # starts localhost:8787 and opens the browser
```

Speak to interrupt the briefing at any time. Press Pause to freeze mid-sentence
(resumes seamlessly); mute the mic; Hang up keeps the thread.

### On the road (primary): always-on URL in your DMs

1. Point a named tunnel / reverse proxy at `XLC_PORT` and set `XLC_PUBLIC_URL`.
2. Keep the room up on the host (`python3 scripts/voice_room.py --share`, or
   `scripts/ensure_room.sh`).
3. After generating today's brief, DM the **same** link:

```bash
# After the brief recipe writes briefs/latest.json:
bash scripts/ensure_room.sh --dm
# or: python3 scripts/voice_room.py --dm-only
```

Open the evergreen link on your phone — today's brief and prior threads are on
the host. Quick-tunnel `--share --dm` remains available for demos only.

### Connect live X data (real agent tools)

During the call the host can call `search_x`, `get_home_timeline`,
`get_user_posts`, `get_bookmarks`, `get_post` (open one status URL — text +
linked article cards), `get_post_replies` (recent comments under a post), and
`read_url` (fetch a non-X article body after `get_post` shows a linked URL).
text — e.g. when a post links out and the user wants to know what it says).
These use
the official X CLI `xurl` (same auth as X's hosted MCP), which runs locally and
handles OAuth. One-time setup:

```bash
brew install --cask xdevplatform/tap/xurl
xurl auth apps add my-app --client-id YOUR_CLIENT_ID --client-secret YOUR_SECRET
xurl auth oauth2 --app my-app        # browser login once
python3 scripts/x_tools.py search "ai voice agents" 3   # verify
```

Until `xurl` is set up, tool calls return a clear "not connected" message and
the host continues. X API is pay-per-use (~$0.005/read). Posting is not exposed
during the live call — it happens in the outer agent (Phase D) with confirmation.

## Generating a daily brief (recipe for the harness)

This is not a script — it's a task the agent harness runs (on demand or via
cron). When the user asks for a brief (or on schedule), do the following:

1. **Read `prompt.md`** in the skill root — it defines the user's topics,
   accounts, tone, length, and which sources to pull. Treat it as instructions.
   Optionally skim `memory/USER.md` and `memory/TASTE.md` if present (Phase 1.5
   taste memory) and fold durable prefs into the brief.
2. **Pull X data** for the sources the prompt asks for. Prefer the hosted **X
   MCP** if connected (`get_users_timeline`, `get_users_bookmarks`,
   `search_posts_all`, `get_trends_by_woeid`, `search_news`). If MCP isn't
   available, use `scripts/x_tools.py` (`search_x`, `get_home_timeline`,
   `get_bookmarks`) or `xurl` directly.
   - **Only-new (memory):** for bookmark-based briefs, use
     `python3 scripts/x_tools.py bookmarks-new N` — it returns only items not yet
     briefed (tracked in `.state/seen.json`). After writing the brief, record
     them with `python3 scripts/x_tools.py mark-seen bookmarks <ids...>` so the
     next run only covers newly-added bookmarks.
3. **Synthesize a spoken brief** following the prompt's style/length. Keep it
   tight; name who said what **by display name** (e.g. "Peter Steinberger"),
   not `@handle` — handles are for links, not speech. Skip low-signal noise.
4. **Write `briefs/latest.json`** using the schema in
   `references/brief.schema.example.json`. The only required field is `script`
   (what the voice host reads aloud). **Also include `items`, and give each
   source a structured object — `{"author", "name", "id", "url"}` — not a bare
   `"@handle"` string.** `name` is the display name used in the spoken script;
   `author` is the @handle used for links. The voice room passes this to the
   model as grounding: when the user asks about something specific in the brief,
   the model should use the exact source it already has (via `get_post`) instead
   of a broad re-search. Bare handles still work but lose this grounding.
5. (Optional) Tell the user it's ready, or ensure the always-on room and DM the
   evergreen link: `bash scripts/ensure_room.sh --dm`.

The user can run this **as many times a day as they want** — each run overwrites
`briefs/latest.json`. Keep history by snapshotting a timestamped copy
(`cp briefs/latest.json briefs/$(date +%Y%m%dT%H%M%S).json`).

### Memory / preferences / history (local, file-based)

- **Preferences:** `prompt.md` (the user edits it; persistent).
- **Taste memory (Phase 1.5):** optional `memory/USER.md` + `memory/TASTE.md` —
  curated listener prefs the brief/recap recipes may read. Not a full memory DB.
- **History:** timestamped `briefs/*.json`; `latest.json` = most recent.
  Conversation threads: `sessions/<id>.json`.
- **"Only new":** `.state/seen.json` records ids already briefed per source, so a
  repeat run covers only newly-added items (see `bookmarks-new` / `mark-seen`).

### Then talk to it

```bash
python3 scripts/voice_room.py     # reads briefs/latest.json, opens the room
# Always-on host already running:
#   open XLC_PUBLIC_URL on your phone (or --dm-only to re-send the link)
```

### Optional: schedule brief + ensure room

Any scheduler works — your harness's cron, system `cron`, etc. Not limited to
mornings. Examples:

```bash
# After the harness writes briefs/latest.json, keep the room up and DM the same URL:
# bash scripts/ensure_room.sh --dm

# System cron (harness-agnostic):
# 0 7 * * *  cd /path/to/x-livecast && <your-agent-cli> "Generate my daily brief (see SKILL.md)" && bash scripts/ensure_room.sh --dm

# OpenClaw, if that's your harness:
# openclaw cron add "0 7 * * *" "Generate my x-livecast daily brief (see SKILL.md recipe), then ensure_room --dm" --agent main --session isolated
```

## Conversation threads (resume + synthesize)

A LiveCast conversation is a **thread**, not a one-shot call:

1. **Hang up** stops the live mic/voice socket but **keeps the transcript**.
2. Come back later → pick the thread → **Continue** opens a new Gemini Live
   session with prior turns injected as context (Gemini Live itself can't
   resume a socket; we reconstruct continuity from the saved transcript).
3. **Synthesize** (not End) turns the thread into `drafts/latest.json` using
   `recap_template.md` + a text Gemini model. Publishing to X stays a separate,
   confirmed step.

Sessions live in `sessions/<id>.json` (and `sessions/latest.json`).

## Generating a recap draft after a session (recipe for the harness)

When the user taps **Synthesize** in the room, the server writes the draft
directly. If you're doing it from the harness instead:

1. **Read `sessions/latest.json`** (or a specific `sessions/<id>.json`) and
   **`recap_template.md`**.
2. **Synthesize a draft** from the *whole* session — not just the brief.
3. **Write `drafts/latest.json`** per `references/draft.schema.example.json`.
4. **Do not auto-post** — publishing to X is a separate, confirmed step.

Or hit the room's API: `POST /synthesize` with `{"session_id": "..."}`.

## Publishing a draft (confirmed — never auto-post)

After Synthesize (or a harness-written `drafts/latest.json`):

1. **Show the user the draft** (`text` or `thread` + sources). Let them edit.
2. **Ask for explicit confirmation** before any write to X.
3. **Publish** only after they confirm:
   - Room UI: **Publish to X** (browser confirm dialog → `POST /publish` with
     `{"confirm": true, "draft_id": "...", "text"|"thread": ...}`).
   - CLI: `python3 scripts/publish.py publish --draft latest --confirm`
   - Or `xurl -X POST /2/tweets` yourself (single post), / thread replies with
     `reply.in_reply_to_tweet_id`.
4. On success the draft gains `published_at`, `tweet_ids`, `urls`.
5. **Never** post from Synthesize, cron, or an unconfirmed harness step.
   Needs `tweet.write` (often OAuth 1.0a Read+Write on the X app).

## Feed bundles (export / import)

A **bundle** is a portable pack of feed preferences (`prompt.md` + optional
`memory/TASTE.md`) — not a session recording.

```bash
python3 scripts/bundle_tools.py export
python3 scripts/bundle_tools.py import bundles/latest.json   # backs up prompt.md → .bak
```

Schema: `references/bundle.schema.example.json`. Host/CLI only (not in the room UI).
Optional: after export, ask the user if they want to **confirm-post** a short intro
tweet pointing people at the JSON (same confirm rules as Publishing).

## Always-on vs demo

| Mode | When | How |
| --- | --- | --- |
| **Basic / demo** | Laptop tryout | `python3 scripts/voice_room.py --share --dm` (temporary `*.trycloudflare.com`) |
| **Advanced / daily** | Always-on host (Mac Mini, VPS, OpenClaw gateway) | Set `XLC_PUBLIC_URL`, keep room up, `bash scripts/ensure_room.sh --dm` |

Step-by-step named tunnel + gateway recipe: [`references/always-on.setup.md`](references/always-on.setup.md).
Local files (sessions, drafts, memory, what belongs in `.env`): [`references/local-layout.md`](references/local-layout.md).
Manual release checklist: [`TESTING.md`](TESTING.md).

## Configuration

See `references/config.example.md` and `.env.example`. Key settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `GEMINI_API_KEY` | (required) | Free Gemini key, used only on the host |
| `XLC_PORT` | `8787` | Voice-room port |
| `XLC_PUBLIC_URL` | (unset) | Evergreen HTTPS origin for DMs / phones |
| `XLC_TUNNEL_MODE` | `named` if public URL else `quick` | `named` \| `quick` \| `none` |
| `XLC_ROOM_TOKEN` | (unset) | Optional gate for sensitive APIs |
| `XLC_GEMINI_MODEL` | `gemini-3.1-flash-live-preview` | Gemini Live model (latest) |
| `XLC_GEMINI_VOICE` | `Puck` | Prebuilt voice (Puck, Charon, Kore, Fenrir, Aoede) |
| `XLC_SYNTH_MODEL` | `gemini-2.5-flash` | Text model for Synthesize |

## Roadmap

- [x] A. Scaffold (skill file, structure)
- [x] B. Local voice room (barge-in, pause, captions) + in-call X tools
- [x] C. On-demand daily brief via harness recipe (`prompt.md` → `briefs/latest.json`)
- [x] C.5. On-the-road sharing (ephemeral tokens + tunnel + DM link) and session
      threads (`sessions/<id>.json`) + in-room **Synthesize** → `drafts/latest.json`
- [x] C.6. Always-on host persona (`XLC_PUBLIC_URL`, `ensure_room`, optional room token,
      light `memory/` scaffold)
- [x] D. Review + confirmed publish UI / `POST /publish` + threaded `xurl` posting
- [x] E. Feed bundle export/import (`bundle_tools` CLI; host-side, not room UI)
- [ ] Later: richer evolving memory, ClawHub packaging polish
