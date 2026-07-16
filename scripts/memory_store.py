#!/usr/bin/env python3
"""Resolve memory/USER.md + TASTE.md under XLC_DATA_DIR when set (cloud disk)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_root() -> Path:
    raw = (os.environ.get("XLC_DATA_DIR") or "").strip()
    return Path(raw) if raw else ROOT


def memory_dir() -> Path:
    """Runtime memory dir. On cloud, prefer disk; seed from repo templates once."""
    base = data_root()
    mem = base / "memory" if base != ROOT else ROOT / "memory"
    try:
        mem.mkdir(parents=True, exist_ok=True)
    except OSError:
        mem = ROOT / "memory"
        mem.mkdir(parents=True, exist_ok=True)
    # Seed missing files from repo checkout so cloud starts with scaffolds.
    for name in ("USER.md", "TASTE.md"):
        dest = mem / name
        src = ROOT / "memory" / name
        if not dest.exists() and src.exists():
            try:
                shutil.copy2(src, dest)
            except OSError:
                pass
    return mem


def user_path() -> Path:
    return memory_dir() / "USER.md"


def taste_path() -> Path:
    return memory_dir() / "TASTE.md"


def proposals_dir() -> Path:
    d = memory_dir() / "proposals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_user() -> str:
    p = user_path()
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def read_taste() -> str:
    p = taste_path()
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_markdown(path: Path, text: str, *, backup: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = text if text.endswith("\n") else text + "\n"
    if backup and path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
    path.write_text(body, encoding="utf-8")
