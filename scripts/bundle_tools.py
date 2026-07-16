#!/usr/bin/env python3
"""Export / import X-LiveCast feed bundles (prompt.md + optional taste).

A bundle is a portable "what I listen to / how it should sound" pack — not a
session recording and not a SaaS subscription.
"""

from __future__ import annotations

import datetime
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompt.md"
TASTE_PATH = ROOT / "memory" / "TASTE.md"
BUNDLES_DIR = ROOT / "bundles"

BUNDLE_VERSION = 1


def _now_id() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_section(md: str, heading: str) -> str:
    """Return markdown under `## heading` until the next ## or end."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(md)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", md[start:], re.MULTILINE)
    end = start + nxt.start() if nxt else len(md)
    return md[start:end].strip()


def _bullets(section: str) -> list[str]:
    items = []
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("- "):
            items.append(s[2:].strip())
    return items


def prompt_to_bundle_fields(prompt_md: str) -> dict:
    focus = _extract_section(prompt_md, "Focus")
    sources = _extract_section(prompt_md, "Sources to pull")
    style = _extract_section(prompt_md, "Style")
    notes = _extract_section(prompt_md, "Notes")

    topics: list[str] = []
    accounts: list[str] = []
    ignore: list[str] = []
    mode = None
    for line in focus.splitlines():
        low = line.strip().lower()
        if low.startswith("topics"):
            mode = "topics"
            continue
        if low.startswith("accounts"):
            mode = "accounts"
            continue
        if low.startswith("ignore"):
            mode = "ignore"
            continue
        if line.strip().startswith("- "):
            item = line.strip()[2:].strip()
            if mode == "accounts":
                accounts.append(item)
            elif mode == "ignore":
                ignore.append(item)
            else:
                topics.append(item)

    return {
        "prompt_markdown": prompt_md.strip() + "\n",
        "focus": {
            "topics": topics,
            "accounts": accounts,
            "ignore": ignore,
        },
        "sources_markdown": sources,
        "style_markdown": style,
        "notes_markdown": notes,
        "style_bullets": _bullets(style),
    }


def export_bundle(*, name: str | None = None, include_taste: bool = True) -> Path:
    """Write bundles/<id>.json and bundles/latest.json. Returns path to id file."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"missing {PROMPT_PATH}")

    prompt_md = PROMPT_PATH.read_text(encoding="utf-8")
    fields = prompt_to_bundle_fields(prompt_md)
    taste = ""
    if include_taste and TASTE_PATH.exists():
        taste = TASTE_PATH.read_text(encoding="utf-8").strip()

    bundle_id = _now_id()
    out = {
        "version": BUNDLE_VERSION,
        "id": bundle_id,
        "exported_at": _now_iso(),
        "name": name or "My X-LiveCast feed",
        "description": "Portable feed preferences for X-LiveCast (prompt + optional taste).",
        **fields,
    }
    if taste:
        out["taste_markdown"] = taste + "\n"

    BUNDLES_DIR.mkdir(exist_ok=True)
    blob = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    path = BUNDLES_DIR / f"{bundle_id}.json"
    path.write_text(blob, encoding="utf-8")
    (BUNDLES_DIR / "latest.json").write_text(blob, encoding="utf-8")
    return path


def import_bundle_dict(bundle: dict, *, write_taste: bool = True) -> dict:
    """Replace prompt.md from a bundle object. Backs up previous prompt to .bak."""
    if not isinstance(bundle, dict):
        raise ValueError("bundle must be an object")
    md = (bundle.get("prompt_markdown") or "").strip()
    if not md:
        raise ValueError("bundle.prompt_markdown is required")

    backup = None
    if PROMPT_PATH.exists():
        backup = PROMPT_PATH.with_suffix(".md.bak")
        shutil.copy2(PROMPT_PATH, backup)

    PROMPT_PATH.write_text(md if md.endswith("\n") else md + "\n", encoding="utf-8")

    taste_written = False
    taste_backup = None
    taste_md = (bundle.get("taste_markdown") or "").strip()
    if write_taste and taste_md:
        TASTE_PATH.parent.mkdir(exist_ok=True)
        if TASTE_PATH.exists():
            taste_backup = TASTE_PATH.with_suffix(".md.bak")
            shutil.copy2(TASTE_PATH, taste_backup)
        TASTE_PATH.write_text(taste_md if taste_md.endswith("\n") else taste_md + "\n", encoding="utf-8")
        taste_written = True

    return {
        "ok": True,
        "prompt": str(PROMPT_PATH),
        "prompt_backup": str(backup) if backup else None,
        "taste_written": taste_written,
        "taste_backup": str(taste_backup) if taste_backup else None,
        "bundle_id": bundle.get("id"),
        "bundle_name": bundle.get("name"),
        "summary": {
            "topics": (bundle.get("focus") or {}).get("topics") or [],
            "accounts": (bundle.get("focus") or {}).get("accounts") or [],
        },
    }


def import_bundle_file(path: Path, *, write_taste: bool = True) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return import_bundle_dict(data, write_taste=write_taste)


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage:\n"
            "  bundle_tools.py export [--name NAME]\n"
            "  bundle_tools.py import <file.json>\n",
            file=sys.stderr,
        )
        return 2
    cmd = argv[0]
    if cmd == "export":
        name = None
        if len(argv) >= 3 and argv[1] == "--name":
            name = argv[2]
        path = export_bundle(name=name)
        print(json.dumps({"ok": True, "saved": str(path), "latest": str(BUNDLES_DIR / "latest.json")}, indent=2))
        return 0
    if cmd == "import":
        if len(argv) < 2:
            print("import requires a file path", file=sys.stderr)
            return 2
        result = import_bundle_file(Path(argv[1]))
        print(json.dumps(result, indent=2))
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
