"""Конфигурация «чёрного ящика» (OBS-1, задача 1).

Значения по умолчанию, пороги вердиктов и пути — из раздела «Общие ограничения»
плана `docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md` и раздела 5
спецификации. Python 3.6: только стандартная библиотека, без f-строк с `=`,
без `dataclasses`, без `:=`.
"""
import json
import os

#: Путь к файлу конфигурации по умолчанию (переопределяется параметром `path`).
DEFAULT_CONFIG_PATH = "/etc/nas-blackbox.json"

#: Префикс переменных окружения: NAS_BLACKBOX_<ИМЯ_АТРИБУТА>.
ENV_PREFIX = "NAS_BLACKBOX_"


class Config(object):
    """Неизменяемый (по соглашению) набор путей и порогов «чёрного ящика».

    `Config(**overrides)` переопределяет любой известный атрибут; неизвестный
    ключ — `TypeError` (опечатка в конфиге не должна проходить молча).
    """

    #: Значения по умолчанию. Порядок и имена — дословно по плану задачи 1.
    DEFAULTS = {
        "ssd_mount": "/mnt/storage",
        "hdd_mount": "/mnt/hdd2tb",
        "sysfs_root": "/sys",
        "proc_root": "/proc",
        "dev_root": "/dev",
        "docker_sock": "/var/run/docker.sock",
        "docker_root": "/var/lib/docker",
        "ssd_root": "/mnt/storage/blackbox",
        "fallback_root": "/var/lib/nas-blackbox/fallback",
        "hdd_archive_root": "/mnt/hdd2tb/backups/blackbox",
        "family_containers": (
            "homecloud_nasa_api",
            "homecloud_llm_gateway",
            "homecloud_stt",
        ),
        "vin_low_mv": 4750,
        "mem_low_mb": 300,
        "mem_crit_mb": 150,
        "load_high": 6.0,
        "swap_growth_mb_min": 50,
        "disk_stall_s": 60,
        "hot_cap_bytes": 1 << 30,
        "fallback_cap_bytes": 20 << 20,
        "hot_min_days": 7,
        "hdd_retention_days": 365,
        "hdd_busy_units": (
            "nas_jetson_nano-immich-hdd-copy.service",
            "nas_jetson_nano-config-backup.service",
            "nasa-backup.service",
        ),
    }

    def __init__(self, **overrides):
        unknown = sorted(k for k in overrides if k not in self.DEFAULTS)
        if unknown:
            raise TypeError(
                "Config: неизвестные атрибуты: " + ", ".join(unknown)
            )
        for name, default in self.DEFAULTS.items():
            setattr(self, name, overrides.get(name, default))


def _read_config_file(path):
    """Содержимое JSON-файла конфигурации или `{}`, если файла нет.

    Отсутствие файла — штатный случай (значения по умолчанию), а не ошибка.
    """
    real_path = DEFAULT_CONFIG_PATH if path is None else path
    if not os.path.isfile(real_path):
        return {}
    with open(real_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _coerce_env_value(default, raw):
    """Строка из окружения -> тип значения по умолчанию атрибута."""
    if isinstance(default, bool):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default, int):
        return int(raw)
    if isinstance(default, float):
        return float(raw)
    if isinstance(default, tuple):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    return raw


def _apply_env_overrides(overrides, env):
    """Дописывает в `overrides` переменные NAS_BLACKBOX_<ИМЯ> из `env`.

    Порядок (план задачи 1): сначала JSON-файл, затем окружение — окружение
    побеждает, поэтому вызывается после чтения файла и перезаписывает ключи.
    """
    source = os.environ if env is None else env
    for name, default in Config.DEFAULTS.items():
        env_name = ENV_PREFIX + name.upper()
        if env_name in source:
            overrides[name] = _coerce_env_value(default, source[env_name])


def load_config(path=None, env=None):
    """Конфигурация: умолчания -> JSON-файл (`path` или `/etc/nas-blackbox.json`) -> окружение.

    `path=None` и отсутствующий файл — не ошибка, значения по умолчанию.
    `env=None` — читать настоящее окружение процесса (`os.environ`).
    """
    overrides = dict(_read_config_file(path))
    _apply_env_overrides(overrides, env)
    return Config(**overrides)
