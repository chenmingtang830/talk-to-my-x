# X-LiveCast configuration reference

All configuration is read from environment variables (optionally via a `.env`
file in the skill root). Copy `.env.example` to `.env` and edit.

## Core (Phase B — voice room, Gemini Live)

| Variable | Default | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | (required) | Free key from https://aistudio.google.com/apikey. Used only on the host. |
| `XLC_PORT` | `8787` | Port for the voice-room server. |
| `XLC_GEMINI_MODEL` | `gemini-3.1-flash-live-preview` | Latest Live audio-to-audio model. |
| `XLC_GEMINI_VOICE` | `Puck` | Prebuilt voice: Puck, Charon, Kore, Fenrir, Aoede. |
| `XLC_BRIEF_FILE` | (unset) | Path to a generated brief `.json`. Falls back to `assets/sample-brief.md`. |
| `XLC_PUBLIC_URL` | (unset) | Evergreen HTTPS origin (always-on). |
| `XLC_TUNNEL_MODE` | see above | `named` \| `quick` \| `none`. |
| `XLC_ROOM_TOKEN` | (unset) | Optional API gate for the shared room. |
| `XLC_SYNTH_MODEL` | `gemini-2.5-flash` | Text model for Synthesize / recap. |
| `XLC_NO_BROWSER` | (unset) | Set `1` to skip opening a browser on local-only starts. |

## Publishing (confirm required)

`POST /publish` with `{"confirm": true, ...}` or
`python3 scripts/publish.py publish --confirm`. Without confirm, the server
refuses. Thread posts use `reply.in_reply_to_tweet_id`. See SKILL.md
“Publishing a draft (confirmed)” and `TESTING.md`.

## Feed bundles

`python3 scripts/bundle_tools.py export|import` — schema in
`references/bundle.schema.example.json`. Host/CLI only (not exposed in the room UI).

## Always-on

Step-by-step: [`always-on.setup.md`](always-on.setup.md).

Live (audio-to-audio) models, latest first: `gemini-3.1-flash-live-preview`,
then `gemini-2.5-flash-live-preview`. Note `gemini-2.0-flash-live-001` is shut
down. See https://ai.google.dev/gemini-api/docs/models#audio_models.

## Voice session behavior

The room configures the Gemini Live session with:

- `responseModalities: ["AUDIO"]` and a prebuilt voice.
- Automatic VAD (default) — enables barge-in; the server sends
  `serverContent.interrupted` when the user talks over the host.
- Input audio: raw PCM16 LE @ 16 kHz. Output audio: PCM16 @ 24 kHz.
- `systemInstruction` — the host persona + the current brief text as context.

## Security: ephemeral tokens (always on)

`GET /config` never returns the raw `GEMINI_API_KEY`. It mints a short-lived
Gemini **ephemeral token** per session and returns that instead:

- `POST https://generativelanguage.googleapis.com/v1alpha/auth_tokens?key=KEY`
  with a flat JSON body `{"expireTime": ..., "newSessionExpireTime": ...}`
  (verified empirically — not `authTokens`/camelCase, and no `config` wrapper).
  Returns `{"name": "auth_tokens/..."}`; that `name` value is the token.
- The browser connects to
  `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained?access_token=<name>`
  (the **constrained** endpoint — plain `BidiGenerateContent?key=...` won't
  accept an ephemeral token).
- Default token lifetime: 30 min to use in messages, 10 min window to start the
  session (see `mint_ephemeral_token()` in `scripts/voice_room.py`).

This is on by default (not just for sharing) — it's free and strictly safer,
and it's required anyway once the room can be reached off the local machine.

## Sharing: always-on URL (primary) vs quick tunnel (demo)

**Primary:** set `XLC_PUBLIC_URL` to an evergreen HTTPS origin (named Cloudflare
tunnel or reverse proxy) that fronts `XLC_PORT`. Keep the room process up on the
host. Daily cron DMs that **same** URL after regenerating the brief:

```bash
bash scripts/ensure_room.sh --dm
python3 scripts/voice_room.py --dm-only
```

| Variable | Default | Notes |
| --- | --- | --- |
| `XLC_PUBLIC_URL` | (unset) | Evergreen HTTPS origin used in DMs and `/health` checks. |
| `XLC_TUNNEL_MODE` | `named` if public URL else `quick` | `named` = don't start cloudflared; `quick` = demo trycloudflare; `none` = bind only. |
| `XLC_ROOM_TOKEN` | (unset) | If set, gates `/config`, `/tool`, `/session(s)`, `/synthesize`, `/draft`, `/publish`, `/bundle`. Pass `X-XLC-Token` or `?token=`. DM helper appends the token to the shared URL. |
| `XLC_NO_BROWSER` | (unset) | Set `1` to skip opening a browser on local-only starts. |

`GET /health` is ungated and returns `{ok, publicUrl}` for `ensure_room.sh`.

**Demo:** `python3 scripts/voice_room.py --share --dm` with `XLC_TUNNEL_MODE=quick`
(or no `XLC_PUBLIC_URL`) starts a temporary `cloudflared` quick tunnel. The link
dies when the process stops. Requires `brew install cloudflared`.

Mobile browsers require a **secure context** (HTTPS or localhost) for
microphone access — a plain LAN IP over HTTP will not get mic permission on a
phone.

### Known limitation: some networks block `*.trycloudflare.com`

Quick-tunnel domains are dynamically generated, so some DNS filters (NextDNS,
AdGuard, carrier "safe browsing" DNS, corporate/hotel WiFi) flag them as
suspicious "newly seen" domains and refuse to resolve them — you'll see a
"server not found" error on the phone even though the tunnel itself is healthy.
This is a client-side DNS/network issue, not a server problem (verify: `curl`
the printed URL from another machine — if that works, it's the phone's network).

Workarounds, roughly in order of effort:
- Switch off WiFi (use cellular) or vice versa, and retry.
- Temporarily disable any custom/private DNS app or "Private DNS" setting on
  the phone (Settings → often under VPN/DNS).
- Try a different browser.
- **Preferred permanent fix:** named Cloudflare Tunnel (or any reverse proxy)
  bound to your own domain → set `XLC_PUBLIC_URL`. That is the always-on path
  this skill is designed around.

## Costs: who bills what

Two completely separate billing systems are involved, and it's easy to conflate
them:

| What | Who bills | Rate |
| --- | --- | --- |
| The voice conversation itself (audio in/out, text tokens for tool-call plumbing) | **Google** (Gemini Live API), via your `GEMINI_API_KEY` | ~$0.005/min audio in, ~$0.018/min audio out on `gemini-3.1-flash-live-preview` (free tier available) |
| Each in-call tool invocation that actually hits X (`search_x`, `get_home_timeline`, `get_bookmarks`, `get_user_posts`) | **X**, via your `xurl`-authenticated app | ~$0.005/read (your own bookmarks/timeline: ~$0.001/read) |

So: asking the host a question that doesn't trigger a tool call only costs
Gemini (voice minutes). Asking it to "search X for the latest on ___" costs
Gemini (a little, for the function-call plumbing + the audio of it explaining
the results) **and** X (one read, charged to your X API credits). Calling a
tool sends the *result* back to Gemini as text, which is cheap (~$0.75/1M
tokens) — the X-side read is the more meaningful per-call cost of the two.

## X integration (Phase C/D — not required for the voice demo)

Prefer OpenClaw's X channel for DM delivery and posting. Direct X API usage is
optional and requires a paid X API tier with write access.

| Variable | Notes |
| --- | --- |
| `X_BEARER_TOKEN` | App-only read (timeline). |
| `X_API_KEY` / `X_API_SECRET` | OAuth 1.0a app credentials. |
| `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | User context for posting / DM. |
