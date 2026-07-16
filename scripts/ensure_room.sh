#!/usr/bin/env bash
# Ensure the always-on voice room is reachable, then optionally DM the evergreen URL.
#
# Intended for cron after generating briefs/latest.json:
#   1) health-check XLC_PUBLIC_URL (or localhost:XLC_PORT)
#   2) if down, start voice_room.py in the background (named/none tunnel mode)
#   3) optionally DM the same evergreen link (--dm)
#
# Requires: XLC_PUBLIC_URL for real "on the road" use. Quick tunnels are demo-only
# and are NOT started by this script (they die with the process / change URL daily).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Load .env without overriding real env (same spirit as voice_room.load_dotenv).
if [[ -f "$ROOT/.env" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    # trim key
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ -z "$key" ]] && continue
    # skip if already set in environment
    if [[ -n "${!key+x}" ]]; then
      continue
    fi
    # trim + strip simple quotes from value
    val="${val#"${val%%[![:space:]]*}"}"
    val="${val%"${val##*[![:space:]]}"}"
    if [[ "$val" == \"*\" && "$val" == *\" ]]; then
      val="${val:1:${#val}-2}"
    elif [[ "$val" == \'*\' && "$val" == *\' ]]; then
      val="${val:1:${#val}-2}"
    fi
    export "$key=$val"
  done < "$ROOT/.env"
fi

PORT="${XLC_PORT:-8787}"
PUBLIC="${XLC_PUBLIC_URL:-}"
PUBLIC="${PUBLIC%/}"
DO_DM=0
START_IF_DOWN=1

usage() {
  cat <<EOF
Usage: scripts/ensure_room.sh [--dm] [--no-start]

  --dm         DM XLC_PUBLIC_URL to your X account (via voice_room --dm-only)
  --no-start   Only check / DM; do not start the room if health fails
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dm) DO_DM=1; shift ;;
    --no-start) START_IF_DOWN=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

health_url() {
  if [[ -n "$PUBLIC" ]]; then
    echo "${PUBLIC}/health"
  else
    echo "http://127.0.0.1:${PORT}/health"
  fi
}

room_up() {
  curl -fsS --max-time 5 "$(health_url)" >/dev/null 2>&1
}

if room_up; then
  echo "[ensure_room] Room healthy: $(health_url)"
else
  echo "[ensure_room] Room not healthy: $(health_url)" >&2
  if [[ -n "$PUBLIC" ]]; then
    echo "[ensure_room] Tip: is voice_room running on this host? Is the tunnel/proxy" >&2
    echo "[ensure_room]      forwarding ${PUBLIC} → 127.0.0.1:${PORT} ?" >&2
  else
    echo "[ensure_room] Tip: for always-on, set XLC_PUBLIC_URL to your HTTPS origin." >&2
  fi
  if [[ "$START_IF_DOWN" -eq 0 ]]; then
    echo "[ensure_room] --no-start set; not launching." >&2
    exit 1
  fi
  if [[ -z "$PUBLIC" ]]; then
    echo "[ensure_room] Set XLC_PUBLIC_URL for always-on hosting (named tunnel / reverse proxy)." >&2
    echo "[ensure_room] Refusing to auto-start a quick tunnel (demo-only; URL changes)." >&2
    echo "[ensure_room] Demo instead: python3 scripts/voice_room.py --share --dm" >&2
    exit 1
  fi
  mkdir -p "$ROOT/.state"
  LOG="$ROOT/.state/voice_room.log"
  echo "[ensure_room] Starting voice_room.py (bind public; tunnel mode from env)…"
  echo "[ensure_room] Log: $LOG"
  # Prefer named/none: XLC_TUNNEL_MODE defaults to named when XLC_PUBLIC_URL is set.
  nohup python3 "$ROOT/scripts/voice_room.py" --share >>"$LOG" 2>&1 &
  echo $! >"$ROOT/.state/voice_room.pid"
  echo "[ensure_room] pid $(cat "$ROOT/.state/voice_room.pid")"
  for _ in $(seq 1 30); do
    if room_up; then
      echo "[ensure_room] Room is up."
      break
    fi
    sleep 1
  done
  if ! room_up; then
    echo "[ensure_room] Started but health still failing after ~30s." >&2
    echo "[ensure_room] Last log lines:" >&2
    tail -n 40 "$LOG" >&2 || true
    echo "[ensure_room] Check tunnel → port ${PORT}, GEMINI_API_KEY, and $LOG" >&2
    exit 1
  fi
fi

if [[ "$DO_DM" -eq 1 ]]; then
  if [[ -z "$PUBLIC" ]]; then
    echo "[ensure_room] --dm needs XLC_PUBLIC_URL" >&2
    exit 1
  fi
  python3 "$ROOT/scripts/voice_room.py" --dm-only
fi

echo "[ensure_room] OK"
exit 0
