"""Deterministic, local-only state for Talk to My X."""

from __future__ import annotations

import datetime as dt
import importlib.resources
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
POST_SOURCES = {"timeline", "bookmarks", "search", "news", "priority_accounts", "user_posts"}
POST_SIGNALS = {"selected", "skipped", "explored"}
CARD_STATUSES = {"open", "developing", "ready", "drafted", "archived"}
ACTION_TYPES = {"post", "reply", "follow", "like", "bookmark"}
ACTION_RESULTS = {"cancelled", "succeeded", "failed", "partial"}
EVIDENCE_TYPES = {"reaction", "draft_revision", "signal", "action"}
CONFIRMATION_PHRASES = {
    "post": "确认发布",
    "reply": "确认回复",
    "follow": "确认关注",
    "like": "确认点赞",
    "bookmark": "确认收藏",
}
MAX_POSTS_PER_INGEST = 200
MAX_REACTION_LENGTH = 50_000
MAX_DOCUMENT_LENGTH = 200_000
MAX_COLLECTION_ITEMS = 100
MAX_SHORT_TEXT = 10_000


class TalkToMyXError(ValueError):
    """User-facing validation or state error."""


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def now_iso() -> str:
    return now().isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TalkToMyXError(f"invalid timestamp: {value}") from exc


def new_id(prefix: str) -> str:
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}"


DATA_ROOT_VARIABLES = ("TTMX_HOME", "PLUGIN_DATA")


def data_root_source() -> str:
    """Name the variable that decided the data root, or "default"."""

    for name in DATA_ROOT_VARIABLES:
        value = (os.environ.get(name) or "").strip()
        if value and "${" not in value:
            return name
    return "default"


def data_root() -> Path:
    for name in DATA_ROOT_VARIABLES:
        value = (os.environ.get(name) or "").strip()
        if value and "${" not in value:
            return Path(value).expanduser()
    return Path.home() / ".codex" / "plugin-data" / "talk-to-my-x"


def _safe_id(value: Any, field: str = "id") -> str:
    text = str(value or "").strip()
    if not SAFE_ID.fullmatch(text):
        raise TalkToMyXError(f"{field} must match [A-Za-z0-9_-] and be at most 160 characters")
    return text


def _path(directory: Path, value: Any, field: str = "id") -> Path:
    ident = _safe_id(value, field)
    directory = directory.resolve()
    target = (directory / f"{ident}.json").resolve()
    if directory not in target.parents:
        raise TalkToMyXError(f"invalid {field}")
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
        raise TalkToMyXError(f"could not read {path}: {exc}") from exc


@contextmanager
def _state_lock(root: Path) -> Iterator[None]:
    lock_path = root / ".state.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:
            pass
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ImportError:
            pass
        handle.close()


def _template(name: str) -> str:
    return importlib.resources.files("talk_to_my_x").joinpath("templates", name).read_text(encoding="utf-8")


def ensure_layout(root: Path | None = None) -> Path:
    use_default = root is None
    root = (root or data_root()).expanduser()
    for rel in (
        "memory",
        "posts",
        "reactions",
        "drafts",
        "actions",
        "history/memory",
        "history/preferences",
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
    if use_default:
        marker = root / "migration" / "auto-x-feed-loop.json"
        legacy = Path.home() / ".x-feed-loop"
        if legacy.exists() and legacy.resolve() != root.resolve() and not marker.exists():
            report = migrate_legacy(legacy, root)
            _write_json(marker, report)
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


def normalize_post(raw: dict[str, Any], source: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TalkToMyXError("each post must be a JSON object")
    if source not in POST_SOURCES:
        raise TalkToMyXError(f"source must be one of: {', '.join(sorted(POST_SOURCES))}")
    declared = str(raw.get("source") or source).strip()
    if declared != source:
        raise TalkToMyXError(f"post source {declared!r} does not match source {source!r}")
    ident = _safe_id(raw.get("id"), "post id")
    text = str(raw.get("text") or raw.get("title") or "").strip()
    author = str(raw.get("author") or raw.get("username") or "X News").strip().lstrip("@")
    url = str(raw.get("url") or "").strip()
    if not text:
        raise TalkToMyXError(f"post {ident} is missing text")
    if len(text) > 100_000:
        raise TalkToMyXError(f"post {ident} text is too long")
    if len(author) > 100 or len(url) > 2_048:
        raise TalkToMyXError(f"post {ident} author or url is too long")
    if not url.startswith("https://"):
        raise TalkToMyXError(f"post {ident} url must use https://")
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
        raise TalkToMyXError("posts must be an array")
    if len(raw_posts) > MAX_POSTS_PER_INGEST:
        raise TalkToMyXError(f"at most {MAX_POSTS_PER_INGEST} posts may be ingested at once")
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    ids: list[str] = []
    with _state_lock(root):
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
                    "status": "new",
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
    bounded = max(1, min(int(limit), 200))
    posts = [row for row in _all_json(root / "posts") if row.get("status") in {"new", "selected"}]
    cards = [row for row in _all_json(root / "reactions") if row.get("status") != "archived"]
    drafts = [row for row in _all_json(root / "drafts") if not row.get("published_at")]
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
        "posts": posts[:bounded],
        "reaction_cards": cards[:bounded],
        "drafts": drafts[:bounded],
        "recent_actions": _all_json(root / "actions")[:bounded],
    }


def signal_post(post_id: str, kind: str, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if kind not in POST_SIGNALS:
        raise TalkToMyXError(f"kind must be one of: {', '.join(sorted(POST_SIGNALS))}")
    with _state_lock(root):
        path = _path(root / "posts", post_id, "post id")
        post = _read_json(path)
        if not post:
            raise TalkToMyXError(f"post not found: {post_id}")
        event = {"id": new_id("signal"), "kind": kind, "at": now_iso()}
        post.setdefault("signals", []).append(event)
        post["status"] = kind
        post["updated_at"] = event["at"]
        _write_json(path, post)
    return {"ok": True, "post_id": post_id, "status": kind, "signal_id": event["id"]}


def _source(value: Any, root: Path) -> dict[str, Any]:
    if isinstance(value, str):
        ident = _safe_id(value, "source id")
        stored = _read_json(_path(root / "posts", ident, "source id"))
        if not stored:
            raise TalkToMyXError(f"source post not found: {ident}")
        return {key: stored.get(key) for key in ("id", "author", "name", "url", "text") if stored.get(key)}
    if not isinstance(value, dict):
        raise TalkToMyXError("each source must be a post id or object")
    ident = _safe_id(value.get("id"), "source id")
    stored = _read_json(_path(root / "posts", ident, "source id"), {}) or {}
    merged = {**stored, **value, "id": ident}
    url = str(merged.get("url") or "").strip()
    text = str(merged.get("text") or "")
    author = str(merged.get("author") or "")
    name = str(merged.get("name") or "")
    if not url.startswith("https://"):
        raise TalkToMyXError(f"source {ident} is missing an https URL")
    if len(url) > 2_048 or len(text) > 100_000 or len(author) > 100 or len(name) > 100:
        raise TalkToMyXError(f"source {ident} is too long")
    merged.update({"url": url, "text": text, "author": author, "name": name})
    return {key: merged.get(key) for key in ("id", "author", "name", "url", "text") if merged.get(key)}


def capture_reaction(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise TalkToMyXError("reaction must be an object")
    raw = str(payload.get("raw_reaction") or "").strip()
    sources_raw = payload.get("sources")
    if not raw:
        raise TalkToMyXError("raw_reaction is required")
    if len(raw) > MAX_REACTION_LENGTH:
        raise TalkToMyXError(f"raw_reaction exceeds {MAX_REACTION_LENGTH} characters")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise TalkToMyXError("sources must be a non-empty array")
    if len(sources_raw) > MAX_COLLECTION_ITEMS:
        raise TalkToMyXError(f"sources may contain at most {MAX_COLLECTION_ITEMS} items")
    sources = [_source(value, root) for value in sources_raw]
    card_id = _safe_id(payload.get("id") or new_id("reaction"), "reaction id")
    status = str(payload.get("status") or "open")
    if status not in CARD_STATUSES:
        raise TalkToMyXError(f"status must be one of: {', '.join(sorted(CARD_STATUSES))}")
    with _state_lock(root):
        path = _path(root / "reactions", card_id, "reaction id")
        card = _read_json(path, {}) or {}
        timestamp = now_iso()
        card.setdefault("id", card_id)
        card.setdefault("created_at", timestamp)
        card.setdefault("reactions", [])
        card.setdefault("draft_ids", [])
        by_id = {str(item.get("id")): item for item in card.get("sources", []) if isinstance(item, dict)}
        by_id.update({str(item["id"]): item for item in sources})
        card["sources"] = list(by_id.values())
        card["reactions"].append({"text": raw, "at": timestamp})
        card["raw_reaction"] = raw
        for field in ("summary", "stance"):
            if payload.get(field) is not None:
                value = str(payload.get(field) or "").strip()
                if len(value) > MAX_SHORT_TEXT:
                    raise TalkToMyXError(f"{field} is too long")
                card[field] = value
        for field in ("questions", "connections"):
            incoming = payload.get(field) or []
            if not isinstance(incoming, list):
                raise TalkToMyXError(f"{field} must be an array")
            if len(incoming) > MAX_COLLECTION_ITEMS:
                raise TalkToMyXError(f"{field} may contain at most {MAX_COLLECTION_ITEMS} items")
            clean = [str(item).strip() for item in incoming if str(item).strip()]
            if any(len(item) > MAX_SHORT_TEXT for item in clean):
                raise TalkToMyXError(f"{field} items are too long")
            card[field] = list(dict.fromkeys([*card.get(field, []), *clean]))
        card["status"] = status
        card["updated_at"] = timestamp
        _write_json(path, card)
        for source in sources:
            post_path = _path(root / "posts", source["id"], "post id")
            post = _read_json(post_path)
            if post:
                event = {"id": new_id("signal"), "kind": "explored", "at": timestamp}
                post["status"] = "explored"
                post["updated_at"] = timestamp
                post.setdefault("signals", []).append(event)
                _write_json(post_path, post)
    return {"ok": True, "id": card_id, "status": status, "path": str(path)}


def _normalize_draft(payload: dict[str, Any]) -> tuple[str | None, list[str] | None]:
    text, thread = payload.get("text"), payload.get("thread")
    if bool(text) == bool(thread):
        raise TalkToMyXError("draft must contain exactly one of text or thread")
    if text is not None:
        clean = str(text).strip()
        if not clean or len(clean) > 280:
            raise TalkToMyXError("draft text must be 1-280 characters")
        return clean, None
    if not isinstance(thread, list) or not thread:
        raise TalkToMyXError("thread must be a non-empty array")
    if len(thread) > 25:
        raise TalkToMyXError("thread may contain at most 25 posts")
    clean_thread = [str(item).strip() for item in thread if str(item).strip()]
    if not clean_thread or any(len(item) > 280 for item in clean_thread):
        raise TalkToMyXError("each thread post must be 1-280 characters")
    return None, clean_thread


def save_draft(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise TalkToMyXError("draft must be an object")
    text, thread = _normalize_draft(payload)
    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise TalkToMyXError("sources must be a non-empty array")
    if len(sources_raw) > MAX_COLLECTION_ITEMS:
        raise TalkToMyXError(f"sources may contain at most {MAX_COLLECTION_ITEMS} items")
    sources = [_source(value, root) for value in sources_raw]
    card_ids_raw = payload.get("card_ids") or []
    if not isinstance(card_ids_raw, list) or len(card_ids_raw) > MAX_COLLECTION_ITEMS:
        raise TalkToMyXError(f"card_ids must be an array of at most {MAX_COLLECTION_ITEMS} items")
    card_ids = [_safe_id(value, "reaction card id") for value in card_ids_raw]
    edit_summary = str(payload.get("edit_summary") or "").strip()
    if len(edit_summary) > MAX_SHORT_TEXT:
        raise TalkToMyXError("edit_summary is too long")
    draft_id = _safe_id(payload.get("id") or new_id("draft"), "draft id")
    with _state_lock(root):
        for card_id in card_ids:
            if not _path(root / "reactions", card_id, "reaction card id").exists():
                raise TalkToMyXError(f"reaction card not found: {card_id}")
        path = _path(root / "drafts", draft_id, "draft id")
        current = _read_json(path, {}) or {}
        if current.get("published_at"):
            raise TalkToMyXError(f"draft already published: {draft_id}")
        timestamp = now_iso()
        revision = {
            "number": len(current.get("revisions", [])) + 1,
            "saved_at": timestamp,
            "text": text,
            "thread": thread,
            "sources": sources,
            "card_ids": card_ids,
            "edit_summary": edit_summary or None,
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


def _clean_target(action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    target = payload.get("target") or {}
    if not isinstance(target, dict):
        raise TalkToMyXError("target must be an object")
    if action_type in {"reply", "like", "bookmark"}:
        post_id = _safe_id(target.get("post_id"), "target post id")
        url = str(target.get("url") or "").strip()
        if url and not url.startswith("https://"):
            raise TalkToMyXError("target url must use https://")
        author = str(target.get("author") or "").strip().lstrip("@")
        excerpt = str(target.get("excerpt") or "").strip()
        if len(url) > 2_048 or len(author) > 100 or len(excerpt) > MAX_SHORT_TEXT:
            raise TalkToMyXError("target details are too long")
        return {
            "post_id": post_id,
            "url": url or None,
            "author": author or None,
            "excerpt": excerpt[:500] or None,
        }
    if action_type == "follow":
        username = str(target.get("username") or "").strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", username):
            raise TalkToMyXError("target username is invalid")
        name = str(target.get("name") or "").strip()
        if len(name) > 100:
            raise TalkToMyXError("target name is too long")
        return {"username": username, "name": name or None}
    return {}


def prepare_action(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise TalkToMyXError("action must be an object")
    action_type = str(payload.get("type") or "").strip()
    if action_type not in ACTION_TYPES:
        raise TalkToMyXError(f"type must be one of: {', '.join(sorted(ACTION_TYPES))}")
    target = _clean_target(action_type, payload)
    text = thread = None
    if action_type in {"post", "reply"}:
        if action_type == "reply":
            text = str(payload.get("text") or "").strip()
            if not text or len(text) > 280:
                raise TalkToMyXError("reply text must be 1-280 characters")
        else:
            text, thread = _normalize_draft(payload)
    action_id = _safe_id(payload.get("id") or new_id("action"), "action id")
    timestamp = now()
    source_ids_raw = payload.get("source_ids") or []
    if not isinstance(source_ids_raw, list) or len(source_ids_raw) > MAX_COLLECTION_ITEMS:
        raise TalkToMyXError(f"source_ids must be an array of at most {MAX_COLLECTION_ITEMS} items")
    action = {
        "id": action_id,
        "type": action_type,
        "status": "prepared",
        "target": target,
        "text": text,
        "thread": thread,
        "source_ids": [_safe_id(item, "source id") for item in source_ids_raw],
        "confirmation_phrase": CONFIRMATION_PHRASES[action_type],
        "created_at": timestamp.isoformat().replace("+00:00", "Z"),
        "expires_at": (timestamp + dt.timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
        "updated_at": timestamp.isoformat().replace("+00:00", "Z"),
    }
    with _state_lock(root):
        path = _path(root / "actions", action_id, "action id")
        if path.exists():
            raise TalkToMyXError(f"action already exists: {action_id}")
        _write_json(path, action)
    return {"ok": True, **action, "path": str(path)}


def _contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if any(token in str(key).lower() for token in ("token", "secret", "authorization", "credential")):
                return True
            if _contains_secret(item):
                return True
    if isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    return False


def complete_action(action_id: str, payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise TalkToMyXError("action result must be an object")
    status = str(payload.get("status") or "").strip()
    if status not in ACTION_RESULTS:
        raise TalkToMyXError(f"status must be one of: {', '.join(sorted(ACTION_RESULTS))}")
    with _state_lock(root):
        path = _path(root / "actions", action_id, "action id")
        action = _read_json(path)
        if not action:
            raise TalkToMyXError(f"action not found: {action_id}")
        if action.get("status") != "prepared":
            raise TalkToMyXError(f"action is already terminal: {action_id}")
        if status in {"succeeded", "partial"}:
            phrase = str(payload.get("confirmation") or "").strip()
            if phrase != action["confirmation_phrase"]:
                raise TalkToMyXError(f"exact confirmation required: {action['confirmation_phrase']}")
            if now() > _parse_iso(action["expires_at"]):
                raise TalkToMyXError("action confirmation expired; prepare a new action")
            action["confirmed_at"] = now_iso()
        result = payload.get("result") or {}
        if not isinstance(result, dict) or _contains_secret(result):
            raise TalkToMyXError("result must be an object without credentials")
        if len(json.dumps(result, ensure_ascii=False)) > 100_000:
            raise TalkToMyXError("result is too large")
        action["status"] = status
        action["result"] = result
        error = str(payload.get("error") or "").strip()
        if len(error) > MAX_SHORT_TEXT:
            raise TalkToMyXError("error is too long")
        action["error"] = error or None
        action["updated_at"] = now_iso()
        _write_json(path, action)
    return {"ok": True, "id": action_id, "type": action["type"], "status": status}


def _evidence_refs(payload: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    refs = payload.get("evidence_refs")
    if refs is None:
        refs = [{"type": "reaction", "id": item} for item in payload.get("evidence_card_ids") or []]
    if not isinstance(refs, list) or not refs:
        raise TalkToMyXError("evidence_refs must be a non-empty array")
    if len(refs) > MAX_COLLECTION_ITEMS:
        raise TalkToMyXError(f"evidence_refs may contain at most {MAX_COLLECTION_ITEMS} items")
    clean: list[dict[str, Any]] = []
    for raw in refs:
        if not isinstance(raw, dict):
            raise TalkToMyXError("each evidence ref must be an object")
        kind = str(raw.get("type") or "")
        if kind not in EVIDENCE_TYPES:
            raise TalkToMyXError(f"unsupported evidence type: {kind}")
        ident = _safe_id(raw.get("id"), "evidence id")
        if kind == "reaction":
            exists = _path(root / "reactions", ident).exists()
        elif kind == "draft_revision":
            draft = _read_json(_path(root / "drafts", ident), {}) or {}
            revision = int(raw.get("revision") or 0)
            exists = 1 <= revision <= len(draft.get("revisions", []))
        elif kind == "action":
            action = _read_json(_path(root / "actions", ident), {}) or {}
            exists = action.get("status") in {"succeeded", "partial"}
        else:
            post = _read_json(_path(root / "posts", ident), {}) or {}
            signal_id = str(raw.get("signal_id") or "")
            exists = any(item.get("id") == signal_id for item in post.get("signals", []))
        if not exists:
            raise TalkToMyXError(f"evidence not found: {kind}:{ident}")
        item = {"type": kind, "id": ident}
        if kind == "draft_revision":
            item["revision"] = int(raw["revision"])
        if kind == "signal":
            item["signal_id"] = str(raw["signal_id"])
        clean.append(item)
    return clean


def apply_memory(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise TalkToMyXError("memory update must be an object")
    taste = str(payload.get("taste_md") or "").strip()
    voice = str(payload.get("voice_md") or "").strip()
    rationale_raw = payload.get("rationale") or []
    if not isinstance(rationale_raw, list) or len(rationale_raw) > MAX_COLLECTION_ITEMS:
        raise TalkToMyXError(f"rationale must be an array of at most {MAX_COLLECTION_ITEMS} items")
    rationale = [str(item).strip() for item in rationale_raw if str(item).strip()]
    if not taste.startswith("#") or not voice.startswith("#"):
        raise TalkToMyXError("taste_md and voice_md must be complete Markdown documents")
    if not rationale:
        raise TalkToMyXError("rationale is required")
    if len(taste) > MAX_DOCUMENT_LENGTH or len(voice) > MAX_DOCUMENT_LENGTH:
        raise TalkToMyXError(f"memory documents are limited to {MAX_DOCUMENT_LENGTH} characters")
    if any(len(item) > MAX_SHORT_TEXT for item in rationale):
        raise TalkToMyXError("rationale items are too long")
    evidence = _evidence_refs(payload, root)
    with _state_lock(root):
        taste_path, voice_path = root / "memory" / "TASTE.md", root / "memory" / "VOICE.md"
        snapshot_id = new_id("memory")
        snapshot = {
            "id": snapshot_id,
            "applied_at": now_iso(),
            "evidence_refs": evidence,
            "rationale": rationale,
            "before": {
                "taste_md": taste_path.read_text(encoding="utf-8"),
                "voice_md": voice_path.read_text(encoding="utf-8"),
            },
            "after": {"taste_md": taste + "\n", "voice_md": voice + "\n"},
        }
        _write_json(_path(root / "history" / "memory", snapshot_id), snapshot)
        _atomic_text(taste_path, taste + "\n")
        _atomic_text(voice_path, voice + "\n")
    return {"ok": True, "snapshot_id": snapshot_id, "evidence_refs": evidence}


def rollback_memory(snapshot_id: str, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    with _state_lock(root):
        snapshot = _read_json(_path(root / "history" / "memory", snapshot_id, "snapshot id"))
        if not snapshot:
            raise TalkToMyXError(f"memory snapshot not found: {snapshot_id}")
        before = snapshot.get("before") or {}
        if not before.get("taste_md") or not before.get("voice_md"):
            raise TalkToMyXError("memory snapshot is incomplete")
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


def set_preferences(payload: Any, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    if not isinstance(payload, dict):
        raise TalkToMyXError("preferences must be an object")
    mapping = {
        "preferences_md": root / "preferences.md",
        "user_md": root / "memory" / "USER.md",
        "taste_md": root / "memory" / "TASTE.md",
        "voice_md": root / "memory" / "VOICE.md",
    }
    values = {key: str(payload.get(key) or "").strip() for key in mapping}
    values = {key: value for key, value in values.items() if value}
    if not values or any(not value.startswith("#") for value in values.values()):
        raise TalkToMyXError("provide at least one complete Markdown document starting with #")
    if any(len(value) > MAX_DOCUMENT_LENGTH for value in values.values()):
        raise TalkToMyXError(f"preference and memory documents are limited to {MAX_DOCUMENT_LENGTH} characters")
    with _state_lock(root):
        backup = root / "history" / "preferences" / new_id("preferences")
        backup.mkdir(parents=True)
        for key, value in values.items():
            path = mapping[key]
            if path.exists():
                shutil.copy2(path, backup / path.name)
            _atomic_text(path, value + "\n")
    return {"ok": True, "changed": sorted(values), "backup": str(backup)}


def export_data(root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    output = root / "exports" / f"talk-to-my-x-{now().strftime('%Y%m%dT%H%M%SZ')}.zip"
    included: list[str] = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in ("preferences.md", "memory", "posts", "reactions", "drafts", "actions", "history"):
            path = root / relative
            candidates = [path] if path.is_file() else list(path.rglob("*"))
            for candidate in candidates:
                if candidate.is_file() and candidate != output and candidate.name != ".state.lock":
                    arcname = str(candidate.relative_to(root))
                    archive.write(candidate, arcname)
                    included.append(arcname)
    return {"ok": True, "path": str(output), "files": len(included)}


def migrate_legacy(source: Path, root: Path | None = None) -> dict[str, Any]:
    root = ensure_layout(root)
    source = source.expanduser().resolve()
    if not source.exists() or source == root.resolve():
        raise TalkToMyXError(f"legacy path not found or equals destination: {source}")
    report: dict[str, Any] = {"ok": True, "from": str(source), "to": str(root), "migrated": [], "skipped": {}}
    with _state_lock(root):
        preference_source = source / "preferences.md"
        if not preference_source.exists():
            preference_source = source / "prompt.md"
        if preference_source.exists():
            text = preference_source.read_text(encoding="utf-8")
            text = text.replace("X Feed Loop", "Talk to My X").replace("X-LiveCast", "Talk to My X")
            _atomic_text(root / "preferences.md", text)
            report["migrated"].append("preferences.md")
        for name in ("USER.md", "TASTE.md", "VOICE.md"):
            old = source / "memory" / name
            if old.exists():
                shutil.copy2(old, root / "memory" / name)
                report["migrated"].append(f"memory/{name}")
        for directory in ("posts", "reactions", "drafts", "actions"):
            count = 0
            old_dir = source / directory
            if old_dir.exists():
                for old in old_dir.glob("*.json"):
                    target = root / directory / old.name
                    if not target.exists() and SAFE_ID.fullmatch(old.stem):
                        shutil.copy2(old, target)
                        count += 1
            if count:
                report["migrated"].append(f"{directory}:{count}")
        old_seen = source / ".state" / "seen.json"
        if not old_seen.exists():
            old_seen = source / "state" / "seen.json"
        if old_seen.exists():
            shutil.copy2(old_seen, root / "state" / "seen.json")
            report["migrated"].append("state/seen.json")
        report["skipped"] = {
            "sessions": len(list((source / "sessions").glob("*.json"))) if (source / "sessions").exists() else 0,
            "briefs": len(list((source / "briefs").glob("*.json"))) if (source / "briefs").exists() else 0,
            "reason": "legacy transcripts and briefs were left untouched",
        }
        report_path = root / "migration" / f"{new_id('migration')}.json"
        _write_json(report_path, report)
    return {**report, "report": str(report_path)}
