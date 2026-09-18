"""ADR-0011: admission gate + tool schemas (offline, no network).

  python -m pytest tests/unit/test_bobik_gate.py -q
  python tests/unit/test_bobik_gate.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"
sys.path.insert(0, str(API))

from app.bobik_gate import (  # noqa: E402
    ADMIT_CHAT,
    ADMIT_EXECUTE,
    ADMIT_REFUSE,
    DAR_FIXTURES,
    TOOL_CALL_SCHEMA,
    TOOL_NAMES,
    admit,
    match_tool_intent,
    validate_tool_call,
)


class TestBobikGate(unittest.TestCase):
    def test_tool_schema_enum_covers_registry(self):
        enum = TOOL_CALL_SCHEMA["properties"]["tool"]["enum"]
        self.assertEqual(set(enum), set(TOOL_NAMES))

    def test_validate_tool_call_ok(self):
        ok, msg = validate_tool_call({"tool": "home.status", "args": {}})
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")

    def test_validate_tool_call_rejects_unknown(self):
        ok, _ = validate_tool_call({"tool": "home.wipe", "args": {}})
        self.assertFalse(ok)

    def test_validate_tool_call_rejects_extra_fields(self):
        ok, _ = validate_tool_call(
            {"tool": "home.status", "args": {}, "shell": "rm -rf /"}
        )
        self.assertFalse(ok)

    def test_dar_fixtures(self):
        fails = []
        for text, expected in DAR_FIXTURES:
            got = admit(text, structured_tools=True)["decision"]
            if got != expected:
                fails.append((text, expected, got))
        self.assertEqual(fails, [], msg="DAR mismatches: %r" % fails)

    def test_dangerous_never_chat(self):
        for text, expected in DAR_FIXTURES:
            if expected != ADMIT_REFUSE:
                continue
            d = admit(text)["decision"]
            self.assertEqual(d, ADMIT_REFUSE, text)
            self.assertNotEqual(d, ADMIT_CHAT, text)

    def test_home_tool_without_structured_still_refuses_danger(self):
        d = admit("rm -rf /", structured_tools=False)
        self.assertEqual(d["decision"], ADMIT_REFUSE)

    def test_chat_when_no_tool(self):
        d = admit("что приготовить из курицы и риса", structured_tools=True)
        self.assertEqual(d["decision"], ADMIT_CHAT)

    def test_match_tool_intent_status(self):
        self.assertEqual(match_tool_intent("статус jetson"), "home.status")

    def test_execute_returns_tool_name(self):
        d = admit("сколько места на диске")
        self.assertEqual(d["decision"], ADMIT_EXECUTE)
        self.assertEqual(d["tool"], "home.disk")


if __name__ == "__main__":
    unittest.main()
