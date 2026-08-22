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
import re
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


SWAP_WARN_PERCENT = 85


def check_swap():
    """Подкачка живёт в ОЗУ (zram), и когда она кончается — следующая остановка OOM.

    Проверять именно заполнение, а не факт использования: подкачка на zram
    используется ПОСТОЯННО и это нормально. Замер 2026-08-22: занято 33 %,
    трафик swap-in около 6 МБ/час — то есть механизм работает тихо и правильно.
    Тревога нужна на исчерпание, а не на работу.
    """
    total = free = None
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("SwapTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("SwapFree:"):
                    free = int(line.split()[1])
    except OSError as exc:
        return "swap", "🟠 Не прочитать /proc/meminfo: %s" % exc

    if not total:
        return "swap", "🟠 Подкачка отсутствует — zram не поднялся."

    used_pct = (total - free) * 100 // total
    if used_pct >= SWAP_WARN_PERCENT:
        return "swap", ("🔴 Подкачка (zram) заполнена на %d%% — %d из %d МБ. "
                        "Дальше начнутся снятия процессов по памяти."
                        % (used_pct, (total - free) // 1024, total // 1024))
    return "swap", None


HDD_DEV = "/dev/sdb"
HDD_FATAL_ATTRS = ("Reallocated_Sector_Ct", "Current_Pending_Sector", "Offline_Uncorrectable")
HDD_TEMP_MAX = 50


def check_hdd_smart():
    """SMART на 2-ТБ HDD ЕСТЬ — вопреки допущению, записанному в проекте.

    Проверено 2026-08-22: мост RTL9201 (0bda:9201) пропускает SAT-команды, и
    `smartctl -d sat` читает полную таблицу атрибутов. Невозможен SMART только на
    USB-SSD за мостом JMS583 — там квирк действительно закрывает passthrough.
    Раньше запрет распространяли на оба диска; для HDD это было неверно.

    Диск не будим: `-n standby` возвращает управление, если он спит.
    """
    try:
        out = subprocess.run(["smartctl", "-H", "-A", "-l", "selftest",
                              "-n", "standby", "-d", "sat", HDD_DEV],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True, timeout=60).stdout
    except Exception as exc:
        return "hdd_smart", "🟠 SMART на %s не прочитан: %s" % (HDD_DEV, exc)

    if "STANDBY" in out.upper():
        return "hdd_smart", None

    verdict = re.search(r"SMART overall-health.*?:\s*(\S+)", out)
    if not verdict:
        return "hdd_smart", ("🟠 SMART на %s не отвечает — проверьте мост или кабель."
                             % HDD_DEV)

    problems = []
    if verdict.group(1).upper() != "PASSED":
        problems.append("вердикт SMART: %s" % verdict.group(1))

    for name in HDD_FATAL_ATTRS:
        m = re.search(r"^\s*\d+\s+%s\s+\S+\s+\d+\s+\d+\s+\d+\s+\S+\s+\S+\s+\S+\s+(\d+)"
                      % name, out, re.M)
        if m and int(m.group(1)) > 0:
            problems.append("%s = %s" % (name, m.group(1)))

    t = re.search(r"^\s*194\s+Temperature_Celsius\s+\S+\s+\d+\s+\d+\s+\d+\s+\S+\s+\S+\s+\S+\s+(\d+)",
                  out, re.M)
    if t and int(t.group(1)) > HDD_TEMP_MAX:
        problems.append("температура %s °C" % t.group(1))

    # Самый свежий самотест: строка «# 1» в журнале самотестов.
    #
    # ⚠️ Здесь была ловушка, на которую я наступил 2026-08-22: успешный статус звучит
    # как «Completed without error», и шаблон, искавший подстроку "error", объявлял
    # успешный тест отказом. Ложная тревога подрывает доверие к алертам быстрее, чем
    # их отсутствие. Поэтому: сначала явно признаём успех, и только потом ищем отказ,
    # причём по словам, которых в успешном статусе быть не может.
    st = re.search(r"^#\s*1\s+(.+?)\s{2,}(\S.*?)\s{2,}", out, re.M)
    if st:
        status = st.group(2).strip()
        ok = status.lower().startswith("completed without error")
        if not ok and re.search(r"fail|fatal|abort|interrupt|unknown", status, re.I):
            problems.append("последний самотест: %s" % status)

    if problems:
        return "hdd_smart", "🔴 HDD 2 ТБ (семейный архив): " + "; ".join(problems)
    return "hdd_smart", None


CHECKS = (check_dumps, check_storage, check_containers, check_disk, check_ram,
          check_swap, check_hdd_smart)


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
                    "swap": "подкачка zram",
                    "hdd_smart": "SMART диска с семейным архивом",
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
