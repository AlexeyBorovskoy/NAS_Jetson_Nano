"""E3: «бобик, что сломалось?» — сборка ответа (app/routers/talk_bot.py).

Ключевой сценарий — инцидент 2026-09-20: зависший ntfs-3g на /mnt/hdd2tb сделал
обращение к точке монтирования блокирующим навсегда и уронил весь API. Проверка
HDD обязана возвращать ответ за отведённый таймаут, а не виснуть вместе с диском.

Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load_bot():
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
    return importlib.import_module("app.routers.talk_bot")


def _async(value):
    async def f(*a, **k):
        return value
    return f


# ── HDD: таймаут вместо зависания ───────────────────────────────────────────────

def test_hdd_check_times_out_instead_of_hanging(monkeypatch):
    # Важно: не через asyncio.run() — его штатное завершение само дожидается
    # default-executor (shutdown_default_executor) и замаскировало бы регрессию
    # временем самого процесса, а не временем ответа _check_hdd_mount(). У
    # реального uvicorn-цикла такого дожидания на каждый вызов нет — обработка
    # следующих сообщений бота продолжается сразу после таймаута.
    bot = load_bot()

    def hang():
        time.sleep(1.5)  # имитация зависшего ntfs-3g (D-state) короче, чем нужно для теста
        return True, ""

    monkeypatch.setattr(bot, "_hdd_mount_probe", hang)
    loop = asyncio.new_event_loop()
    try:
        start = time.monotonic()
        result = loop.run_until_complete(bot._check_hdd_mount(timeout=0.1))
        elapsed = time.monotonic() - start
    finally:
        loop.close()
    assert elapsed < 1.0, "проверка HDD не должна ждать зависший диск"
    assert result is not None and "не отвечает" in result


def test_hdd_check_reports_not_mounted():
    bot = load_bot()
    orig = bot._hdd_mount_probe
    try:
        bot._hdd_mount_probe = lambda: (False, "")
        result = asyncio.run(bot._check_hdd_mount(timeout=1))
        assert result is not None and "не смонтирован" in result
    finally:
        bot._hdd_mount_probe = orig


def test_hdd_check_ok_when_mounted():
    bot = load_bot()
    orig = bot._hdd_mount_probe
    try:
        bot._hdd_mount_probe = lambda: (True, "")
        result = asyncio.run(bot._check_hdd_mount(timeout=1))
        assert result is None
    finally:
        bot._hdd_mount_probe = orig


# ── алерты Phase E: читаем снимок, не пересчитываем ─────────────────────────────

def test_read_active_alerts_parses_state_file():
    bot = load_bot()
    tmp = tempfile.mkdtemp()
    state_file = os.path.join(tmp, "state.json")
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump({
            "dumps": {"active": True, "text": "🔴 бэкапы устарели"},
            "ram": {"active": False, "text": "🟠 мало памяти"},
            "disk": {"active": True, "text": ""},  # без текста — пропускается
        }, fh)
    bot.settings.talk_alert_state_file = state_file
    assert bot._read_active_alerts() == ["🔴 бэкапы устарели"]


def test_read_active_alerts_missing_file_is_not_an_alarm():
    bot = load_bot()
    bot.settings.talk_alert_state_file = "/no/such/file-e3-test.json"
    assert bot._read_active_alerts() == []


def test_read_active_alerts_corrupt_file_is_not_an_alarm():
    bot = load_bot()
    tmp = tempfile.mkdtemp()
    state_file = os.path.join(tmp, "broken.json")
    with open(state_file, "w", encoding="utf-8") as fh:
        fh.write("{не json")
    bot.settings.talk_alert_state_file = state_file
    assert bot._read_active_alerts() == []


# ── systemd: best-effort, недоступность — не тревога ────────────────────────────

def test_failed_units_check_survives_missing_binary(monkeypatch):
    bot = load_bot()

    async def boom(*a, **k):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(bot.asyncio, "create_subprocess_exec", boom)
    result = asyncio.run(bot._check_failed_units(timeout=1))
    assert result is None


# ── сборка ответа ─────────────────────────────────────────────────────────────

def test_build_health_all_clear(monkeypatch):
    bot = load_bot()
    monkeypatch.setattr(bot.system_mod, "_docker_ps_json", _async([]))
    monkeypatch.setattr(bot.storage_mod, "_disk_info", lambda p: {"mounted": True, "used_pct": 12})
    monkeypatch.setattr(bot.storage_mod, "_backup_info", lambda: {"available": True, "dumps": [
        {"db": "nextcloud", "age_hours": 3}, {"db": "immich", "age_hours": 4}]})
    monkeypatch.setattr(bot, "_check_hdd_mount", _async(None))
    monkeypatch.setattr(bot, "_check_failed_units", _async(None))
    monkeypatch.setattr(bot, "_read_active_alerts", lambda: [])
    result = asyncio.run(bot._build_health())
    assert result == "✅ Дома всё в порядке — контейнеры, диски и бэкапы штатно."


def test_build_health_lists_every_kind_of_problem_once(monkeypatch):
    bot = load_bot()
    bot.settings.expected_containers = "homecloud_nextcloud"
    monkeypatch.setattr(bot.system_mod, "_docker_ps_json",
                        _async([{"name": "homecloud_nextcloud", "state": "exited"}]))
    monkeypatch.setattr(bot.storage_mod, "_disk_info", lambda p: {"mounted": True, "used_pct": 95})
    monkeypatch.setattr(bot.storage_mod, "_backup_info", lambda: {"available": True, "dumps": [
        {"db": "nextcloud", "age_hours": None}]})
    monkeypatch.setattr(bot, "_check_hdd_mount", _async("HDD /mnt/hdd2tb не смонтирован"))
    monkeypatch.setattr(bot, "_check_failed_units", _async("systemd: аварийные юниты — foo.service"))
    monkeypatch.setattr(bot, "_read_active_alerts", lambda: ["🟠 квота GigaChat кончается"])
    result = asyncio.run(bot._build_health())
    assert result.startswith("⚠️ Не в порядке:")
    assert "homecloud_nextcloud" in result
    assert "заполнен" in result
    assert "нет дампа nextcloud" in result
    assert "HDD /mnt/hdd2tb не смонтирован" in result
    assert "foo.service" in result
    assert "квота GigaChat" in result
    # каждая строка — ровно один буллит, без повторов
    assert result.count("HDD /mnt/hdd2tb не смонтирован") == 1


def test_build_health_ssd_not_mounted_skips_backup_check(monkeypatch):
    # SSD не смонтирован — читать дампы с него бессмысленно (тот же путь недоступен).
    bot = load_bot()
    monkeypatch.setattr(bot.system_mod, "_docker_ps_json", _async([]))
    monkeypatch.setattr(bot.storage_mod, "_disk_info", lambda p: {"mounted": False})
    called = []
    monkeypatch.setattr(bot.storage_mod, "_backup_info", lambda: called.append(1))
    monkeypatch.setattr(bot, "_check_hdd_mount", _async(None))
    monkeypatch.setattr(bot, "_check_failed_units", _async(None))
    monkeypatch.setattr(bot, "_read_active_alerts", lambda: [])
    result = asyncio.run(bot._build_health())
    assert "SSD /mnt/storage не смонтирован" in result
    assert called == []
