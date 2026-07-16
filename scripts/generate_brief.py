#!/usr/bin/env python3
"""Generate briefs/latest.json from prompt.md + new X bookmarks (SKILL recipe).

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
    raw = (os.environ.get("XLC_DATA_DIR") or "").strip()
    return Path(raw) if raw else ROOT


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


def generate_brief(*, bookmark_limit: int = 25) -> dict:
    """Pull new bookmarks, synthesize brief, write briefs/latest.json. Returns the brief dict."""
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
    user_md = _read_optional(ROOT / "memory" / "USER.md")
    taste_md = _read_optional(ROOT / "memory" / "TASTE.md")

    bookmarks = x_tools.dispatch("get_bookmarks", {"limit": bookmark_limit})
    if bookmarks.get("error"):
        raise RuntimeError(bookmarks["error"])
    new_items = x_tools.filter_unseen("bookmarks", bookmarks.get("results") or [])
    if not new_items:
        raise RuntimeError(
            "No new bookmarks to brief (all recent bookmarks already marked seen). "
            "Bookmark something new on X, or clear .state/seen.json."
        )

    model = _cfg("XLC_SYNTH_MODEL", "gemini-3.5-flash")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Explicit calendar date — models invent wrong weekdays if left open-ended.
    try:
        today = now_utc.strftime("%A %B %-d")  # Linux
    except ValueError:
        today = now_utc.strftime("%A %B %d").replace(" 0", " ")  # macOS
    today_iso = now_utc.strftime("%Y-%m-%d")

    synth_prompt = (
        "You write a spoken X-LiveCast brief script from the user's NEW bookmarks.\n"
        "Follow the user's prompt.md for focus, length, and tone.\n"
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
        '      "sources": [{"author","name","id","url","aliases"?}]\n'
        "    }\n"
        "  ],\n"
        '  "bookmark_ids": ["<id>", ...]\n'
        "}\n"
        "Every source must use the real id/url from the bookmark list. "
        "bookmark_ids = every bookmark id you actually used.\n\n"
        f"=== prompt.md ===\n{prompt_md}\n\n"
        f"=== memory/USER.md ===\n{user_md or '(empty)'}\n\n"
        f"=== memory/TASTE.md ===\n{taste_md or '(empty)'}\n\n"
        f"=== NEW BOOKMARKS (JSON) ===\n{json.dumps(new_items, ensure_ascii=False)[:24000]}\n"
    )

    draft = _gemini_json(synth_prompt, model, api_key)
    script = (draft.get("script") or "").strip()
    if not script:
        raise RuntimeError("model returned empty script")
    # Models often invent a spoken calendar date — normalize weekday+month phrases.
    script = re.sub(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r",?\s+(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b",
        today,
        script,
        count=3,
    )

    used_ids = [str(i) for i in (draft.get("bookmark_ids") or []) if i]
    if not used_ids:
        # Fall back to all new bookmark ids referenced in items.
        for item in draft.get("items") or []:
            for src in (item or {}).get("sources") or []:
                if src.get("id"):
                    used_ids.append(str(src["id"]))
    if not used_ids:
        used_ids = [str(it["id"]) for it in new_items if it.get("id")]

    now = datetime.datetime.now(datetime.timezone.utc)
    # Never trust the model for the calendar date in the title.
    out = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": f"Your X brief — {today}",
        "source": "bookmarks-new",
        "bookmark_ids": used_ids,
        "script": script,
        "items": draft.get("items") or [],
    }

    briefs_dir = _data_root() / "briefs"
    try:
        briefs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        briefs_dir = ROOT / "briefs"
        briefs_dir.mkdir(parents=True, exist_ok=True)

    latest = briefs_dir / "latest.json"
    if latest.exists():
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(latest, briefs_dir / f"{stamp}.json")

    latest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    x_tools.mark_seen("bookmarks", used_ids)
    out["_saved"] = str(latest)
    out["_new_bookmark_count"] = len(new_items)
    out["_marked_seen"] = len(used_ids)
    return out


def main(argv: list[str]) -> int:
    limit = 25
    if len(argv) >= 1 and argv[0].isdigit():
        limit = int(argv[0])
    try:
        result = generate_brief(bookmark_limit=limit)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "saved": result.get("_saved"), "title": result.get("title"),
                      "new_bookmarks": result.get("_new_bookmark_count"),
                      "marked_seen": result.get("_marked_seen")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
