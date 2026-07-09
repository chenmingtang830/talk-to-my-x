#!/usr/bin/env python3
"""X-LiveCast voice-room server (Gemini Live), with optional public sharing.

Primary use case: "on the road". Your agent harness runs this (anywhere — your
laptop, a cloud box, doesn't matter), and you end up with a link in your X DMs
that you open on your phone to listen and barge in with questions.

It:
  - serves the static UI in ../web
  - GET /config  mints a short-lived Gemini ephemeral token (never the real key)
  - GET /brief   returns the briefing script + structured grounding (items/sources)
  - GET/POST /tool, /tools  in-call X tools (search_x, get_home_timeline, ...)

Modes:
  python3 scripts/voice_room.py                  # local only (http://localhost:PORT)
  python3 scripts/voice_room.py --share          # + public HTTPS tunnel (cloudflared)
  python3 scripts/voice_room.py --share --dm     # + DM the link to your own X account

Why ephemeral tokens always: mobile browsers require a secure context (HTTPS or
localhost) for microphone access, so any non-localhost access (LAN or tunnel)
needs HTTPS anyway — and since links can leave the machine, the server never
hands out the real GEMINI_API_KEY. It mints a token (expires in ~30 min, single
use) and the browser uses that instead. See references/config.example.md.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x_tools  # noqa: E402 (local module, after sys.path setup)

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT / "assets"

# Constrained endpoint required for ephemeral-token auth (v1alpha only).
GEMINI_WS_BASE = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained"
)
GEMINI_TOKEN_URL = "https://generativelanguage.googleapis.com/v1alpha/auth_tokens"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no external deps). Does not override real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def cfg(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def read_brief_full() -> dict:
    """Return the brief as {text, title, items}. `items` is the structured
    grounding data (topic/summary/sources with real links, when the generator
    provided it) — the live model is given this alongside the spoken script so
    follow-up questions can be answered from the exact source, instead of
    falling back to a broad re-search. Empty `items` for plain-text briefs.
    """
    candidates = []
    explicit = os.environ.get("XLC_BRIEF_FILE", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(ROOT / "briefs" / "latest.json")
    candidates.append(ASSETS_DIR / "sample-brief.md")

    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            return {
                "text": (data.get("script") or data.get("text") or "").strip(),
                "title": data.get("title"),
                "items": data.get("items") or [],
            }
        return {"text": text.strip(), "title": None, "items": []}
    return {
        "text": "Good morning! Your briefing content is not configured yet.",
        "title": None,
        "items": [],
    }


def save_session(payload: dict) -> Path:
    """Persist a finished voice session (turns + tool calls) for the recap recipe.

    Writes a timestamped copy (history) and updates sessions/latest.json, mirroring
    how briefs/ is handled.
    """
    sessions_dir = ROOT / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    dated_path = sessions_dir / f"{ts}.json"
    dated_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (sessions_dir / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return dated_path


def mint_ephemeral_token(ttl_minutes: int = 30, session_window_minutes: int = 10) -> dict:
    """Mint a short-lived Gemini auth token. Never hands out the real API key."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    now = datetime.datetime.now(datetime.timezone.utc)
    expire_time = (now + datetime.timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_session_expire = (now + datetime.timedelta(minutes=session_window_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

    body = json.dumps({"expireTime": expire_time, "newSessionExpireTime": new_session_expire}).encode("utf-8")
    req = request.Request(
        f"{GEMINI_TOKEN_URL}?key={api_key}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return {"token": payload["name"], "expires_at": expire_time}


class Handler(BaseHTTPRequestHandler):
    server_version = "XLiveCast/0.2"

    def log_message(self, fmt: str, *args) -> None:  # noqa: N802 (stdlib name)
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send_json(self, status: int, obj: dict) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self._send_json(404, {"error": "not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (stdlib name)
        route = self.path.split("?", 1)[0]

        if route == "/config":
            try:
                minted = mint_ephemeral_token()
                self._send_json(200, {
                    "provider": "gemini",
                    "wsBase": GEMINI_WS_BASE,
                    "token": minted["token"],
                    "hasKey": True,
                    "model": cfg("XLC_GEMINI_MODEL", "gemini-3.1-flash-live-preview"),
                    "voice": cfg("XLC_GEMINI_VOICE", "Puck"),
                })
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")
                self._send_json(exc.code, {"error": "gemini_error", "detail": detail, "hasKey": False})
            except Exception as exc:  # noqa: BLE001 (surface to the UI)
                self._send_json(500, {"error": str(exc), "hasKey": False})
            return

        if route == "/brief":
            self._send_json(200, read_brief_full())
            return

        if route == "/tools":
            self._send_json(200, {"tools": list(x_tools.TOOLS.keys())})
            return

        # Static files from web/.
        rel = "index.html" if route in ("/", "") else route.lstrip("/")
        target = (WEB_DIR / rel).resolve()
        if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
            self._send_json(403, {"error": "forbidden"})
            return
        self._send_file(target)

    def do_HEAD(self) -> None:  # noqa: N802 (stdlib name)
        # Bots/crawlers (e.g. link-preview generators, including likely X's own
        # DM preview fetcher) probe with HEAD before GET. The base handler 501s
        # on this by default, which can break preview generation. Mirror the
        # real headers for static routes (never for /config or /tool — those
        # have side effects / call external APIs, which HEAD must not trigger).
        route = self.path.split("?", 1)[0]
        rel = "index.html" if route in ("/", "") else route.lstrip("/")
        target = (WEB_DIR / rel).resolve()
        if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
            self.send_response(403)
            self.end_headers()
            return
        try:
            size = target.stat().st_size
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(size))
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 (stdlib name)
        route = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        if route == "/tool":
            name = payload.get("name", "")
            args = payload.get("args") or {}
            self._send_json(200, {"result": x_tools.dispatch(name, args)})
            return

        if route == "/session":
            path = save_session(payload)
            self._send_json(200, {"saved": str(path)})
            return

        self._send_json(404, {"error": "not found"})


# --- Optional public sharing: cloudflared quick tunnel + DM ---

_TUNNEL_URL_RE = re.compile(r"https://[a-zA-Z0-9.-]*trycloudflare\.com")


def start_tunnel(port: int, timeout_s: float = 20.0):
    """Start a cloudflared quick tunnel to localhost:port. Returns (proc, public_url)."""
    binpath = shutil.which("cloudflared")
    for candidate in ("/opt/homebrew/bin/cloudflared", "/usr/local/bin/cloudflared"):
        if not binpath and os.path.exists(candidate):
            binpath = candidate
    if not binpath:
        raise RuntimeError(
            "cloudflared not found. Install it: brew install cloudflared "
            "(no account needed for quick tunnels)."
        )

    proc = subprocess.Popen(
        [binpath, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    deadline = time.time() + timeout_s
    url = None
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            continue
        match = _TUNNEL_URL_RE.search(line)
        if match:
            url = match.group(0)
            break
    if not url:
        proc.terminate()
        raise RuntimeError("cloudflared did not report a public URL in time")

    # Drain remaining output in the background so the process doesn't block on a full pipe.
    threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
    return proc, url


def shorten_url(url: str) -> str:
    """Best-effort URL shortener. X's own link-entity detection is unreliable on
    long, multi-hyphen quick-tunnel hostnames (e.g. glad-testimonials-resume-
    corps.trycloudflare.com) — it sometimes fails to linkify them at all, so the
    URL shows as inert plain text in the DM. A short, plain-domain link is
    recognized far more reliably. Falls back to the original URL on any failure
    (network hiccup, service down) — never blocks sending the DM.
    """
    services = [
        f"https://is.gd/create.php?format=simple&url={quote(url, safe='')}",
        f"https://tinyurl.com/api-create.php?url={quote(url, safe='')}",
    ]
    for endpoint in services:
        try:
            with request.urlopen(endpoint, timeout=8) as resp:
                short = resp.read().decode("utf-8").strip()
            if short.startswith("http"):
                return short
        except Exception:  # noqa: BLE001 (best-effort; any failure just falls through)
            continue
    return url


def dm_room_link(url: str) -> dict:
    """DM the room link to the authenticated user's own X account."""
    xurl = x_tools.xurl_bin()
    if not xurl:
        return {"error": "xurl not found; install it and run `xurl auth oauth2` first"}

    short_url = shorten_url(url)

    try:
        who = json.loads(
            subprocess.run([xurl, "/2/users/me"], capture_output=True, text=True, timeout=15, check=True).stdout
        )
        user_id = who["data"]["id"]
    except Exception as exc:  # noqa: BLE001
        return {"error": f"could not resolve X user: {exc}"}

    # URL on its own line, nothing touching it (no emoji/punctuation adjacent) —
    # keeps link-detection unambiguous across chat clients.
    text = (
        f"\U0001f3a7 Your X-LiveCast room is ready.\n\n"
        f"{short_url}\n\n"
        "Link not loading? Some WiFi/DNS setups block new tunnel domains \u2014 "
        "try switching to cellular data or a different browser."
    )
    try:
        result = subprocess.run(
            [xurl, "-X", "POST", f"/2/dm_conversations/with/{user_id}/messages", "-d", json.dumps({"text": text})],
            capture_output=True, text=True, timeout=15,
        )
        return json.loads(result.stdout) if result.stdout else {"error": result.stderr}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="X-LiveCast voice room server")
    parser.add_argument("--share", action="store_true",
                         help="Expose the room over a public HTTPS tunnel (cloudflared).")
    parser.add_argument("--dm", action="store_true",
                         help="DM the (shared) room link to your own X account. Implies --share.")
    args = parser.parse_args()
    if args.dm:
        args.share = True

    if not os.environ.get("GEMINI_API_KEY", "").strip():
        sys.stderr.write(
            "\n[X-LiveCast] GEMINI_API_KEY is not set.\n"
            "  Get a free key at https://aistudio.google.com/apikey (no billing needed),\n"
            "  then copy .env.example to .env and set GEMINI_API_KEY.\n"
            "  The server will still start, but the voice room won't connect until it's set.\n\n"
        )

    port = int(cfg("XLC_PORT", "8787"))
    local_url = f"http://localhost:{port}"

    httpd = ThreadingHTTPServer(("0.0.0.0" if args.share else "127.0.0.1", port), Handler)
    sys.stderr.write(f"[X-LiveCast] Local:  {local_url}  (Ctrl+C to stop)\n")

    public_url = None
    tunnel_proc = None
    if args.share:
        try:
            tunnel_proc, public_url = start_tunnel(port)
            sys.stderr.write(f"[X-LiveCast] Public: {public_url}  (temporary, dies when this process stops)\n")
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[X-LiveCast] Could not start tunnel: {exc}\n")

    if args.dm:
        if public_url:
            sys.stderr.write("[X-LiveCast] Sending yourself a DM with the room link...\n")
            result = dm_room_link(public_url)
            if result.get("error"):
                sys.stderr.write(f"[X-LiveCast] DM failed: {result['error']}\n")
            else:
                sys.stderr.write("[X-LiveCast] DM sent.\n")
        else:
            sys.stderr.write("[X-LiveCast] Skipping DM: no public URL (tunnel failed to start).\n")

    open_url = public_url or local_url
    if os.environ.get("XLC_NO_BROWSER", "").strip() not in ("1", "true", "yes") and not args.share:
        threading.Timer(0.6, lambda: webbrowser.open(open_url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\n[X-LiveCast] Stopped.\n")
    finally:
        httpd.server_close()
        if tunnel_proc:
            tunnel_proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
