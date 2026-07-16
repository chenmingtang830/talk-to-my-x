#!/usr/bin/env python3
"""Hermes-lite: evolve memory/USER.md + TASTE.md from a voice session.

Modes (XLC_MEMORY_EVOLVE):
  suggest (default) — write proposals under memory/proposals/; do not overwrite
  auto              — apply with .bak backup
  off               — no-op
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def evolve_mode() -> str:
    mode = _cfg("XLC_MEMORY_EVOLVE", "suggest").lower()
    if mode in ("suggest", "auto", "off", "0", "false", "no"):
        if mode in ("0", "false", "no"):
            return "off"
        return mode
    return "suggest"


def _gemini_json(prompt: str, model: str, api_key: str) -> dict:
    url = GEMINI_TEXT_URL.format(model=model) + f"?key={api_key}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.35, "responseMimeType": "application/json"},
    }).encode("utf-8")
    req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=90) as resp:
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
            raise RuntimeError(f"could not parse evolve JSON: {text_out[:400]}") from None
        return json.loads(m.group(0))


def _session_transcript(session: dict) -> str:
    lines = []
    for ev in session.get("events") or []:
        kind = ev.get("type") or "?"
        if kind == "tool_call":
            continue
        who = "You" if kind == "user" else ("Host" if kind == "host" else kind)
        text = (ev.get("text") or "").strip()
        if text:
            lines.append(f"{who}: {text}")
    return "\n".join(lines)[:14000]


def evolve_from_session(session: dict, *, mode: str | None = None) -> dict:
    """Propose or apply USER/TASTE updates from a finished session."""
    _load_dotenv()
    mode = (mode or evolve_mode()).lower()
    if mode == "off":
        return {"ok": True, "mode": "off", "applied": False, "skipped": True}

    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    transcript = _session_transcript(session)
    if len(transcript.strip()) < 80:
        return {
            "ok": True,
            "mode": mode,
            "applied": False,
            "skipped": True,
            "reason": "session too short to evolve memory",
        }

    user_md = memory_store.read_user()
    taste_md = memory_store.read_taste()
    model = _cfg("XLC_SYNTH_MODEL", "gemini-3.5-flash")

    prompt = (
        "You maintain lightweight listener memory for X-LiveCast (Hermes-lite).\n"
        "From ONE voice session, propose durable updates to USER.md and TASTE.md.\n\n"
        "Hard rules:\n"
        "1. Only durable prefs (topics, accounts, tone, depth, skips) — not one-off jokes.\n"
        "2. Keep each file SHORT (≤25 lines). Bullet lists. Preserve useful existing bullets.\n"
        "3. Do not invent biography. If unsure, leave that section unchanged.\n"
        "4. Output ONLY JSON:\n"
        "{\n"
        '  "changed": true|false,\n'
        '  "summary": "<1-2 sentences of what you learned>",\n'
        '  "user_md": "<full USER.md markdown>",\n'
        '  "taste_md": "<full TASTE.md markdown>",\n'
        '  "rationale": ["bullet", ...]\n'
        "}\n"
        "If nothing durable changed, set changed=false and echo the current files.\n\n"
        f"=== CURRENT USER.md ===\n{user_md or '(empty scaffold)'}\n\n"
        f"=== CURRENT TASTE.md ===\n{taste_md or '(empty scaffold)'}\n\n"
        f"=== SESSION TRANSCRIPT ===\n{transcript}\n"
    )

    draft = _gemini_json(prompt, model, api_key)
    changed = bool(draft.get("changed"))
    user_out = (draft.get("user_md") or user_md or "").strip()
    taste_out = (draft.get("taste_md") or taste_md or "").strip()
    if not user_out.startswith("#"):
        user_out = "# USER\n\n" + user_out
    if not taste_out.startswith("#"):
        taste_out = "# TASTE\n\n" + taste_out

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    proposal = {
        "generated_at": now,
        "from_session": session.get("id"),
        "mode": mode,
        "changed": changed,
        "summary": (draft.get("summary") or "").strip(),
        "rationale": draft.get("rationale") or [],
        "user_md": user_out,
        "taste_md": taste_out,
        "applied": False,
    }

    prop_dir = memory_store.proposals_dir()
    latest = prop_dir / "latest.json"
    stamp = prop_dir / f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    blob = json.dumps(proposal, indent=2, ensure_ascii=False) + "\n"
    latest.write_text(blob, encoding="utf-8")
    stamp.write_text(blob, encoding="utf-8")
    (prop_dir / "USER.proposed.md").write_text(user_out + "\n", encoding="utf-8")
    (prop_dir / "TASTE.proposed.md").write_text(taste_out + "\n", encoding="utf-8")

    if mode == "auto" and changed:
        apply_proposal(proposal)
        proposal["applied"] = True

    proposal["ok"] = True
    proposal["proposal_path"] = str(latest)
    return proposal


def apply_proposal(proposal: dict | None = None) -> dict:
    """Apply latest (or provided) proposal to USER.md / TASTE.md with .bak."""
    if proposal is None:
        path = memory_store.proposals_dir() / "latest.json"
        if not path.exists():
            raise RuntimeError("no memory proposal to apply")
        proposal = json.loads(path.read_text(encoding="utf-8"))
    user_md = (proposal.get("user_md") or "").strip()
    taste_md = (proposal.get("taste_md") or "").strip()
    if not user_md or not taste_md:
        raise RuntimeError("proposal missing user_md or taste_md")
    memory_store.write_markdown(memory_store.user_path(), user_md, backup=True)
    memory_store.write_markdown(memory_store.taste_path(), taste_md, backup=True)
    proposal["applied"] = True
    proposal["applied_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    latest = memory_store.proposals_dir() / "latest.json"
    latest.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "applied": True,
        "user_path": str(memory_store.user_path()),
        "taste_path": str(memory_store.taste_path()),
        "summary": proposal.get("summary"),
    }


def load_latest_proposal() -> dict | None:
    path = memory_store.proposals_dir() / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def main(argv: list[str]) -> int:
    _load_dotenv()
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: evolve_memory.py apply | evolve <session.json>\n"
            "  XLC_MEMORY_EVOLVE=suggest|auto|off",
            file=sys.stderr,
        )
        return 2
    cmd = argv[0]
    try:
        if cmd == "apply":
            print(json.dumps(apply_proposal(), indent=2))
            return 0
        if cmd == "evolve":
            if len(argv) < 2:
                print("need session json path", file=sys.stderr)
                return 2
            session = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
            print(json.dumps(evolve_from_session(session), indent=2, ensure_ascii=False))
            return 0
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
