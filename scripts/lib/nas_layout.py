"""NAS_Jetson_Nano — единая раскладка хоста (Python-двойник scripts/lib/layout.sh).

Правила разрешения обязаны совпадать с layout.sh — tests/unit/test_layout.py сверяет.
Совместимо с Python 3.6 (хост Jetson).

Порядок: явное окружение → файл /etc/nas-layout.env (KEY=VALUE) → автоопределение
(только старые каталоги `nasa-monitor` → префикс `nasa`) → целевые имена.
"""
import os
import re

_KEY = re.compile(r"^NAS_[A-Z_]+$")
_LIB_DIR = os.path.dirname(os.path.abspath(__file__))


def _read_layout_file(path):
    values = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.rstrip("\r\n").partition("=")
                if not sep or not _KEY.match(key):
                    continue
                if value.endswith('"'):
                    value = value[:-1]
                if value.startswith('"'):
                    value = value[1:]
                values[key] = value
    except OSError:
        pass
    return values


def resolve(env=None):
    """Return the layout as a dict of NAS_* strings."""
    env = os.environ if env is None else env
    root = env.get("NAS_LAYOUT_ROOT", "")
    lay = {k: v for k, v in env.items() if _KEY.match(k) and v}

    layout_file = env.get("NAS_LAYOUT_FILE") or root + "/etc/nas-layout.env"
    for k, v in _read_layout_file(layout_file).items():
        lay.setdefault(k, v)

    def isdir(p):
        return os.path.isdir(root + p)

    if not lay.get("NAS_PREFIX"):
        legacy = (not isdir("/etc/nas_jetson_nano-monitor")
                  and (isdir("/etc/nasa-monitor") or isdir("/var/log/nasa-monitor")))
        lay["NAS_PREFIX"] = "nasa" if legacy else "nas_jetson_nano"
    p = lay["NAS_PREFIX"]

    lay.setdefault("NAS_PROJECT_DIR", os.path.normpath(os.path.join(_LIB_DIR, "..", "..")))
    lay.setdefault("NAS_ENV_FILE", lay["NAS_PROJECT_DIR"] + "/config/.env")
    lay.setdefault("NAS_CONF_DIR", "/etc/%s-monitor" % p)
    lay.setdefault("NAS_LOG_DIR", "/var/log/%s-monitor" % p)
    lay.setdefault("NAS_STATE_DIR", "/var/lib/%s-monitor" % p)
    lay.setdefault("NAS_SBIN_PREFIX", "/usr/local/sbin/%s" % p)
    lay.setdefault("NAS_UNIT_PREFIX", p)
    lay.setdefault("NAS_OPT_DIR", "/opt/%s" % p)
    # Решение 2026-08-30: API-контейнер не переименовывается (конфликт порта 8099).
    lay.setdefault("NAS_API_CONTAINER", "homecloud_nasa_api")
    return lay
