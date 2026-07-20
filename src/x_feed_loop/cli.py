"""Command-line interface for X Feed Loop local state."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .store import (
    FeedLoopError,
    apply_memory,
    build_context,
    capture_reaction,
    data_root,
    ensure_layout,
    export_preferences,
    import_preferences,
    ingest_posts,
    mark_published,
    migrate_legacy,
    rollback_memory,
    save_draft,
    signal_post,
)


def _stdin_json() -> Any:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise FeedLoopError(f"invalid JSON on stdin: {exc}") from exc


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def doctor() -> dict[str, Any]:
    root = ensure_layout()
    binary = shutil.which("xurl")
    result: dict[str, Any] = {
        "ok": bool(binary),
        "version": __version__,
        "home": str(root),
        "python": sys.version.split()[0],
        "xurl": binary,
        "x_auth_configured": False,
        "official_x_skill": "https://docs.x.com/tools/skill-md",
    }
    if binary:
        env = dict(os.environ)
        env.setdefault("NO_COLOR", "1")
        proc = subprocess.run([binary, "auth", "status"], capture_output=True, text=True, timeout=15, env=env)
        status = re.sub(r"\x1b\[[0-9;]*m", "", (proc.stdout or proc.stderr or ""))
        oauth2 = re.search(r"oauth2:\s+(?!\(none\))\S+", status)
        oauth1 = re.search(r"oauth1:\s+(?![–-]\s*$)\S+", status, re.MULTILINE)
        result["x_auth_configured"] = proc.returncode == 0 and bool(oauth1 or oauth2)
        result["ok"] = result["ok"] and result["x_auth_configured"]
    if not result["ok"]:
        result["hint"] = "Install the official X skill and complete xurl authentication; see SKILL.md."
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="x-feed-loop", description="Local state for thinking with your X feed")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor")

    ingest = commands.add_parser("ingest")
    ingest.add_argument("--source", choices=("timeline", "bookmarks", "search"), required=True)
    ingest.add_argument("--stdin", action="store_true", required=True, help="Read normalized posts from stdin")

    context = commands.add_parser("context")
    context.add_argument("--json", action="store_true")
    context.add_argument("--limit", type=int, default=50)

    signal = commands.add_parser("signal")
    signal.add_argument("--post", required=True)
    signal.add_argument("--kind", choices=("selected", "skipped", "explored"), required=True)

    capture = commands.add_parser("capture")
    capture.add_argument("--stdin", action="store_true", required=True)

    draft = commands.add_parser("draft")
    draft_commands = draft.add_subparsers(dest="draft_command", required=True)
    draft_save = draft_commands.add_parser("save")
    draft_save.add_argument("--stdin", action="store_true", required=True)
    draft_published = draft_commands.add_parser("mark-published")
    draft_published.add_argument("--id", required=True)
    draft_published.add_argument("--stdin", action="store_true", required=True)

    memory = commands.add_parser("memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    memory_apply = memory_commands.add_parser("apply")
    memory_apply.add_argument("--stdin", action="store_true", required=True)
    memory_rollback = memory_commands.add_parser("rollback")
    memory_rollback.add_argument("--snapshot", required=True)

    preferences = commands.add_parser("preferences")
    preferences_commands = preferences.add_subparsers(dest="preferences_command", required=True)
    preferences_export = preferences_commands.add_parser("export")
    preferences_export.add_argument("--output")
    preferences_import = preferences_commands.add_parser("import")
    preferences_import.add_argument("--stdin", action="store_true", required=True)

    migrate = commands.add_parser("migrate")
    migrate.add_argument("--from", dest="source", required=True)
    return root


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "doctor":
        return doctor()
    if args.command == "ingest":
        return ingest_posts(_stdin_json(), args.source)
    if args.command == "context":
        return build_context(limit=args.limit)
    if args.command == "signal":
        return signal_post(args.post, args.kind)
    if args.command == "capture":
        return capture_reaction(_stdin_json())
    if args.command == "draft" and args.draft_command == "save":
        return save_draft(_stdin_json())
    if args.command == "draft" and args.draft_command == "mark-published":
        return mark_published(args.id, _stdin_json())
    if args.command == "memory" and args.memory_command == "apply":
        return apply_memory(_stdin_json())
    if args.command == "memory" and args.memory_command == "rollback":
        return rollback_memory(args.snapshot)
    if args.command == "preferences" and args.preferences_command == "export":
        payload = export_preferences()
        if args.output:
            output = Path(args.output).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return {"ok": True, "output": str(output)}
        return payload
    if args.command == "preferences" and args.preferences_command == "import":
        return import_preferences(_stdin_json())
    if args.command == "migrate":
        return migrate_legacy(Path(args.source))
    raise FeedLoopError("unsupported command")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        payload = run(args)
        _print(payload)
        return 0 if payload.get("ok", True) else 1
    except (FeedLoopError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
