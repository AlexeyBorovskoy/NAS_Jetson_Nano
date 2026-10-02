"""
«Что сломалось?» (E3): собирает короткий отчёт о состоянии дома для Telegram-бота.

Вынесено из app/routers/talk_bot.py (CQ-02, docs/audit/2026-10-02_code_audit/REPORT.ru.md
§4, §6): `app/telegram_bot.py` звал `_build_health` как приватную функцию чужого
роутера через ленивый импорт `app.routers.talk_bot` — переименование внутри роутера
молча ломало бы ответ на «что сломалось?», а тесты роутера этого не видели. Весь блок
переехал целиком, потому что используется ТОЛЬКО этой функцией (Talk-бот её не
вызывает вовсе — только Telegram); внутренние хелперы остаются приватными внутри
модуля. Логика не менялась, только место и имя верхнего уровня (`build_health`, без
ведущего `_`).

⚠️ `storage_mod` (`app.routers.storage`) — сознательное исключение из правила «сервисы
не импортируют роутеры» (см. allowlist в tests/nas_api/test_layering.py): `disk_info`
и `backup_info` уже публичные функции, не были частью находки CQ-02, а перенос самого
`storage.py` в сервисный слой — отдельная, не начатая задача (вне рамок стадии 11,
docs/audit/2026-10-02_code_audit/PLAN.ru.md).
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from app import blocking
from app.config import settings
from app.routers import storage as storage_mod
from app.services import system_info

# ── «что сломалось?» (E3) ────────────────────────────────────────────────────────
# Владелец узнаёт о неполадках не от системы, а сам замечает — как 2026-09-20, когда
# завис HDD и вместе с ним лёг NAS API. Ответ обязан быть коротким (человек читает
# в Telegram, не сводку) и не должен виснуть сам: именно зависший ntfs-3g уронил API
# в тот раз, потому что обращение к мёртвой точке монтирования встало намертво.

HDD_ROOT = Path("/mnt/hdd2tb")
HDD_CHECK_TIMEOUT = 3.0
SYSTEMD_CHECK_TIMEOUT = 3.0
DISK_WARN_PCT = 90
DUMP_MAX_AGE_HOURS = 26  # тот же запас, что у scripts/monitoring/nas_jetson_nano-talk-alert.py


def _hdd_mount_probe() -> tuple[bool, str]:
    """Синхронная проверка — обязана вызываться только через `blocking.run_io` (см. ниже).

    Зависший ntfs-3g держит `os.stat()` в D-state сколько угодно; в event loop
    это остановило бы обработку любых других сообщений бота. Поток, оставшийся
    висеть навсегда после того, как вызывающий код отступился по таймауту, —
    меньшее зло по сравнению с остановкой всего API (инцидент 2026-09-20). Ключ
    `blocking.run_io` один на все вызовы — пока поток не вернулся, новый не
    заводится (CQ-01, аудит 2026-10-02): раньше каждый вопрос «что сломалось?»
    плодил свой навсегда висящий поток и через ~8 вопросов исчерпывал пул,
    общий с `app/blocking.py` (API-1), ломая защиту таймаутом у /storage и /system.
    """
    try:
        if not HDD_ROOT.exists():
            return False, ""
        mounted = os.stat(HDD_ROOT).st_dev != os.stat("/").st_dev
    except OSError as exc:
        return False, str(exc)
    return mounted, ""


async def _check_hdd_mount(timeout: float = HDD_CHECK_TIMEOUT) -> str | None:
    """None = смонтирован и здоров; иначе — короткая причина."""
    try:
        mounted, err = await blocking.run_io("hdd2tb_mount", _hdd_mount_probe, timeout=timeout)
    except asyncio.TimeoutError:
        return "HDD /mnt/hdd2tb не отвечает (таймаут %.0fс — похоже на зависший ntfs-3g)" % timeout
    if not mounted:
        return "HDD /mnt/hdd2tb не смонтирован" + (" (%s)" % err if err else "")
    return None


async def _check_failed_units(timeout: float = SYSTEMD_CHECK_TIMEOUT) -> str | None:
    """Лучшее, что можно сделать из контейнера API: внутри нет systemd/dbus, и в
    обычном деплое команды просто нет — тогда молчим, а не выдумываем ответ,
    вместо того чтобы объявлять «всё чисто» без проверки."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "--failed", "--plain", "--no-legend",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except (FileNotFoundError, OSError, asyncio.TimeoutError):
        return None
    names = [line.split()[0] for line in stdout.decode().splitlines() if line.strip()]
    if names:
        return "systemd: аварийные юниты — %s" % ", ".join(names)
    return None


def _read_active_alerts() -> list[str]:
    """Phase E (scripts/monitoring/nas_jetson_nano-talk-alert.py) уже проверяет то,
    что из контейнера API не проверить вовсе — SMART HDD, swap, off-site бэкап,
    квоты GigaChat, расходы Cloud.ru. Читаем готовый снимок, а не пересчитываем.
    Файла нет или он битый — не тревога, а «данных нет»: остальные проверки
    в этом модуле прямые и от этого файла не зависят."""
    try:
        with open(settings.talk_alert_state_file, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(state, dict):
        return []
    return [v.get("text") or key for key, v in state.items()
            if isinstance(v, dict) and v.get("active") and v.get("text")]


async def build_health() -> str:
    """Короткий человеческий ответ: что не в порядке, или одна строка, если всё
    хорошо. Каждая проверка — best-effort и не роняет остальные."""
    problems: list[str] = []

    try:
        expected = set(settings.expected_containers.split())
        containers = await system_info.docker_ps_json()
        down = [c.get("name", "") for c in containers
                if c.get("name") in expected and c.get("state", "").lower() != "running"]
        if down:
            problems.append("не работают контейнеры: %s" % ", ".join(down))
    except Exception as exc:
        problems.append("не смог проверить контейнеры (%s)" % exc)

    ssd = await storage_mod.disk_info(storage_mod.STORAGE_ROOT)
    if not ssd.get("mounted"):
        problems.append("SSD /mnt/storage не смонтирован")
    else:
        if ssd.get("used_pct", 0) >= DISK_WARN_PCT:
            problems.append("SSD почти заполнен — %s%%" % ssd["used_pct"])
        for d in (await storage_mod.backup_info()).get("dumps", []):
            age = d.get("age_hours")
            if age is None:
                problems.append("нет дампа %s" % d["db"])
            elif age > DUMP_MAX_AGE_HOURS:
                problems.append("бэкап %s устарел — %dч назад" % (d["db"], age))

    hdd_problem = await _check_hdd_mount()
    if hdd_problem:
        problems.append(hdd_problem)

    unit_problem = await _check_failed_units()
    if unit_problem:
        problems.append(unit_problem)

    problems.extend(_read_active_alerts())

    if not problems:
        return "✅ Дома всё в порядке — контейнеры, диски и бэкапы штатно."
    seen = dict.fromkeys(problems)  # без повторов (алерт может дублировать прямую проверку), порядок сохранён
    return "⚠️ Не в порядке:\n" + "\n".join("- %s" % p for p in seen)
