"""OBS-1 «чёрный ящик», задача 2: чтение sysfs/proc (services/blackbox/blackbox/sources/sysfs.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, задача 2;
спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md, §4.1.

Подставные деревья /sys, /proc, /dev собираются в tmp_path; ни процессов, ни сокетов
эта задача не касается. Путь к пакету добавляет tests/blackbox/conftest.py (задача 1
плана). На момент написания пакета ещё нет — тесты обязаны падать на импорте (шаг 2).
"""
import io
import os

import pytest

from blackbox.config import Config
from blackbox.sources import sysfs

TS = 1791861274  # секунда эпохи из «Контрактов данных» плана

# Контракт sample: «ключи ровно такие; отсутствующее значение — None».
SAMPLE_KEYS = frozenset([
    "ts", "vin_mv", "vin_ma", "cpu_mw", "gpu_mw",
    "t_cpu", "t_gpu", "t_pmic", "t_ao",
    "cpu_pct", "freq_mhz", "mem_avail_mb", "swap_mb", "zram_mb",
    "load1", "net_rx", "net_tx",
])

MICRON = "usb-JMicron_Generic_STORAGE_0001-0:0"
WD_ELEMENTS = "usb-WD_Elements_0002-0:0"
WWN = "wwn-0x50014ee20b5f1c2d"  # не usb-/ata- — в карту дисков входить не должен


# ── Подставные деревья ────────────────────────────────────────────────────────

def _write(path, text):
    """Файл вместе с каталогами; newline="\\n" — байты одинаковы на Windows и Linux."""
    path = str(path)
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def _write_ina3221(sys_root, channels):
    """Подставной датчик: (rail_name, {поле: значение}) по номерам каналов.

    Поле "in_voltage" → in_voltage<N>_input и так далее. Порядок каналов задаёт
    вызывающий: соответствие обязано браться по rail_name_<N>, а не по номеру.
    """
    if os.name == "nt":
        pytest.skip("Linux sysfs fixture contains ':'; exercised by Linux tests")
    device = os.path.join(sys_root, "bus", "i2c", "drivers", "ina3221x", "6-0040", "iio:device0")
    for number, (rail_name, fields) in enumerate(channels):
        _write(os.path.join(device, "rail_name_%d" % number), rail_name + "\n")
        for field, value in fields.items():
            _write(os.path.join(device, "%s%d_input" % (field, number)), "%d\n" % value)


# Каналы перемешаны: POM_5V_IN стоит последним (индекс 2) — соответствие только по имени.
# 7368 — из строки таблицы; 40 — из контракта sample (gpu_mw); 5120/5088/5150 — ловушки
# на «взять по номеру» (5120/5088 — чужие напряжения) и «взять мощность IN» (5150).
CHANNELS_SHUFFLED = (
    ("POM_5V_GPU", {"in_voltage": 5120, "in_power": 40}),
    ("POM_5V_CPU", {"in_voltage": 5088, "in_power": 7368}),
    ("POM_5V_IN", {"in_voltage": 5080, "in_current": 1450, "in_power": 5150}),
)

# Раскладка для строки таблицы «Файл in_voltage0_input недоступен»: IN — на канале 0.
CHANNELS_IN_FIRST = (
    ("POM_5V_IN", {"in_voltage": 5080, "in_current": 1450}),
    ("POM_5V_CPU", {"in_power": 7368}),
    ("POM_5V_GPU", {"in_power": 40}),
)


def _write_thermal(sys_root, zones):
    """Терм-зоны: пары (имя зоны в /type, миллиградусы в /temp)."""
    for number, (name, millidegrees) in enumerate(zones):
        zone = os.path.join(sys_root, "class", "thermal", "thermal_zone%d" % number)
        _write(os.path.join(zone, "type"), name + "\n")
        _write(os.path.join(zone, "temp"), "%d\n" % millidegrees)


def _deny_read(monkeypatch, path):
    """Делает файл нечитаемым: chmod 000 (Linux) или подмена open (Windows/root).

    chmod 000 на Windows чтение не запрещает вовсе, а под root не запрещает и на Linux,
    поэтому там подменяем open в модуле — и io.open, чтобы подмена накрыла и pathlib.
    """
    path = str(path)
    if os.name == "posix":
        os.chmod(path, 0o000)
        try:
            with open(path, "rb"):
                pass
        except OSError:
            return  # запрет сработал по-настоящему
        os.chmod(path, 0o644)
    real_open = io.open
    denied_path = os.path.normcase(os.path.abspath(path))

    def denied_open(file, *args, **kwargs):
        if os.path.normcase(os.path.abspath(str(file))) == denied_path:
            raise PermissionError(13, "Permission denied", path)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(sysfs, "open", denied_open, raising=False)
    monkeypatch.setattr(io, "open", denied_open)


def _build_by_id_links(dev_root, names_to_targets):
    """Подставной disk/by-id из настоящих символических ссылок.

    False — ссылки создать нельзя (Windows: нет прав и запрещён символ «:» в именах
    usb-…-0:0). Решение о пропуске теста принимает вызывающий.
    """
    by_id = os.path.join(dev_root, "disk", "by-id")
    os.makedirs(by_id, exist_ok=True)
    created = []
    try:
        for name, target in names_to_targets.items():
            link = os.path.join(by_id, name)
            os.symlink(os.path.join("..", "..", target), link)
            created.append(link)
    except (OSError, NotImplementedError):
        for link in created:
            os.unlink(link)
        return False
    return True


# ── Содержимое /proc и /sys ────────────────────────────────────────────────────

# /proc/stat: user 200, nice 50, system 0, idle 850 (iowait и прочее — нули),
# то есть total=1100, idle=850 — при prev_cpu=(1000, 800) даёт cpu_pct 50.0.
PROC_STAT = "cpu  200 50 0 850 0 0 0 0 0 0\n"

# Строка таблицы: MemAvailable 1359456 kB → 1327 МБ; занятая подкачка
# 2029560 − 1750000 = 279560 kB → 273 МБ.
MEMINFO = (
    "MemTotal:        4055352 kB\n"
    "MemFree:          873456 kB\n"
    "MemAvailable:    1359456 kB\n"
    "SwapTotal:       2029560 kB\n"
    "SwapFree:        1750000 kB\n"
)

LOADAVG = "1.76 0.95 0.60 2/345 12345\n"

# /proc/net/dev — как на устройстве: имена с отступом, eth0 в окружении lo и docker0.
NET_DEV = (
    "Inter-|   Receive                                                |  Transmit\n"
    " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
    "    lo:    1000      10    0    0    0     0          0         0     1000      10    0    0    0     0       0          0\n"
    "  eth0: 123456789    5000    0    0    0     0          0         0 98765432    4000    0    0    0     0       0          0\n"
    "docker0:       88       1    0    0    0     0          0         0       99       1    0    0    0     0       0          0\n"
)

# /proc/diskstats: все значимые поля различимы, чтобы индекс не угадывался.
# Ожидаемые (ts, id, rios, wios, rsect, wsect, busy_ms) берутся по индексам 3, 7, 5, 9, 12.
DISKSTATS = (
    "   8       0 sda 1101 12 5103 14 7105 16 9107 18 20 11109 22\n"
    "   8       1 sda1 1 2 3 4 5 6 7 8 9 10 11\n"
    "   8      16 sdb 2201 0 5203 0 7205 0 9207 0 0 22209 0\n"
    " 179       0 mmcblk0 31 32 33 34 35 36 37 38 39 40 41\n"
)

# mm_stat: поля равны намеренно — план говорит «поле 1», не уточняя нумерацию
# (0- или 1-с-начала); при равных полях выбор поля на результат не влияет,
# а сумма по устройствам и перевод в МБ проверяются.
ZRAM_MM_STAT = " ".join(["1048576"] * 8) + "\n"


# ── read_power: INA3221 ────────────────────────────────────────────────────────

def test_power_channels_matched_by_rail_name(tmp_path):
    """Строка таблицы: «INA3221 с тремя каналами POM_5V_IN/GPU/CPU, значения
    5080/1450/7368 — vin_mv=5080, vin_ma=1450, gpu_mw и cpu_mw по именам, не по
    номерам (порядок каналов перемешан)»."""
    sys_root = str(tmp_path / "sys")
    _write_ina3221(sys_root, CHANNELS_SHUFFLED)
    power = sysfs.read_power(sys_root)
    assert power == {"vin_mv": 5080, "vin_ma": 1450, "cpu_mw": 7368, "gpu_mw": 40}


def test_power_without_sensor_is_all_none(tmp_path):
    """Строка таблицы: «Нет каталога ina3221x — все четыре None, без исключения»."""
    sys_root = str(tmp_path / "sys")
    os.makedirs(sys_root, exist_ok=True)
    power = sysfs.read_power(sys_root)
    assert power == {"vin_mv": None, "vin_ma": None, "cpu_mw": None, "gpu_mw": None}


def test_power_unreadable_input_file_gives_none(tmp_path, monkeypatch):
    """Строка таблицы: «Файл in_voltage0_input недоступен (chmod 000; на Windows —
    подменить open, бросающий PermissionError) — None».

    Проверяем vin_mv: строка таблицы требует именно None, а решать за реализацию,
    станет ли None всё или только это поле (в интерфейсе сказано «все значения
    None», в контракте данных — «отсутствующее значение — None»), тест не должен.
    """
    sys_root = str(tmp_path / "sys")
    _write_ina3221(sys_root, CHANNELS_IN_FIRST)
    _deny_read(monkeypatch, tmp_path / "sys" / "bus" / "i2c" / "drivers" / "ina3221x"
               / "6-0040" / "iio:device0" / "in_voltage0_input")
    assert sysfs.read_power(sys_root)["vin_mv"] is None


# ── read_thermal ───────────────────────────────────────────────────────────────

def test_thermal_millidegrees_to_tenths(tmp_path):
    """Строка таблицы: «Терм-зоны CPU-therm=63000, GPU-therm=60500 — t_cpu=630,
    t_gpu=605». Зоны перемешаны (GPU первой); отсутствующих зон значения — None."""
    sys_root = str(tmp_path / "sys")
    _write_thermal(sys_root, [("GPU-therm", 60500), ("CPU-therm", 63000)])
    assert sysfs.read_thermal(sys_root) == {
        "t_cpu": 630, "t_gpu": 605, "t_pmic": None, "t_ao": None}


# ── cpu_pct ────────────────────────────────────────────────────────────────────

def test_cpu_pct_share_and_bootstrap():
    """Строка таблицы: «cpu_pct((1000, 800), (1100, 850)) — 50.0;
    при prev=None — None»."""
    assert sysfs.cpu_pct((1000, 800), (1100, 850)) == 50.0
    assert sysfs.cpu_pct(None, (1100, 850)) is None


# ── read_mem ───────────────────────────────────────────────────────────────────

def test_mem_avail_and_swap_used(tmp_path):
    """Строка таблицы: «MemAvailable 1359456 kB, SwapTotal 2029560, SwapFree
    1750000 — mem_avail_mb=1327, swap_mb=273» (swap_mb — занятая подкачка)."""
    proc_root = str(tmp_path / "proc")
    _write(tmp_path / "proc" / "meminfo", MEMINFO)
    assert sysfs.read_mem(proc_root) == {"mem_avail_mb": 1327, "swap_mb": 273}


# ── disk_id_map: /dev/disk/by-id ───────────────────────────────────────────────

def test_disk_id_map_by_links_only_devices(tmp_path):
    """Строка таблицы: «disk/by-id: usb-JMicron_…-0:0 → ../../sdb, …-part1 → ../../sdb1 —
    {"sdb": "usb-JMicron_…-0:0"}». Ссылка wwn-… (не usb-/ata-) отброшена.

    На Windows ссылку с «:» в имени создать нельзя в принципе — тест идёт на Linux.
    """
    dev_root = str(tmp_path / "dev")
    for device in ("sdb", "sdb1", "sdc"):
        _write(tmp_path / "dev" / device, "")
    linked = _build_by_id_links(dev_root, {
        MICRON: "sdb",
        MICRON + "-part1": "sdb1",
        WWN: "sdc",
    })
    if not linked:
        pytest.skip("Windows: символические ссылки disk/by-id недоступны (нужны права "
                    "и запрещён символ «:» в имени usb-…-0:0) — сценарий проверяется на Linux")
    assert sysfs.disk_id_map(dev_root) == {"sdb": MICRON}


# ── read_disks: /proc/diskstats ────────────────────────────────────────────────

def test_read_disks_only_idmap_and_field_indexes(tmp_path):
    """Строка таблицы: «/proc/diskstats со строками sda, sda1, sdb, mmcblk0 и idmap
    только для sda, sdb — ровно 2 кортежа, поля по индексам 3, 7, 5, 9, 12».

    sda1 (раздел) и mmcblk0 (карта) в карте отсутствуют — их быть не должно.
    """
    proc_root = str(tmp_path / "proc")
    _write(tmp_path / "proc" / "diskstats", DISKSTATS)
    rows = sysfs.read_disks(proc_root, {"sda": MICRON, "sdb": WD_ELEMENTS}, TS)
    assert len(rows) == 2
    assert set(tuple(row) for row in rows) == {
        (TS, MICRON, 1101, 7105, 5103, 9107, 11109),
        (TS, WD_ELEMENTS, 2201, 7205, 5203, 9207, 22209),
    }


# ── read_fast_sample: полное дерево ────────────────────────────────────────────

def test_read_fast_sample_has_full_contract(tmp_path):
    """Строка таблицы: «read_fast_sample на полном подставном дереве — все ключи
    контракта sample присутствуют» (ключи ровно контрактные, значения — источников)."""
    sys_root = str(tmp_path / "sys")
    proc_root = str(tmp_path / "proc")
    dev_root = str(tmp_path / "dev")
    _write_ina3221(sys_root, CHANNELS_SHUFFLED)
    _write_thermal(sys_root, [("GPU-therm", 60500), ("CPU-therm", 63000),
                              ("PMIC-Die", 50000), ("AO-therm", 64500)])
    # На устройстве scaling_cur_freq — килогерцы (так его читает и cpp1_probe.py).
    _write(tmp_path / "sys" / "devices" / "system" / "cpu" / "cpu0" / "cpufreq" / "scaling_cur_freq",
           "1479000\n")
    _write(tmp_path / "sys" / "devices" / "system" / "cpu" / "cpu1" / "cpufreq" / "scaling_cur_freq",
           "408000\n")
    _write(tmp_path / "sys" / "block" / "zram0" / "mm_stat", ZRAM_MM_STAT)
    _write(tmp_path / "proc" / "stat", PROC_STAT)
    _write(tmp_path / "proc" / "meminfo", MEMINFO)
    _write(tmp_path / "proc" / "loadavg", LOADAVG)
    _write(tmp_path / "proc" / "net" / "dev", NET_DEV)
    _write(tmp_path / "proc" / "diskstats", DISKSTATS)
    _write(tmp_path / "dev" / "sdb", "")
    _write(tmp_path / "dev" / "sdb1", "")
    linked = _build_by_id_links(dev_root, {WD_ELEMENTS: "sdb", WD_ELEMENTS + "-part1": "sdb1"})

    cfg = Config(sysfs_root=sys_root, proc_root=proc_root, dev_root=dev_root)
    sample, disks, cur_cpu = sysfs.read_fast_sample(cfg, (1000, 800), TS)

    assert set(sample) == SAMPLE_KEYS
    assert sample["ts"] == TS
    assert sample["vin_mv"] == 5080
    assert sample["vin_ma"] == 1450
    assert sample["cpu_mw"] == 7368
    assert sample["gpu_mw"] == 40
    assert sample["t_cpu"] == 630
    assert sample["t_gpu"] == 605
    assert sample["t_pmic"] == 500
    assert sample["t_ao"] == 645
    assert sample["cpu_pct"] == 50.0
    assert sample["freq_mhz"] == 1479
    assert sample["mem_avail_mb"] == 1327
    assert sample["swap_mb"] == 273
    assert sample["zram_mb"] == 1
    assert sample["load1"] == 1.76
    assert sample["net_rx"] == 123456789
    assert sample["net_tx"] == 98765432
    assert cur_cpu == (1100, 850)
    if linked:
        assert [tuple(row) for row in disks] == [
            (TS, WD_ELEMENTS, 2201, 7205, 5203, 9207, 22209)]
    else:
        # Ссылки disk/by-id недоступны (Windows) — карта пуста, дисков нет; этот
        # случай проверяется здесь, а сопоставление по ссылкам — на Linux.
        assert disks == []


# ── Прочие функции интерфейса (строк таблицы нет — значения из интерфейса) ─────

def test_freq_mhz_is_max_over_cpus(tmp_path):
    """Интерфейс: максимум по cpu*/cpufreq/scaling_cur_freq. Файл в килогерцах —
    на устройстве так: в проекте он уже читается как cpu_freq_khz (cpp1_probe.py),
    а контракт sample зовёт поле freq_mhz=1479 при максимуме Jetson 1479 МГц."""
    _write(tmp_path / "sys" / "devices" / "system" / "cpu" / "cpu0" / "cpufreq" / "scaling_cur_freq",
           "1479000\n")
    _write(tmp_path / "sys" / "devices" / "system" / "cpu" / "cpu1" / "cpufreq" / "scaling_cur_freq",
           "408000\n")
    assert sysfs.read_freq_mhz(str(tmp_path / "sys")) == 1479


def test_zram_mb_sums_devices(tmp_path):
    """Интерфейс: сумма block/zram*/mm_stat «поле 1» в мегабайтах.

    Поля mm_stat равны намеренно — план не уточняет нумерацию «поля 1», и при равных
    полях выбор поля не влияет на результат; проверяются сумма и перевод в МБ.
    """
    _write(tmp_path / "sys" / "block" / "zram0" / "mm_stat", ZRAM_MM_STAT)
    _write(tmp_path / "sys" / "block" / "zram1" / "mm_stat", ZRAM_MM_STAT)
    assert sysfs.read_zram_mb(str(tmp_path / "sys")) == 2


def test_load1_from_loadavg(tmp_path):
    """Интерфейс: read_load1 — первое поле /proc/loadavg."""
    _write(tmp_path / "proc" / "loadavg", LOADAVG)
    assert sysfs.read_load1(str(tmp_path / "proc")) == 1.76


def test_net_rx_tx_of_eth0(tmp_path):
    """Интерфейс: read_net по умолчанию берёт eth0 (значения — из контракта sample)."""
    _write(tmp_path / "proc" / "net" / "dev", NET_DEV)
    assert sysfs.read_net(str(tmp_path / "proc")) == {"net_rx": 123456789, "net_tx": 98765432}
