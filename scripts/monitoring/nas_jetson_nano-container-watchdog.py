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

РУЧНОЕ ОБСЛУЖИВАНИЕ. Файл `/etc/nas-watchdog.pause` — сторож молчит и ничего
не трогает (например, на время миграции или починки ntfs-3g, где контейнеры
намеренно остановлены — см. «Грабли» в CLAUDE.md).

Алерт владельцу — тем же каналом, что D2 (boot-alert): Telegram через SOCKS.
Не доставился — не страшно: действие уже выполнено и записано в journal.
Python 3.6 (хост Jetson).
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
START_COOLDOWN = 120
UNHEALTHY_COOLDOWN = 900
MAX_ACTIONS_PER_HOUR = 6


def _load_boot_alert():
    spec = importlib.util.spec_from_file_location(
        "boot_alert", os.path.join(HERE, "nas_jetson_nano-boot-alert.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        out.append({"name": c["Name"].lstrip("/"),
                    "status": (c.get("State") or {}).get("Status", ""),
                    "health": health,
                    "policy": ((c.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name", "")})
    return out


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


def main():
    if os.path.exists(PAUSE_FILE):
        print("watchdog: пауза (%s) — ничего не трогаю" % PAUSE_FILE)
        return 0
    ba = _load_boot_alert()
    state_file = os.path.join(ba.LAYOUT["NAS_STATE_DIR"], "container-watchdog.json")
    state = load_state(state_file)
    now = int(time.time())
    notes = []
    for c in list_containers():
        hist = [t for t in state.get(c["name"], []) if now - t < 86400]
        action = decide(c, hist, now)
        if action is None:
            state[c["name"]] = hist
            continue
        if action == "give_up":
            if not state.get("_gave_up_" + c["name"]):
                notes.append("⛔ %s: %s, уже %d попыток за час — больше не трогаю, нужен человек"
                             % (c["name"], c["status"] + ("/" + c["health"] if c["health"] else ""),
                                MAX_ACTIONS_PER_HOUR))
                state["_gave_up_" + c["name"]] = now
            state[c["name"]] = hist
            continue
        r = docker(action, c["name"])
        hist.append(now)
        state[c["name"]] = hist
        state.pop("_gave_up_" + c["name"], None)
        ok = r.returncode == 0
        line = "%s %s: был %s%s → docker %s %s" % (
            "🔁" if ok else "❌", c["name"], c["status"],
            "/" + c["health"] if c["health"] else "", action, "OK" if ok else "ОШИБКА: " + r.stderr.strip()[:200])
        print("watchdog: " + line)
        notes.append(line)
    save_state(state_file, state)
    if notes:
        token = ba.read_env(ba.ENV_FILE, "TELEGRAM_BOT_TOKEN")
        chat_id = ba.resolve_owner_chat_id(ba.read_env(ba.ENV_FILE, "TELEGRAM_USERS", ""),
                                           ba.read_env(ba.ENV_FILE, "TELEGRAM_OWNER_LOGIN", "admin"))
        if token and chat_id:
            try:
                ba.send_with_retries(token, chat_id, "🐕 Сторож контейнеров Jetson:\n" + "\n".join(notes),
                                     proxy=ba.read_env(ba.ENV_FILE, "TELEGRAM_PROXY") or None,
                                     attempts=2, delay_sec=5)
            except Exception as exc:  # доставка — не главное, действие уже сделано
                sys.stderr.write("watchdog: алерт не доставлен: %s\n" % type(exc).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
