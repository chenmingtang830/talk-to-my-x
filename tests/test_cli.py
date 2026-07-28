from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

LIB = Path(__file__).resolve().parents[1] / "plugins" / "talk-to-my-x" / "lib"
sys.path.insert(0, str(LIB))

from talk_to_my_x.cli import doctor, main  # noqa: E402


class CliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"TTMX_HOME": self.temp.name})
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temp.cleanup()

    def invoke(self, argv: list[str], payload: object | None = None) -> tuple[int, dict[str, object]]:
        stdin = io.StringIO(json.dumps(payload) if payload is not None else "")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, json.loads(stdout.getvalue() or stderr.getvalue())

    def test_end_to_end_local_contract(self) -> None:
        source = {
            "id": "100",
            "text": "A useful post",
            "author": "alice",
            "url": "https://x.com/alice/status/100",
            "source": "timeline",
        }
        code, result = self.invoke(["ingest", "--source", "timeline", "--stdin"], [source])
        self.assertEqual((code, result["created"]), (0, 1))
        code, card = self.invoke(
            ["capture", "--stdin"],
            {"id": "card_1", "sources": ["100"], "raw_reaction": "Distribution compounds."},
        )
        self.assertEqual((code, card["id"]), (0, "card_1"))
        code, draft = self.invoke(
            ["draft", "--stdin"],
            {"id": "draft_1", "text": "Distribution compounds.", "sources": ["100"], "card_ids": ["card_1"]},
        )
        self.assertEqual((code, draft["revision"]), (0, 1))
        code, context = self.invoke(["context"])
        self.assertEqual(code, 0)
        self.assertEqual(context["drafts"][0]["id"], "draft_1")

    def test_action_cli_cancel(self) -> None:
        code, prepared = self.invoke(["action", "prepare", "--stdin"], {"id": "a1", "type": "follow", "target": {"username": "alice"}})
        self.assertEqual(code, 0)
        code, completed = self.invoke(["action", "complete", "--id", "a1", "--stdin"], {"status": "cancelled"})
        self.assertEqual((code, completed["status"]), (0, "cancelled"))

    def test_invalid_json_is_structured_error(self) -> None:
        stdin, stdout, stderr = io.StringIO("{"), io.StringIO(), io.StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["capture", "--stdin"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(stderr.getvalue())["ok"])

    def test_doctor_checks_official_skill_and_oauth(self) -> None:
        skill = Path(self.temp.name) / "x" / "SKILL.md"
        skill.parent.mkdir()
        skill.write_text("# X\n", encoding="utf-8")
        oauth = subprocess.CompletedProcess(["xurl"], 0, stdout="oauth2: richardt830\n", stderr="")
        with patch.dict(os.environ, {"TTMX_X_SKILL": str(skill)}), patch(
            "talk_to_my_x.cli.shutil.which", return_value="/opt/homebrew/bin/xurl"
        ), patch("talk_to_my_x.cli.subprocess.run", return_value=oauth):
            result = doctor()
        self.assertTrue(result["ok"])
        self.assertTrue(result["official_x_skill_installed"])


if __name__ == "__main__":
    unittest.main()
