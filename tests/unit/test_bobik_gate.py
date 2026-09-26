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


# ── Инцидент 2026-09-26: «какая температура в Париже» уходила в home.status ──
# Голосовой вопрос владельца был общим, бот ответил домашней командой (журнал
# «bobik home tool»). Причина: _TOOL_INTENTS искал «температур»/«нагрузк»/
# «контейнер»/«альбом»/«команды»/«помощ» подстрокой где угодно во фразе.
# Разбор — СИЛЬНЫЕ/СЛАБЫЕ шаблоны + домашний якорь + анти-якорь (погода/город)
# + предел длины фразы. Регрессия ниже — оба направления сразу.

_REGRESSION_TO_CHAT = [
    # из задания (инцидент + расширенный набор)
    "какая температура в Париже",
    "какая завтра погода",
    "какая нагрузка на мышцы при беге",
    "помоги с домашкой по математике",
    "сделай альбом песен на день рождения",
    "сколько будет два плюс два",
    "расскажи про контейнерные перевозки",
    "напиши команды для зарядки",
    # голосовые (строчные, без знаков препинания, «бобик» в начале)
    "бобик какая температура в сочи",
    "бобик расскажи про контейнер как жанр кино",
    "бобик какая нагрузка была на команду вчера в матче",
    # правило 4: длинная фраза (>12 слов) без сильного шаблона — к модели,
    # даже если внутри есть и якорь («сервере»), и слабое слово («температура»)
    "бобик расскажи подробно какая обычно температура держится на сервере в дата-центре этим летом",
]

_REGRESSION_TO_TOOL = [
    # из задания
    ("какая температура у сервера", "home.status"),
    ("статус", "home.status"),
    ("как там сервер", "home.status"),
    ("нагрузка на процессор джетсона", "home.status"),
    ("жив ли нас", "home.status"),
    ("сколько места на диске", "home.disk"),
    ("свободное место на hdd", "home.disk"),
    ("когда был бэкап", "home.backup_age"),
    ("сколько фото в immich", "home.photos"),
    ("сколько фото", "home.photos"),
    ("кто я", "home.whoami"),
    ("что умеешь", "home.help"),
    # свои дополнения, включая голосовой стиль
    ("бобик какая температура у джетсона", "home.status"),
    ("бобик как там процессор дома", "home.status"),
    ("бобик статус", "home.status"),
    ("сколько места осталось на ssd", "home.disk"),
    ("бобик сколько свободного места", "home.disk"),
    ("бобик когда был последний бэкап", "home.backup_age"),
    # «копия...свежая» — СЛАБЫЙ шаблон, нужен якорь («сервер»), иначе это
    # может быть про что угодно («копия документа свежая?»)
    ("копия на сервере свежая?", "home.backup_age"),
    ("бобик сколько фото у нас в immich", "home.photos"),
    ("сколько всего фото", "home.photos"),
    ("бобик кто я такой", "home.whoami"),
    ("как меня зовут", "home.whoami"),
    ("бобик что умеешь", "home.help"),
    ("помощь по командам", "home.help"),
]


class TestBobikGateRegression20260926(unittest.TestCase):
    """Инцидент 2026-09-26: классификатор путал общий вопрос с домашней командой."""

    def test_general_questions_go_to_chat_not_tool(self):
        fails = []
        for text in _REGRESSION_TO_CHAT:
            d = admit(text)
            if d["decision"] != ADMIT_CHAT:
                fails.append((text, d["decision"], d.get("tool")))
        self.assertEqual(fails, [], msg="ожидался chat, получено: %r" % fails)

    def test_home_questions_still_hit_the_right_tool(self):
        fails = []
        for text, expected_tool in _REGRESSION_TO_TOOL:
            d = admit(text)
            if d["decision"] != ADMIT_EXECUTE or d.get("tool") != expected_tool:
                fails.append((text, expected_tool, d["decision"], d.get("tool")))
        self.assertEqual(fails, [], msg="разошлось с ожиданием: %r" % fails)


if __name__ == "__main__":
    unittest.main()
