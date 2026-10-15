#!/usr/bin/env python3
"""OPS-2 — HDD-guard: защита /mnt/hdd2tb от повторения инцидента 13-14.10.2026.

Инцидент: два параллельных обхода внешней библиотеки Immich повесили `ntfs-3g`
на /mnt/hdd2tb. Сторож контейнеров (OPS-1,
nas_jetson_nano-container-watchdog.py) увидел Nextcloud `unhealthy` и сделал
`docker restart` — контейнер держал bind на мёртвом монтировании и не
поднялся, Nextcloud лежал 10 часов.

Вынесено в отдельный модуль (круг ревью 1, 2026-10-15): вся эта логика в
самом файле сторожа раздувала его LOC и число `except` сверх допуска
храповика метрик (`docs/audit/2026-10-02_code_audit/baseline.json`, R2 —
не более +10% LOC и без новых `except` в уже некосметическом файле). Как
отдельный новый модуль он подчиняется только R3 (новая функция: CC<=10,
LOC<=40) — обоснованно, у него нет истории в baseline.

Загружается сторожем так же, как сторож сам загружает
nas_jetson_nano-boot-alert.py — через importlib.util.spec_from_file_location
(имя файла с дефисами не годится для обычного `import`; здесь дефисов нет,
но способ подключения оставлен тем же для единообразия).

Python 3.6 (хост Jetson), только stdlib.
"""
import os
import subprocess
import time

HDD_MOUNT = "/mnt/hdd2tb"
HDD_PROBE_TIMEOUT = 10
HDD_DISKSTATS_WINDOW = 5
HDD_ALERT_COOLDOWN = 3600
HDD_RECOVER_HINT = "scripts/storage/hdd_hang_recover.sh"


def holds_hdd(container, mount=HDD_MOUNT):
    """True, если у контейнера есть bind-источник mount или подкаталог под ним:
    такой контейнер нельзя start/restart-ить на мёртвом fuseblk."""
    prefix = mount.rstrip("/") + "/"
    for src in container.get("mounts", []):
        if src == mount or src.startswith(prefix):
            return True
    return False


def _mount_device(mount, mounts_path):
    """Устройство-источник точки mount по /proc/mounts (не по хардкоженной
    букве/имени — источник берётся из реальной таблицы монтирования), либо
    None, если точка не смонтирована вовсе."""
    try:
        with open(mounts_path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == mount:
                    return os.path.basename(parts[0])
    except OSError:
        return None
    return None


def _diskstats_snapshot(dev, diskstats_path):
    """Четвёрка счётчиков операций (reads/sectors_read/writes/sectors_written)
    устройства dev из /proc/diskstats, либо None, если устройство не нашлось."""
    try:
        with open(diskstats_path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) > 9 and parts[2] == dev:
                    return (parts[3], parts[5], parts[7], parts[9])
    except OSError:
        return None
    return None


def _diskstats_changed(dev, window, diskstats_path, sleep):
    """Корректировка «stat не ответил» → «диск жив, просто медленный»: если
    счётчики операций устройства меняются за window секунд, это не
    зависание. Устройство не нашли в /proc/diskstats — подтвердить
    активность нечем, считаем это НЕ подтверждением (осторожный вариант)."""
    before = _diskstats_snapshot(dev, diskstats_path)
    sleep(window)
    after = _diskstats_snapshot(dev, diskstats_path)
    if before is None or after is None:
        return False
    return before != after


def hdd_probe(mount=HDD_MOUNT, timeout=HDD_PROBE_TIMEOUT, run=subprocess.run,
             mounts_path="/proc/mounts", diskstats_path="/proc/diskstats",
             diskstats_window=HDD_DISKSTATS_WINDOW, sleep=time.sleep):
    """"absent" — точки нет в /proc/mounts; "ok" — `stat -f` ответил, ИЛИ не
    ответил, но счётчики диска за diskstats_window секунд меняются (диск
    живой, просто медленный); "hung" — не ответил И счётчики не меняются.

    Проба — только в дочернем процессе (`timeout` снаружи и собственный
    timeout= у subprocess.run — двойная страховка). Если сам `stat` застрял
    в непрерываемом D-state внутри ядра на мёртвом fuseblk, ни SIGTERM от
    `timeout`, ни что-либо ещё его не снимет — osiротевший процесс останется
    висеть до тех пор, пока не освободится само монтирование (kill ntfs-3g +
    umount -l в hdd_hang_recover.sh); дожидаться его здесь не нужно и
    опасно — subprocess.run(timeout=) вернёт управление вызывающему коду
    независимо от судьбы ребёнка."""
    dev = _mount_device(mount, mounts_path)
    if dev is None:
        return "absent"
    try:
        r = run(["timeout", str(timeout), "stat", "-f", mount],
               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
               universal_newlines=True, timeout=timeout + 5)
    except Exception:
        r = None
    if r is not None and r.returncode == 0:
        return "ok"
    if _diskstats_changed(dev, diskstats_window, diskstats_path, sleep):
        return "ok"
    return "hung"


def hdd_alert_text(status):
    where = "не смонтирован" if status == "absent" else "не отвечает"
    return ("⛔ HDD %s %s — держателей не перезапускаю; восстановление вручную: %s"
            % (HDD_MOUNT, where, HDD_RECOVER_HINT))


def hdd_status_note(state, status, now, cooldown=HDD_ALERT_COOLDOWN):
    """Решает, нужен ли алерт о состоянии /mnt/hdd2tb, и обновляет state["_hdd"].
    Проблема репортится не чаще раза в cooldown секунд; восстановление после
    проблемы — всегда одним алертом сразу, без ожидания cooldown."""
    prev = state.get("_hdd") or {}
    prev_status, last_alert = prev.get("status", "ok"), prev.get("last_alert", 0)
    if status == "ok":
        state["_hdd"] = {"status": "ok", "last_alert": last_alert}
        if prev_status != "ok":
            return "✅ HDD %s снова отвечает" % HDD_MOUNT
        return None
    if prev_status == "ok" or now - last_alert >= cooldown:
        state["_hdd"] = {"status": status, "last_alert": now}
        return hdd_alert_text(status)
    state["_hdd"] = {"status": status, "last_alert": last_alert}
    return None
