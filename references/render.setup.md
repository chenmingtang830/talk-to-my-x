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
| Build Command | `true` *(no pip deps; stdlib only)* |
| Start Command | `python3 scripts/voice_room.py --share` |
| Instance | **Starter** or higher *(avoid Free — sleeps, no persistent disk)* |
| Health check path | `/health` |

4. **Environment:**

| Key | Value |
| --- | --- |
| `GEMINI_API_KEY` | your key |
| `XLC_NO_BROWSER` | `1` |
| `XLC_TUNNEL_MODE` | `none` |
| `XLC_DATA_DIR` | `/var/data` |
| `XLC_PUBLIC_URL` | `https://<your-service>.onrender.com` *(after first deploy)* |

5. **Disk** (Starter+): mount path `/var/data`, ≥1 GB.

6. Deploy → open `https://<service>.onrender.com/health`.

## After it’s up

- Phone: open the Render HTTPS URL → Start.
- Optional later: a separate **Cron Job** to regenerate briefs / DM the same URL.
- `xurl` on Render is optional; room + Gemini need only `GEMINI_API_KEY`.

See also `local-layout.md` for what lands under `/var/data`.
