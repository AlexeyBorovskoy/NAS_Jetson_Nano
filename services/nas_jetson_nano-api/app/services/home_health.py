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
import os
from pathlib import Path

from app import blocking
from app.config import settings
from app.routers import storage as storage_mod
from app.services import system_info, home_health_checks as checks

# ── «что сломалось?» (E3) ────────────────────────────────────────────────────────
# Владелец узнаёт о неполадках не от системы, а сам замечает — как 2026-09-20, когда
# завис HDD и вместе с ним лёг NAS API. Ответ обязан быть коротким (человек читает
# в Telegram, не сводку) и не должен виснуть сам: именно зависший ntfs-3g уронил API
# в тот раз, потому что обращение к мёртвой точке монтирования встало намертво.

HDD_ROOT = Path("/mnt/hdd2tb")
HDD_CHECK_TIMEOUT = 3.0
SYSTEMD_CHECK_TIMEOUT = 3.0
SYSTEMD_CLEANUP_TIMEOUT = 1.0
UNKNOWN_PREFIX = "не удалось проверить: "
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
        return UNKNOWN_PREFIX + "HDD /mnt/hdd2tb не отвечает (таймаут %.0fс)" % timeout
    if err:
        return UNKNOWN_PREFIX + "HDD /mnt/hdd2tb (ошибка чтения)"
    if not mounted:
        return "HDD /mnt/hdd2tb не смонтирован" + (" (%s)" % err if err else "")
    return None


async def _check_failed_units(timeout: float = SYSTEMD_CHECK_TIMEOUT) -> str | None:
    """None означает успешную проверку без аварийных юнитов; отказ — unknown."""
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "--failed", "--plain", "--no-legend",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except (FileNotFoundError, OSError, asyncio.TimeoutError):
        return UNKNOWN_PREFIX + "systemd (команда недоступна или не отвечает)"
    finally:
        await checks.reap_process(proc, SYSTEMD_CLEANUP_TIMEOUT)
    if proc.returncode != 0:
        return UNKNOWN_PREFIX + "systemd (команда завершилась с ошибкой)"
    names = [line.split()[0] for line in stdout.decode().splitlines() if line.strip()]
    if names:
        return "systemd: аварийные юниты — %s" % ", ".join(names)
    return None


def _read_active_alerts() -> list[str] | None:
    return checks.read_active_alerts(settings.talk_alert_state_file)


def _categorize_problem(result: str | None, problems: list[str], unknown: list[str]) -> None:
    """Раскладывает результат одной проверки в `problems` или `unknown`.

    Вынесено из `build_health` под храповик метрик (docs/audit/2026-10-02_code_audit/
    PLAN.ru.md): пустой результат — неполадки нет, строка с `UNKNOWN_PREFIX` — сама
    проверка не удалась, остальное — настоящая неполадка. Поведение не менялось.
    """
    if not result:
        return
    if result.startswith(UNKNOWN_PREFIX):
        unknown.append(result[len(UNKNOWN_PREFIX):])
    else:
        problems.append(result)


async def _backup_section_details() -> list[str]:
    """Строки «база — возраст, размер» для раздела о дампах; пустой список — раздела нет.

    Вынесено из `build_health` под храповик метрик. Порядок короткого замыкания
    прежний: `disk_info` вызывается, только если задан `BACKUP_METADATA_FILE`,
    `backup_info` — только если SSD смонтирован.
    """
    if (not os.environ.get('BACKUP_METADATA_FILE')
            or not (await storage_mod.disk_info(storage_mod.STORAGE_ROOT)).get('mounted')):
        return []
    backups = await storage_mod.backup_info()
    if not (backups.get('available') and backups.get('source') == 'host-metadata'):
        return []
    return ["%s — %sч назад, %s МБ" % (d['db'], d['age_hours'], d['size_mb'])
           for d in backups['dumps'] if d.get('age_hours') is not None]


async def build_health() -> str:
    """Короткий человеческий ответ: что не в порядке, или одна строка, если всё
    хорошо. Каждая проверка — best-effort и не роняет остальные."""
    problems, unknown = await checks.container_problems(
        system_info, settings.expected_containers)

    disk_problems, disk_unknown = await checks.storage_problems(
        storage_mod, DISK_WARN_PCT, DUMP_MAX_AGE_HOURS)
    problems.extend(disk_problems)
    unknown.extend(disk_unknown)

    _categorize_problem(await _check_hdd_mount(), problems, unknown)
    _categorize_problem(await _check_failed_units(), problems, unknown)

    alerts = _read_active_alerts()
    if alerts is None:
        unknown.append("снимок алертов (нет файла или некорректные данные)")
    else:
        problems.extend(alerts)

    if not problems and not unknown:
        return "✅ Дома всё в порядке — контейнеры, диски и бэкапы штатно."
    seen = dict.fromkeys(problems)  # без повторов (алерт может дублировать прямую проверку), порядок сохранён
    sections = []
    if seen:
        sections.append("⚠️ Не в порядке:\n" + "\n".join("- %s" % p for p in seen))
    if unknown:
        sections.append("❔ Не удалось проверить:\n" + "\n".join("- %s" % p for p in dict.fromkeys(unknown)))
    details = await _backup_section_details()
    if details:
        sections.append("📦 Дампы БД (наличие и возраст):\n" + "\n".join('- ' + d for d in details))
    return "\n\n".join(sections)
