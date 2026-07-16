#!/usr/bin/env python3
"""X-LiveCast voice-room server (Gemini Live), with optional public sharing.

Primary use case: "on the road" from an always-on harness host (OpenClaw on a
Mac Mini / VPS, etc.). Set XLC_PUBLIC_URL to an evergreen HTTPS origin (named
Cloudflare tunnel or reverse proxy). Daily cron DMs that same URL; briefs and
sessions live on the host disk behind it.

Demo mode: --share still spins a temporary cloudflared quick tunnel (dies when
the process stops).

It:
  - serves the static UI in ../web
  - GET /config  mints a short-lived Gemini ephemeral token (never the real key)
  - GET /brief   returns the briefing script + structured grounding (items/sources)
  - POST /brief/generate  regenerate brief from new bookmarks (token-gated)
  - GET /drafts  list post drafts; GET /draft?id= load one
  - GET/POST /tool, /tools, /session(s), /synthesize  in-call + thread APIs

Modes:
  python3 scripts/voice_room.py                  # local only (http://localhost:PORT)
  python3 scripts/voice_room.py --share          # quick tunnel (demo) or named via env
  python3 scripts/voice_room.py --share --dm     # + DM the public link to yourself
  python3 scripts/voice_room.py --dm-only        # DM XLC_PUBLIC_URL; room must already run
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
from urllib.parse import quote, urlencode, parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x_tools  # noqa: E402 (local module, after sys.path setup)
import publish as publish_mod  # noqa: E402
import bundle_tools as bundle_mod  # noqa: E402
import generate_brief as generate_brief_mod  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT / "assets"
# Writable runtime dirs (overridable via XLC_DATA_DIR for Render/Railway disks).
SESSIONS_DIR = ROOT / "sessions"
DRAFTS_DIR = ROOT / "drafts"
BUNDLES_DIR = ROOT / "bundles"
BRIEFS_DIR = ROOT / "briefs"


def apply_data_dir() -> None:
    """Point sessions/drafts/briefs/bundles at XLC_DATA_DIR when set (persistent disk).

    If the path isn't writable (common on Render when Disk isn't mounted yet),
    fall back to repo-local dirs so the room still boots.
    """
    global SESSIONS_DIR, DRAFTS_DIR, BUNDLES_DIR, BRIEFS_DIR
    raw = os.environ.get("XLC_DATA_DIR", "").strip()
    if not raw:
        return
    base = Path(raw)
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".xlc_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        sys.stderr.write(
            f"[X-LiveCast] XLC_DATA_DIR={base} not writable ({exc}). "
            "Falling back to repo-local sessions/drafts/briefs. "
            "On Render: add a Disk mounted at this path, or unset XLC_DATA_DIR.\n"
        )
        return
    SESSIONS_DIR = base / "sessions"
    DRAFTS_DIR = base / "drafts"
    BUNDLES_DIR = base / "bundles"
    BRIEFS_DIR = base / "briefs"
    for d in (SESSIONS_DIR, DRAFTS_DIR, BUNDLES_DIR, BRIEFS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    # Keep publish / bundle helpers / bookmark seen-state on the same volume.
    publish_mod.DRAFTS_DIR = DRAFTS_DIR
    bundle_mod.BUNDLES_DIR = BUNDLES_DIR
    x_tools.apply_state_dir(base)
    # Prefer HOME under the disk so ~/.xurl survives redeploys (Render).
    home = base / "home"
    try:
        home.mkdir(parents=True, exist_ok=True)
        if not (os.environ.get("HOME") or "").startswith(str(base)):
            # Only tip if operator forgot HOME=; do not override a deliberate HOME.
            sys.stderr.write(
                f"[X-LiveCast] Tip: set HOME={home} so xurl tokens persist on the disk.\n"
            )
    except OSError:
        pass
    sys.stderr.write(f"[X-LiveCast] Runtime data dir: {base}\n")

# Constrained endpoint required for ephemeral-token auth (v1alpha only).
GEMINI_WS_BASE = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained"
)
GEMINI_TOKEN_URL = "https://generativelanguage.googleapis.com/v1alpha/auth_tokens"
# Text model for post-session synthesis (not Live).
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

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


def public_url_from_env() -> str | None:
    """Evergreen HTTPS origin for DMs (named tunnel / reverse proxy)."""
    url = cfg("XLC_PUBLIC_URL", "").rstrip("/")
    return url or None


def tunnel_mode() -> str:
    """quick (demo) | named (external tunnel already running) | none."""
    mode = cfg("XLC_TUNNEL_MODE", "").lower()
    if mode in ("quick", "named", "none"):
        return mode
    return "named" if public_url_from_env() else "quick"


def room_token() -> str:
    return cfg("XLC_ROOM_TOKEN", "")


def _request_room_token(handler: BaseHTTPRequestHandler) -> str:
    hdr = (handler.headers.get("X-XLC-Token") or "").strip()
    if hdr:
        return hdr
    qs = parse_qs(urlparse(handler.path).query)
    return ((qs.get("token") or [""])[0] or "").strip()


def require_room_token(handler: BaseHTTPRequestHandler) -> bool:
    """If XLC_ROOM_TOKEN is set, gate sensitive APIs. Returns False if rejected."""
    expected = room_token()
    if not expected:
        return True
    if _request_room_token(handler) == expected:
        return True
    handler._send_json(401, {"error": "unauthorized", "hint": "pass X-XLC-Token or ?token="})
    return False


def read_brief_full() -> dict:
    """Return the brief as {text, title, items, source}.

    `source` is `live` for briefs/latest.json (bookmark-generated), `sample`
    for assets/sample-brief.md, or `file` for XLC_BRIEF_FILE. `items` is
    structured grounding when the generator provided it.
    """
    candidates: list[tuple[Path, str]] = []
    explicit = os.environ.get("XLC_BRIEF_FILE", "").strip()
    if explicit:
        candidates.append((Path(explicit), "file"))
    candidates.append((BRIEFS_DIR / "latest.json", "live"))
    if BRIEFS_DIR.resolve() != (ROOT / "briefs").resolve():
        candidates.append((ROOT / "briefs" / "latest.json", "live"))
    candidates.append((ASSETS_DIR / "sample-brief.md", "sample"))

    for path, source in candidates:
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
                "source": source,
                "generated_at": data.get("generated_at"),
            }
        return {
            "text": text.strip(),
            "title": None,
            "items": [],
            "source": source,
            "generated_at": None,
        }
    return {
        "text": "Good morning! Your briefing content is not configured yet.",
        "title": None,
        "items": [],
        "source": "none",
        "generated_at": None,
    }


def list_drafts(limit: int = 30) -> list[dict]:
    """Newest-first draft summaries for the drafts library."""
    DRAFTS_DIR.mkdir(exist_ok=True)
    rows = []
    for path in DRAFTS_DIR.glob("*.json"):
        if path.name == "latest.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        text = (data.get("text") or "").strip()
        if not text and isinstance(data.get("thread"), list):
            text = " ".join(str(p) for p in data["thread"] if p).strip()
        preview = (text.split("\n")[0] if text else "")[:100]
        rows.append({
            "id": data.get("id") or path.stem,
            "generated_at": data.get("generated_at") or data.get("created_at"),
            "published_at": data.get("published_at"),
            "published": bool(data.get("published_at") or data.get("tweet_ids")),
            "preview": preview,
            "session_id": data.get("session_id"),
        })
    rows.sort(key=lambda r: r.get("generated_at") or "", reverse=True)
    return rows[: max(1, min(int(limit), 100))]


def save_session(payload: dict) -> Path:
    """Upsert a conversation thread. Same id → overwrite; keeps ChatGPT-style history.

    Writes `sessions/<id>.json` and mirrors to `sessions/latest.json`.
    """
    SESSIONS_DIR.mkdir(exist_ok=True)
    sid = (payload.get("id") or "").strip()
    if not sid:
        sid = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload["id"] = sid
    payload["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not payload.get("started_at"):
        payload["started_at"] = payload["updated_at"]
    # Title for the thread list — first host/user line or brief title.
    if not payload.get("title"):
        title = (payload.get("brief_title") or "").strip()
        if not title:
            for ev in payload.get("events") or []:
                if ev.get("type") in ("host", "user") and (ev.get("text") or "").strip():
                    title = (ev["text"] or "").strip().split("\n")[0][:72]
                    break
        payload["title"] = title or f"Session {sid}"

    path = SESSIONS_DIR / f"{sid}.json"
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    (SESSIONS_DIR / "latest.json").write_text(text + "\n", encoding="utf-8")
    return path


def list_sessions(limit: int = 30) -> list[dict]:
    """Newest-first thread summaries for the session picker."""
    SESSIONS_DIR.mkdir(exist_ok=True)
    rows = []
    for path in SESSIONS_DIR.glob("*.json"):
        if path.name == "latest.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        events = data.get("events") or []
        rows.append({
            "id": data.get("id") or path.stem,
            "title": data.get("title") or path.stem,
            "started_at": data.get("started_at"),
            "updated_at": data.get("updated_at") or data.get("ended_at") or data.get("started_at"),
            "event_count": len(events),
            "has_draft": bool(data.get("draft_id")),
        })
    rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return rows[: max(1, min(int(limit), 100))]


def load_session(session_id: str) -> dict | None:
    sid = (session_id or "").strip()
    if not sid or "/" in sid or "\\" in sid or sid in (".", ".."):
        return None
    path = SESSIONS_DIR / f"{sid}.json"
    if not path.exists() and sid == "latest":
        path = SESSIONS_DIR / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _collect_source_links(session: dict) -> list[dict]:
    """Deduped {id, author, url, name?} from brief grounding + tool results."""
    seen: set[str] = set()
    out: list[dict] = []

    def add(src: dict | None) -> None:
        if not isinstance(src, dict):
            return
        url = (src.get("url") or "").strip()
        tid = str(src.get("id") or "").strip()
        author = (src.get("author") or "").strip().lstrip("@")
        if not url and tid and author:
            url = f"https://x.com/{author}/status/{tid}"
        if not url:
            return
        key = tid or url
        if key in seen:
            return
        seen.add(key)
        row = {"url": url}
        if tid:
            row["id"] = tid
        if author:
            row["author"] = author
        if src.get("name"):
            row["name"] = src["name"]
        out.append(row)

    for item in session.get("brief_items") or []:
        if not isinstance(item, dict):
            continue
        for src in item.get("sources") or []:
            add(src if isinstance(src, dict) else None)

    for ev in session.get("events") or []:
        if ev.get("type") != "tool_call":
            continue
        result = ev.get("result")
        if isinstance(result, dict):
            add(result)
            for key in ("posts", "results", "data", "replies"):
                arr = result.get(key)
                if isinstance(arr, list):
                    for row in arr:
                        add(row if isinstance(row, dict) else None)
    return out


def _session_transcript(session: dict) -> str:
    lines = []
    if session.get("brief_title"):
        lines.append(f"Brief title: {session['brief_title']}")
    if session.get("brief"):
        lines.append("=== ORIGINAL BRIEF (spoken script) ===")
        lines.append(session["brief"])
        lines.append("")

    links = _collect_source_links(session)
    if links:
        lines.append("=== AVAILABLE SOURCE LINKS (use these URLs inline when citing) ===")
        for src in links:
            name = src.get("name") or src.get("author") or "?"
            author = src.get("author") or "?"
            tid = src.get("id") or "?"
            lines.append(f"- {name} (@{author}) id={tid} → {src['url']}")
        lines.append("")

    lines.append("=== CONVERSATION ===")
    for ev in session.get("events") or []:
        kind = ev.get("type") or "?"
        if kind == "tool_call":
            name = ev.get("name") or "tool"
            args = ev.get("args") or {}
            result = ev.get("result") or {}
            lines.append(f"[tool] {name}({json.dumps(args, ensure_ascii=False)[:200]})")
            if isinstance(result, dict) and result.get("error"):
                lines.append(f"  error: {result['error']}")
            else:
                lines.append(f"  result: {json.dumps(result, ensure_ascii=False)[:1200]}")
        else:
            who = "You" if kind == "user" else ("Host" if kind == "host" else kind)
            text = (ev.get("text") or "").strip()
            if text:
                lines.append(f"{who}: {text}")
    return "\n".join(lines)


def _ensure_cited_urls(draft: dict) -> dict:
    """If sources list URLs missing from body, append a short sources line (last resort)."""
    sources = [s for s in (draft.get("sources") or []) if isinstance(s, dict) and s.get("url")]
    if not sources:
        return draft
    if draft.get("thread"):
        body = "\n".join(str(p) for p in draft["thread"])
    else:
        body = str(draft.get("text") or "")
    missing = [s for s in sources if s["url"] not in body]
    if not missing:
        return draft
    trailer = " ".join(s["url"] for s in missing)
    if draft.get("thread"):
        posts = [str(p) for p in draft["thread"]]
        last = (posts[-1] + " " + trailer).strip() if posts else trailer
        if len(last) <= 280:
            if posts:
                posts[-1] = last
            else:
                posts = [trailer]
        else:
            posts.append(trailer[:280])
        draft["thread"] = posts
        draft.pop("text", None)
    else:
        text = (body + "\n\n" + trailer).strip()
        draft["text"] = text if len(text) <= 280 else (body[: 280 - len(trailer) - 2] + " " + trailer)[:280]
    return draft


def synthesize_draft(session_id: str) -> dict:
    """Turn a saved thread into drafts/latest.json using recap_template.md + Gemini text."""
    session = load_session(session_id)
    if not session:
        raise RuntimeError(f"session not found: {session_id}")

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    template_path = ROOT / "recap_template.md"
    template = template_path.read_text(encoding="utf-8") if template_path.exists() else (
        "Write a first-person X post or short thread from this session. Link sources."
    )
    transcript = _session_transcript(session)
    model = cfg("XLC_SYNTH_MODEL", "gemini-2.5-flash")

    prompt = (
        "You turn a finished X-LiveCast voice session into a shareable X draft.\n"
        "This is NOT a generic summary of the feed. Center the USER's participation:\n"
        "what they dug into, what they asked, what they took away — with inline source URLs.\n\n"
        "Hard rules:\n"
        "1. First person as the user. Insightful and concrete; zero AI-slop filler.\n"
        "2. Ban phrases like: super interesting, eye-opening, sounds smart, really resonated,\n"
        "   dive deep, game-changer, it's all about, in today's world.\n"
        "3. Every cited post MUST include its full https://x.com/.../status/... URL in the\n"
        "   post body (not only in the sources array). Use AVAILABLE SOURCE LINKS / tool results.\n"
        "4. Prefer a thread when 2+ distinct sources were discussed.\n"
        "5. Do not invent opinions or digs that aren't in the conversation.\n"
        "6. Output ONLY valid JSON:\n"
        '   {"text":"<single post>"} OR {"thread":["<post1>",...]} '
        'plus "sources":[{"id","author","url"},...]\n'
        "Do not wrap in markdown fences.\n\n"
        "=== TEMPLATE ===\n"
        f"{template}\n\n"
        "=== SESSION ===\n"
        f"{transcript}\n"
    )

    url = GEMINI_TEXT_URL.format(model=model) + f"?key={api_key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.55, "responseMimeType": "application/json"},
    }).encode("utf-8")
    req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=90) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    parts = (((raw.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text_out = "".join(p.get("text", "") for p in parts).strip()
    if not text_out:
        raise RuntimeError(f"empty synthesis response: {json.dumps(raw)[:400]}")

    try:
        draft = json.loads(text_out)
    except json.JSONDecodeError:
        # Model sometimes wraps JSON in prose — pull the first {...} block.
        m = re.search(r"\{[\s\S]*\}", text_out)
        if not m:
            raise RuntimeError(f"could not parse draft JSON: {text_out[:400]}") from None
        draft = json.loads(m.group(0))

    draft = _ensure_cited_urls(draft)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    draft_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {
        "id": draft_id,
        "generated_at": now,
        "from_session": session.get("id") or session_id,
        "sources": draft.get("sources") or [],
    }
    if draft.get("thread"):
        out["thread"] = draft["thread"]
    else:
        out["text"] = draft.get("text") or text_out

    DRAFTS_DIR.mkdir(exist_ok=True)
    draft_path = DRAFTS_DIR / f"{draft_id}.json"
    latest = DRAFTS_DIR / "latest.json"
    blob = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    draft_path.write_text(blob, encoding="utf-8")
    latest.write_text(blob, encoding="utf-8")

    # Mark the session as having a draft (doesn't lock the thread — can re-synth).
    session["draft_id"] = draft_id
    session["draft_at"] = now
    save_session(session)
    return out


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
        # Mobile browsers (esp. in-app X WebView) aggressively cache JS/CSS;
        # without this, a fix can look "not deployed" after refresh.
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (stdlib name)
        route = self.path.split("?", 1)[0]

        if route == "/config":
            if not require_room_token(self):
                return
            try:
                minted = mint_ephemeral_token()
                self._send_json(200, {
                    "provider": "gemini",
                    "wsBase": GEMINI_WS_BASE,
                    "token": minted["token"],
                    "hasKey": True,
                    "model": cfg("XLC_GEMINI_MODEL", "gemini-3.1-flash-live-preview"),
                    "voice": cfg("XLC_GEMINI_VOICE", "Puck"),
                    "publicUrl": public_url_from_env(),
                    "roomTokenRequired": bool(room_token()),
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

        if route == "/health":
            self._send_json(200, {"ok": True, "publicUrl": public_url_from_env()})
            return

        if route == "/tools":
            if not require_room_token(self):
                return
            self._send_json(200, {"tools": list(x_tools.TOOLS.keys())})
            return

        if route == "/sessions":
            if not require_room_token(self):
                return
            self._send_json(200, {"sessions": list_sessions()})
            return

        if route == "/session":
            if not require_room_token(self):
                return
            # GET /session?id=... — load one thread (default: latest)
            qs = parse_qs(urlparse(self.path).query)
            sid = (qs.get("id") or ["latest"])[0]
            data = load_session(sid)
            if not data:
                self._send_json(404, {"error": "session not found"})
                return
            self._send_json(200, data)
            return

        if route == "/draft":
            if not require_room_token(self):
                return
            qs = parse_qs(urlparse(self.path).query)
            did = (qs.get("id") or ["latest"])[0]
            path = DRAFTS_DIR / ("latest.json" if did == "latest" else f"{did}.json")
            if not path.exists():
                self._send_json(404, {"error": "draft not found"})
                return
            try:
                self._send_json(200, json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/drafts":
            if not require_room_token(self):
                return
            self._send_json(200, {"drafts": list_drafts()})
            return

        if route == "/bundle":
            if not require_room_token(self):
                return
            # GET /bundle — return latest exported bundle, or export fresh if missing
            try:
                latest = BUNDLES_DIR / "latest.json"
                if not latest.exists():
                    bundle_mod.export_bundle()
                self._send_json(200, json.loads(latest.read_text(encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": str(exc)})
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
            if not require_room_token(self):
                return
            name = payload.get("name", "")
            args = payload.get("args") or {}
            self._send_json(200, {"result": x_tools.dispatch(name, args)})
            return

        if route == "/session":
            if not require_room_token(self):
                return
            path = save_session(payload)
            self._send_json(200, {"saved": str(path), "id": payload.get("id")})
            return

        if route == "/synthesize":
            if not require_room_token(self):
                return
            sid = (payload.get("session_id") or payload.get("id") or "").strip()
            if not sid:
                # Fall back to latest thread.
                latest = load_session("latest")
                sid = (latest or {}).get("id") or ""
            if not sid:
                self._send_json(400, {"error": "no session_id and no latest session"})
                return
            try:
                draft = synthesize_draft(sid)
                self._send_json(200, {"draft": draft})
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")
                self._send_json(exc.code, {"error": "gemini_error", "detail": detail})
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/brief/generate":
            if not require_room_token(self):
                return
            limit = payload.get("limit", 25)
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                limit = 25
            try:
                # Keep generate_brief on the same volume as the room's BRIEFS_DIR.
                if BRIEFS_DIR.resolve() != (ROOT / "briefs").resolve():
                    os.environ["XLC_DATA_DIR"] = str(BRIEFS_DIR.parent)
                result = generate_brief_mod.generate_brief(bookmark_limit=limit)
                brief = read_brief_full()
                self._send_json(200, {
                    "ok": True,
                    "brief": brief,
                    "title": result.get("title"),
                    "new_bookmarks": result.get("_new_bookmark_count"),
                    "marked_seen": result.get("_marked_seen"),
                    "saved": result.get("_saved"),
                })
            except error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")
                self._send_json(exc.code, {"error": "gemini_error", "detail": detail})
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/publish":
            if not require_room_token(self):
                return
            confirm = payload.get("confirm") is True
            draft_id = (payload.get("draft_id") or payload.get("id") or "latest").strip()
            text = payload.get("text")
            thread = payload.get("thread")
            if text is not None and not isinstance(text, str):
                self._send_json(400, {"error": "text must be a string"})
                return
            if thread is not None and not isinstance(thread, list):
                self._send_json(400, {"error": "thread must be an array of strings"})
                return
            try:
                result = publish_mod.publish_draft(
                    draft_id=draft_id,
                    confirm=confirm,
                    text=text,
                    thread=thread,
                )
                self._send_json(200, result)
            except publish_mod.PublishError as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/bundle":
            if not require_room_token(self):
                return
            action = (payload.get("action") or "").strip().lower()
            try:
                if action == "export":
                    path = bundle_mod.export_bundle()
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self._send_json(200, {"ok": True, "bundle": data, "saved": str(path)})
                elif action == "import":
                    raw = payload.get("bundle")
                    if not isinstance(raw, dict):
                        self._send_json(400, {"error": "bundle must be a JSON object"})
                        return
                    result = bundle_mod.import_bundle_dict(raw)
                    self._send_json(200, result)
                else:
                    self._send_json(400, {"error": "action must be export or import"})
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": str(exc)})
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

    Note: is.gd / v.gd / tinyurl blacklist *.trycloudflare.com, so we use
    cleanuri (and similar) instead.
    """
    headers = {"User-Agent": "X-LiveCast/0.1"}

    # (name, method, endpoint, body_or_None)
    attempts = [
        (
            "cleanuri",
            "POST",
            "https://cleanuri.com/api/v1/shorten",
            urlencode({"url": url}).encode(),
        ),
        (
            "is.gd",
            "GET",
            f"https://is.gd/create.php?format=simple&url={quote(url, safe='')}",
            None,
        ),
        (
            "v.gd",
            "GET",
            f"https://v.gd/create.php?format=simple&url={quote(url, safe='')}",
            None,
        ),
    ]
    for name, method, endpoint, body in attempts:
        try:
            req_headers = dict(headers)
            if body is not None:
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            req = request.Request(endpoint, data=body, headers=req_headers, method=method)
            with request.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode("utf-8").strip()
            short = raw
            if name == "cleanuri":
                try:
                    short = json.loads(raw).get("result_url") or ""
                except json.JSONDecodeError:
                    short = ""
            if short.startswith("http") and "error" not in short.lower():
                return short
        except Exception:  # noqa: BLE001 (best-effort; any failure just falls through)
            continue
    return url


def _send_dm(xurl: str, user_id: str, text: str) -> dict:
    """Send one DM; returns parsed JSON or {error: ...}."""
    try:
        result = subprocess.run(
            [xurl, "-X", "POST", f"/2/dm_conversations/with/{user_id}/messages",
             "-d", json.dumps({"text": text})],
            capture_output=True, text=True, timeout=15,
        )
        if not result.stdout:
            return {"error": result.stderr or "empty DM response"}
        return json.loads(result.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def dm_room_link(url: str, *, ephemeral: bool = False) -> dict:
    """DM the room link to the authenticated user's own X account.

    Sends two messages on purpose:
      1) the short URL alone — X linkifies bare-URL DMs far more reliably than
         URLs buried in a paragraph (self-DMs are especially picky)
      2) a short note with no URL, so the first bubble stays a clean tap target
    """
    xurl = x_tools.xurl_bin()
    if not xurl:
        return {"error": "xurl not found; install it and run `xurl auth oauth2` first"}

    # If the host gates APIs, bake the token into the shared URL so the phone
    # UI can pass it on every request (also stored in sessionStorage).
    token = room_token()
    if token and "token=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}token={quote(token, safe='')}"

    # Evergreen URLs are already short/stable — skip shorteners that may rewrite them.
    short_url = shorten_url(url) if ephemeral or "trycloudflare.com" in url else url
    if short_url != url:
        sys.stderr.write(f"[X-LiveCast] Short link: {short_url}\n")

    try:
        who = json.loads(
            subprocess.run([xurl, "/2/users/me"], capture_output=True, text=True, timeout=15, check=True).stdout
        )
        user_id = who["data"]["id"]
    except Exception as exc:  # noqa: BLE001
        return {"error": f"could not resolve X user: {exc}"}

    # Message 1: URL only — nothing else on the line.
    first = _send_dm(xurl, user_id, short_url)
    if first.get("error") and "data" not in first:
        return first

    # Message 2: context, no URL (avoids competing with the tap target above).
    if ephemeral:
        note = (
            "\U0001f3a7 X-LiveCast room is ready \u2014 tap the link above.\n"
            "Demo link (dies when the host process stops). "
            "If it won't open: long-press \u2192 Copy, or switch to cellular."
        )
    else:
        note = (
            "\U0001f3a7 X-LiveCast is ready \u2014 tap the link above.\n"
            "Same URL every day; today's brief is live on the host."
        )
    second = _send_dm(xurl, user_id, note)
    if second.get("error") and "data" not in second:
        # Link already went out; treat note failure as soft.
        return {"ok": True, "short_url": short_url, "note_error": second["error"], "link": first}
    return {"ok": True, "short_url": short_url, "link": first, "note": second}


def _do_dm(url: str, *, ephemeral: bool) -> None:
    sys.stderr.write("[X-LiveCast] Sending yourself a DM with the room link...\n")
    result = dm_room_link(url, ephemeral=ephemeral)
    if result.get("error"):
        sys.stderr.write(f"[X-LiveCast] DM failed: {result['error']}\n")
    else:
        short = result.get("short_url") or ""
        sys.stderr.write(f"[X-LiveCast] DM sent.{(' Short: ' + short) if short else ''}\n")


def main() -> int:
    load_dotenv(ROOT / ".env")
    apply_data_dir()

    parser = argparse.ArgumentParser(description="X-LiveCast voice room server")
    parser.add_argument("--share", action="store_true",
                         help="Bind 0.0.0.0 and expose via tunnel (see XLC_TUNNEL_MODE).")
    parser.add_argument("--dm", action="store_true",
                         help="DM the public room link to your own X account.")
    parser.add_argument("--dm-only", action="store_true",
                         help="DM XLC_PUBLIC_URL and exit (room must already be running).")
    args = parser.parse_args()

    if args.dm_only:
        evergreen = public_url_from_env()
        if not evergreen:
            sys.stderr.write(
                "[X-LiveCast] --dm-only needs XLC_PUBLIC_URL in .env "
                "(evergreen HTTPS origin for the always-on host).\n"
            )
            return 1
        _do_dm(evergreen, ephemeral=False)
        return 0

    if not os.environ.get("GEMINI_API_KEY", "").strip():
        sys.stderr.write(
            "\n[X-LiveCast] GEMINI_API_KEY is not set.\n"
            "  Get a free key at https://aistudio.google.com/apikey (no billing needed),\n"
            "  then copy .env.example to .env and set GEMINI_API_KEY.\n"
            "  The server will still start, but the voice room won't connect until it's set.\n\n"
        )

    # Render/Railway set PORT; fall back to XLC_PORT / 8787 for local.
    port = int(cfg("PORT", cfg("XLC_PORT", "8787")))
    local_url = f"http://localhost:{port}"
    mode = tunnel_mode()
    evergreen = public_url_from_env()
    # PaaS (Render sets RENDER=true) and share/evergreen need 0.0.0.0.
    on_paas = bool(os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT") or cfg("PORT", ""))
    bind_public = bool(args.share or evergreen or mode == "named" or on_paas)

    httpd = ThreadingHTTPServer(("0.0.0.0" if bind_public else "127.0.0.1", port), Handler)
    sys.stderr.write(f"[X-LiveCast] Local:  {local_url}  (Ctrl+C to stop)\n")
    if evergreen:
        sys.stderr.write(f"[X-LiveCast] Public: {evergreen}  (XLC_PUBLIC_URL, evergreen)\n")
    if room_token():
        sys.stderr.write("[X-LiveCast] Room token gate ON (XLC_ROOM_TOKEN)\n")

    public_url = evergreen
    tunnel_proc = None
    ephemeral = False

    if args.share:
        if mode == "named":
            if not evergreen:
                sys.stderr.write(
                    "[X-LiveCast] XLC_TUNNEL_MODE=named but XLC_PUBLIC_URL is unset. "
                    "Point a named cloudflared tunnel / reverse proxy at this port, "
                    "then set XLC_PUBLIC_URL to that HTTPS origin.\n"
                )
            else:
                sys.stderr.write(
                    "[X-LiveCast] Tunnel mode=named — expecting an external tunnel "
                    f"already forwarding to localhost:{port}.\n"
                )
        elif mode == "none":
            if not evergreen:
                sys.stderr.write(
                    "[X-LiveCast] Tunnel mode=none and no XLC_PUBLIC_URL — "
                    "room is LAN-only unless something else fronts it.\n"
                )
        else:
            # quick (demo)
            try:
                tunnel_proc, public_url = start_tunnel(port)
                ephemeral = True
                sys.stderr.write(
                    f"[X-LiveCast] Public: {public_url}  "
                    "(quick tunnel demo — dies when this process stops)\n"
                )
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write(f"[X-LiveCast] Could not start tunnel: {exc}\n")

    if args.dm:
        dm_target = public_url or evergreen
        if dm_target:
            _do_dm(dm_target, ephemeral=ephemeral or ("trycloudflare.com" in dm_target))
        else:
            sys.stderr.write(
                "[X-LiveCast] Skipping DM: no public URL. "
                "Set XLC_PUBLIC_URL, or use --share with quick tunnel.\n"
            )

    if os.environ.get("XLC_NO_BROWSER", "").strip() not in ("1", "true", "yes") and not bind_public:
        threading.Timer(0.6, lambda: webbrowser.open(local_url)).start()

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
