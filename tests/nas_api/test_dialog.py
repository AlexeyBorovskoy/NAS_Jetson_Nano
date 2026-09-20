"""Память разговора @бобик (спецификация 2026-09-19 §4, §6).

Зачем: семья спрашивает «а без мяса?» вторым сообщением. Память живёт только в процессе —
никакой переписки на диске; забывается через 30 минут тишины, чтобы вечером не всплыл утренний
разговор и чтобы история не съедала квоту GigaChat.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.dialog")


class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def __call__(self):
        return self.t


def test_history_keeps_order_and_speakers():
    d = load()
    m = d.DialogMemory()
    m.add("tg:1", "Оля", "что приготовить на ужин?")
    m.add("tg:1", "Бобик", "Паста с курицей.")
    m.add("tg:1", "Ваня", "а без мяса?")
    assert m.history("tg:1") == "Оля: что приготовить на ужин?\nБобик: Паста с курицей.\nВаня: а без мяса?"


def test_unknown_key_is_empty():
    d = load()
    assert d.DialogMemory().history("tg:нет") == ""


def test_keys_do_not_mix():
    d = load()
    m = d.DialogMemory()
    m.add("tg:1", "Оля", "первый")
    m.add("tg:2", "Ваня", "второй")
    assert m.history("tg:1") == "Оля: первый"
    assert m.history("tg:2") == "Ваня: второй"


def test_only_last_turns_are_kept():
    d = load()
    m = d.DialogMemory(max_turns=4)
    for i in range(6):
        m.add("k", "Оля", "реплика %d" % i)
    lines = m.history("k").split("\n")
    assert len(lines) == 4
    assert lines[0].endswith("реплика 2") and lines[-1].endswith("реплика 5")


def test_conversation_is_forgotten_after_idle():
    d = load()
    c = Clock()
    m = d.DialogMemory(idle_ttl=1800, clock=c)
    m.add("k", "Оля", "привет")
    c.t += 1799
    assert m.history("k") == "Оля: привет"
    c.t += 2
    assert m.history("k") == ""
    m.add("k", "Оля", "снова")
    assert m.history("k") == "Оля: снова"


def test_idle_counts_from_last_turn():
    d = load()
    c = Clock()
    m = d.DialogMemory(idle_ttl=100, clock=c)
    m.add("k", "Оля", "раз")
    c.t += 60
    m.add("k", "Бобик", "два")
    c.t += 60
    assert m.history("k") == "Оля: раз\nБобик: два"


def test_forget_clears_only_that_key():
    d = load()
    m = d.DialogMemory()
    m.add("a", "Оля", "раз")
    m.add("b", "Ваня", "два")
    assert m.forget("a") is True
    assert m.forget("a") is False
    assert m.history("a") == "" and m.history("b") == "Ваня: два"


def test_long_turn_is_trimmed():
    d = load()
    m = d.DialogMemory(max_chars_turn=20)
    m.add("k", "Оля", "я" * 100)
    assert m.history("k") == "Оля: " + "я" * 20


def test_total_history_is_capped_dropping_oldest():
    d = load()
    m = d.DialogMemory(max_turns=10, max_chars_total=60)
    for i in range(5):
        m.add("k", "Оля", "реплика номер %d" % i)
    text = m.history("k")
    assert len(text) <= 60
    assert "номер 4" in text and "номер 0" not in text


def test_whitespace_is_collapsed_and_empty_ignored():
    d = load()
    m = d.DialogMemory()
    m.add("k", "Оля", "  две\n\nстроки  ")
    m.add("k", "Оля", "   ")
    assert m.history("k") == "Оля: две строки"


def test_module_level_memory_exists():
    d = load()
    assert isinstance(d.MEMORY, d.DialogMemory)
