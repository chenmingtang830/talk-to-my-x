# Deploy voice room on Render (Web Service)

Not a Cron Job — the room is a long-running **Web Service**.
Native **Python 3** only (no Docker).

## Configure in the Render UI

1. **New → Web Services**
2. Connect this GitHub repo
3. Fill:

| Field | Value |
| --- | --- |
| Name | `x-livecast` |
| Language | **Python 3** |
| Branch | your deploy branch |
| Region | closest to you |
| Root Directory | *(leave empty)* |
| Build Command | see **Build (xurl)** below |
| Start Command | `python3 scripts/voice_room.py --share` |
| Instance | **Starter** or higher *(avoid Free — sleeps, no persistent disk)* |
| Health check path | `/health` |

### Build (xurl)

Install `xurl` once per deploy and put it on `PATH`:

Install into the service slug (and copy into `./.local/bin` so runtime finds it
even when Start sets `HOME=/var/data/home`):

```bash
export HOME=/opt/render/project && mkdir -p "$HOME/.local/bin" .local/bin && curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash && export PATH="$HOME/.local/bin:$PATH" && cp -f "$HOME/.local/bin/xurl" .local/bin/xurl && ./.local/bin/xurl --version && echo "xurl at $(pwd)/.local/bin/xurl"
```

Optional: set env `XLC_XURL_BIN=/opt/render/project/src/.local/bin/xurl`.

### Environment

| Key | Value |
| --- | --- |
| `GEMINI_API_KEY` | your key |
| `XLC_SYNTH_MODEL` | e.g. `gemini-3.5-flash` *(Generate brief + Synthesize; not Live voice)* |
| `XLC_MEMORY_EVOLVE` | `suggest` *(default)* \| `auto` \| `off` — USER/TASTE after Synthesize |
| `XLC_CRON_SECRET` | shared secret for daily `POST /brief/generate` from a Cron Job |
| `XLC_NO_BROWSER` | `1` |
| `XLC_TUNNEL_MODE` | `none` |
| `XLC_DATA_DIR` | `/var/data` |
| `XLC_PUBLIC_URL` | `https://<your-service>.onrender.com` *(after first deploy)* |
| `XLC_XURL_BIN` | *(optional)* e.g. `/opt/render/project/src/.local/bin/xurl` |
| `XLC_XURL_APP` | *(optional)* `xurl` app name if not the default |
| `XLC_ROOM_TOKEN` | *(optional)* gate `/config`, generate, publish, etc. |

Step-by-step local vs cloud checklists: [`run-modes.md`](run-modes.md).

**Do not set `HOME=/var/data/home` as a service env var** — Render applies it during
**build** too, and `/var/data` is read-only until runtime (xurl install will fail with
`mkdir: cannot create directory '/var/data'`). Instead set HOME in **Start Command**:

```bash
export HOME=/var/data/home; mkdir -p "$HOME"; export PATH="$(pwd)/.local/bin:$PATH"; python3 scripts/voice_room.py --share
```

And force a writable HOME during **Build** when installing xurl:

```bash
export HOME=/opt/render/project && mkdir -p "$HOME" .local/bin && curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash && XBIN=$(command -v xurl || true) && test -n "$XBIN" && cp -f "$XBIN" .local/bin/xurl && test -x .local/bin/xurl && echo "xurl at $(pwd)/.local/bin/xurl"
```

### Disk

Starter+: left nav **Disk** → create disk, mount path **`/var/data`**, ≥1 GB.

If you set `XLC_DATA_DIR=/var/data` **without** a mounted disk, the room falls back to
repo-local dirs (sessions won’t survive redeploys).

Layout under the disk (see also `local-layout.md`):

```
/var/data/
  sessions/   drafts/   briefs/   bundles/   .state/
  memory/              # USER.md + TASTE.md (+ proposals/)
  home/.xurl/          # when HOME=/var/data/home
```

6. Deploy → open `https://<service>.onrender.com/health`.

## One-time: authenticate xurl (Render Shell)

Do this in the Render **Shell** tab — never paste client secrets into chat.

1. Ensure `HOME` is the disk home (same as env), and `xurl` is on PATH / `XLC_XURL_BIN`.
2. Register the X developer app (once):

```bash
mkdir -p "$HOME"
xurl auth apps add <your-app-name> \
  --client-id '…' \
  --client-secret '…' \
  --api-key '…' \
  --api-secret '…'
```

3. Headless OAuth2 (browser isn’t on the server — paste the redirect URL when prompted):

```bash
xurl auth oauth2 --headless --app <your-app-name>
```

4. For **Publish to X**, you usually also need OAuth1 with write:

```bash
xurl auth oauth1 --app <your-app-name>
```

5. Smoke:

```bash
python3 scripts/x_tools.py check
python3 scripts/x_tools.py bookmarks 3
```

Tokens live under `$HOME/.xurl` on the disk.

## After it’s up

- Phone: open the Render HTTPS URL → Start.
- **Generate today’s brief** pulls **new bookmarks + home timeline** (or daily cron
  pre-runs it — [`daily-brief.cron.md`](daily-brief.cron.md)).
- Until the first live brief exists, the room serves `assets/sample-brief.md`.
- After **Synthesize**, review **Taste / user update** → **Apply to memory**
  (`XLC_MEMORY_EVOLVE=suggest`).
- Sessions / drafts / briefs / memory persist on the Disk.

See also `run-modes.md`, `local-layout.md`, `TESTING.md`.
