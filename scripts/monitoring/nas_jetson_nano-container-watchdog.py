#!/usr/bin/env python3
"""OPS-1 — сторож контейнеров: поднимает то, что Docker сам не поднимет.

ЗАЧЕМ. `restart: always` не перезапускает контейнер после `docker kill`/`stop`
(Docker считает это ручной остановкой) и никак не реагирует на `unhealthy` —
это только статус. Проверено живым тестом 2026-09-26: aria2 после `docker kill`
134 с оставался `Exited (137)`, пока его не подняли руками (аудит, OPS-1).

ЧТО ДЕЛАЕТ. Раз в 2 минуты (таймер) для контейнеров `homecloud_*` с политикой
`always`: остановлен/создан/мёртв — `docker start`; работает, но `unhealthy` —
`docker restart`, не чаще раза в 15 минут. Не больше 6 действий на контейнер
в час — дальше только алерт: бесконечный цикл рестартов хуже честной тревоги.
Контейнеры с другой политикой не трогает — их остановили намеренно.

РУЧНОЕ ОБСЛУЖИВАНИЕ. Файл `/etc/nas-watchdog.pause` ставит на паузу весь сторож.
Файл `/etc/nas-watchdog.pause.d/<container>` или Docker label
`nas.watchdog.maintenance=true` исключает только указанный контейнер.

Алерт владельцу — тем же каналом, что D2 (boot-alert): Telegram через SOCKS.
Не доставился — не страшно: действие уже выполнено и записано в journal.
Python 3.6 (хост Jetson).

OPS-2 (инцидент 13-14.10.2026, CLAUDE.md «Грабли»): два параллельных обхода
внешней библиотеки Immich повесили `ntfs-3g` на /mnt/hdd2tb. Сторож увидел
Nextcloud `unhealthy` и сделал `docker restart` — контейнер держал bind на
мёртвом монтировании и не поднялся, Nextcloud лежал 10 часов. Теперь перед
любым действием сторож один раз пробует /mnt/hdd2tb и, если точка не отвечает
или не смонтирована, НЕ трогает контейнеры-держатели (с bind-монтированием
из /mnt/hdd2tb) и шлёт отдельный алерт с подсказкой на
scripts/storage/hdd_hang_recover.sh — восстановление делает человек руками.
Сама проба и решение об алерте — в scripts/monitoring/hdd_guard.py (круг
ревью 1, 2026-10-15: вынесено отдельным модулем, иначе LOC и число `except`
этого файла выходили за допуск храповика метрик, docs/audit/2026-10-02_code_audit).
"""
import importlib.util
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
PREFIX = "homecloud_"
PAUSE_FILE = "/etc/nas-watchdog.pause"
PAUSE_DIR = "/etc/nas-watchdog.pause.d"
START_COOLDOWN = 120
UNHEALTHY_COOLDOWN = 900
MAX_ACTIONS_PER_HOUR = 6


def _load_module(name, filename):
    """Подключает соседний файл как модуль (имена с дефисами не годятся для
    обычного `import`) — общий код для _load_boot_alert/_load_hdd_guard."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_boot_alert():
    return _load_module("boot_alert", "nas_jetson_nano-boot-alert.py")


def _load_hdd_guard():
    return _load_module("hdd_guard", "hdd_guard.py")


def docker(*args, timeout=120):
    return subprocess.run(["docker"] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)


def list_containers():
    names = docker("ps", "-a", "--filter", "name=^" + PREFIX, "--format", "{{.Names}}").stdout.split()
    if not names:
        return []
    raw = docker("inspect", *names).stdout
    out = []
    for c in json.loads(raw or "[]"):
        health = ((c.get("State") or {}).get("Health") or {}).get("Status", "")
        labels = (c.get("Config") or {}).get("Labels") or {}
        mounts = [m.get("Source", "") for m in (c.get("Mounts") or []) if m.get("Type") == "bind" and m.get("Source")]
        out.append({"name": c["Name"].lstrip("/"),
                    "status": (c.get("State") or {}).get("Status", ""),
                    "health": health,
                    "policy": ((c.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name", ""),
                    "maintenance": str(labels.get("nas.watchdog.maintenance", "")).lower()
                    in ("1", "true", "yes", "on"),
                    "mounts": mounts})
    return out


def is_paused(c):
    """True when this container is explicitly in manual maintenance."""
    return c.get("maintenance", False) or os.path.exists(os.path.join(PAUSE_DIR, c["name"]))


def decide(c, history, now):
    """Действие для контейнера или None. history — список времён прошлых действий."""
    if c["policy"] != "always":
        return None
    recent = [t for t in history if now - t < 3600]
    last = max(history) if history else 0
    if c["status"] in ("exited", "created", "dead"):
        action, cooldown = "start", START_COOLDOWN
    elif c["status"] == "running" and c["health"] == "unhealthy":
        action, cooldown = "restart", UNHEALTHY_COOLDOWN
    else:
        return None
    if now - last < cooldown:
        return None
    if len(recent) >= MAX_ACTIONS_PER_HOUR:
        return "give_up"
    return action


def load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    os.replace(tmp, path)


def process_container(c, state, now, notes):
    """Применяет decide() к одному контейнеру: start/restart через docker или
    алерт give_up. Вынесено из main() отдельной функцией (OPS-2), чтобы HDD-
    проверка держателей в main() не разбухала вместе с этой веткой."""
    name = c["name"]
    hist = [t for t in state.get(name, []) if now - t < 86400]
    action = decide(c, hist, now)
    if action is None:
        state[name] = hist
        return
    if action == "give_up":
        if not state.get("_gave_up_" + name):
            notes.append("⛔ %s: %s, уже %d попыток за час — больше не трогаю, нужен человек" % (
                name, c["status"] + ("/" + c["health"] if c["health"] else ""), MAX_ACTIONS_PER_HOUR))
            state["_gave_up_" + name] = now
        state[name] = hist
        return
    r = docker(action, name)
    hist.append(now)
    state[name] = hist
    state.pop("_gave_up_" + name, None)
    ok = r.returncode == 0
    line = "%s %s: был %s%s → docker %s %s" % ("🔁" if ok else "❌", name, c["status"],
        "/" + c["health"] if c["health"] else "", action, "OK" if ok else "ОШИБКА: " + r.stderr.strip()[:200])
    print("watchdog: " + line)
    notes.append(line)


def main():
    if os.path.exists(PAUSE_FILE):
        print("watchdog: пауза (%s) — ничего не трогаю" % PAUSE_FILE)
        return 0
    ba = _load_boot_alert()
    hg = _load_hdd_guard()
    state_file = os.path.join(ba.LAYOUT["NAS_STATE_DIR"], "container-watchdog.json")
    state = load_state(state_file)
    now = int(time.time())
    notes = []
    hdd_status = hg.hdd_probe()
    hdd_note = hg.hdd_status_note(state, hdd_status, now)
    if hdd_note:
        notes.append(hdd_note)
    for c in list_containers():
        if is_paused(c):
            print("watchdog: обслуживание %s — пропускаю" % c["name"])
            continue
        if hdd_status != "ok" and hg.holds_hdd(c):
            print("watchdog: %s держит /mnt/hdd2tb (%s) — не трогаю" % (c["name"], hdd_status))
            continue
        process_container(c, state, now, notes)
    save_state(state_file, state)
    if notes:
        token = ba.read_env(ba.ENV_FILE, "TELEGRAM_BOT_TOKEN")
        owner = ba.read_env(ba.ENV_FILE, "TELEGRAM_OWNER_LOGIN", "admin")
        chat_id = ba.resolve_owner_chat_id(ba.read_env(ba.ENV_FILE, "TELEGRAM_USERS", ""), owner)
        if token and chat_id:
            try:
                delivered, error = ba.send_with_retries(
                    token, chat_id, "🐕 Сторож контейнеров Jetson:\n" + "\n".join(notes),
                    proxy=ba.read_env(ba.ENV_FILE, "TELEGRAM_PROXY") or None, attempts=2, delay_sec=5)
                if not delivered:
                    sys.stderr.write("watchdog: алерт не доставлен: %s\n" % (error or "unknown error"))
                else:
                    print("watchdog: алерт доставлен")
            except Exception as exc:  # доставка — не главное, действие уже сделано
                sys.stderr.write("watchdog: алерт не доставлен: %s\n" % type(exc).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
