#!/usr/bin/env python3
"""Launch the bundled Talk to My X state MCP."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from talk_to_my_x.mcp_server import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
