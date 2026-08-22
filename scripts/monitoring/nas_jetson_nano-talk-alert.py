#!/usr/bin/env python3
"""Фаза E — системные алерты в семейный чат Nextcloud Talk.

Почему именно эти проверки: каждая соответствует отказу, который в этом проекте
уже случался.

  * дампы устарели   — 16 дней «успешных» юнитов без единого бэкапа (2026-07/08);
  * /mnt/storage     — отвал SSD, ради которого написано авто-восстановление;
  * контейнеры       — то, ради чего вообще существует мониторинг;
  * диск и память    — 4 ГБ на Nano, три контейнера у своих лимитов.

Два правила, без которых алерты перестают читать:

  1. Молчать, когда всё хорошо. Ежедневное «всё в порядке» перестают замечать
     ровно к тому дню, когда оно перестаёт быть правдой.
  2. Сообщать и о выздоровлении. Алерт без парного «снова в норме» оставляет
     человека гадать, починилось оно само или он просто перестал смотреть.

Повторно об одной и той же беде — не чаще раза в сутки.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ENV_FILE = "/home/admin/nas_jetson_nano/config/.env"
MONITOR_ENV = "/etc/nas_jetson_nano-monitor/nas_jetson_nano-monitor.env"
STATE_FILE = "/var/lib/nas_jetson_nano-monitor/talk-alert-state.json"
API = "http://127.0.0.1:8099"
DUMPS = "/mnt/storage/backups/database-dumps"

REPEAT_AFTER = 24 * 3600          # повтор об активной проблеме — раз в сутки
DUMP_MAX_AGE_HOURS = 26           # бэкап суточный; 26 ч даёт запас на сдвиг таймера


# ── чтение конфигурации ────────────────────────────────────────────────────────

def read_env(path, key, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return default


# ── проверки ───────────────────────────────────────────────────────────────────

def check_dumps():
    """Свежесть дампов проверяется файлами, а не статусом юнита. Именно на этом
    проект однажды потерял 16 дней бэкапов при «успешном» systemd."""
    try:
        names = [n for n in os.listdir(DUMPS) if n.endswith(".sql.gz")]
    except OSError:
        return "dumps", "🔴 Каталог бэкапов недоступен: " + DUMPS
    if not names:
        return "dumps", "🔴 В каталоге бэкапов нет ни одного дампа."
    newest = max(os.path.getmtime(os.path.join(DUMPS, n)) for n in names)
    age_h = (time.time() - newest) / 3600
    if age_h > DUMP_MAX_AGE_HOURS:
        return "dumps", ("🔴 Свежего бэкапа нет уже %d ч. Последний дамп: %s."
                         % (age_h, time.strftime("%d.%m %H:%M", time.localtime(newest))))
    return "dumps", None


def check_storage():
    ok = subprocess.run(["mountpoint", "-q", "/mnt/storage"]).returncode == 0
    if not ok:
        return "storage", "🔴 /mnt/storage не примонтирован — диск отвалился."
    return "storage", None


def check_containers():
    expected = (read_env(MONITOR_ENV, "EXPECTED_CONTAINERS", "") or "").split()
    if not expected:
        return "containers", None
    try:
        # На Jetson Python 3.6: ни capture_output, ни text= здесь нет.
        out = subprocess.run(["docker", "ps", "--format", "{{.Names}}"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True, timeout=30).stdout
    except Exception as exc:
        return "containers", "🔴 Не удалось опросить Docker: %s" % exc
    running = set(out.split())
    missing = [c for c in expected if c not in running]
    if missing:
        return "containers", ("🔴 Не работают контейнеры (%d): %s"
                              % (len(missing), ", ".join(missing)))
    return "containers", None


def check_disk():
    limit = int(read_env(MONITOR_ENV, "DISK_WARN_PERCENT", "80") or 80)
    bad = []
    for path in ("/", "/mnt/storage"):
        try:
            st = os.statvfs(path)
        except OSError:
            continue
        used = 100 - (st.f_bavail * 100 // st.f_blocks)
        if used >= limit:
            bad.append("%s — %d%%" % (path, used))
    if bad:
        return "disk", "🟠 Диск заполняется: " + "; ".join(bad)
    return "disk", None


def check_ram():
    limit = int(read_env(MONITOR_ENV, "RAM_WARN_MB", "300") or 300)
    avail = None
    with open("/proc/meminfo", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("MemAvailable:"):
                avail = int(line.split()[1]) // 1024
                break
    if avail is not None and avail < limit:
        return "ram", "🟠 Свободной памяти мало: %d МБ." % avail
    return "ram", None


CHECKS = (check_dumps, check_storage, check_containers, check_disk, check_ram)


# ── отправка ───────────────────────────────────────────────────────────────────

def send(text):
    user = read_env(ENV_FILE, "NEXTCLOUD_ADMIN_USER")
    password = read_env(ENV_FILE, "NEXTCLOUD_ADMIN_PASSWORD")
    if not user or not password:
        raise SystemExit("нет учётных данных в " + ENV_FILE)

    def post(url, payload, headers=None):
        hdr = {"Content-Type": "application/json"}
        hdr.update(headers or {})
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=hdr)
        return json.load(urllib.request.urlopen(req, timeout=25))

    token = post(API + "/api/auth/login",
                 {"username": user, "password": password})["access_token"]
    # Технические алерты идут в комнату владельца, а не в общий семейный чат:
    # «диск заполняется» — это не то, что должно будить пятерых человек.
    # Комната задаётся в nasa-monitor.env; без неё берётся умолчание API.
    room = read_env(MONITOR_ENV, "TALK_ALERT_ROOM") or None
    body = {"message": text}
    if room:
        body["room_token"] = room
    return post(API + "/v1/talk/notify", body, {"Authorization": "Bearer " + token})


# ── состояние ──────────────────────────────────────────────────────────────────

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def main():
    if "--test" in sys.argv:
        r = send("🧪 Проверка канала системных алертов. Это тест, делать ничего не нужно.")
        print("тестовое сообщение отправлено:", json.dumps(r, ensure_ascii=False))
        return 0

    state = load_state()
    now = time.time()
    sent = 0

    for check in CHECKS:
        key, problem = check()
        prev = state.get(key) or {}

        if problem:
            last = prev.get("last_sent", 0)
            if not prev.get("active") or now - last >= REPEAT_AFTER:
                send(problem)
                sent += 1
                last = now
            state[key] = {"active": True, "last_sent": last, "text": problem}
        else:
            if prev.get("active"):
                send("✅ Снова в норме: %s" % {
                    "dumps": "бэкапы делаются",
                    "storage": "/mnt/storage примонтирован",
                    "containers": "все контейнеры работают",
                    "disk": "место на диске",
                    "ram": "свободная память",
                }.get(key, key))
                sent += 1
            state[key] = {"active": False, "last_sent": prev.get("last_sent", 0)}

    save_state(state)
    active = [k for k, v in state.items() if v.get("active")]
    print("проверок: %d, активных проблем: %d %s, отправлено сообщений: %d"
          % (len(CHECKS), len(active), active or "", sent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
