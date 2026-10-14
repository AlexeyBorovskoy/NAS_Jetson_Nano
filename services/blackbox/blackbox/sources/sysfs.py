"""Чтение sysfs/proc (OBS-1, задача 2, спецификация §4.1, цикл fast).

Все функции — чистое чтение подставных/настоящих дерев `sysfs_root`/`proc_root`/
`dev_root`; ни одна не обращается к боевым путям напрямую — пути приходят
параметром (`Config` или голой строкой), как того требует тестовый план задачи 2.

Контракт `sample` (план, «Контракты данных») — секундный замер с ключами ровно
по списку ниже; отсутствующее значение — `None`, а не пропущенный ключ.
Python 3.6 (хост Jetson): только стандартная библиотека, без f-строк с `=`,
без `dataclasses`, без `:=`.

Канал `read_power` обязан ловить `PermissionError` на бару без root — датчик
INA3221 на устройстве читается только от root (CLAUDE.md, факты 13.10).
Бару `read_power` используется голый `open(...)`, а не `io.open`/обёртка:
тест подменяет имя `open` в этом модуле (`monkeypatch.setattr(sysfs, "open", ...)`),
и подмена видна только обычному вызову `open()` внутри самого модуля.
"""
import glob
import os

#: Имена термозон -> ключ контракта sample (миллиградусы -> десятые °C).
_THERMAL_ZONES = {
    "CPU-therm": "t_cpu",
    "GPU-therm": "t_gpu",
    "PMIC-Die": "t_pmic",
    "AO-therm": "t_ao",
}


def _read_text(path):
    """Содержимое файла или `None`, если файла нет/нет доступа (не бросает)."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return stream.read()
    except OSError:
        return None


# ── read_power: INA3221 ─────────────────────────────────────────────────────

def _find_ina3221_device(sysfs_root):
    """Первый (по сортировке) каталог `iio:device*` датчика INA3221 или `None`."""
    pattern = os.path.join(sysfs_root, "bus", "i2c", "drivers", "ina3221x",
                           "*", "iio:device*")
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None


def _read_rail_names(device):
    """{номер_канала: имя_рельса} по файлам `rail_name_<N>`."""
    channels = {}
    for path in sorted(glob.glob(os.path.join(device, "rail_name_*"))):
        suffix = os.path.basename(path).rsplit("_", 1)[-1]
        if not suffix.isdigit():
            continue
        with open(path, "r", encoding="utf-8") as stream:
            channels[int(suffix)] = stream.read().strip()
    return channels


def _read_channel_field(device, prefix, number):
    """`<prefix><number>_input` как `int`, или `None`, если файла нет вовсе."""
    path = os.path.join(device, "%s%d_input" % (prefix, number))
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as stream:
        return int(stream.read().strip())


def _assign_power_channel(result, device, number, rail_name):
    """Заполняет один канал `result` по имени рельса (не по номеру!)."""
    if rail_name == "POM_5V_IN":
        result["vin_mv"] = _read_channel_field(device, "in_voltage", number)
        result["vin_ma"] = _read_channel_field(device, "in_current", number)
    elif rail_name == "POM_5V_CPU":
        result["cpu_mw"] = _read_channel_field(device, "in_power", number)
    elif rail_name == "POM_5V_GPU":
        result["gpu_mw"] = _read_channel_field(device, "in_power", number)


def read_power(sysfs_root):
    """{"vin_mv","vin_ma","cpu_mw","gpu_mw"} по каналам INA3221.

    Нет датчика или `PermissionError` на любом файле -> все четыре значения
    `None` (план, задача 2: «нет датчика или PermissionError -> все значения
    None»); без исключения наружу в обоих случаях.
    """
    result = {"vin_mv": None, "vin_ma": None, "cpu_mw": None, "gpu_mw": None}
    device = _find_ina3221_device(sysfs_root)
    if device is None:
        return result
    try:
        for number, rail_name in _read_rail_names(device).items():
            _assign_power_channel(result, device, number, rail_name)
    except PermissionError:
        return {"vin_mv": None, "vin_ma": None, "cpu_mw": None, "gpu_mw": None}
    return result


# ── read_thermal ─────────────────────────────────────────────────────────

def read_thermal(sysfs_root):
    """{"t_cpu","t_gpu","t_pmic","t_ao"} из `class/thermal/thermal_zone*`.

    Миллиградусы -> десятые доли °C (`// 100`); зона, которой нет в снимке
    (или вовсе отсутствует каталог) -> `None` для своего ключа.
    """
    result = {"t_cpu": None, "t_gpu": None, "t_pmic": None, "t_ao": None}
    base = os.path.join(sysfs_root, "class", "thermal")
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return result
    for entry in entries:
        zone_dir = os.path.join(base, entry)
        name = _read_text(os.path.join(zone_dir, "type"))
        key = _THERMAL_ZONES.get(name.strip()) if name is not None else None
        if key is None:
            continue
        millidegrees = _read_text(os.path.join(zone_dir, "temp"))
        if millidegrees is None:
            continue
        result[key] = int(millidegrees.strip()) // 100
    return result


# ── CPU: /proc/stat, cpufreq ────────────────────────────────────────────────

def read_cpu_times(proc_root):
    """(total, idle) по первой строке `/proc/stat` (`cpu  ...`)."""
    path = os.path.join(proc_root, "stat")
    with open(path, "r", encoding="utf-8") as stream:
        first_line = stream.readline()
    fields = [int(x) for x in first_line.split()[1:]]
    idle = fields[3] if len(fields) > 3 else 0
    return (sum(fields), idle)


def cpu_pct(prev, cur):
    """Доля занятости CPU между двумя снимками `read_cpu_times`, или `None`."""
    if prev is None:
        return None
    total_prev, idle_prev = prev
    total_cur, idle_cur = cur
    delta_total = total_cur - total_prev
    if delta_total <= 0:
        return None
    delta_idle = idle_cur - idle_prev
    return (delta_total - delta_idle) * 100.0 / delta_total


def read_freq_mhz(sysfs_root):
    """Максимум по `cpu*/cpufreq/scaling_cur_freq` (файл в кГц) -> МГц, `None` если нет ни одного."""
    pattern = os.path.join(sysfs_root, "devices", "system", "cpu", "cpu*",
                           "cpufreq", "scaling_cur_freq")
    values = []
    for path in glob.glob(pattern):
        text = _read_text(path)
        if text is None:
            continue
        values.append(int(text.strip()))
    return max(values) // 1000 if values else None


# ── Память, ZRAM, загрузка, сеть ────────────────────────────────────────────

def _parse_meminfo(text):
    values = {}
    for line in text.splitlines():
        key, sep, rest = line.partition(":")
        if not sep:
            continue
        parts = rest.split()
        if parts:
            values[key.strip()] = int(parts[0])
    return values


def read_mem(proc_root):
    """{"mem_avail_mb","swap_mb"} из `/proc/meminfo` (КБ -> МБ, целочисленно)."""
    text = _read_text(os.path.join(proc_root, "meminfo"))
    if text is None:
        return {"mem_avail_mb": None, "swap_mb": None}
    values = _parse_meminfo(text)
    mem_avail = values.get("MemAvailable")
    swap_total = values.get("SwapTotal")
    swap_free = values.get("SwapFree")
    swap_mb = None
    if swap_total is not None and swap_free is not None:
        swap_mb = (swap_total - swap_free) // 1024
    return {
        "mem_avail_mb": mem_avail // 1024 if mem_avail is not None else None,
        "swap_mb": swap_mb,
    }


def read_zram_mb(sysfs_root):
    """Сумма `block/zram*/mm_stat` поля 1 (байты) по всем устройствам -> МБ, `None` если ZRAM нет."""
    pattern = os.path.join(sysfs_root, "block", "zram*", "mm_stat")
    total_bytes = 0
    found = False
    for path in glob.glob(pattern):
        text = _read_text(path)
        if text is None:
            continue
        fields = text.split()
        if len(fields) < 2:
            continue
        total_bytes += int(fields[1])
        found = True
    return total_bytes // (1024 * 1024) if found else None


def read_load1(proc_root):
    """Первое поле `/proc/loadavg` (нагрузка за минуту), или `None`."""
    text = _read_text(os.path.join(proc_root, "loadavg"))
    if text is None:
        return None
    parts = text.split()
    return float(parts[0]) if parts else None


def read_net(proc_root, ifaces=("eth0",)):
    """{"net_rx","net_tx"} — сумма байт `ifaces` из `/proc/net/dev`."""
    text = _read_text(os.path.join(proc_root, "net", "dev"))
    result = {"net_rx": None, "net_tx": None}
    if text is None:
        return result
    rx_total = tx_total = 0
    found = False
    for line in text.splitlines():
        name, sep, rest = line.partition(":")
        if not sep or name.strip() not in ifaces:
            continue
        fields = rest.split()
        if len(fields) < 9:
            continue
        rx_total += int(fields[0])
        tx_total += int(fields[8])
        found = True
    return {"net_rx": rx_total, "net_tx": tx_total} if found else result


# ── Диски: disk/by-id, /proc/diskstats ──────────────────────────────────────

def disk_id_map(dev_root):
    """{имя_устройства: by-id-имя} только для `usb-`/`ata-` ссылок без `-part`."""
    by_id_dir = os.path.join(dev_root, "disk", "by-id")
    result = {}
    try:
        entries = sorted(os.listdir(by_id_dir))
    except OSError:
        return result
    for name in entries:
        if "-part" in name or not (name.startswith("usb-") or name.startswith("ata-")):
            continue
        try:
            target = os.readlink(os.path.join(by_id_dir, name))
        except OSError:
            continue
        result[os.path.basename(target)] = name
    return result


def read_disks(proc_root, idmap, ts):
    """[disk_sample, ...] из `/proc/diskstats` только для устройств из `idmap`.

    Поля по индексам 3 (rios), 7 (wios), 5 (rsect), 9 (wsect), 12 (busy_ms) —
    план, таблица случаев задачи 2.
    """
    text = _read_text(os.path.join(proc_root, "diskstats"))
    if text is None:
        return []
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 13:
            continue
        disk_id = idmap.get(fields[2])
        if disk_id is None:
            continue
        rows.append((ts, disk_id, int(fields[3]), int(fields[7]),
                     int(fields[5]), int(fields[9]), int(fields[12])))
    return rows


# ── read_fast_sample: сборка контракта sample ───────────────────────────────

def read_fast_sample(cfg, prev_cpu, ts):
    """(sample, disk_samples, cur_cpu) — один секундный замер (цикл fast)."""
    cur_cpu = read_cpu_times(cfg.proc_root)
    mem = read_mem(cfg.proc_root)
    idmap = disk_id_map(cfg.dev_root)

    sample = {"ts": ts}
    sample.update(read_power(cfg.sysfs_root))
    sample.update(read_thermal(cfg.sysfs_root))
    sample["cpu_pct"] = cpu_pct(prev_cpu, cur_cpu)
    sample["freq_mhz"] = read_freq_mhz(cfg.sysfs_root)
    sample["mem_avail_mb"] = mem["mem_avail_mb"]
    sample["swap_mb"] = mem["swap_mb"]
    sample["zram_mb"] = read_zram_mb(cfg.sysfs_root)
    sample["load1"] = read_load1(cfg.proc_root)
    net = read_net(cfg.proc_root)
    sample["net_rx"] = net["net_rx"]
    sample["net_tx"] = net["net_tx"]

    disks = read_disks(cfg.proc_root, idmap, ts)
    return sample, disks, cur_cpu
