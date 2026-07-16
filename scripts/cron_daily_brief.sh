#!/usr/bin/env bash
# Hit the live room's POST /brief/generate (same disk / xurl as the web service).
#
# Default schedule idea: America/New_York 08:00
#   Render Cron (UTC):  0 12 * * *   during EDT (UTC-4)
#                       0 13 * * *   during EST (UTC-5)
# Or run hourly and let this script no-op outside the window (set XLC_BRIEF_TZ + hour).
#
# Usage:
#   XLC_PUBLIC_URL=https://x-livecast.onrender.com \
#   XLC_CRON_SECRET=…   # or XLC_ROOM_TOKEN=…
#   bash scripts/cron_daily_brief.sh

set -euo pipefail

URL="${XLC_PUBLIC_URL:-}"
if [[ -z "$URL" ]]; then
  echo "XLC_PUBLIC_URL is required" >&2
  exit 2
fi
URL="${URL%/}"

TZ_NAME="${XLC_BRIEF_TZ:-America/New_York}"
HOUR="${XLC_BRIEF_HOUR:-8}"
# If XLC_BRIEF_FORCE=1, skip the local-hour gate (use for Render Cron timed to 8am ET).
if [[ "${XLC_BRIEF_FORCE:-0}" != "1" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    in_window="$(XLC_BRIEF_TZ="$TZ_NAME" XLC_BRIEF_HOUR="$HOUR" python3 - <<'PY'
import os
from datetime import datetime
from zoneinfo import ZoneInfo
tz = ZoneInfo(os.environ.get("XLC_BRIEF_TZ", "America/New_York"))
hour = int(os.environ.get("XLC_BRIEF_HOUR", "8"))
now = datetime.now(tz)
print("1" if now.hour == hour else "0")
PY
)"
    if [[ "$in_window" != "1" ]]; then
      echo "skip: not ${HOUR}:00 in ${TZ_NAME}"
      exit 0
    fi
  fi
fi

AUTH_HEADER=()
if [[ -n "${XLC_CRON_SECRET:-}" ]]; then
  AUTH_HEADER=(-H "X-XLC-Cron: ${XLC_CRON_SECRET}")
elif [[ -n "${XLC_ROOM_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "X-XLC-Token: ${XLC_ROOM_TOKEN}")
fi

# Wake cold instances (Render Starter often 503s on the first hit).
curl -fsS --retry 8 --retry-all-errors --retry-delay 15 \
  "${URL}/health" >/dev/null

curl -fsS --retry 5 --retry-all-errors --retry-delay 10 -X POST \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d '{"allow_empty":true}' \
  "${URL}/brief/generate"
echo
