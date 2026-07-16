#!/usr/bin/env python3
"""Generate briefs/latest.json from prompt.md + new bookmarks + home timeline.

Usable as CLI or imported by voice_room (POST /brief/generate).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import x_tools  # noqa: E402
import memory_store  # noqa: E402

GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


def _load_dotenv() -> None:
    path = ROOT / ".env"
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


def _cfg(name: str, default: str) -> str:
    return (os.environ.get(name) or "").strip() or default


def _data_root() -> Path:
    return memory_store.data_root()


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _gemini_json(prompt: str, model: str, api_key: str) -> dict:
    url = GEMINI_TEXT_URL.format(model=model) + f"?key={api_key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.55, "responseMimeType": "application/json"},
    }).encode("utf-8")
    req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=120) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    parts = (((raw.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text_out = "".join(p.get("text", "") for p in parts).strip()
    if not text_out:
        raise RuntimeError(f"empty Gemini response: {json.dumps(raw)[:400]}")
    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text_out)
        if not m:
            raise RuntimeError(f"could not parse brief JSON: {text_out[:400]}") from None
        return json.loads(m.group(0))


def _today_labels(now_utc: datetime.datetime) -> tuple[str, str]:
    try:
        today = now_utc.strftime("%A %B %-d")
    except ValueError:
        today = now_utc.strftime("%A %B %d").replace(" 0", " ")
    return today, now_utc.strftime("%Y-%m-%d")


def _briefs_dir() -> Path:
    briefs_dir = _data_root() / "briefs"
    try:
        briefs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        briefs_dir = ROOT / "briefs"
        briefs_dir.mkdir(parents=True, exist_ok=True)
    return briefs_dir


def _load_latest_brief() -> dict | None:
    latest = _briefs_dir() / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _pull_feed(*, bookmark_limit: int, timeline_limit: int) -> tuple[list[dict], list[dict]]:
    """Return (new_bookmarks, new_timeline_posts)."""
    bookmarks = x_tools.dispatch("get_bookmarks", {"limit": bookmark_limit})
    if bookmarks.get("error"):
        raise RuntimeError(bookmarks["error"])
    new_bookmarks = x_tools.filter_unseen("bookmarks", bookmarks.get("results") or [])
    for it in new_bookmarks:
        it["_feed"] = "bookmark"

    timeline = x_tools.dispatch("get_home_timeline", {"limit": timeline_limit})
    if timeline.get("error"):
        # Timeline is secondary — don't fail the whole brief if bookmarks work.
        new_timeline: list[dict] = []
        if not new_bookmarks:
            raise RuntimeError(timeline["error"])
    else:
        new_timeline = x_tools.filter_unseen("timeline", timeline.get("results") or [])
        for it in new_timeline:
            it["_feed"] = "timeline"
    return new_bookmarks, new_timeline


def generate_brief(
    *,
    bookmark_limit: int = 25,
    timeline_limit: int = 25,
    allow_empty: bool = False,
) -> dict:
    """Pull new bookmarks + home timeline, synthesize brief, write briefs/latest.json."""
    _load_dotenv()
    x_tools.apply_state_dir(_data_root())

    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not x_tools.xurl_bin():
        raise RuntimeError(
            "xurl not found. Install xurl and authenticate "
            "(see references/render.setup.md), or set XLC_XURL_BIN."
        )

    prompt_md = _read_optional(ROOT / "prompt.md")
    user_md = memory_store.read_user()
    taste_md = memory_store.read_taste()

    new_bookmarks, new_timeline = _pull_feed(
        bookmark_limit=bookmark_limit,
        timeline_limit=timeline_limit,
    )
    # Prefer bookmarks; keep timeline signal but cap total payload size.
    feed_items = list(new_bookmarks) + list(new_timeline)[:15]
    if not feed_items:
        if allow_empty:
            prev = _load_latest_brief() or {}
            prev["_skipped"] = True
            prev["_reason"] = "no_new_feed_items"
            prev["_new_bookmark_count"] = 0
            prev["_new_timeline_count"] = 0
            prev["_marked_seen"] = 0
            return prev
        raise RuntimeError(
            "No new bookmarks or home-timeline posts to brief "
            "(all recent items already marked seen). "
            "Bookmark something new, wait for feed activity, or clear .state/seen.json."
        )

    model = _cfg("XLC_SYNTH_MODEL", "gemini-3.5-flash")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today, today_iso = _today_labels(now_utc)

    synth_prompt = (
        "You write a spoken X-LiveCast brief script from the user's NEW X items.\n"
        "Follow the user's prompt.md for focus, length, and tone.\n"
        "Sources include bookmarked posts AND new home-timeline posts from accounts they follow.\n"
        "Prefer bookmarks when both cover the same story; use timeline for fresh signal.\n"
        "Weight topics toward prompt.md / USER.md / TASTE.md — skip low-signal noise.\n"
        "Speak display names (not @handles). ~150–220 words.\n"
        "Group into 2–4 themes. End by inviting interrupts and saying wrap up.\n"
        f"TODAY (UTC) is {today_iso} — spoken as {today}. "
        "Use ONLY this date in title and script. Do not invent another date.\n"
        "Output ONLY valid JSON:\n"
        "{\n"
        f'  "title": "Your X brief — {today}",\n'
        '  "script": "<spoken text>",\n'
        '  "items": [\n'
        "    {\n"
        '      "topic": "...",\n'
        '      "summary": "...",\n'
        '      "sources": [{"author","name","id","url","aliases"?,"feed"?}]\n'
        "    }\n"
        "  ],\n"
        '  "bookmark_ids": ["<id>", ...],\n'
        '  "timeline_ids": ["<id>", ...]\n'
        "}\n"
        "Every source must use the real id/url from the feed list. "
        "bookmark_ids / timeline_ids = ids you actually used from each feed.\n"
        "Set each source.feed to \"bookmark\" or \"timeline\".\n\n"
        f"=== prompt.md ===\n{prompt_md}\n\n"
        f"=== memory/USER.md ===\n{user_md or '(empty)'}\n\n"
        f"=== memory/TASTE.md ===\n{taste_md or '(empty)'}\n\n"
        f"=== NEW FEED ITEMS (JSON) ===\n{json.dumps(feed_items, ensure_ascii=False)[:28000]}\n"
    )

    draft = _gemini_json(synth_prompt, model, api_key)
    script = (draft.get("script") or "").strip()
    if not script:
        raise RuntimeError("model returned empty script")
    script = re.sub(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r",?\s+(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b",
        today,
        script,
        count=3,
    )

    used_bookmarks = [str(i) for i in (draft.get("bookmark_ids") or []) if i]
    used_timeline = [str(i) for i in (draft.get("timeline_ids") or []) if i]
    if not used_bookmarks and not used_timeline:
        for item in draft.get("items") or []:
            for src in (item or {}).get("sources") or []:
                sid = str(src.get("id") or "")
                if not sid:
                    continue
                feed = (src.get("feed") or "").lower()
                if feed == "timeline":
                    used_timeline.append(sid)
                else:
                    used_bookmarks.append(sid)
    if not used_bookmarks and not used_timeline:
        used_bookmarks = [str(it["id"]) for it in new_bookmarks if it.get("id")]
        used_timeline = [str(it["id"]) for it in new_timeline if it.get("id")]

    now = datetime.datetime.now(datetime.timezone.utc)
    out = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": f"Your X brief — {today}",
        "source": "bookmarks+timeline",
        "bookmark_ids": used_bookmarks,
        "timeline_ids": used_timeline,
        "script": script,
        "items": draft.get("items") or [],
    }

    briefs_dir = _briefs_dir()
    latest = briefs_dir / "latest.json"
    if latest.exists():
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(latest, briefs_dir / f"{stamp}.json")

    latest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if used_bookmarks:
        x_tools.mark_seen("bookmarks", used_bookmarks)
    if used_timeline:
        x_tools.mark_seen("timeline", used_timeline)

    out["_saved"] = str(latest)
    out["_new_bookmark_count"] = len(new_bookmarks)
    out["_new_timeline_count"] = len(new_timeline)
    out["_marked_seen"] = len(set(used_bookmarks) | set(used_timeline))
    out["_skipped"] = False
    return out


def main(argv: list[str]) -> int:
    limit = 25
    allow_empty = "--allow-empty" in argv
    args = [a for a in argv if a != "--allow-empty" and not a.startswith("-")]
    if args and args[0].isdigit():
        limit = int(args[0])
    try:
        result = generate_brief(
            bookmark_limit=limit,
            timeline_limit=limit,
            allow_empty=allow_empty,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({
        "ok": True,
        "skipped": bool(result.get("_skipped")),
        "saved": result.get("_saved"),
        "title": result.get("title"),
        "new_bookmarks": result.get("_new_bookmark_count"),
        "new_timeline": result.get("_new_timeline_count"),
        "marked_seen": result.get("_marked_seen"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
