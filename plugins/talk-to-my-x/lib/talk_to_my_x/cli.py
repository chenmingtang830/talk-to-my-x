"""Recovery and development CLI for Talk to My X."""

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
    TalkToMyXError,
    apply_memory,
    build_context,
    capture_reaction,
    complete_action,
    data_root,
    data_root_source,
    ensure_layout,
    export_data,
    export_preferences,
    ingest_posts,
    migrate_legacy,
    prepare_action,
    rollback_memory,
    save_draft,
    set_preferences,
    signal_post,
)


OFFICIAL_X_SKILL_URL = "https://docs.x.com"


def official_x_skill_candidates() -> list[Path]:
    explicit = (os.environ.get("TTMX_X_SKILL") or "").strip()
    candidates = [
        Path(explicit).expanduser() if explicit else None,
        Path.cwd() / ".agents" / "skills" / "x" / "SKILL.md",
        Path.home() / ".agents" / "skills" / "x" / "SKILL.md",
        Path.home() / ".codex" / "skills" / "x" / "SKILL.md",
    ]
    return [path for path in candidates if path]


def official_x_skill_path() -> Path | None:
    return next((path.resolve() for path in official_x_skill_candidates() if path.is_file()), None)


def stdin_json() -> Any:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise TalkToMyXError(f"invalid JSON on stdin: {exc}") from exc


def doctor() -> dict[str, Any]:
    root = ensure_layout()
    binary = shutil.which("xurl")
    x_skill = official_x_skill_path()
    result: dict[str, Any] = {
        "ok": bool(binary and x_skill),
        "version": __version__,
        "home": str(root),
        "home_source": data_root_source(),
        "python": sys.version.split()[0],
        "xurl": binary,
        "x_auth_configured": False,
        "x_api_credits": "not_verifiable_locally",
        "official_x_skill": OFFICIAL_X_SKILL_URL,
        "official_x_skill_installed": bool(x_skill),
        "official_x_skill_path": str(x_skill) if x_skill else None,
        "official_x_skill_searched": [str(path) for path in official_x_skill_candidates()],
        "onboarding_complete": "Add what you want to follow" not in (root / "preferences.md").read_text(encoding="utf-8"),
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
        missing = []
        if not x_skill:
            missing.append(
                f"install the official X Skill with `npx skills add {OFFICIAL_X_SKILL_URL} "
                "--global --agent codex --yes`, or point TTMX_X_SKILL at an existing SKILL.md"
            )
        if not binary:
            missing.append("install official xurl")
        elif not result["x_auth_configured"]:
            missing.append("configure your X Developer App and complete OAuth")
        result["hint"] = "; ".join(missing) + "."
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="talk-to-my-x", description="Local state for talking to your X")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--source", required=True)
    ingest.add_argument("--stdin", action="store_true", required=True)
    context = commands.add_parser("context")
    context.add_argument("--limit", type=int, default=50)
    signal = commands.add_parser("signal")
    signal.add_argument("--post", required=True)
    signal.add_argument("--kind", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("--stdin", action="store_true", required=True)
    draft = commands.add_parser("draft")
    draft.add_argument("--stdin", action="store_true", required=True)
    action = commands.add_parser("action")
    action_sub = action.add_subparsers(dest="action_command", required=True)
    prepare = action_sub.add_parser("prepare")
    prepare.add_argument("--stdin", action="store_true", required=True)
    complete = action_sub.add_parser("complete")
    complete.add_argument("--id", required=True)
    complete.add_argument("--stdin", action="store_true", required=True)
    memory = commands.add_parser("memory")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    apply = memory_sub.add_parser("apply")
    apply.add_argument("--stdin", action="store_true", required=True)
    rollback = memory_sub.add_parser("rollback")
    rollback.add_argument("--snapshot", required=True)
    preferences = commands.add_parser("preferences")
    preferences_sub = preferences.add_subparsers(dest="preferences_command", required=True)
    preferences_sub.add_parser("export")
    set_command = preferences_sub.add_parser("set")
    set_command.add_argument("--stdin", action="store_true", required=True)
    commands.add_parser("export")
    migrate = commands.add_parser("migrate")
    migrate.add_argument("--from", dest="source", required=True)
    return root


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "doctor":
        return doctor()
    if args.command == "ingest":
        return ingest_posts(stdin_json(), args.source)
    if args.command == "context":
        return build_context(limit=args.limit)
    if args.command == "signal":
        return signal_post(args.post, args.kind)
    if args.command == "capture":
        return capture_reaction(stdin_json())
    if args.command == "draft":
        return save_draft(stdin_json())
    if args.command == "action" and args.action_command == "prepare":
        return prepare_action(stdin_json())
    if args.command == "action" and args.action_command == "complete":
        return complete_action(args.id, stdin_json())
    if args.command == "memory" and args.memory_command == "apply":
        return apply_memory(stdin_json())
    if args.command == "memory" and args.memory_command == "rollback":
        return rollback_memory(args.snapshot)
    if args.command == "preferences" and args.preferences_command == "export":
        return export_preferences()
    if args.command == "preferences" and args.preferences_command == "set":
        return set_preferences(stdin_json())
    if args.command == "export":
        return export_data()
    if args.command == "migrate":
        return migrate_legacy(Path(args.source))
    raise TalkToMyXError("unsupported command")


def main(argv: list[str] | None = None) -> int:
    try:
        payload = run(parser().parse_args(argv))
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get("ok", True) else 1
    except (TalkToMyXError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
