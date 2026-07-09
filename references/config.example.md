# X-LiveCast configuration reference

All configuration is read from environment variables (optionally via a `.env`
file in the skill root). Copy `.env.example` to `.env` and edit.

## Core (Phase B — voice room, Gemini Live)

| Variable | Default | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | (required) | Free key from https://aistudio.google.com/apikey. Used only locally. |
| `XLC_PORT` | `8787` | Port for the local voice-room server. |
| `XLC_GEMINI_MODEL` | `gemini-3.1-flash-live-preview` | Latest Live audio-to-audio model. |
| `XLC_GEMINI_VOICE` | `Puck` | Prebuilt voice: Puck, Charon, Kore, Fenrir, Aoede. |
| `XLC_BRIEF_FILE` | (unset) | Path to a generated brief `.json`. Falls back to `assets/sample-brief.md`. |

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

## Sharing: tunnel + DM (`--share`, `--dm`)

`python3 scripts/voice_room.py --share` starts a temporary public HTTPS tunnel
via `cloudflared tunnel --url http://localhost:PORT` (no account needed; dies
when the process stops). `--dm` additionally sends yourself an X DM with that
link via `xurl -X POST /2/dm_conversations/with/<your_user_id>/messages`.

Mobile browsers require a **secure context** (HTTPS or localhost) for
microphone access — a plain LAN IP over HTTP will not get mic permission on a
phone, so the tunnel (HTTPS) is required for real mobile use, not just a
convenience.

Requires: `brew install cloudflared`, and `xurl` authenticated for `--dm`.

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
- For a more permanent fix: use a **named Cloudflare Tunnel bound to your own
  domain** instead of a quick tunnel (requires a Cloudflare account + a domain
  you own) — a real, stable domain is far less likely to be filtered than a
  random `trycloudflare.com` subdomain. Not implemented yet; quick tunnels
  cover the common case.

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
