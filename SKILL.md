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

## Architecture: local server, remote-capable by design

The server (`scripts/voice_room.py`) always runs wherever the harness runs —
your laptop, a cloud box, doesn't matter. But the **primary use case is
"on the road"**: the device you listen from (your phone) is usually a
*different* device than the one running the harness, and it's away from home
WiFi. That drives two design decisions:

1. **The real `GEMINI_API_KEY` never reaches the browser.** The server mints a
   short-lived Gemini **ephemeral token** per session (`/v1alpha/auth_tokens`,
   ~30 min, single session) and the browser connects with that instead. This is
   always on, not just for sharing — it's free and strictly safer.
2. **Mobile browsers require HTTPS (or localhost) for microphone access** — a
   plain LAN IP (`http://192.168.x.x`) will not get mic permission on a phone.
   So real remote/mobile access needs an HTTPS tunnel, not just port-forwarding.

```
Agent harness (anywhere) ──runs──> scripts/voice_room.py
                                      ├─ serves web/ (voice room UI)
                                      ├─ GET /config → mints a Gemini ephemeral token
                                      └─ --share → cloudflared quick tunnel (HTTPS, temporary)
                                           └─ --dm → xurl DMs the link to your own X account
Phone browser ── access_token=<ephemeral> ──> wss://generativelanguage.../BidiGenerateContentConstrained
```

Modes:

```bash
python3 scripts/voice_room.py                # local only: http://localhost:8787
python3 scripts/voice_room.py --share        # + public HTTPS link (cloudflared, no account)
python3 scripts/voice_room.py --share --dm   # + DM that link to your own X account (the "on the road" flow)
```

The tunnel is temporary — it dies when the process stops. Requires
`brew install cloudflared` (or the download from `pkg.cloudflare.com`).

## Prerequisites

- A free Gemini API key: https://aistudio.google.com/apikey (no billing needed).
  Set `GEMINI_API_KEY` (see `.env.example`).
- Python 3.9+ (the local server uses only the standard library — no pip install).
- `xurl` for X access (see below). No specific agent harness is required.
- (Optional, for `--share`/`--dm`) `cloudflared` — `brew install cloudflared`.
- (Optional) any scheduler for recurring briefs — your harness's cron, system
  `cron`, or e.g. `openclaw cron`.

## Usage

### Try the voice room locally (no X credentials needed)

```bash
export GEMINI_API_KEY=...          # or put it in .env
python3 scripts/voice_room.py      # starts localhost:8787 and opens the browser
```

Speak to interrupt the briefing at any time. Press Pause to freeze mid-sentence
(resumes seamlessly); mute the mic; close the tab to end.

### On the road (primary flow): generate a brief, then DM yourself the room

```bash
# 1. Generate today's brief (see "Generating a daily brief" recipe below).
# 2. Open a shareable room and DM the link to your own X account:
python3 scripts/voice_room.py --share --dm
```

You'll get a DM like "Your X-LiveCast room is ready 🎧 https://xxxx.trycloudflare.com".
Open it on your phone, listen, and interrupt with questions — the host can pull
fresh X data live via tools. Needs `xurl` authenticated (see below) and
`cloudflared` installed (`brew install cloudflared`).

### Connect live X data (real agent tools)

During the call the host can call `search_x`, `get_home_timeline`,
`get_user_posts`, `get_bookmarks`, and `read_url` (fetches a linked article's
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
   tight; name who said what; skip low-signal noise.
4. **Write `briefs/latest.json`** using the schema in
   `references/brief.schema.example.json`. The only required field is `script`
   (what the voice host reads aloud). **Also include `items`, and give each
   source a structured object — `{"author", "id", "url"}` — not a bare
   `"@handle"` string.** The voice room passes this to the model as grounding:
   when the user asks about something specific in the brief, the model should
   use the exact source it already has instead of a broad re-search (e.g.
   pulling a person's whole post history). Bare handles still work but lose
   this grounding.
5. (Optional) Tell the user it's ready, or launch the voice room.

The user can run this **as many times a day as they want** — each run overwrites
`briefs/latest.json`. Keep history by snapshotting a timestamped copy
(`cp briefs/latest.json briefs/$(date +%Y%m%dT%H%M%S).json`).

### Memory / preferences / history (local, file-based)

- **Preferences:** `prompt.md` (the user edits it; persistent).
- **History:** timestamped `briefs/*.json`; `latest.json` = most recent.
- **"Only new":** `.state/seen.json` records ids already briefed per source, so a
  repeat run covers only newly-added items (see `bookmarks-new` / `mark-seen`).

### Then talk to it

```bash
python3 scripts/voice_room.py     # reads briefs/latest.json, opens the room
```

### Optional: schedule it

Any scheduler works — your harness's cron, system `cron`, etc. Not limited to
mornings. Examples:

```bash
# System cron (harness-agnostic): run the recipe via your agent CLI at 7am.
# 0 7 * * *  cd /path/to/x-livecast && <your-agent-cli> "Generate my daily brief (see SKILL.md)"

# OpenClaw, if that's your harness:
# openclaw cron add "0 7 * * *" "Generate my x-livecast daily brief (see SKILL.md recipe)" --agent main --session isolated
```

## Generating a recap draft after a session (recipe for the harness)

When the user ends a voice session (clicks **End**), the room persists the full
conversation to `sessions/latest.json` — the brief, every turn (user/host), and
every tool call made (including the actual posts looked up, with ids/authors).
When the user asks for a recap/post/thread from their session (or you want to
offer one after a session ends), do the following:

1. **Read `sessions/latest.json`** (the raw material) and **`recap_template.md`**
   (the user's editable taste/format guide — it deliberately does not fix a
   granularity; read it, it explains when to write one post vs. a thread).
2. **Synthesize a draft** using the *whole* session — not just the brief. The
   value is the user's actual participation: what they asked, what got looked
   up, what they took away. Build source links from tool_call results
   (`https://x.com/<author>/status/<id>`).
3. **Write `drafts/latest.json`** per `references/draft.schema.example.json`
   (either a single `text` or a `thread` array, plus `sources`).
4. Tell the user the draft is ready (or, once the review/publish flow exists,
   open it for one-click review). **Do not auto-post** — publishing to X is a
   separate, confirmed step.

## Configuration

See `references/config.example.md` and `.env.example`. Key settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `GEMINI_API_KEY` | (required) | Free Gemini key, used only locally |
| `XLC_PORT` | `8787` | Local voice-room port |
| `XLC_GEMINI_MODEL` | `gemini-3.1-flash-live-preview` | Gemini Live model (latest) |
| `XLC_GEMINI_VOICE` | `Puck` | Prebuilt voice (Puck, Charon, Kore, Fenrir, Aoede) |

## Roadmap

- [x] A. Scaffold (skill file, structure)
- [x] B. Local voice room (barge-in, pause, captions) + in-call X tools
- [x] C. On-demand daily brief via harness recipe (`prompt.md` → `briefs/latest.json`)
- [x] C.5. On-the-road sharing (ephemeral tokens + tunnel + DM link) and session
      capture (`sessions/latest.json`) + recap draft recipe (`recap_template.md`
      → `drafts/latest.json`)
- [ ] D. Review/one-click-publish UI for drafts + actual `xurl` posting (threaded)
- [ ] E. Bundle sharing, further polish
