#!/usr/bin/env python3
"""Launch the bundled Talk to My X state MCP.

This file stays parseable on old interpreters so the version check below can
report a readable error instead of a SyntaxError from the package it imports.
"""

from __future__ import annotations

import sys
from pathlib import Path

MINIMUM_PYTHON = (3, 10)

if sys.version_info < MINIMUM_PYTHON:
    sys.stderr.write(
        "Talk to My X needs Python {}.{}+, but this MCP server was started with "
        "{} ({}).\nPoint the `state` server in the plugin's .mcp.json at a newer "
        "interpreter, or install one and make it the first `python3` on PATH.\n".format(
            MINIMUM_PYTHON[0],
            MINIMUM_PYTHON[1],
            ".".join(str(part) for part in sys.version_info[:3]),
            sys.executable,
        )
    )
    raise SystemExit(1)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from talk_to_my_x.mcp_server import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
