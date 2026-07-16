#!/usr/bin/env python3
"""X tools for X-LiveCast, backed by the official `xurl` CLI.

These are the real tools that make the voice room an agent. They shell out to
`xurl` (the official X CLI, https://github.com/xdevplatform/xurl), which handles
OAuth locally and talks to the X API v2. The same auth powers the hosted X MCP
(`xurl mcp`), so this stays consistent with the "official X MCP" approach while
being trivial to call from Python.

Exposed (read-only, safe to call during a live conversation):
  - search_x(query, limit)       recent search (7-day window)
  - get_home_timeline(limit)     your reverse-chronological home timeline
  - get_bookmarks(limit)         your bookmarked posts
  - get_user_posts(username)     a specific user's recent posts
  - get_post(url_or_id)          open one X post (text + linked article cards)
  - get_post_replies(url_or_id)  recent replies in that post's thread
  - read_url(url)                fetch + extract readable text from a linked
                                  page (e.g. an article a post links to)

Note: trending topics (`/2/trends/by/woeid/{id}`) requires X's Pro tier
($5,000/mo) — confirmed via X's own docs, not available on pay-per-use, so it
is not exposed as a tool.

Writes (post/reply) are intentionally NOT exposed here — posting is handled by
the outer agent after the call, with confirmation (Phase D), to avoid accidental
voice-triggered posts.

CLI (for testing):
  python3 scripts/x_tools.py search "ai voice agents" 5
  python3 scripts/x_tools.py timeline 5
  python3 scripts/x_tools.py check
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote

ROOT_DIR = Path(__file__).resolve().parent.parent

_SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "nav", "footer", "aside", "form", "button", "iframe"}
_CONTENT_TAGS = {"article", "main"}  # if present, prefer text from inside these over the whole page
_READ_URL_USER_AGENT = (
    "Mozilla/5.0 (compatible; XLiveCastBot/1.0; local personal voice skill; "
    "+https://github.com/richardtang/live-x-podcast)"
)


class _ReadableTextExtractor(HTMLParser):
    """Minimal, dependency-free HTML-to-text extractor (title + body text).

    Skips obvious UI chrome (nav/footer/aside/forms/scripts) and, when the page
    uses semantic <article>/<main> tags, prefers text from inside them — a
    cheap approximation of "readability" without adding a parsing dependency.
    """

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._content_depth = 0
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []      # fallback: all non-chrome text
        self.content_parts: list[str] = []   # text inside <article>/<main>, if any

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _CONTENT_TAGS:
            self._content_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in _CONTENT_TAGS and self._content_depth > 0:
            self._content_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
            return
        self.body_parts.append(text)
        if self._content_depth > 0:
            self.content_parts.append(text)

_TWEET_FIELDS = "created_at,author_id,public_metrics,entities,note_tweet,text,attachments"
_EXPANSIONS = "author_id,attachments.media_keys,referenced_tweets.id"
_USER_FIELDS = "username,name"
_MEDIA_FIELDS = "type,url,preview_image_url,alt_text"


class XToolError(Exception):
    """Raised when an X tool cannot complete (missing xurl, auth, or API error)."""


# Common install locations, so we work even when launched without Homebrew's
# bin on PATH (e.g. GUI-launched processes on macOS). Override with XLC_XURL_BIN.
_XURL_CANDIDATES = [
    "/opt/homebrew/bin/xurl",
    "/usr/local/bin/xurl",
    os.path.expanduser("~/.local/bin/xurl"),
]


def xurl_bin() -> str | None:
    """Resolve the xurl executable path independent of PATH."""
    override = os.environ.get("XLC_XURL_BIN", "").strip()
    if override and os.path.exists(override):
        return override
    found = shutil.which("xurl")
    if found:
        return found
    for candidate in _XURL_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return None


def _xurl(path: str, method: str = "GET", body: str | None = None) -> dict:
    """Run an xurl request and return parsed JSON, or raise XToolError."""
    binpath = xurl_bin()
    if binpath is None:
        raise XToolError(
            "xurl not found. Install it (brew install --cask "
            "xdevplatform/tap/xurl), run `xurl auth oauth2`, or set XLC_XURL_BIN."
        )

    cmd = [binpath]
    # Optionally pin a specific xurl app (otherwise xurl uses its default app;
    # set one with `xurl auth default <app>`).
    app = os.environ.get("XLC_XURL_APP", "").strip()
    if app:
        cmd += ["--app", app]
    if method != "GET":
        cmd += ["-X", method]
    if body is not None:
        cmd += ["-d", body]
    cmd.append(path)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:  # noqa: PERF203
        raise XToolError("xurl request timed out") from exc

    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        detail = (proc.stderr or out or "unknown error").strip()
        raise XToolError(f"xurl failed: {detail[:400]}")

    if not out:
        raise XToolError("xurl returned no data (are you authenticated? run `xurl auth oauth2`)")

    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        raise XToolError(f"could not parse xurl output: {out[:200]}") from exc

    if isinstance(data, dict) and data.get("errors"):
        raise XToolError(f"X API error: {json.dumps(data['errors'])[:400]}")
    return data


def _format_tweets(data: dict, limit: int) -> list[dict]:
    """Turn an X v2 tweets response into a compact list of posts.

    Each item includes both `author` (@handle) and `name` (display name) when
    available — the brief should speak the display name aloud.
    """
    users = {}
    for u in (data.get("includes", {}) or {}).get("users", []):
        users[u.get("id")] = {
            "username": u.get("username") or "unknown",
            "name": u.get("name") or u.get("username") or "unknown",
        }

    tweets = []
    for t in (data.get("data") or [])[:limit]:
        metrics = t.get("public_metrics") or {}
        tweet_id = t.get("id")
        user = users.get(t.get("author_id"), {})
        author = user.get("username") or t.get("author_id", "unknown")
        name = user.get("name") or author
        tweets.append({
            "id": tweet_id,
            "author": author,
            "name": name,
            "text": (t.get("text") or "").replace("\n", " ").strip(),
            "likes": metrics.get("like_count", 0),
            "url": f"https://x.com/{author}/status/{tweet_id}" if tweet_id and author != "unknown" else None,
        })
    return tweets


def _extract_tweet_id(url_or_id: str) -> str | None:
    """Accept a bare tweet id or an x.com / twitter.com / t.co status URL."""
    s = (url_or_id or "").strip()
    if not s:
        return None
    if s.isdigit():
        return s
    m = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", s)
    if m:
        return m.group(1)
    return None


def _linked_urls_from_entities(tweet: dict) -> list[dict]:
    """Pull expanded/unwound URLs (with title/description when X has them)."""
    out = []
    entities = tweet.get("entities") or {}
    for u in entities.get("urls") or []:
        item = {
            "url": u.get("unwound_url") or u.get("expanded_url") or u.get("url"),
            "tco": u.get("url"),
            "title": u.get("title") or "",
            "description": u.get("description") or "",
        }
        if item["url"]:
            out.append(item)
    return out


def get_post_replies(url_or_id: str, limit: int = 15) -> dict:
    """Pull recent replies in a post's conversation thread.

    Uses recent search with `conversation_id:<tweet_id>` (last ~7 days). Returns
    the root post summary plus reply texts — enough for the host to skim what
    people are saying under a post.
    """
    tweet_id = _extract_tweet_id(url_or_id)
    if not tweet_id:
        raise XToolError("need a tweet id or an x.com/.../status/... URL")
    limit = max(1, min(int(limit), 25))

    root = None
    try:
        root = get_post(tweet_id)
    except XToolError:
        root = {"id": tweet_id, "url": f"https://x.com/i/status/{tweet_id}"}

    q = quote(f"conversation_id:{tweet_id}")
    path = (
        f"/2/tweets/search/recent?query={q}&max_results={max(limit, 10)}"
        f"&tweet.fields={_TWEET_FIELDS}"
        f"&expansions={_EXPANSIONS}&user.fields={_USER_FIELDS}"
    )
    data = _xurl(path)
    replies = []
    for item in _format_tweets(data, limit + 5):
        # Skip the root post itself if it shows up in search results.
        if item.get("id") == tweet_id:
            continue
        replies.append(item)
        if len(replies) >= limit:
            break

    return {
        "root": {
            "id": root.get("id"),
            "author": root.get("author"),
            "name": root.get("name"),
            "text": (root.get("text") or "")[:280],
            "url": root.get("url"),
        },
        "reply_count_returned": len(replies),
        "replies": replies,
        "note": (
            "Recent-search window is ~7 days; older replies may be missing. "
            "Summarize the interesting ones — don't read every reply aloud."
        ),
    }


def get_post(url_or_id: str) -> dict:
    """Open a specific X post by status URL or tweet id.

    Returns the post text, author handle + display name, and any linked
    articles X already unwound (title + description). Prefer this over
    read_url when the user asks to open a post — x.com pages are JS shells
    and often return nothing useful to a plain HTTP fetch.
    """
    tweet_id = _extract_tweet_id(url_or_id)
    if not tweet_id:
        raise XToolError("need a tweet id or an x.com/.../status/... URL")

    path = (
        f"/2/tweets/{tweet_id}"
        f"?tweet.fields={_TWEET_FIELDS}"
        f"&expansions={_EXPANSIONS}"
        f"&user.fields={_USER_FIELDS}"
        f"&media.fields={_MEDIA_FIELDS}"
    )
    data = _xurl(path)
    tweet = data.get("data")
    if not tweet:
        raise XToolError(f"post {tweet_id} not found or not accessible")

    users = {u.get("id"): u for u in ((data.get("includes") or {}).get("users") or [])}
    author_u = users.get(tweet.get("author_id"), {})
    author = author_u.get("username") or "unknown"
    name = author_u.get("name") or author

    # Prefer note_tweet (long-form) text when present.
    note = tweet.get("note_tweet") or {}
    text = (note.get("text") or tweet.get("text") or "").strip()

    media = []
    media_by_key = {m.get("media_key"): m for m in ((data.get("includes") or {}).get("media") or [])}
    for key in ((tweet.get("attachments") or {}).get("media_keys") or []):
        m = media_by_key.get(key)
        if not m:
            continue
        media.append({
            "type": m.get("type"),
            "alt_text": m.get("alt_text") or "",
            "url": m.get("url") or m.get("preview_image_url"),
        })

    linked = _linked_urls_from_entities(tweet)
    metrics = tweet.get("public_metrics") or {}
    return {
        "id": tweet_id,
        "author": author,
        "name": name,
        "text": text,
        "likes": metrics.get("like_count", 0),
        "url": f"https://x.com/{author}/status/{tweet_id}",
        "linked_urls": linked,
        "media": media,
        "hint": (
            "If linked_urls has a title/description, summarize from that first. "
            "Call read_url on linked_urls[].url only if the user wants the full article body."
        ),
    }


def search_x(query: str, limit: int = 10) -> dict:
    """Search recent X posts (last 7 days) matching `query`."""
    limit = max(1, min(int(limit), 25))
    q = quote(query)
    path = (
        f"/2/tweets/search/recent?query={q}&max_results={max(limit, 10)}"
        f"&tweet.fields={_TWEET_FIELDS}&expansions={_EXPANSIONS}&user.fields={_USER_FIELDS}"
    )
    data = _xurl(path)
    return {"query": query, "results": _format_tweets(data, limit)}


def get_bookmarks(limit: int = 25) -> dict:
    """Return the authenticated user's bookmarked posts (most recent first)."""
    limit = max(1, min(int(limit), 100))
    me = _xurl("/2/users/me")
    user_id = (me.get("data") or {}).get("id")
    if not user_id:
        raise XToolError("could not resolve current user (run `xurl auth oauth2`)")
    path = (
        f"/2/users/{user_id}/bookmarks"
        f"?max_results={max(limit, 10)}&tweet.fields={_TWEET_FIELDS}"
        f"&expansions={_EXPANSIONS}&user.fields={_USER_FIELDS}"
    )
    data = _xurl(path)
    return {"results": _format_tweets(data, limit)}


def get_user_posts(username: str, limit: int = 10) -> dict:
    """Return a specific X user's recent posts by @handle."""
    limit = max(1, min(int(limit), 25))
    username = (username or "").lstrip("@").strip()
    if not username:
        raise XToolError("username is required")

    who = _xurl(f"/2/users/by/username/{quote(username)}")
    user_id = (who.get("data") or {}).get("id")
    if not user_id:
        raise XToolError(f"could not resolve @{username}")

    path = f"/2/users/{user_id}/tweets?max_results={max(limit, 10)}&tweet.fields={_TWEET_FIELDS}"
    data = _xurl(path)
    # Single-author endpoint has no `includes.users`; inject it so
    # _format_tweets can resolve the author name instead of falling back to id.
    for t in data.get("data") or []:
        t["author_id"] = user_id
    # Resolve display name when possible.
    display = (who.get("data") or {}).get("name") or username
    data.setdefault("includes", {})["users"] = [
        {"id": user_id, "username": username, "name": display}
    ]
    return {"username": username, "results": _format_tweets(data, limit)}


def read_url(url: str, max_chars: int = 3000) -> dict:
    """Fetch a web page (following redirects, e.g. t.co short links) and return
    its readable title/text, so the host can discuss an article a post links to.
    Best-effort: no JS execution, so client-rendered pages may return little text.
    """
    url = (url or "").strip()
    if not url:
        raise XToolError("url is required")
    if not url.startswith(("http://", "https://")):
        raise XToolError("url must start with http:// or https://")

    max_chars = max(200, min(int(max_chars), 8000))
    req = urlrequest.Request(url, headers={"User-Agent": _READ_URL_USER_AGENT, "Accept": "text/html,*/*"})

    try:
        with urlrequest.urlopen(req, timeout=15) as resp:  # nosec B310 - user-directed fetch, not SSRF-exposed
            final_url = resp.geturl()
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read(2_000_000)  # cap at 2MB to bound latency/memory
    except urlerror.HTTPError as exc:
        raise XToolError(f"HTTP {exc.code} fetching {url}") from exc
    except Exception as exc:  # noqa: BLE001 (network/timeout/ssl — surface any failure)
        raise XToolError(f"could not fetch {url}: {exc}") from exc

    if "html" not in content_type and "text" not in content_type:
        return {"url": url, "final_url": final_url, "content_type": content_type,
                "error": f"not a readable page ({content_type or 'unknown type'})"}

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")

    parser = _ReadableTextExtractor()
    try:
        parser.feed(text)
    except Exception:  # noqa: BLE001 (malformed HTML shouldn't crash the tool)
        pass

    title = " ".join(parser.title_parts).strip()
    raw_body = parser.content_parts if parser.content_parts else parser.body_parts
    body = " ".join(" ".join(raw_body).split())  # collapse whitespace
    truncated = len(body) > max_chars
    return {
        "url": url,
        "final_url": final_url,
        "title": title,
        "text": body[:max_chars],
        "truncated": truncated,
    }


def get_home_timeline(limit: int = 10) -> dict:
    """Return the authenticated user's reverse-chronological home timeline."""
    limit = max(1, min(int(limit), 25))
    me = _xurl("/2/users/me")
    user_id = (me.get("data") or {}).get("id")
    if not user_id:
        raise XToolError("could not resolve current user (run `xurl auth oauth2`)")
    path = (
        f"/2/users/{user_id}/timelines/reverse_chronological"
        f"?max_results={max(limit, 10)}&tweet.fields={_TWEET_FIELDS}"
        f"&expansions={_EXPANSIONS}&user.fields={_USER_FIELDS}"
    )
    data = _xurl(path)
    return {"results": _format_tweets(data, limit)}


# --- Lightweight local memory: which items we've already briefed. ---
# Stored as .state/seen.json -> {"<source>": ["<id>", ...]}. This lets a repeat
# run brief only NEW items (e.g. bookmarks added since last time).

_STATE_DIR = ROOT_DIR / ".state"
_SEEN_PATH = _STATE_DIR / "seen.json"


def load_seen() -> dict:
    if not _SEEN_PATH.exists():
        return {}
    try:
        return json.loads(_SEEN_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_seen(seen: dict) -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    _SEEN_PATH.write_text(json.dumps(seen, indent=2), encoding="utf-8")


def filter_unseen(source: str, items: list[dict]) -> list[dict]:
    """Return only items whose id hasn't been marked seen for this source."""
    seen = set(load_seen().get(source, []))
    return [it for it in items if it.get("id") and it["id"] not in seen]


def mark_seen(source: str, ids: list[str]) -> int:
    """Record ids as seen for a source. Returns the new total count."""
    seen = load_seen()
    current = set(seen.get(source, []))
    current.update(i for i in ids if i)
    seen[source] = sorted(current)
    _save_seen(seen)
    return len(seen[source])


# Tool dispatch table used by the /tool endpoint and (later) the outer agent.
TOOLS = {
    "search_x": lambda args: search_x(args.get("query", ""), args.get("limit", 10)),
    "get_home_timeline": lambda args: get_home_timeline(args.get("limit", 10)),
    "get_bookmarks": lambda args: get_bookmarks(args.get("limit", 25)),
    "get_user_posts": lambda args: get_user_posts(args.get("username", ""), args.get("limit", 10)),
    "get_post": lambda args: get_post(args.get("url_or_id") or args.get("url") or args.get("id") or ""),
    "get_post_replies": lambda args: get_post_replies(
        args.get("url_or_id") or args.get("url") or args.get("id") or "",
        args.get("limit", 15),
    ),
    "read_url": lambda args: read_url(args.get("url", ""), args.get("max_chars", 3000)),
}


def dispatch(name: str, args: dict) -> dict:
    """Run a named tool; always returns a JSON-serializable dict (never raises)."""
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return fn(args or {})
    except XToolError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001 (surface anything to the model)
        return {"error": f"tool failed: {exc}"}


def _cli(argv: list[str]) -> int:
    if not argv:
        print(
            "usage: x_tools.py [search QUERY [N] | timeline [N] | bookmarks [N] |"
            " bookmarks-new [N] | mark-seen SOURCE id1 id2 ... | user-posts USERNAME [N] |"
            " post URL_OR_ID | replies URL_OR_ID [N] | read URL | check]",
            file=sys.stderr,
        )
        return 2
    cmd = argv[0]
    if cmd == "check":
        print(json.dumps({
            "xurl_bin": xurl_bin(),
            "seen": {k: len(v) for k, v in load_seen().items()},
        }))
        return 0
    if cmd == "search":
        query = argv[1] if len(argv) > 1 else ""
        limit = int(argv[2]) if len(argv) > 2 else 5
        print(json.dumps(dispatch("search_x", {"query": query, "limit": limit}), indent=2))
        return 0
    if cmd == "timeline":
        limit = int(argv[1]) if len(argv) > 1 else 5
        print(json.dumps(dispatch("get_home_timeline", {"limit": limit}), indent=2))
        return 0
    if cmd == "bookmarks":
        limit = int(argv[1]) if len(argv) > 1 else 25
        print(json.dumps(dispatch("get_bookmarks", {"limit": limit}), indent=2))
        return 0
    if cmd == "user-posts":
        username = argv[1] if len(argv) > 1 else ""
        limit = int(argv[2]) if len(argv) > 2 else 5
        print(json.dumps(dispatch("get_user_posts", {"username": username, "limit": limit}), indent=2))
        return 0
    if cmd == "post":
        url_or_id = argv[1] if len(argv) > 1 else ""
        print(json.dumps(dispatch("get_post", {"url_or_id": url_or_id}), indent=2))
        return 0
    if cmd == "replies":
        url_or_id = argv[1] if len(argv) > 1 else ""
        limit = int(argv[2]) if len(argv) > 2 else 10
        print(json.dumps(dispatch("get_post_replies", {"url_or_id": url_or_id, "limit": limit}), indent=2))
        return 0
    if cmd == "read":
        url = argv[1] if len(argv) > 1 else ""
        print(json.dumps(dispatch("read_url", {"url": url}), indent=2))
        return 0
    if cmd == "bookmarks-new":
        # Only bookmarks not yet briefed (does not mark them seen).
        limit = int(argv[1]) if len(argv) > 1 else 25
        res = dispatch("get_bookmarks", {"limit": limit})
        if "error" in res:
            print(json.dumps(res, indent=2)); return 1
        new = filter_unseen("bookmarks", res.get("results", []))
        print(json.dumps({"new_count": len(new), "results": new}, indent=2))
        return 0
    if cmd == "mark-seen":
        if len(argv) < 3:
            print("usage: x_tools.py mark-seen SOURCE id1 id2 ...", file=sys.stderr)
            return 2
        total = mark_seen(argv[1], argv[2:])
        print(json.dumps({"source": argv[1], "marked": len(argv[2:]), "total_seen": total}))
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
