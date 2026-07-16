#!/usr/bin/env python3
"""Publish a confirmed X-LiveCast draft via xurl (tweet.write).

Never auto-posts: callers must pass confirm=True (API) or --confirm (CLI).
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = ROOT / "drafts"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x_tools  # noqa: E402


class PublishError(Exception):
    """User-facing publish failure (auth, confirm, API)."""


def load_draft(draft_id: str = "latest") -> dict | None:
    did = (draft_id or "latest").strip()
    if not did or "/" in did or "\\" in did or did in (".", ".."):
        return None
    path = DRAFTS_DIR / ("latest.json" if did == "latest" else f"{did}.json")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_draft(draft: dict) -> Path:
    """Write draft to drafts/<id>.json and drafts/latest.json."""
    DRAFTS_DIR.mkdir(exist_ok=True)
    draft_id = draft.get("id") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    draft["id"] = draft_id
    blob = json.dumps(draft, indent=2, ensure_ascii=False) + "\n"
    path = DRAFTS_DIR / f"{draft_id}.json"
    path.write_text(blob, encoding="utf-8")
    (DRAFTS_DIR / "latest.json").write_text(blob, encoding="utf-8")
    return path


def _posts_from_draft(draft: dict, text: str | None = None, thread: list | None = None) -> list[str]:
    if thread is not None:
        posts = [str(p).strip() for p in thread if str(p).strip()]
    elif text is not None and str(text).strip():
        posts = [str(text).strip()]
    elif draft.get("thread"):
        posts = [str(p).strip() for p in draft["thread"] if str(p).strip()]
    elif draft.get("text"):
        posts = [str(draft["text"]).strip()]
    else:
        posts = []
    if not posts:
        raise PublishError("draft has no text or thread to publish")
    for i, p in enumerate(posts):
        if len(p) > 280:
            raise PublishError(f"post {i + 1}/{len(posts)} is {len(p)} chars (max 280)")
    return posts


def post_tweet(text: str, reply_to_id: str | None = None) -> dict:
    """POST /2/tweets. Returns {id, text, url} or raises PublishError."""
    body: dict = {"text": text}
    if reply_to_id:
        body["reply"] = {"in_reply_to_tweet_id": str(reply_to_id)}
    try:
        data = x_tools._xurl("/2/tweets", method="POST", body=json.dumps(body))
    except x_tools.XToolError as exc:
        msg = str(exc)
        hint = ""
        low = msg.lower()
        if "403" in msg or "forbidden" in low or "oauth1" in low or "write" in low:
            hint = (
                " Hint: posting needs tweet.write (usually OAuth 1.0a user context). "
                "Try `xurl auth oauth1 --app <app>` and ensure the app has Read and Write."
            )
        elif "401" in msg or "unauthorized" in low or "auth" in low:
            hint = " Hint: run `xurl auth oauth2` or `xurl auth oauth1` and retry."
        raise PublishError(msg + hint) from exc

    tweet = data.get("data") if isinstance(data, dict) else None
    if not isinstance(tweet, dict) or not tweet.get("id"):
        raise PublishError(f"unexpected tweet response: {json.dumps(data)[:400]}")
    tid = str(tweet["id"])
    return {
        "id": tid,
        "text": tweet.get("text") or text,
        "url": f"https://x.com/i/status/{tid}",
    }


def publish_draft(
    *,
    draft_id: str = "latest",
    confirm: bool = False,
    text: str | None = None,
    thread: list | None = None,
) -> dict:
    """Publish a draft to X. Requires confirm=True. Updates the draft file on success."""
    if not confirm:
        raise PublishError("refusing to publish without confirm=true (safety)")

    draft = load_draft(draft_id)
    if not draft:
        raise PublishError(f"draft not found: {draft_id}")

    if draft.get("tweet_ids"):
        raise PublishError(
            f"draft already published (tweet_ids={draft.get('tweet_ids')}). "
            "Edit and clear tweet_ids to re-publish, or synthesize a new draft."
        )

    posts = _posts_from_draft(draft, text=text, thread=thread)
    # Persist edits before posting so a partial failure still keeps the reviewed text.
    if thread is not None:
        draft["thread"] = posts
        draft.pop("text", None)
    elif text is not None:
        draft["text"] = posts[0]
        draft.pop("thread", None)

    tweet_ids: list[str] = []
    urls: list[str] = []
    parent_id: str | None = None
    for post in posts:
        result = post_tweet(post, reply_to_id=parent_id)
        tweet_ids.append(result["id"])
        urls.append(result["url"])
        parent_id = result["id"]

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    draft["published_at"] = now
    draft["tweet_ids"] = tweet_ids
    draft["urls"] = urls
    path = save_draft(draft)
    return {
        "ok": True,
        "draft_id": draft["id"],
        "published_at": now,
        "tweet_ids": tweet_ids,
        "urls": urls,
        "saved": str(path),
    }


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: publish.py publish [--draft ID] [--confirm] [--text TEXT]\n"
            "  Requires --confirm. Posts drafts/latest.json (or --draft) via xurl.",
            file=sys.stderr,
        )
        return 2
    if argv[0] != "publish":
        print(f"unknown command: {argv[0]}", file=sys.stderr)
        return 2
    draft_id = "latest"
    confirm = False
    text = None
    i = 1
    while i < len(argv):
        if argv[i] == "--draft" and i + 1 < len(argv):
            draft_id = argv[i + 1]
            i += 2
        elif argv[i] == "--confirm":
            confirm = True
            i += 1
        elif argv[i] == "--text" and i + 1 < len(argv):
            text = argv[i + 1]
            i += 2
        else:
            print(f"unknown arg: {argv[i]}", file=sys.stderr)
            return 2
    try:
        result = publish_draft(draft_id=draft_id, confirm=confirm, text=text)
    except PublishError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
