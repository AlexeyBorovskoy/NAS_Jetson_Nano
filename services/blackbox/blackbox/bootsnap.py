"""OBS-1, задача 8: снимок загрузки и сводка прошлой загрузки (blackbox/bootsnap.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «Задача 8».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md,
раздел 4.2 (содержимое снимка) и 5.1 (раскладка `boots/<boot_id>/`).

Снимок пишется на SSD (`cfg.ssd_root`) только если `cfg.ssd_mount` действительно
смонтирован; иначе — в запасной корень (`cfg.fallback_root`), а на
несмонтированный SSD не создаётся ничего (§5.4, грабли проекта: иначе снимок
молча лёг бы на SD под видом SSD).

Python 3.6: только стандартная библиотека, без f-строк с `=`, без
`dataclasses`, без `:=`.
"""
import json
import os
import re
import stat
import subprocess
import sys
import time

from .config import load_config
from .redact import mask_family_text, redact_line
from .sources.sysfs import disk_id_map

#: Предел ожидания одной команды, с: снимок — oneshot при загрузке.
COMMAND_TIMEOUT_S = 30
#: Предел копии одного файла pstore; больший файл обрезается с явной пометкой.
PSTORE_MAX_BYTES = 1 << 20
PSTORE_MAX_FILES = 64
TEXT_MAX_BYTES = 4 << 20
SNAPSHOT_MAX_BYTES = 8 << 20
TEXT_AGGREGATE_BYTES = 4 << 20
PSTORE_AGGREGATE_BYTES = 4 << 20
SNAPSHOT_META_RESERVE = 128 << 10
MIN_SNAPSHOT_BUDGET = 256 << 10
FALLBACK_WALK_MAX_ENTRIES = 10000
#: Фиксированные классы ошибок: в файл попадают класс и код, а не трассировка.
ERROR_COMMAND = "ошибка команды"
ERROR_TIMEOUT = "ошибка таймаута"
ERROR_START = "ошибка запуска"
ERROR_READ = "ошибка чтения"
ERROR_RESET = "ошибка reset source"
ERROR_UNAVAILABLE = "команда недоступна"

#: Разрешённый список команд снимка: (ключ, argv, имя файла). Только этот
#: список исполняется — без shell, без `docker inspect` (запрет §4.2).
COMMANDS = (
    ("uname", ("uname", "-a"), "uname.txt"),
    ("nv_tegra_release", ("cat", "/etc/nv_tegra_release"),
     "nv_tegra_release.txt"),
    ("dmesg", ("dmesg",), "dmesg.txt"),
    ("lsblk", ("lsblk", "-o",
               "NAME,MAJ:MIN,RM,SIZE,RO,TYPE,MOUNTPOINT,MODEL,SERIAL,UUID"),
     "lsblk.txt"),
    ("by-id", ("ls", "-l", "{dev_root}/disk/by-id"), "by-id.txt"),
    ("lsusb", ("lsusb", "-t"), "lsusb.txt"),
    ("journalctl", ("journalctl", "--no-pager", "-o", "short-iso-precise",
                    "--boot=-1", "-n", "300"), "prev_journal_tail.txt"),
    ("docker", ("docker", "ps", "-a", "--format",
                "{{.Names}}\t{{.Image}}\t{{.Status}}"), "docker_ps.txt"),
)

#: Приметы штатного выключения в журнале прошлой загрузки (раздел 6).
SHUTDOWN_MARKERS = ("Reached target Shutdown", "systemd-shutdown", "Power-Off")
_BOOT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_URL_AUTH_RE = re.compile(r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@")
_SPACE_SECRET_RE = re.compile(
    r"(?i)(--?(?:password|passwd|token|secret|api[-_]?key)(?:=|\s+)|-[pu]\s+)([^\s]+)")


def _check_boot_id(boot_id):
    """boot_id — один компонент пути: без слэшей, обратных слэшей и `..`."""
    if not isinstance(boot_id, str) or not _BOOT_ID_RE.match(boot_id):
        raise ValueError("boot_id: недопустимое значение")
    return boot_id


def _chmod(path, mode):
    """Применяет права POSIX; на Windows chmod может не поддерживаться."""
    try:
        os.chmod(path, mode)
    except OSError:
        if os.name != "nt":
            raise


def _make_dirs(path):
    """Создаёт каталог (с родителями) с правами 0700 -> True/False при OSError."""
    try:
        missing = []
        parent = path
        while not os.path.exists(parent):
            missing.append(parent)
            next_parent = os.path.dirname(parent)
            if next_parent == parent:
                break
            parent = next_parent
        if not os.path.isdir(path):
            os.makedirs(path, mode=0o700)
        for created in missing:
            _chmod(created, 0o700)
        _chmod(path, 0o700)
        return True
    except OSError:
        return False


def _is_mounted(path):
    """Точка монтирования действительно смонтирована (иначе писать на SSD нельзя)."""
    try:
        return bool(os.path.ismount(path))
    except OSError:
        return False


def _snapshot_dir(cfg, boot_id):
    """Каталог `boots/<boot_id>`: SSD при смонтированной точке, иначе запасной."""
    if _is_mounted(cfg.ssd_mount):
        snap = os.path.join(cfg.ssd_root, "boots", boot_id)
        if _make_dirs(snap):
            return snap
    snap = os.path.join(cfg.fallback_root, "boots", boot_id)
    if not _make_dirs(snap):
        raise OSError("bootsnap: не удалось создать каталог снимка: " + snap)
    return snap


def _argv(template, cfg):
    """argv из шаблона таблицы: подставляет настроенный dev_root, без shell."""
    return tuple(part.replace("{dev_root}", cfg.dev_root) for part in template)


def _capture(argv, run, key, timeout=COMMAND_TIMEOUT_S):
    """Запускает разрешённую команду -> текст вывода или фиксированная ошибка.

    `run` — как `subprocess.run`; в тестах подменяется, настоящий процесс не
    запускается. Любой отказ команды — текст класса ошибки, а не исключение.
    """
    try:
        completed = run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        universal_newlines=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ERROR_TIMEOUT
    except (OSError, ValueError):
        return ERROR_START
    if completed.returncode != 0:
        return key + ": " + ERROR_UNAVAILABLE
    text = completed.stdout or ""
    if len(text.encode("utf-8", "replace")) > TEXT_MAX_BYTES:
        text = text.encode("utf-8", "replace")[:TEXT_MAX_BYTES].decode(
            "utf-8", "ignore") + "\n[output truncated]\n"
    return text


def _truncate_text(text, budget):
    """Укладывает строку в байтовый бюджет, сохраняя видимую метку усечения."""
    data = text.encode("utf-8", "replace")
    if len(data) <= budget:
        return text
    marker = b"\n[output truncated]\n"
    keep = max(0, budget - len(marker))
    return data[:keep].decode("utf-8", "ignore") + marker.decode("ascii")


def _fit_texts(cfg, snap, outputs, budget):
    """Распределяет общий текстовый бюджет между файлами снимка в фиксированном порядке."""
    pending = [(name, outputs[key]) for key, _argv, name in COMMANDS]
    pending.extend((("mounts.txt", _read_mounts(cfg)),
                    ("reset_source.txt", _reset_source(outputs["dmesg"]))))
    result = {}
    for index, (name, text) in enumerate(pending):
        safe = _safe_text(os.path.join(snap, name), text, cfg)
        reserve = min(budget, (len(pending) - index - 1) * 24)
        allowance = max(0, budget - reserve)
        fitted = _truncate_text(safe, allowance)
        result[name] = fitted
        budget -= len(fitted.encode("utf-8"))
    return result


def _replaceable_paths(cfg, snap):
    """Известные назначения текущего снимка; остальные файлы учитываются в cap."""
    paths = [os.path.join(snap, name) for _key, _argv, name in COMMANDS]
    paths.extend(os.path.join(snap, name) for name in
                 ("mounts.txt", "reset_source.txt", "summary.json"))
    src = os.path.join(cfg.sysfs_root, "fs", "pstore")
    try:
        names = sorted(os.listdir(src))[:PSTORE_MAX_FILES]
    except OSError:
        names = []
    for name in names:
        source = os.path.join(src, name)
        if (name and os.path.basename(name) == name and
                not os.path.islink(source) and os.path.isfile(source)):
            base = os.path.join(snap, "pstore", name)
            paths.append(base)
    return set(os.path.normcase(os.path.abspath(path)) for path in paths)


def _fallback_entries(root):
    """Обходит только реальные каталоги fallback, ограничивая число записей."""
    pending = [os.path.abspath(root)]
    seen = 0
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError:
            raise OSError("bootsnap: fallback недоступен")
        for entry in entries:
            seen += 1
            if seen > FALLBACK_WALK_MAX_ENTRIES:
                raise OSError("bootsnap: fallback лимит обхода")
            yield entry
            if not entry.is_symlink() and entry.is_dir(follow_symlinks=False):
                pending.append(entry.path)


def _entry_stat(entry):
    """Получает метаданные без следования по symlink."""
    try:
        return entry.stat(follow_symlinks=False)
    except OSError:
        raise OSError("bootsnap: fallback недоступен")


def _fallback_usage(root, replaceable):
    """Считает fallback-файлы без прохода по symlink и с пределом числа записей."""
    if os.path.islink(root):
        raise OSError("bootsnap: fallback недоступен")
    total = 0
    if not os.path.exists(root):
        return total
    for entry in _fallback_entries(root):
        if entry.is_symlink():
            continue
        info = _entry_stat(entry)
        path = os.path.normcase(os.path.abspath(entry.path))
        if stat.S_ISREG(info.st_mode) and path not in replaceable:
            total += info.st_size
    return total


def _snapshot_budget(cfg, snap, is_ssd):
    """Возвращает бюджет этого снимка после учёта существующих fallback-данных."""
    budget = SNAPSHOT_MAX_BYTES
    if not is_ssd:
        used = _fallback_usage(cfg.fallback_root, _replaceable_paths(cfg, snap))
        budget = min(budget, cfg.fallback_cap_bytes - used)
    if budget < MIN_SNAPSHOT_BUDGET:
        raise OSError("bootsnap: недостаточный бюджет снимка")
    return budget


def _safe_text(path, text, cfg):
    """Маскирует секреты, URL credentials и journal-текст до записи."""
    lines = []
    journal = os.path.basename(path) == "prev_journal_tail.txt"
    for line in text.splitlines(True):
        line = _URL_AUTH_RE.sub(r"\1<скрыто>@", line)
        line = _SPACE_SECRET_RE.sub(r"\1<скрыто>", line)
        line = redact_line("host", line, cfg)
        if journal:
            line = mask_family_text(line)
        lines.append(line)
    return "".join(lines)


def _open_private_temp(path, file_mode):
    """Эксклюзивно создаёт temp-файл с 0600 до первой записи (POSIX)."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    fd = os.open(path, flags, 0o600)
    return os.fdopen(fd, file_mode, **({} if "b" in file_mode else
                                      {"encoding": "utf-8", "newline": ""}))


def _write_text(path, text, cfg):
    """Пишет текст после маскирования секретов (`redact_line`) с правами 0600."""
    tmp_path = path + ".tmp"
    try:
        with _open_private_temp(tmp_path, "w") as fh:
            fh.write(_safe_text(path, text, cfg))
            fh.flush()
            os.fsync(fh.fileno())
        _chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
        _chmod(path, 0o600)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


def _read_mounts(cfg):
    """Содержимое `<proc_root>/mounts` (подставной корень, не живой /proc)."""
    path = os.path.join(cfg.proc_root, "mounts")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(TEXT_MAX_BYTES + 1)
        if len(text.encode("utf-8", "replace")) > TEXT_MAX_BYTES:
            return text.encode("utf-8", "replace")[:TEXT_MAX_BYTES].decode(
                "utf-8", "ignore") + "\n[output truncated]\n"
        return text
    except OSError:
        return ERROR_READ + ": mounts"


def _reset_source(dmesg_text):
    """Строки `PMC reset source` из dmesg; нет их — фиксированный класс ошибки.

    Признак чистоты загрузки — не этот текст (при аппаратном сбросе он тоже
    TEGRA_POWER_ON_RESET), а журнал прошлой загрузки (грабли проекта).
    """
    lines = [line for line in dmesg_text.splitlines()
             if "PMC reset source" in line]
    if not lines:
        return ERROR_RESET + ": PMC reset source не найден"
    return "\n".join(lines) + "\n"


def _read_bounded(path, limit=PSTORE_MAX_BYTES):
    """(data, truncated, total): читает максимум per-file и доступный aggregate cap."""
    total = os.path.getsize(path)
    with open(path, "rb") as fh:
        data = fh.read(min(PSTORE_MAX_BYTES, limit) + 1)
    if len(data) > min(PSTORE_MAX_BYTES, limit):
        return data[:min(PSTORE_MAX_BYTES, limit)], True, total
    return data, False, total


def _copy_one_pstore(cfg, dst_dir, name, src, budget, reserve):
    """Копирует один pstore-файл в остаток aggregate cap; возвращает байты/успех."""
    if os.path.islink(src) or not os.path.isfile(src):
        return False, 0
    try:
        data, truncated, total = _read_bounded(src, max(0, budget - reserve))
        dst = os.path.join(dst_dir, name)
        tmp_path = dst + ".tmp"
        with _open_private_temp(tmp_path, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _chmod(tmp_path, 0o600)
        os.replace(tmp_path, dst)
        _chmod(dst, 0o600)
    except OSError:
        _write_text(os.path.join(dst_dir, name + ".error"),
                    ERROR_READ + ": pstore " + name, cfg)
        return False, 0
    used = len(data)
    if truncated:
        marker = "truncated: %d of %d bytes\n" % (len(data), total)
        _write_text(dst + ".truncated", marker, cfg)
        used += len(marker.encode("utf-8"))
    return True, used


def _copy_pstore(cfg, snap, budget):
    """Копии pstore в aggregate cap; отказ одного файла не рвёт снимок."""
    src_dir = os.path.join(cfg.sysfs_root, "fs", "pstore")
    dst_dir = os.path.join(snap, "pstore")
    if not _make_dirs(dst_dir):
        raise OSError("bootsnap: pstore недоступен")
    try:
        names = sorted(os.listdir(src_dir))[:PSTORE_MAX_FILES]
    except OSError:
        return []
    copied = []
    budget = min(budget, PSTORE_AGGREGATE_BYTES)
    for index, name in enumerate(names):
        if name in (".", "..") or os.path.basename(name) != name:
            continue
        reserve = (len(names) - index - 1) * 128 + 64
        ok, used = _copy_one_pstore(cfg, dst_dir, name,
                                    os.path.join(src_dir, name), budget, reserve)
        if ok:
            budget -= used
            copied.append(name)
    return copied


def _write_summary(snap, boot_id, ts, pstore, cfg):
    """`summary.json` атомарно: временный файл + fsync + os.replace, права 0600."""
    disks = _disk_mapping(cfg)
    payload = json.dumps({"boot_id": boot_id, "ts": ts, "pstore": list(pstore),
                          "disks": disks, "mounts": _mount_mapping(cfg, disks)},
                         ensure_ascii=False, sort_keys=True)
    path = os.path.join(snap, "summary.json")
    tmp_path = path + ".tmp"
    with _open_private_temp(tmp_path, "w") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, path)
    _chmod(path, 0o600)


def _disk_mapping(cfg):
    """Use the same whole-disk aliases as sampled diskstats."""
    return disk_id_map(cfg.dev_root)


def _mount_mapping(cfg, disks):
    """Resolve proc mount records without touching mounted filesystems."""
    result = {}
    for line in _read_mounts(cfg).splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        device = os.path.basename(fields[0])
        match = re.match(r"^((?:sd|vd|xvd)[a-z]+)[0-9]+$", device)
        if match is None:
            match = re.match(r"^((?:mmcblk[0-9]+|nvme[0-9]+n[0-9]+))p[0-9]+$", device)
        whole = match.group(1) if match else device
        if whole in disks:
            mountpoint = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), fields[1])
            result[mountpoint] = disks[whole]
    return result


def take_snapshot(cfg, boot_id, run=subprocess.run, now=time.time):
    """Снимок загрузки `boots/<boot_id>/` (раздел 4.2) -> путь каталога снимка.

    SSD не смонтирован -> запасной корень; каждая упавшая команда оставляет
    файл с текстом ошибки, снимок всё равно создаётся целиком.
    """
    _check_boot_id(boot_id)
    snap = _snapshot_dir(cfg, boot_id)
    ts = now()
    is_ssd = os.path.normcase(os.path.abspath(snap)).startswith(
        os.path.normcase(os.path.abspath(cfg.ssd_root)) + os.sep)
    outputs = {}
    for key, template, name in COMMANDS:
        outputs[key] = _capture(_argv(template, cfg), run, key)
    try:
        budget = _snapshot_budget(cfg, snap, is_ssd)
        _write_snapshot(cfg, snap, boot_id, outputs, ts, budget)
    except OSError:
        if not is_ssd:
            raise
        snap = os.path.join(cfg.fallback_root, "boots", boot_id)
        if not _make_dirs(snap):
            raise OSError("bootsnap: fallback недоступен")
        budget = _snapshot_budget(cfg, snap, False)
        _write_snapshot(cfg, snap, boot_id, outputs, ts, budget)
    return snap


def _write_snapshot(cfg, snap, boot_id, outputs, ts, budget):
    """Записывает полный снимок в выбранный корень; вызывается повторно при fallback."""
    text_budget = min(TEXT_AGGREGATE_BYTES,
                      (budget - SNAPSHOT_META_RESERVE) // 2)
    pstore_budget = min(PSTORE_AGGREGATE_BYTES,
                        budget - text_budget - SNAPSHOT_META_RESERVE)
    texts = _fit_texts(cfg, snap, outputs, text_budget)
    for name, text in texts.items():
        _write_text(os.path.join(snap, name), text, cfg)
    pstore = _copy_pstore(cfg, snap, pstore_budget)
    _write_summary(snap, boot_id, ts, pstore, cfg)


def _clean_shutdown(lines):
    """True — в журнале есть примета штатной shutdown-последовательности."""
    for line in lines or ():
        for marker in SHUTDOWN_MARKERS:
            if marker in line:
                return True
    return False


def _previous_boot(catalog, heartbeat):
    """Строка прошлой загрузки: по boot_id из heartbeat, иначе последняя в каталоге."""
    boot_id = heartbeat.get("boot_id") if isinstance(heartbeat, dict) else None
    if boot_id:
        row = catalog.get_boot(boot_id)
        if row is not None:
            return row
        return {"boot_id": boot_id, "start": None}
    rows = catalog.boots(limit=1)
    return rows[0] if rows else None


def previous_boot_summary(catalog, heartbeat, journal_prev_tail, pstore_files,
                          reset_source):
    """Строка `boot` прошлой загрузки без вердикта (`verdict`/`confidence` — None).

    `clean` доказывает только журнал прошлой загрузки: `PMC reset source` при
    аппаратном сбросе тоже TEGRA_POWER_ON_RESET и признаком чистоты не служит.
    Без heartbeat последний признак жизни и конец загрузки неизвестны — None.
    """
    row = _previous_boot(catalog, heartbeat) or {}
    hb = heartbeat if isinstance(heartbeat, dict) else {}
    return {
        "boot_id": row.get("boot_id") or hb.get("boot_id"),
        "start": row.get("start"),
        "end": hb.get("ts"),
        "clean": _clean_shutdown(journal_prev_tail),
        "last_heartbeat": hb.get("ts"),
        "reset_source": reset_source,
        "pstore": list(pstore_files or ()),
        "verdict": None,
        "confidence": None,
    }


def read_boot_id(cfg):
    """boot_id текущей загрузки из `<proc_root>/sys/kernel/random/boot_id`."""
    path = os.path.join(cfg.proc_root, "sys", "kernel", "random", "boot_id")
    with open(path, "r", encoding="utf-8") as fh:
        return _check_boot_id(fh.read().strip())


def main(argv=None):
    """Точка входа снимка: конфиг, boot_id из настроенного /proc, `take_snapshot`.

    Флагов у снимка нет; `argv` оставлен для единой сигнатуры точек входа.
    """
    try:
        cfg = load_config()
        boot_id = read_boot_id(cfg)
        snap = take_snapshot(cfg, boot_id)
        from .boot_record import record_boot
        record_boot(cfg, boot_id, snap, time.time())
    except (OSError, ValueError):
        sys.stderr.write("bootsnap: сбор не выполнен\n")
        return 1
    sys.stdout.write(snap + "\n")
    return 0
