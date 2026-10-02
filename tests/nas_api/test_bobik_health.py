"""E3: «бобик, что сломалось?» — сборка ответа (app/services/home_health.py).

Ключевой сценарий — инцидент 2026-09-20: зависший ntfs-3g на /mnt/hdd2tb сделал
обращение к точке монтирования блокирующим навсегда и уронил весь API. Проверка
HDD обязана возвращать ответ за отведённый таймаут, а не виснуть вместе с диском.

CQ-02 (аудит 2026-10-02): весь блок `_build_health`/`_check_hdd_mount`/
`_hdd_mount_probe`/`_check_failed_units`/`_read_active_alerts` переехал из
`app/routers/talk_bot.py` в `app/services/home_health.py` — он использовался
только Telegram-ботом, который раньше звал его как приватную функцию чужого
роутера. `_build_photos` остался в `talk_bot.py` (его зовёт сам Talk-бот), но
теперь ходит за статистикой Immich через `app.services.immich` вместо приватной
`photos_mod._immich_get`.

Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def _reset_app_modules():
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


def load_bot():
    _reset_app_modules()
    return importlib.import_module("app.routers.talk_bot")


def load_health():
    """app/services/home_health.py — сюда переехал весь блок E3 (CQ-02)."""
    _reset_app_modules()
    return importlib.import_module("app.services.home_health")


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
    health = load_health()

    def hang():
        time.sleep(1.5)  # имитация зависшего ntfs-3g (D-state) короче, чем нужно для теста
        return True, ""

    monkeypatch.setattr(health, "_hdd_mount_probe", hang)
    loop = asyncio.new_event_loop()
    try:
        start = time.monotonic()
        result = loop.run_until_complete(health._check_hdd_mount(timeout=0.1))
        elapsed = time.monotonic() - start
    finally:
        loop.close()
    assert elapsed < 1.0, "проверка HDD не должна ждать зависший диск"
    assert result is not None and "не отвечает" in result


def test_hdd_check_shares_blocking_key_on_repeated_calls(monkeypatch):
    """CQ-01 (аудит 2026-10-02): раньше каждый вопрос «что сломалось?» заводил свой
    `asyncio.to_thread(_hdd_mount_probe)` — на зависшем ntfs-3g поток оставался висеть
    навсегда, и примерно через 8 вопросов исчерпывал пул потоков, общий с
    `app/blocking.py` (API-1), после чего ломалась защита таймаутом у /storage и
    /system. Проверка обязана идти через `blocking.run_io("hdd2tb_mount", ...)`:
    на висящий диск заводится только один поток, остальные обращения ждут его же
    future и так же упираются в таймаут — новый поток не плодится."""
    health = load_health()

    event = threading.Event()
    calls = {"n": 0}

    def hang():
        calls["n"] += 1
        event.wait(30)  # страховка от вечного зависания прогона
        return True, ""

    monkeypatch.setattr(health, "_hdd_mount_probe", hang)

    async def main():
        results = []
        for _ in range(10):
            results.append(await health._check_hdd_mount(timeout=0.05))
        event.set()
        await asyncio.sleep(0.05)  # поток возвращается, пока цикл ещё жив
        return results

    results = asyncio.run(main())
    assert len(results) == 10
    assert all(r is not None and "не отвечает" in r for r in results), results
    assert calls["n"] == 1, "probe вызван %d раз(а) — поток заводится на каждый вызов" % calls["n"]


def test_hdd_check_reports_not_mounted():
    health = load_health()
    orig = health._hdd_mount_probe
    try:
        health._hdd_mount_probe = lambda: (False, "")
        result = asyncio.run(health._check_hdd_mount(timeout=1))
        assert result is not None and "не смонтирован" in result
    finally:
        health._hdd_mount_probe = orig


def test_hdd_check_ok_when_mounted():
    health = load_health()
    orig = health._hdd_mount_probe
    try:
        health._hdd_mount_probe = lambda: (True, "")
        result = asyncio.run(health._check_hdd_mount(timeout=1))
        assert result is None
    finally:
        health._hdd_mount_probe = orig


# ── алерты Phase E: читаем снимок, не пересчитываем ─────────────────────────────

def test_read_active_alerts_parses_state_file():
    health = load_health()
    tmp = tempfile.mkdtemp()
    state_file = os.path.join(tmp, "state.json")
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump({
            "dumps": {"active": True, "text": "🔴 бэкапы устарели"},
            "ram": {"active": False, "text": "🟠 мало памяти"},
            "disk": {"active": True, "text": ""},  # без текста — пропускается
        }, fh)
    health.settings.talk_alert_state_file = state_file
    assert health._read_active_alerts() == ["🔴 бэкапы устарели"]


def test_read_active_alerts_missing_file_is_not_an_alarm():
    health = load_health()
    health.settings.talk_alert_state_file = "/no/such/file-e3-test.json"
    assert health._read_active_alerts() == []


def test_read_active_alerts_corrupt_file_is_not_an_alarm():
    health = load_health()
    tmp = tempfile.mkdtemp()
    state_file = os.path.join(tmp, "broken.json")
    with open(state_file, "w", encoding="utf-8") as fh:
        fh.write("{не json")
    health.settings.talk_alert_state_file = state_file
    assert health._read_active_alerts() == []


# ── systemd: best-effort, недоступность — не тревога ────────────────────────────

def test_failed_units_check_survives_missing_binary(monkeypatch):
    health = load_health()

    async def boom(*a, **k):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(health.asyncio, "create_subprocess_exec", boom)
    result = asyncio.run(health._check_failed_units(timeout=1))
    assert result is None


# ── сборка ответа ─────────────────────────────────────────────────────────────

def test_build_health_all_clear(monkeypatch):
    health = load_health()
    monkeypatch.setattr(health.system_info, "docker_ps_json", _async([]))
    monkeypatch.setattr(health.storage_mod, "_disk_info", lambda p: {"mounted": True, "used_pct": 12})
    monkeypatch.setattr(health.storage_mod, "_backup_info", lambda: {"available": True, "dumps": [
        {"db": "nextcloud", "age_hours": 3}, {"db": "immich", "age_hours": 4}]})
    monkeypatch.setattr(health, "_check_hdd_mount", _async(None))
    monkeypatch.setattr(health, "_check_failed_units", _async(None))
    monkeypatch.setattr(health, "_read_active_alerts", lambda: [])
    result = asyncio.run(health.build_health())
    assert result == "✅ Дома всё в порядке — контейнеры, диски и бэкапы штатно."


def test_build_health_lists_every_kind_of_problem_once(monkeypatch):
    health = load_health()
    health.settings.expected_containers = "homecloud_nextcloud"
    monkeypatch.setattr(health.system_info, "docker_ps_json",
                        _async([{"name": "homecloud_nextcloud", "state": "exited"}]))
    monkeypatch.setattr(health.storage_mod, "_disk_info", lambda p: {"mounted": True, "used_pct": 95})
    monkeypatch.setattr(health.storage_mod, "_backup_info", lambda: {"available": True, "dumps": [
        {"db": "nextcloud", "age_hours": None}]})
    monkeypatch.setattr(health, "_check_hdd_mount", _async("HDD /mnt/hdd2tb не смонтирован"))
    monkeypatch.setattr(health, "_check_failed_units", _async("systemd: аварийные юниты — foo.service"))
    monkeypatch.setattr(health, "_read_active_alerts", lambda: ["🟠 квота GigaChat кончается"])
    result = asyncio.run(health.build_health())
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
    health = load_health()
    monkeypatch.setattr(health.system_info, "docker_ps_json", _async([]))
    monkeypatch.setattr(health.storage_mod, "_disk_info", lambda p: {"mounted": False})
    called = []
    monkeypatch.setattr(health.storage_mod, "_backup_info", lambda: called.append(1))
    monkeypatch.setattr(health, "_check_hdd_mount", _async(None))
    monkeypatch.setattr(health, "_check_failed_units", _async(None))
    monkeypatch.setattr(health, "_read_active_alerts", lambda: [])
    result = asyncio.run(health.build_health())
    assert "SSD /mnt/storage не смонтирован" in result
    assert called == []


# ── фото Immich: отказ не должен быть немым ─────────────────────────────────────

def test_build_photos_logs_failure_type_without_changing_the_reply(monkeypatch, caplog):
    """CQ-07 (аудит 2026-10-02): молчаливый `except Exception: return "...Недоступен..."`
    прятал причину (сеть? ключ? URL?) даже из журнала. Добавлен `log.warning` с ТИПОМ
    исключения — без текста, чтобы в журнал не утёк ключ/URL из сообщения об ошибке.
    Ответ владельцу не меняется. `_build_photos` остался в talk_bot.py (CQ-02) и
    теперь ходит через app.services.immich вместо приватной photos_mod._immich_get."""
    bot = load_bot()

    async def boom(path):
        raise RuntimeError("http://192.168.0.50:2283/api/server/statistics?key=secret")

    monkeypatch.setattr(bot.immich, "immich_get", boom)
    with caplog.at_level(logging.WARNING):
        result = asyncio.run(bot._build_photos())
    assert result == "📷 **Immich**\n- ⚠️ Недоступен или `IMMICH_API_KEY` не настроен."
    assert "RuntimeError" in caplog.text
    assert "secret" not in caplog.text
