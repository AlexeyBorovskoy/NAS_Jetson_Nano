"""Безопасные адаптеры алертов OBS-1 для D2 и OPS-1 (Python 3.6)."""
import json
import os
import subprocess

WHY_TIMEOUT = 60
SYSTEMCTL_TIMEOUT = 5
HEARTBEAT_MAX_AGE = 120
HEARTBEAT_ALERT_COOLDOWN = 3600
BLACKBOX_UNIT = "nas_jetson_nano-blackbox"
DEFAULT_SSD_ROOT = "/mnt/storage/blackbox"
DEFAULT_FALLBACK_ROOT = "/var/lib/nas-blackbox/fallback"


def run_nas_why(run=None, command="nas-why"):
    """Возвращает короткую диагностику либо None; stderr никогда не раскрывается."""
    runner = run or subprocess.run
    try:
        result = runner([command, "--boot", "-1", "--short"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True, timeout=WHY_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or "").strip()
    return text[:2500] or None


def append_nas_why(text, run=None, command="nas-why"):
    """Дополняет D2 только при успешном и непустом ответе nas-why."""
    diagnosis = run_nas_why(run=run, command=command)
    if not diagnosis:
        return text
    return text + "\n\nДиагностика чёрного ящика:\n" + diagnosis


def blackbox_service_active(run=None, systemctl="systemctl"):
    """Проверяет активность сервиса короткой приватной командой."""
    runner = run or subprocess.run
    try:
        result = runner([systemctl, "is-active", BLACKBOX_UNIT],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True, timeout=SYSTEMCTL_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and (result.stdout or "").strip() == "active"


def read_heartbeat(path):
    """Читает только переданный SSD/fallback heartbeat; повреждение = unknown."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            text = stream.read(4097)
        if len(text) > 4096:
            return None
        data = json.loads(text)
    except (OSError, ValueError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None


def _valid_heartbeat(data, now, boot_id):
    if not isinstance(data, dict):
        return False
    stamp = data.get("ts")
    if isinstance(stamp, bool) or not isinstance(stamp, int) or not 0 <= stamp <= now:
        return False
    recorded_boot = data.get("boot_id")
    if boot_id and recorded_boot != boot_id:
        return False
    return True


def newest_heartbeat(ssd_root, fallback_root, now, boot_id=None,
                     read_json=None):
    """Выбирает самый новый валидный heartbeat только из SSD и fallback."""
    reader = read_json or read_heartbeat
    candidates = []
    for source, root in (("ssd", ssd_root), ("fallback", fallback_root)):
        data = reader(os.path.join(root, "heartbeat"))
        if _valid_heartbeat(data, now, boot_id):
            candidates.append((data["ts"], source, data))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])


def heartbeat_status(ssd_root, fallback_root, now, boot_id=None,
                     max_age=HEARTBEAT_MAX_AGE, read_json=None):
    """Возвращает fresh/stale/unknown и выбранный источник."""
    latest = newest_heartbeat(ssd_root, fallback_root, now, boot_id, read_json)
    if latest is None:
        return "unknown", None
    age = now - latest[0]
    if age > max_age:
        return "stale", latest[1]
    return "fresh", latest[1]


def _cooldown_expired(state, now, cooldown):
    previous = state.get("_blackbox")
    if previous is not None and not isinstance(previous, dict):
        return False
    previous = previous or {}
    last_alert = previous.get("last_alert", 0)
    if isinstance(last_alert, bool) or not isinstance(last_alert, int):
        return False
    if not last_alert:
        return True
    return now >= last_alert + cooldown


def blackbox_heartbeat_note(state, now, ssd_root=DEFAULT_SSD_ROOT,
                            fallback_root=DEFAULT_FALLBACK_ROOT, boot_id=None,
                            service_active=False, read_json=None,
                            cooldown=HEARTBEAT_ALERT_COOLDOWN):
    """Формирует не чаще раза в час один алерт при доказанно старом heartbeat."""
    if not service_active:
        return None
    status, source = heartbeat_status(ssd_root, fallback_root, now, boot_id,
                                      HEARTBEAT_MAX_AGE, read_json)
    if status != "stale":
        return None
    if not _cooldown_expired(state, now, cooldown):
        return None
    state["_blackbox"] = {"last_alert": now, "source": source}
    return "⚠️ чёрный ящик молчит: heartbeat старше %d с" % HEARTBEAT_MAX_AGE


def blackbox_heartbeat_notes(state, now, boot_id=None, run=None,
                             ssd_root=DEFAULT_SSD_ROOT,
                             fallback_root=DEFAULT_FALLBACK_ROOT,
                             read_json=None):
    """Заметка об устаревшем heartbeat или пустой список при неизвестности."""
    active = blackbox_service_active(run=run)
    note = blackbox_heartbeat_note(state, now, ssd_root, fallback_root,
                                   boot_id, active, read_json)
    return [note] if note else []
