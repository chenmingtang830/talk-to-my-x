from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from x_feed_loop.cli import main  # noqa: E402


class CliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"XFL_HOME": self.temp.name})
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temp.cleanup()

    def invoke(self, argv: list[str], payload: object | None = None) -> tuple[int, dict[str, object]]:
        stdin = io.StringIO(json.dumps(payload) if payload is not None else "")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        raw = stdout.getvalue() if stdout.getvalue() else stderr.getvalue()
        return code, json.loads(raw)

    def test_ingest_capture_draft_context_contract(self) -> None:
        source = {
            "id": "100",
            "text": "A useful post",
            "author": "alice",
            "url": "https://x.com/alice/status/100",
            "source": "timeline",
        }
        code, ingested = self.invoke(["ingest", "--source", "timeline", "--stdin"], [source])
        self.assertEqual(code, 0)
        self.assertEqual(ingested["created"], 1)

        code, captured = self.invoke(
            ["capture", "--stdin"],
            {"id": "card_1", "sources": ["100"], "raw_reaction": "This matters because distribution compounds."},
        )
        self.assertEqual(code, 0)
        self.assertEqual(captured["id"], "card_1")

        code, drafted = self.invoke(
            ["draft", "save", "--stdin"],
            {"id": "draft_1", "text": "Distribution compounds.", "sources": ["100"], "card_ids": ["card_1"]},
        )
        self.assertEqual(code, 0)
        self.assertEqual(drafted["revision"], 1)

        code, context = self.invoke(["context", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(context["reaction_cards"][0]["id"], "card_1")
        self.assertEqual(context["posts"], [])

    def test_invalid_contract_is_json_error(self) -> None:
        code, result = self.invoke(
            ["ingest", "--source", "timeline", "--stdin"], [{"id": "100", "source": "timeline"}]
        )
        self.assertEqual(code, 1)
        self.assertFalse(result["ok"])
        self.assertIn("missing text", result["error"])


if __name__ == "__main__":
    unittest.main()
