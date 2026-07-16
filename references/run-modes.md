# How to run X-LiveCast — local vs cloud

Two supported modes. Pick one; don’t mix their setup steps.

| | **A. Local** (default, simplest) | **B. Cloud (Render)** |
| --- | --- | --- |
| Who runs the room | Your laptop / Mac Mini | Render Web Service |
| Who opens the UI | Browser on `localhost` (or phone via tunnel) | Phone/browser → evergreen HTTPS |
| X tokens (`xurl`) | Your machine `~/.xurl` | Disk: `/var/data/home/.xurl` (via Start Command `HOME`) |
| Brief generation | CLI / agent / room **Generate** | Room **Generate** (same script) |
| Docs for deep ops | this file + `local-layout.md` | this file + `render.setup.md` |

---

## Shared once (both modes)

1. Clone repo; `cp .env.example .env` and set `GEMINI_API_KEY`.
2. Edit taste: `prompt.md` (and optional `memory/USER.md`, `memory/TASTE.md`).
3. Install + auth **xurl** on the machine that will call the X API:

```bash
brew install --cask xdevplatform/tap/xurl   # or install.sh on Linux/Render
xurl auth apps add my-app --client-id '…' --client-secret '…' --api-key '…' --api-secret '…'
xurl auth oauth2 --app my-app              # local: browser opens
xurl auth default my-app                   # required so tools find credentials
python3 scripts/x_tools.py check
```

4. Models in `.env` / Render Environment:

| Variable | What it controls | Example |
| --- | --- | --- |
| `XLC_GEMINI_MODEL` | Voice Live call (**Start**) | `gemini-3.1-flash-live-preview` |
| `XLC_SYNTH_MODEL` | **Generate brief** + **Synthesize** (text) | `gemini-3.5-flash` |
| `XLC_GEMINI_VOICE` | TTS voice | `Puck` |

---

## Mode A — Local (recommended to start)

### A1. Generate today’s brief

**Option 1 — script (bookmarks → Gemini text → `briefs/latest.json`):**

```bash
python3 scripts/generate_brief.py
```

**Option 2 — your coding agent:** follow “Generating a daily brief” in `SKILL.md`
(can pull more than bookmarks if the agent uses search/timelines).

**Option 3 — room UI:** start the room (A2), then **Generate today’s brief**.

### A2. Talk in the voice room

```bash
python3 scripts/voice_room.py
# → http://localhost:8787 → Start
```

- Hang up keeps the thread; **Continue** resumes.
- **Synthesize** → edit draft → **Publish to X** (confirm required; needs write auth).

### A3. Optional: share from laptop (demo only)

```bash
python3 scripts/voice_room.py --share --dm   # temporary *.trycloudflare.com
```

URL dies when the process stops. For a stable phone URL, use Mode B or
`references/always-on.setup.md` (named tunnel on a always-on host).

### A4. Local checklist

- [ ] `GEMINI_API_KEY` + `XLC_SYNTH_MODEL` in `.env`
- [ ] `xurl auth status` shows oauth2 user under your app; `xurl auth default <app>` set
- [ ] `python3 scripts/x_tools.py bookmarks 3` works
- [ ] Generate brief → badge **Live · bookmarks** (or agent-written `briefs/latest.json`)
- [ ] Start → barge-in works

---

## Mode B — Cloud (Render)

Goal: same room URL every day on your phone. Full steps and Build/Start strings:
[`render.setup.md`](render.setup.md).

### B1. Deploy service (once)

1. Render → Web Service → this repo → branch `main`.
2. **Build Command** / **Start Command** — copy from `render.setup.md`
   (install xurl into `.local/bin`; Start sets `HOME=/var/data/home`).
3. **Disk** mounted at `/var/data`.
4. **Environment** (not secrets for X OAuth):

| Key | Value |
| --- | --- |
| `GEMINI_API_KEY` | your key |
| `XLC_SYNTH_MODEL` | e.g. `gemini-3.5-flash` |
| `XLC_NO_BROWSER` | `1` |
| `XLC_TUNNEL_MODE` | `none` |
| `XLC_DATA_DIR` | `/var/data` |
| `XLC_PUBLIC_URL` | `https://<service>.onrender.com` |
| `XLC_XURL_BIN` | `/opt/render/project/src/.local/bin/xurl` |
| `XLC_XURL_APP` | `my-app` (same name as `xurl auth apps add`) |

**Do not** set `HOME=/var/data/home` as an Environment variable (breaks build).
HOME belongs only in **Start Command**.

5. Deploy → `curl -fsS https://<service>.onrender.com/health`.

### B2. One-time xurl auth on Render (Web Shell)

Dashboard → service → **Shell** (not your laptop terminal):

```bash
export HOME=/var/data/home
mkdir -p "$HOME"
export PATH="$(pwd)/.local/bin:$PATH"

xurl auth apps add my-app --client-id '…' --client-secret '…' --api-key '…' --api-secret '…'
xurl auth oauth2 --headless --app my-app
# Browser: Authorize → localhost “refused” is OK → paste full callback URL back into Shell
xurl auth default my-app

python3 scripts/x_tools.py check          # home must be /var/data/home
python3 scripts/x_tools.py bookmarks 3
```

Tokens live on the Disk under `/var/data/home/.xurl` — not in Environment.

### B3. Daily use on phone

1. Open `XLC_PUBLIC_URL`.
2. **Generate today’s brief** (needs new bookmarks; else error toast).
3. Confirm badge **Live · bookmarks** (not Sample).
4. **Start** → talk → Hang up → **Synthesize** / **Publish** as needed.

### B4. Cloud checklist

- [ ] Disk + env + Build/Start from `render.setup.md`
- [ ] `XLC_SYNTH_MODEL` set on Render if you changed it locally
- [ ] Shell: `HOME=/var/data/home` before any `xurl` command
- [ ] `xurl auth default <app>` after oauth2
- [ ] Room Generate → Live badge → Start works on phone

---

## What generates the brief?

| Path | Who | Data pulled today |
| --- | --- | --- |
| `python3 scripts/generate_brief.py` / room **Generate** | Host Python + **Gemini text** (`XLC_SYNTH_MODEL`) | New bookmarks only (+ `prompt.md` as writing guide) |
| Coding agent following `SKILL.md` | Your local agent (Cursor, etc.) | Whatever the recipe asks (bookmarks, search, timelines, …) |

Voice **Start** uses **Gemini Live** (`XLC_GEMINI_MODEL`) — separate from text synth.

---

## Related docs

- File layout: [`local-layout.md`](local-layout.md)
- Render knobs / Build strings: [`render.setup.md`](render.setup.md)
- Named tunnel always-on (non-Render): [`always-on.setup.md`](always-on.setup.md)
- Manual tests: [`../TESTING.md`](../TESTING.md)
- Skill recipes: [`../SKILL.md`](../SKILL.md)
