"""Deterministic local state for X Feed Loop.

This module does not call X or an LLM. The host agent composes with the
official X skill, then passes normalized data into these helpers.
"""

from __future__ import annotations

import datetime as dt
import importlib.resources
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
POST_SOURCES = {"timeline", "bookmarks", "search"}
POST_SIGNALS = {"selected", "skipped", "explored"}
CARD_STATUSES = {"open", "developing", "ready", "drafted", "archived"}


class FeedLoopError(ValueError):
    """User-facing validation or state error."""


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}"


def data_root() -> Path:
    raw = (os.environ.get("XFL_HOME") or "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".x-feed-loop"


def _safe_id(value: Any, field: str = "id") -> str:
    text = str(value or "").strip()
    if not SAFE_ID.fullmatch(text):
        raise FeedLoopError(f"{field} must match [A-Za-z0-9_-] and be at most 160 characters")
    return text


def _path(directory: Path, value: Any, field: str = "id") -> Path:
    ident = _safe_id(value, field)
    directory = directory.resolve()
    target = (directory / f"{ident}.json").resolve()
    if directory not in target.parents:
        raise FeedLoopError(f"invalid {field}")
    return target


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temp_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def _write_json(path: Path, payload: Any) -> None:
    _atomic_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeedLoopError(f"could not read {path}: {exc}") from exc


def _template(name: str) -> str:
    return importlib.resources.files("x_feed_loop").joinpath("templates", name).read_text(encoding="utf-8")


def ensure_layout(root: Path | None = None) -> Path:
    root = (root or data_root()).expanduser()
    for rel in (
        "memory",
        "posts",
        "reactions",
        "drafts",
        "history/memory",
        "state",
        "exports",
        "migration",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    seeds = {
        root / "preferences.md": "preferences.md",
        root / "memory" / "USER.md": "USER.md",
        root / "memory" / "TASTE.md": "TASTE.md",
        root / "memory" / "VOICE.md": "VOICE.md",
    }
    for path, template in seeds.items():
        if not path.exists():
            _atomic_text(path, _template(template))
    return root


def _markdown(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _all_json(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in directory.glob("*.json"):
        data = _read_json(path)
        if isinstance(data, dict):
            rows.append(data)
    rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
    return rows


def _legacy_seen(root: Path) -> set[str]:
    data = _read_json(root / "state" / "seen.json", {}) or {}
    if not isinstance(data, dict):
        return set()
    return {str(item) for values in data.values() if isinstance(values, list) for item in values}


def normalize_post(raw: dict[str, Any], source: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise FeedLoopError("each post must be a JSON object")
    if source not in POST_SOURCES:
        raise FeedLoopError(f"source must be one of: {', '.join(sorted(POST_SOURCES))}")
    declared_source = str(raw.get("source") or "").strip()
    if not declared_source:
        raise FeedLoopError("each normalized post must include source")
    if declared_source != source:
        raise FeedLoopError(f"post source {declared_source!r} does not match --source {source!r}")
    ident = _safe_id(raw.get("id"), "post id")
    text = str(raw.get("text") or "").strip()
    author = str(raw.get("author") or "").strip().lstrip("@")
    url = str(raw.get("url") or "").strip()
    if not text:
        raise FeedLoopError(f"post {ident} is missing text")
    if not author:
        raise FeedLoopError(f"post {ident} is missing author")
    if not url.startswith("https://"):
        raise FeedLoopError(f"post {ident} url must use https://")
    return {
        "id": ident,
        "text": text,
        "author": author,
        "name": str(raw.get("name") or author).strip(),
        "url": url,
        "source": source,
        "created_at": str(raw.get("created_at") or "").strip() or None,
        "metrics": raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {},
    }


def ingest_posts(payload: Any, source: str, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    raw_posts = payload.get("posts") if isinstance(payload, dict) else payload
    if not isinstance(raw_posts, list):
        raise FeedLoopError("stdin must be a JSON array or an object with posts[]")
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    ids: list[str] = []
    legacy_seen = _legacy_seen(root)
    for raw in raw_posts:
        post = normalize_post(raw, source)
        path = _path(root / "posts", post["id"], "post id")
        existing = _read_json(path)
        timestamp = now_iso()
        if existing:
            merged = dict(existing)
            changed = any(merged.get(key) != value for key, value in post.items())
            merged.update(post)
            merged["updated_at"] = timestamp
            merged.setdefault("signals", [])
            merged.setdefault("status", "new")
            counts["updated" if changed else "unchanged"] += 1
        else:
            merged = {
                **post,
                "status": "seen" if post["id"] in legacy_seen else "new",
                "signals": [],
                "ingested_at": timestamp,
                "updated_at": timestamp,
            }
            counts["created"] += 1
        _write_json(path, merged)
        ids.append(post["id"])
    return {"ok": True, "source": source, **counts, "ids": ids, "home": str(root)}


def build_context(root: Path | None = None, limit: int = 50) -> dict[str, Any]:
    root = ensure_layout(root)
    posts = [row for row in _all_json(root / "posts") if row.get("status") in {"new", "selected"}]
    cards = [row for row in _all_json(root / "reactions") if row.get("status") != "archived"]
    return {
        "version": 1,
        "generated_at": now_iso(),
        "home": str(root),
        "preferences": _markdown(root, "preferences.md"),
        "memory": {
            "user": _markdown(root, "memory/USER.md"),
            "taste": _markdown(root, "memory/TASTE.md"),
            "voice": _markdown(root, "memory/VOICE.md"),
        },
        "posts": posts[: max(1, min(int(limit), 200))],
        "reaction_cards": cards[: max(1, min(int(limit), 200))],
    }


def signal_post(post_id: str, kind: str, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if kind not in POST_SIGNALS:
        raise FeedLoopError(f"kind must be one of: {', '.join(sorted(POST_SIGNALS))}")
    path = _path(root / "posts", post_id, "post id")
    post = _read_json(path)
    if not post:
        raise FeedLoopError(f"post not found: {post_id}")
    event = {"kind": kind, "at": now_iso()}
    post.setdefault("signals", []).append(event)
    post["status"] = kind
    post["updated_at"] = event["at"]
    _write_json(path, post)
    return {"ok": True, "post_id": post_id, "status": kind}


def _source_from_value(value: Any, root: Path) -> dict[str, Any]:
    if isinstance(value, str):
        ident = _safe_id(value, "source id")
        stored = _read_json(_path(root / "posts", ident, "source id"))
        if not stored:
            raise FeedLoopError(f"source post not found: {ident}")
        return {key: stored.get(key) for key in ("id", "author", "name", "url", "text") if stored.get(key)}
    if not isinstance(value, dict):
        raise FeedLoopError("each source must be a post id or object")
    ident = _safe_id(value.get("id"), "source id")
    stored = _read_json(_path(root / "posts", ident, "source id"), {}) or {}
    merged = {**stored, **value, "id": ident}
    if not str(merged.get("url") or "").startswith("https://"):
        raise FeedLoopError(f"source {ident} is missing an https URL")
    return {key: merged.get(key) for key in ("id", "author", "name", "url", "text") if merged.get(key)}


def capture_reaction(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise FeedLoopError("stdin must be a reaction object")
    raw_reaction = str(payload.get("raw_reaction") or "").strip()
    if not raw_reaction:
        raise FeedLoopError("raw_reaction is required")
    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise FeedLoopError("sources must be a non-empty array")
    sources = [_source_from_value(value, root) for value in sources_raw]
    card_id = _safe_id(payload.get("id") or new_id("reaction"), "reaction id")
    status = str(payload.get("status") or "open")
    if status not in CARD_STATUSES:
        raise FeedLoopError(f"status must be one of: {', '.join(sorted(CARD_STATUSES))}")
    path = _path(root / "reactions", card_id, "reaction id")
    card = _read_json(path, {}) or {}
    timestamp = now_iso()
    card.setdefault("id", card_id)
    card.setdefault("created_at", timestamp)
    card.setdefault("reactions", [])
    card.setdefault("draft_ids", [])
    existing_sources = {str(item.get("id")): item for item in card.get("sources", []) if isinstance(item, dict)}
    existing_sources.update({str(item["id"]): item for item in sources})
    card["sources"] = list(existing_sources.values())
    card["reactions"].append({"text": raw_reaction, "at": timestamp})
    card["raw_reaction"] = raw_reaction
    for field in ("summary", "stance"):
        if payload.get(field) is not None:
            card[field] = str(payload.get(field) or "").strip()
    for field in ("questions", "connections"):
        incoming = payload.get(field) or []
        if not isinstance(incoming, list):
            raise FeedLoopError(f"{field} must be an array")
        card[field] = list(dict.fromkeys([*card.get(field, []), *[str(item).strip() for item in incoming if str(item).strip()]]))
    card["status"] = status
    card["updated_at"] = timestamp
    _write_json(path, card)
    for source in sources:
        post_path = _path(root / "posts", source["id"], "post id")
        post = _read_json(post_path)
        if post:
            post["status"] = "explored"
            post["updated_at"] = timestamp
            post.setdefault("signals", []).append({"kind": "explored", "at": timestamp})
            _write_json(post_path, post)
    return {"ok": True, "id": card_id, "status": status, "path": str(path)}


def _normalize_draft(payload: dict[str, Any]) -> tuple[str | None, list[str] | None]:
    text = payload.get("text")
    thread = payload.get("thread")
    if bool(text) == bool(thread):
        raise FeedLoopError("draft must contain exactly one of text or thread")
    if text is not None:
        text = str(text).strip()
        if not text:
            raise FeedLoopError("draft text cannot be empty")
        if len(text) > 280:
            raise FeedLoopError(f"draft text is {len(text)} characters (max 280)")
        return text, None
    if not isinstance(thread, list) or not thread:
        raise FeedLoopError("thread must be a non-empty array")
    clean = [str(item).strip() for item in thread if str(item).strip()]
    if not clean:
        raise FeedLoopError("thread cannot be empty")
    for index, item in enumerate(clean, 1):
        if len(item) > 280:
            raise FeedLoopError(f"thread post {index} is {len(item)} characters (max 280)")
    return None, clean


def save_draft(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise FeedLoopError("stdin must be a draft object")
    text, thread = _normalize_draft(payload)
    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise FeedLoopError("sources must be a non-empty array")
    sources = [_source_from_value(value, root) for value in sources_raw]
    card_ids = [_safe_id(value, "reaction card id") for value in payload.get("card_ids") or []]
    for card_id in card_ids:
        if not _path(root / "reactions", card_id, "reaction card id").exists():
            raise FeedLoopError(f"reaction card not found: {card_id}")
    draft_id = _safe_id(payload.get("id") or new_id("draft"), "draft id")
    path = _path(root / "drafts", draft_id, "draft id")
    current = _read_json(path, {}) or {}
    if current.get("published_at"):
        raise FeedLoopError(f"draft already published: {draft_id}")
    timestamp = now_iso()
    revision = {
        "number": len(current.get("revisions", [])) + 1,
        "saved_at": timestamp,
        "text": text,
        "thread": thread,
        "sources": sources,
        "card_ids": card_ids,
    }
    draft = {
        "id": draft_id,
        "created_at": current.get("created_at") or timestamp,
        "updated_at": timestamp,
        "text": text,
        "thread": thread,
        "sources": sources,
        "card_ids": card_ids,
        "revisions": [*current.get("revisions", []), revision],
    }
    _write_json(path, draft)
    for card_id in card_ids:
        card_path = _path(root / "reactions", card_id, "reaction card id")
        card = _read_json(card_path)
        card["draft_ids"] = list(dict.fromkeys([*card.get("draft_ids", []), draft_id]))
        card["status"] = "drafted"
        card["updated_at"] = timestamp
        _write_json(card_path, card)
    return {"ok": True, "id": draft_id, "revision": revision["number"], "path": str(path)}


def mark_published(draft_id: str, payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise FeedLoopError("stdin must be a publish result object")
    path = _path(root / "drafts", draft_id, "draft id")
    draft = _read_json(path)
    if not draft:
        raise FeedLoopError(f"draft not found: {draft_id}")
    if draft.get("published_at"):
        raise FeedLoopError(f"draft already published: {draft_id}")
    tweet_ids = [str(value).strip() for value in payload.get("tweet_ids") or [] if str(value).strip()]
    urls = [str(value).strip() for value in payload.get("urls") or [] if str(value).strip()]
    if not tweet_ids or len(tweet_ids) != len(urls):
        raise FeedLoopError("tweet_ids and urls must be non-empty arrays of equal length")
    if any(not url.startswith("https://") for url in urls):
        raise FeedLoopError("published urls must use https://")
    final_payload = {key: payload[key] for key in ("text", "thread") if payload.get(key) is not None}
    if final_payload:
        text, thread = _normalize_draft(final_payload)
        draft["text"], draft["thread"] = text, thread
    draft["published_at"] = str(payload.get("published_at") or now_iso())
    draft["tweet_ids"] = tweet_ids
    draft["urls"] = urls
    draft["updated_at"] = now_iso()
    _write_json(path, draft)
    return {"ok": True, "id": draft_id, "published_at": draft["published_at"], "urls": urls}


def apply_memory(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise FeedLoopError("stdin must be a memory update object")
    taste = str(payload.get("taste_md") or "").strip()
    voice = str(payload.get("voice_md") or "").strip()
    evidence = [_safe_id(value, "evidence card id") for value in payload.get("evidence_card_ids") or []]
    rationale = [str(value).strip() for value in payload.get("rationale") or [] if str(value).strip()]
    if not taste.startswith("#") or not voice.startswith("#"):
        raise FeedLoopError("taste_md and voice_md must be complete Markdown documents starting with #")
    if not evidence or not rationale:
        raise FeedLoopError("evidence_card_ids and rationale are required")
    for card_id in evidence:
        if not _path(root / "reactions", card_id, "evidence card id").exists():
            raise FeedLoopError(f"evidence card not found: {card_id}")
    taste_path = root / "memory" / "TASTE.md"
    voice_path = root / "memory" / "VOICE.md"
    snapshot_id = new_id("memory")
    snapshot = {
        "id": snapshot_id,
        "applied_at": now_iso(),
        "evidence_card_ids": evidence,
        "rationale": rationale,
        "before": {
            "taste_md": taste_path.read_text(encoding="utf-8"),
            "voice_md": voice_path.read_text(encoding="utf-8"),
        },
        "after": {"taste_md": taste + "\n", "voice_md": voice + "\n"},
    }
    _write_json(_path(root / "history" / "memory", snapshot_id, "snapshot id"), snapshot)
    _atomic_text(taste_path, taste + "\n")
    _atomic_text(voice_path, voice + "\n")
    return {"ok": True, "snapshot_id": snapshot_id, "evidence_card_ids": evidence}


def rollback_memory(snapshot_id: str, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    path = _path(root / "history" / "memory", snapshot_id, "snapshot id")
    snapshot = _read_json(path)
    if not snapshot:
        raise FeedLoopError(f"memory snapshot not found: {snapshot_id}")
    before = snapshot.get("before") or {}
    if not before.get("taste_md") or not before.get("voice_md"):
        raise FeedLoopError("memory snapshot is incomplete")
    _atomic_text(root / "memory" / "TASTE.md", str(before["taste_md"]))
    _atomic_text(root / "memory" / "VOICE.md", str(before["voice_md"]))
    rollback = {"snapshot_id": snapshot_id, "rolled_back_at": now_iso()}
    _write_json(root / "history" / "memory" / f"rollback_{snapshot_id}.json", rollback)
    return {"ok": True, **rollback}


def export_preferences(root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    return {
        "version": 1,
        "exported_at": now_iso(),
        "preferences_md": _markdown(root, "preferences.md") + "\n",
        "user_md": _markdown(root, "memory/USER.md") + "\n",
        "taste_md": _markdown(root, "memory/TASTE.md") + "\n",
        "voice_md": _markdown(root, "memory/VOICE.md") + "\n",
    }


def import_preferences(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict) or int(payload.get("version") or 0) != 1:
        raise FeedLoopError("preference bundle version 1 is required")
    mapping = {
        "preferences_md": root / "preferences.md",
        "user_md": root / "memory" / "USER.md",
        "taste_md": root / "memory" / "TASTE.md",
        "voice_md": root / "memory" / "VOICE.md",
    }
    changed: list[str] = []
    backup_dir = root / "history" / "memory" / new_id("preferences_import")
    for key, path in mapping.items():
        value = str(payload.get(key) or "").strip()
        if not value:
            continue
        backup_dir.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)
        _atomic_text(path, value + "\n")
        changed.append(key)
    if not changed:
        raise FeedLoopError("bundle contains no preference or memory documents")
    return {"ok": True, "changed": changed, "backup": str(backup_dir)}


def migrate_legacy(source: Path, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    source = source.expanduser().resolve()
    if not source.exists():
        raise FeedLoopError(f"legacy path not found: {source}")
    report: dict[str, Any] = {"ok": True, "from": str(source), "to": str(root), "migrated": [], "skipped": {}}
    prompt = source / "prompt.md"
    if prompt.exists():
        text = prompt.read_text(encoding="utf-8").replace("X-LiveCast", "X Feed Loop").replace("x-livecast", "x-feed-loop")
        _atomic_text(root / "preferences.md", text)
        report["migrated"].append("preferences.md")
    for name in ("USER.md", "TASTE.md"):
        old = source / "memory" / name
        if old.exists():
            shutil.copy2(old, root / "memory" / name)
            report["migrated"].append(f"memory/{name}")
    old_seen = source / ".state" / "seen.json"
    if old_seen.exists():
        seen = _read_json(old_seen)
        _write_json(root / "state" / "seen.json", seen)
        report["migrated"].append("state/seen.json")
    old_drafts = source / "drafts"
    draft_count = 0
    if old_drafts.exists():
        for old in old_drafts.glob("*.json"):
            target = root / "drafts" / old.name
            if not target.exists():
                shutil.copy2(old, target)
                draft_count += 1
    if draft_count:
        report["migrated"].append(f"drafts:{draft_count}")
    report["skipped"] = {
        "sessions": len(list((source / "sessions").glob("*.json"))) if (source / "sessions").exists() else 0,
        "briefs": len(list((source / "briefs").glob("*.json"))) if (source / "briefs").exists() else 0,
        "reason": "legacy conversations and briefs require semantic conversion and were left untouched",
    }
    _write_json(root / "migration" / f"{new_id('x_livecast')}.json", report)
    return report
