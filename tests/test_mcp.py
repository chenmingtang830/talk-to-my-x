from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "talk-to-my-x" / "scripts" / "state_mcp.py"


class McpContractTests(unittest.TestCase):
    def call(self, messages: list[dict[str, object] | str]) -> list[dict[str, object]]:
        with tempfile.TemporaryDirectory() as temp:
            lines = [item if isinstance(item, str) else json.dumps(item) for item in messages]
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)],
                input="\n".join(lines) + "\n",
                capture_output=True,
                text=True,
                env={**os.environ, "TTMX_HOME": temp},
                timeout=10,
                check=True,
            )
        return [json.loads(line) for line in proc.stdout.splitlines()]

    def test_initialize_and_tool_annotations(self) -> None:
        rows = self.call([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ])
        self.assertEqual(rows[0]["result"]["serverInfo"]["name"], "talk-to-my-x-state")
        tools = {item["name"]: item for item in rows[1]["result"]["tools"]}
        self.assertEqual(len(tools), 12)
        self.assertNotIn("migrate", tools)
        self.assertTrue(tools["get_context"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["prepare_action"]["annotations"]["openWorldHint"])

    def test_tools_call_and_structured_error(self) -> None:
        rows = self.call([
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_context", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "prepare_action", "arguments": {"type": "follow", "target": {"username": "bad-name"}}}},
        ])
        self.assertFalse(rows[0]["result"]["isError"])
        self.assertTrue(rows[1]["result"]["isError"])

    def test_invalid_json_does_not_crash_server(self) -> None:
        rows = self.call(["{", {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}])
        self.assertEqual(rows[0]["error"]["code"], -32700)
        self.assertEqual(rows[1]["result"], {})


if __name__ == "__main__":
    unittest.main()
