# Daily brief cron (bookmarks + home timeline)

Goal: every morning (default **America/New_York 08:00**) regenerate
`briefs/latest.json` so opening the room already has today’s brief. Users can
still press **Generate today’s brief** anytime to regenerate.

`generate_brief` pulls:
1. **New bookmarks** (unseen since last run)
2. **New home-timeline posts** (accounts you follow; unseen)

If nothing new, cron **keeps the previous brief** (`allow_empty`) and exits ok.

## Why cron hits the Web Service (not a second disk)

On Render, only the voice-room Web Service has the Disk (`/var/data`) and
`xurl` tokens under `HOME=/var/data/home`. So the Cron Job should **HTTP POST**
the live room — not re-run Python against an empty FS.

## Render Cron Job (recommended)

1. Dashboard → **New → Cron Job** (same repo optional; a one-liner is enough).
2. Schedule (UTC). Eastern 8am ≈:
   - **EDT** (UTC−4): `0 12 * * *`
   - **EST** (UTC−5): `0 13 * * *`
3. Command:

```bash
# Wake the web service first (Starter can 503 while cold), then generate with retries.
curl -fsS --retry 8 --retry-all-errors --retry-delay 15 \
  https://x-livecast.onrender.com/health >/dev/null && \
curl -fsS --retry 5 --retry-all-errors --retry-delay 10 -X POST \
  -H "X-XLC-Cron: $XLC_CRON_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"allow_empty":true}' \
  "https://x-livecast.onrender.com/brief/generate"
```

Without the health wake + retries, a cold web instance often returns **503** and
the cron exits with `curl: (22)`.

4. Env on the **Cron Job** (and matching secret on the **Web Service**):

| Key | Value |
| --- | --- |
| `XLC_CRON_SECRET` | long random string (same on web + cron) |

Optional: also set `XLC_ROOM_TOKEN` and use `X-XLC-Token` instead of cron header.

## Local / always-on host cron

```bash
# crontab — 08:00 America/New_York (requires tzdata)
0 8 * * *  cd /path/to/x-livecast && \
  XLC_BRIEF_FORCE=1 XLC_PUBLIC_URL=https://your.host \
  XLC_CRON_SECRET=… bash scripts/cron_daily_brief.sh
```

Or run the script hourly without `XLC_BRIEF_FORCE` — it no-ops unless the local
hour matches `XLC_BRIEF_HOUR` (default 8) in `XLC_BRIEF_TZ` (default
`America/New_York`).

## Manual smoke

```bash
curl -fsS -X POST -H "Content-Type: application/json" \
  -d '{"allow_empty":true}' \
  "http://localhost:8787/brief/generate"
# or on Render with secret:
# -H "X-XLC-Cron: …"
```

CLI equivalent on a machine that already has xurl + disk:

```bash
python3 scripts/generate_brief.py --allow-empty
```

## Related

- Ops overview: [`run-modes.md`](run-modes.md)
- Render service setup: [`render.setup.md`](render.setup.md)
