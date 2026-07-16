# Always-on host setup

Primary “on the road” path: one **evergreen HTTPS URL**, room process always
running on a host that also keeps `briefs/`, `sessions/`, and `drafts/` on disk.

Demo alternative (temporary URL): `python3 scripts/voice_room.py --share --dm`
with no `XLC_PUBLIC_URL` — see README. Skip this doc if you only need a laptop demo.

## 1. Prerequisites

- Python 3.9+, `GEMINI_API_KEY` in `.env`
- `xurl` authenticated (for DM + later publish)
- A machine that stays on (Mac Mini, VPS, OpenClaw gateway host, …)
- HTTPS front door: **named Cloudflare Tunnel** (recommended) or any reverse
  proxy (Caddy/nginx) with a certificate

You need a **stable hostname**. A random `*.trycloudflare.com` quick tunnel is
not always-on (URL changes; dies with the process).

## 2. Point HTTPS at the room port

Default port is `8787` (`XLC_PORT`).

### Named Cloudflare Tunnel (sketch)

1. Install `cloudflared` and log in: `cloudflared tunnel login`
2. Create a tunnel and a DNS route to your domain, e.g. `livecast.example.com`
3. Configure ingress so that hostname → `http://127.0.0.1:8787`
4. Run the tunnel as a service / launchd / systemd so it survives reboot

Exact Cloudflare UI/CLI steps change over time; the invariant is:

`https://YOUR_HOST` → `http://127.0.0.1:XLC_PORT`

### Other reverse proxies

Terminate TLS on Caddy/nginx/Traefik and proxy to `127.0.0.1:8787` the same way.

## 3. Configure `.env`

```bash
XLC_PUBLIC_URL=https://livecast.example.com
XLC_TUNNEL_MODE=named
# optional shared secret (DM helper appends ?token=…):
# XLC_ROOM_TOKEN=long-random-string
XLC_NO_BROWSER=1
```

With `XLC_PUBLIC_URL` set, `XLC_TUNNEL_MODE` defaults to `named` (no quick tunnel).

## 4. Keep the room process up

```bash
# Foreground (dev):
python3 scripts/voice_room.py --share

# Or let ensure_room start it if /health is down:
bash scripts/ensure_room.sh
```

`--share` here means “bind publicly / expect a front door”, not “mint a new
trycloudflare URL”, when mode is `named`.

Use launchd/systemd/OpenClaw process supervision so a reboot brings the room back.

## 5. Daily cron: brief → ensure → DM same URL

1. Generate `briefs/latest.json` (SKILL.md “Generating a daily brief”).
2. `bash scripts/ensure_room.sh --dm`  
   — health-checks `XLC_PUBLIC_URL/health`, starts the room if needed, DMs the
   **same** evergreen link (not a new tunnel).

OpenClaw-style: run that recipe on the **same host** that holds the skill
checkout and the voice_room process so sessions stay on one disk.

## 6. OpenClaw gateway note

If OpenClaw already runs on a gateway box:

- Install this skill on that box (same volume you care about persisting).
- Run `voice_room.py` there (or via `ensure_room.sh`).
- Point the gateway’s HTTPS / tunnel at `XLC_PORT`, set `XLC_PUBLIC_URL`.
- Cron: brief recipe + `ensure_room.sh --dm`.

Phone users only ever open the evergreen URL; history never lives in the DM.

## 7. Verify

```bash
curl -fsS "$XLC_PUBLIC_URL/health"    # {"ok": true, "publicUrl": "..."}
python3 scripts/voice_room.py --dm-only
```

On the phone: open the DM link over HTTPS, allow mic, Start.
If you set `XLC_ROOM_TOKEN`, the DM should include `?token=…`.
