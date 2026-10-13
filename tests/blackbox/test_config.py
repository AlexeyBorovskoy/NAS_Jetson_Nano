"""OBS-1, задача 1: конфигурация «чёрного ящика» (blackbox.config).

Покрытие — таблица «Случаи для тестов» задачи 1 плана
`docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md` (каждая строка — минимум один тест).
Пакет `services/blackbox` ещё не создан (TDD): до задачи-реализации тесты обязаны падать
на импорте (`ModuleNotFoundError: No module named 'blackbox'`), а не на утверждениях.

ОС не важна: подставных деревьев здесь нет, файл конфига — в `tmp_path`.
"""
import json

import pytest

from blackbox.config import Config, load_config

# Значения по умолчанию из раздела «Общие ограничения» плана.
DEFAULT_HOT_CAP_BYTES = 1073741824      # 1 << 30 — предел «горячего» на SSD
DEFAULT_FALLBACK_CAP_BYTES = 20971520   # 20 << 20 — запасной каталог на SD
FAMILY_CONTAINERS = ("homecloud_nasa_api", "homecloud_llm_gateway", "homecloud_stt")
HDD_BUSY_UNITS = ("nas_jetson_nano-immich-hdd-copy.service",
                  "nas_jetson_nano-config-backup.service",
                  "nasa-backup.service")


def norm(path):
    """Путь в сравнимом виде: прямые слэши, без хвостового слэша (одинаково на Windows и Linux)."""
    return str(path).replace("\\", "/").rstrip("/")


def absent_path(tmp_path):
    """Путь к файлу, которого нет: значения по умолчанию берутся без чтения диска."""
    return str(tmp_path / "net-takogo-fajla.json")


def clean_env():
    """Окружение без переменных NAS_BLACKBOX_*: пустое по смыслу, но непустое по значению —
    иначе реализация вида `env or os.environ` подставила бы настоящее окружение машины."""
    return {"LC_ALL": "C"}


def test_load_config_defaults_without_file(tmp_path):
    """Нет файла, пустое окружение → значения по умолчанию (1 ГБ, 4750 мВ)."""
    cfg = load_config(path=absent_path(tmp_path), env=clean_env())
    assert isinstance(cfg, Config)
    assert cfg.hot_cap_bytes == 1073741824
    assert cfg.vin_low_mv == 4750
    assert cfg.mem_low_mb == 300
    assert cfg.mem_crit_mb == 150
    assert cfg.load_high == 6.0
    assert cfg.swap_growth_mb_min == 50
    assert cfg.disk_stall_s == 60
    assert cfg.fallback_cap_bytes == DEFAULT_FALLBACK_CAP_BYTES
    assert cfg.hot_min_days == 7
    assert cfg.hdd_retention_days == 365
    assert norm(cfg.ssd_mount) == "/mnt/storage"
    assert norm(cfg.hdd_mount) == "/mnt/hdd2tb"
    assert norm(cfg.sysfs_root) == "/sys"
    assert norm(cfg.proc_root) == "/proc"
    assert norm(cfg.dev_root) == "/dev"
    assert norm(cfg.docker_sock) == "/var/run/docker.sock"
    assert norm(cfg.docker_root) == "/var/lib/docker"
    assert tuple(cfg.family_containers) == FAMILY_CONTAINERS
    assert tuple(cfg.hdd_busy_units) == HDD_BUSY_UNITS
    assert norm(cfg.ssd_root) == "/mnt/storage/blackbox"
    assert norm(cfg.fallback_root) == "/var/lib/nas-blackbox/fallback"
    # Год — подкаталог архиватора, поэтому корень проверяем префиксом.
    assert norm(cfg.hdd_archive_root).startswith("/mnt/hdd2tb/backups/blackbox")


def test_load_config_json_file_overrides_value(tmp_path):
    """Файл {"vin_low_mv": 4700} → 4700; остальные — по умолчанию."""
    path = tmp_path / "nas-blackbox.json"
    path.write_text(json.dumps({"vin_low_mv": 4700}), encoding="utf-8")
    cfg = load_config(path=str(path), env=clean_env())
    assert cfg.vin_low_mv == 4700
    assert cfg.mem_low_mb == 300
    assert cfg.hot_cap_bytes == DEFAULT_HOT_CAP_BYTES
    assert cfg.load_high == 6.0


def test_load_config_env_overrides_int_attribute(tmp_path):
    """env NAS_BLACKBOX_MEM_LOW_MB=250 → mem_low_mb == 250 (int, а не строка)."""
    cfg = load_config(path=absent_path(tmp_path),
                      env={"NAS_BLACKBOX_MEM_LOW_MB": "250"})
    assert cfg.mem_low_mb == 250
    assert isinstance(cfg.mem_low_mb, int)


def test_load_config_env_coerces_to_type_of_default(tmp_path):
    """Число из окружения приводится к типу умолчания (load_high — float)."""
    cfg = load_config(path=absent_path(tmp_path),
                      env={"NAS_BLACKBOX_LOAD_HIGH": "7"})
    assert cfg.load_high == 7.0
    assert isinstance(cfg.load_high, float)


def test_load_config_env_wins_over_file(tmp_path):
    """Порядок из плана: сначала JSON-файл, затем переменные окружения."""
    path = tmp_path / "nas-blackbox.json"
    path.write_text(json.dumps({"vin_low_mv": 4700}), encoding="utf-8")
    cfg = load_config(path=str(path), env={"NAS_BLACKBOX_VIN_LOW_MV": "4650"})
    assert cfg.vin_low_mv == 4650


def test_config_unknown_key_raises_type_error():
    """Config(no_such=1) → TypeError: опечатка в ключе не проходит молча."""
    with pytest.raises(TypeError):
        Config(no_such=1)


def test_config_overrides_any_attribute():
    """Config(**overrides) переопределяет любой атрибут, остальные — по умолчанию."""
    cfg = Config(vin_low_mv=4700, family_containers=("homecloud_stt",))
    assert cfg.vin_low_mv == 4700
    assert tuple(cfg.family_containers) == ("homecloud_stt",)
    assert cfg.mem_low_mb == 300
