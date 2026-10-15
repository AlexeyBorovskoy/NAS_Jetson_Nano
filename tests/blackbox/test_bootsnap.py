"""OBS-1, задача 8: снимок загрузки и сводка прошлой загрузки (blackbox/bootsnap.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «### Задача 8».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md,
раздел 4.2 (содержимое снимка) и раздел 5.1 (раскладка boots/<boot_id>/).

TDD: модуля services/blackbox/blackbox/bootsnap.py ещё нет — файл обязан
падать на импорте (ModuleNotFoundError: No module named 'blackbox.bootsnap'),
а не на утверждениях.

Ни одного настоящего процесса, сокета и сети: `run` и `now` из интерфейса
подменяются, все корни (SSD, запасной, /sys, /proc, /dev) — каталоги tmp_path.
Работает на Windows и Linux.

Что тесты уточняют там, где план молчит (выбор продиктован интерфейсом):

- `journal_prev_tail` — список строк (как `lines` из `journal_since`,
  задача 5), а не единый текст;
- `pstore_files` — список имён файлов (как поле `pstore` строки boot-контракта);
- `summary.json` — плоский словарь с ключами `boot_id`, `ts`, `pstore`;
  `ts` берётся из подставленного `now`;
- свежесть SSD определяется по точке монтирования `cfg.ssd_mount`: в тестах
  это корень диска (tmp_path.anchor), потому что os.path.ismount истинно и на
  Linux ("/"), и на Windows ("C:\\"). При отсутствии точки монтирования снимок
  ложится в `cfg.fallback_root/boots/`, и на несмонтированный SSD не создаётся
  ничего — иначе снимок молча лёг бы на SD (грабли проекта);
- `clean` строки boot определяется журналом прошлой загрузки: строки
  shutdown-последовательности (Reached target Shutdown, systemd-shutdown,
  Power-Off) → True; строки без единой такой приметы → False. PMC reset source
  признаком чистоты быть не может (при аппаратном сбросе он тоже
  TEGRA_POWER_ON_RESET — грабли проекта, CLAUDE.md);
- `previous_boot_summary` только возвращает строку boot без вердикта:
  `verdict` и `confidence` — None (вердикт выставляет задача 10/11).

Фокус ревью плана этой задаче тестов не назначает: все пять случаев
принадлежат задачам 3, 4, 5, 7 и 11 — здесь их дублировать нечего.
"""
import json
import os
import subprocess  # только класс CalledProcessError — ни один процесс не запускается

from blackbox.bootsnap import previous_boot_summary, take_snapshot
from blackbox.config import Config
from blackbox.store import Catalog

T0 = 1791861274  # 2026-10-13 03:14:34 UTC — ts из контракта данных плана
BOOT_ID = "3f2c1ab4-77de-4b6a-9c11-2a5e6f7d8c90"  # boot_id снимаемой загрузки

# ── подставные выводы команд (ни одна не выполняется) ────────────────────────

UNAME_OUT = ("Linux jetson 4.9.253-tegra #1 SMP PREEMPT Mon Jul 10 10:21:56 UTC 2023"
             " aarch64 GNU/Linux\n")
NVTEGRA_OUT = ("# R32 (release), REVISION: 7.2, GCID: 36586245, BOARD: t210ref,"
               " EABI: aarch64\n")
DMESG_OUT = ("[    0.000000] Booting Linux on physical CPU 0x0\n"
             "[    0.000000] PMC reset source: TEGRA_POWER_ON_RESET\n"
             "[   12.345678] eth0: link up, 1000 Mbps, full duplex\n")
RESET_LINE = "PMC reset source: TEGRA_POWER_ON_RESET"
LSBLK_OUT = ("NAME MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT\n"
             "sda    8:0    0 232.9G  0 disk\n"
             "sda1   8:1    0 232.9G  0 part /mnt/storage\n"
             "sdb    8:16   0   1.8T  0 disk\n")
BYID_OUT = ("total 0\n"
            "lrwxrwxrwx 1 root root  9 Oct 13 03:14 usb-JMicron_SSD-0:0 -> ../../sda\n"
            "lrwxrwxrwx 1 root root 10 Oct 13 03:14 usb-JMicron_SSD-0:0-part1 -> ../../sda1\n")
LSUSB_OUT = ("/:  Bus 02.Port 1: Dev 1, Class=root_hub, Driver=tegra-xusb/1p, 5000M\n"
             "    |__ Port 3: Dev 4, Class=Mass Storage, Driver=usb-storage, 5000M\n")
JOURNAL_PREV_OUT = ("2026-10-13T03:13:40+0000 nas systemd[1]: Started Daily apt download"
                    " activities.\n"
                    "2026-10-13T03:13:55+0000 nas kernel: eth0: link up, 1000 Mbps,"
                    " full duplex\n")
DOCKER_PS_OUT = ("homecloud_nextcloud       nextcloud:33.0.4        Up 3 hours\n"
                 "homecloud_immich_server   immich-server:v2.7.5   Up 3 hours\n")
MOUNTS_OUT = ("/dev/sda1 /mnt/storage ext4 rw,noatime 0 0\n"
              "/dev/sdb1 /mnt/hdd2tb fuseblk rw,relatime 0 0\n")

#: Ключевое слово в тексте команды -> подставной вывод. Порядок важен: берётся
#: первое совпадение (например, у команды `dmesg | grep "PMC reset source"`,
#: если она есть, вывод будет полным dmesg и всё равно содержит нужную строку).
#: /proc/mounts отвечает так же, поэтому и чтение файла <proc_root>/mounts,
#: и `cat <proc_root>/mounts` дают одно и то же содержимое mounts.txt.
OUTPUTS = (
    ("uname", UNAME_OUT),
    ("nv_tegra_release", NVTEGRA_OUT),
    ("dmesg", DMESG_OUT),
    ("lsblk", LSBLK_OUT),
    ("by-id", BYID_OUT),
    ("lsusb", LSUSB_OUT),
    ("journalctl", JOURNAL_PREV_OUT),
    ("mounts", MOUNTS_OUT),
    ("docker", DOCKER_PS_OUT),
)

#: Файлы-выводы команд: ключ -> имя файла в снимке. reset_source.txt в списке
#: нет намеренно: он производится из вывода dmesg, а не своим выводом команды.
COMMAND_FILES = (
    ("uname", "uname.txt"),
    ("nv_tegra_release", "nv_tegra_release.txt"),
    ("dmesg", "dmesg.txt"),
    ("lsblk", "lsblk.txt"),
    ("by-id", "by-id.txt"),
    ("lsusb", "lsusb.txt"),
    ("journalctl", "prev_journal_tail.txt"),
    ("docker", "docker_ps.txt"),
)

#: Полный состав каталога снимка (раздел 4.2 спецификации), в отсортированном виде.
EXPECTED_NAMES = sorted([
    "uname.txt", "nv_tegra_release.txt", "dmesg.txt", "reset_source.txt",
    "lsblk.txt", "by-id.txt", "lsusb.txt", "mounts.txt", "pstore",
    "prev_journal_tail.txt", "docker_ps.txt", "summary.json",
])

PSTORE_BYTES = b"\x00\x01ramoops-dump: panic\xff\n"  # ramoops — двоичный буфер


def _error_marker(key):
    """Текст stderr, который подставной run кладёт упавшей команде."""
    return "%s: команда недоступна" % key


# ── подставной run ───────────────────────────────────────────────────────────

class _FakeCompleted(object):
    """Ответ как у subprocess.CompletedProcess (текстовый режим: строки)."""

    def __init__(self, stdout="", stderr="", returncode=0, args=None):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.args = args


class _FakeRun(object):
    """Подставной subprocess.run: помнит команды, отдаёт вывод по ключу.

    fail=True — «каждая команда упала»: код возврата 1, stdout пуст, stderr —
    «<ключ>: команда недоступна». check=True воспроизводится как у настоящего
    subprocess.run — через CalledProcessError; модуль subprocess нужен только
    ради этого класса, ни один процесс не запускается.
    """

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def _key(self, cmd):
        for key, _out in OUTPUTS:
            if key in cmd:
                return key
        return None

    def __call__(self, args, **kwargs):
        cmd = args if isinstance(args, str) else " ".join(str(a) for a in args)
        self.calls.append(cmd)
        key = self._key(cmd)
        if self.fail:
            completed = _FakeCompleted(stderr=_error_marker(key or "команда"),
                                       returncode=1, args=cmd)
        else:
            completed = _FakeCompleted(stdout=dict(OUTPUTS).get(key, ""), args=cmd)
        if kwargs.get("check") and completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode, cmd,
                output=completed.stdout, stderr=completed.stderr)
        return completed


# ── подставное дерево и конфигурация ─────────────────────────────────────────

def _norm(path):
    """Путь в сравнимом виде: прямые слэши, без хвостового слэша (Windows и Linux)."""
    return str(path).replace("\\", "/").rstrip("/")


def _cfg_with_fake_roots(tmp_path, ssd_present=True):
    """Config с подставными корнями, деревом /proc и /sys.

    ssd_present=True — cfg.ssd_mount указывает на корень диска (tmp_path.anchor):
    os.path.ismount там истинно и на Windows ("C:\\"), и на Linux ("/"),
    а cfg.ssd_root заранее создан внутри tmp_path.
    ssd_present=False — точки монтирования нет вовсе: это и есть «SSD нет».
    """
    proc = tmp_path / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    (proc / "mounts").write_text(MOUNTS_OUT, encoding="utf-8")
    (tmp_path / "sys" / "fs" / "pstore").mkdir(parents=True, exist_ok=True)

    ssd_root = tmp_path / "ssd" / "blackbox"
    if ssd_present:
        ssd_root.mkdir(parents=True, exist_ok=True)
        mount = tmp_path.anchor
    else:
        mount = str(tmp_path / "нет-ssd")

    return Config(ssd_root=str(ssd_root),
                  fallback_root=str(tmp_path / "fallback"),
                  ssd_mount=mount,
                  sysfs_root=str(tmp_path / "sys"),
                  proc_root=str(proc),
                  dev_root=str(tmp_path / "dev"))


def _write_pstore(cfg, files):
    """Подложить файлы в <sysfs_root>/fs/pstore (пустой словарь — pstore пуст)."""
    root = os.path.join(cfg.sysfs_root, "fs", "pstore")
    for name, data in files.items():
        with open(os.path.join(root, name), "wb") as fh:
            fh.write(data)


def _read_text(snap, name):
    with open(os.path.join(str(snap), name), "r", encoding="utf-8") as fh:
        return fh.read()


def _read_summary(snap):
    return json.loads(_read_text(snap, "summary.json"))


# ── take_snapshot ────────────────────────────────────────────────────────────

def test_take_snapshot_creates_all_files_of_section_4_2(tmp_path):
    """Состав снимка из раздела 4.2: одиннадцать файлов и каталог pstore;
    каталог — boots/<boot_id>/ под корнем SSD."""
    cfg = _cfg_with_fake_roots(tmp_path)
    _write_pstore(cfg, {"dmesg-ramoops-0": PSTORE_BYTES})
    run = _FakeRun()

    snap = take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    assert _norm(snap) == _norm(os.path.join(str(cfg.ssd_root), "boots", BOOT_ID))
    assert os.path.isdir(str(snap))
    assert sorted(os.listdir(str(snap))) == EXPECTED_NAMES
    assert os.listdir(os.path.join(str(snap), "pstore")) == ["dmesg-ramoops-0"]


def test_take_snapshot_writes_command_outputs_to_named_files(tmp_path):
    """Каждый файл — вывод своей команды (через подставной run); /proc/mounts —
    из <proc_root>/mounts, а не с настоящего хоста."""
    cfg = _cfg_with_fake_roots(tmp_path)
    _write_pstore(cfg, {})
    run = _FakeRun()

    snap = take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    assert run.calls, "снимок обязан запускать команды через run"
    assert "Linux jetson 4.9.253-tegra" in _read_text(snap, "uname.txt")
    assert "R32 (release), REVISION: 7.2" in _read_text(snap, "nv_tegra_release.txt")
    assert "Booting Linux on physical CPU 0x0" in _read_text(snap, "dmesg.txt")
    assert RESET_LINE in _read_text(snap, "reset_source.txt")
    assert "232.9G" in _read_text(snap, "lsblk.txt")
    assert "usb-JMicron_SSD-0:0 -> ../../sda" in _read_text(snap, "by-id.txt")
    assert "Driver=usb-storage" in _read_text(snap, "lsusb.txt")
    assert ("Started Daily apt download activities."
            in _read_text(snap, "prev_journal_tail.txt"))
    assert "homecloud_immich_server" in _read_text(snap, "docker_ps.txt")
    assert "/dev/sdb1 /mnt/hdd2tb fuseblk" in _read_text(snap, "mounts.txt")


def test_take_snapshot_copies_pstore_file_and_fills_summary(tmp_path):
    """Строка таблицы: pstore с dmesg-ramoops-0 — побайтовая копия в снимке и
    summary.pstore == ["dmesg-ramoops-0"]; ts сводки — из подставленного now."""
    cfg = _cfg_with_fake_roots(tmp_path)
    _write_pstore(cfg, {"dmesg-ramoops-0": PSTORE_BYTES})
    run = _FakeRun()

    snap = take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    copied = os.path.join(str(snap), "pstore", "dmesg-ramoops-0")
    assert os.path.isfile(copied)
    with open(copied, "rb") as fh:
        assert fh.read() == PSTORE_BYTES

    summary = _read_summary(snap)
    assert summary["boot_id"] == BOOT_ID
    assert summary["ts"] == T0
    assert summary["pstore"] == ["dmesg-ramoops-0"]


def test_take_snapshot_with_empty_pstore_has_empty_summary_list(tmp_path):
    """Строка таблицы: pstore пуст — summary.pstore == [], без исключения."""
    cfg = _cfg_with_fake_roots(tmp_path)
    _write_pstore(cfg, {})
    run = _FakeRun()

    snap = take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    assert _read_summary(snap)["pstore"] == []
    pstore_dir = os.path.join(str(snap), "pstore")
    if os.path.isdir(pstore_dir):
        assert os.listdir(pstore_dir) == []


def test_take_snapshot_when_every_command_fails_still_creates_snapshot(tmp_path):
    """Строка таблицы: каждая команда упала — в файле текст ошибки (stderr),
    снимок всё равно создан целиком.

    reset_source.txt здесь не сверяется по тексту: он производится из вывода
    dmesg, а не является выводом своей команды.
    """
    cfg = _cfg_with_fake_roots(tmp_path)
    _write_pstore(cfg, {"dmesg-ramoops-0": PSTORE_BYTES})
    run = _FakeRun(fail=True)

    snap = take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    assert os.path.isdir(str(snap))
    assert sorted(os.listdir(str(snap))) == EXPECTED_NAMES
    for key, name in COMMAND_FILES:
        text = _read_text(snap, name)
        assert text.strip(), "пустой файл вместо текста ошибки: " + name
        assert _error_marker(key) in text, name
    assert os.path.isfile(os.path.join(str(snap), "pstore", "dmesg-ramoops-0"))
    assert _read_summary(snap)["pstore"] == ["dmesg-ramoops-0"]


def test_take_snapshot_without_ssd_writes_to_fallback_root(tmp_path):
    """Строка таблицы: SSD нет — каталог снимка в запасном корне; на
    несмонтированный SSD не создаётся ничего (иначе снимок молча лёг бы на SD)."""
    cfg = _cfg_with_fake_roots(tmp_path, ssd_present=False)
    _write_pstore(cfg, {"dmesg-ramoops-0": PSTORE_BYTES})
    run = _FakeRun()

    snap = take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    assert _norm(snap) == _norm(os.path.join(str(cfg.fallback_root), "boots", BOOT_ID))
    assert os.path.isfile(os.path.join(str(snap), "summary.json"))
    assert not os.path.exists(str(cfg.ssd_root))


def test_take_snapshot_commands_never_contain_docker_inspect(tmp_path):
    """Строка таблицы: в списке выполненных команд нет inspect — раздел 4.2
    разрешает только docker ps, вывод docker inspect не сохраняется никогда."""
    cfg = _cfg_with_fake_roots(tmp_path)
    _write_pstore(cfg, {})
    run = _FakeRun()

    take_snapshot(cfg, BOOT_ID, run=run, now=lambda: T0)

    assert any("docker" in cmd and "ps" in cmd for cmd in run.calls), run.calls
    assert "inspect" not in "\n".join(run.calls)


# ── previous_boot_summary ────────────────────────────────────────────────────

PREV_BOOT_ID = "8a11c2d3-0f4e-4a55-9b66-71c8d9e0f123"
PREV_START = 1791763200  # 2026-10-12 00:00:00 UTC — начало прошлой загрузки
PREV_END = 1791861235    # 2026-10-13 03:13:55 UTC — её последний heartbeat

#: Файл heartbeat (формат store.write_heartbeat): загрузка, время, питание.
HEARTBEAT = {"boot_id": PREV_BOOT_ID, "ts": PREV_END,
             "power": {"vin_mv": 5080, "vin_ma": 1450}}

#: Журнал прошлой загрузки — строки (как `lines` из journal_since, задача 5).
JOURNAL_CLEAN_TAIL = [
    "2026-10-13T03:05:00+0000 nas systemd[1]: Stopping User Manager for UID 1000...",
    "2026-10-13T03:05:01+0000 nas systemd[1]: Stopped target Multi-User System.",
    "2026-10-13T03:05:02+0000 nas systemd[1]: Reached target Shutdown.",
    "2026-10-13T03:05:03+0000 nas systemd-shutdown[1]: Sending SIGTERM to remaining"
    " processes...",
    "2026-10-13T03:05:04+0000 nas systemd-shutdown[1]: Reached target Power-Off.",
]
JOURNAL_DIRTY_TAIL = [
    "2026-10-13T03:13:40+0000 nas systemd[1]: Started Daily apt download activities.",
    "2026-10-13T03:13:55+0000 nas kernel: eth0: link up, 1000 Mbps, full duplex",
    "2026-10-13T03:13:56+0000 nas kernel: usb 2-3: new SuperSpeed USB device number 4",
]

#: Строка boot-контракта плана — ровно эти ключи.
BOOT_ROW_KEYS = sorted(["boot_id", "start", "end", "clean", "last_heartbeat",
                        "reset_source", "pstore", "verdict", "confidence"])


def _boot_row(boot_id, start):
    """Строка boot в каталоге — та же форма, что кладёт store.upsert_boot."""
    return {"boot_id": boot_id, "start": start, "end": None, "clean": None,
            "last_heartbeat": None, "reset_source": None, "pstore": [],
            "verdict": None, "confidence": None}


def _catalog_with_prev_boot(tmp_path):
    """Каталог с одной строкой — прошлой загрузкой.

    Строка текущей загрузки ещё не записана (take_snapshot каталог не трогает),
    а heartbeat, снятый до старта сборщика, называет именно прошлую загрузку.
    """
    catalog = Catalog(str(tmp_path / "catalog.db"))
    catalog.upsert_boot(_boot_row(PREV_BOOT_ID, PREV_START))
    return catalog


def test_previous_boot_summary_clean_shutdown_is_clean(tmp_path):
    """Штатное выключение в журнале прошлой загрузки → clean=True; поля boot
    заполнены из heartbeat, reset_source и pstore, вердикта нет.

    PMC reset source признаком чистоты не служит: при аппаратном сбросе он тоже
    TEGRA_POWER_ON_RESET — чистоту доказывает только журнал.
    """
    catalog = _catalog_with_prev_boot(tmp_path)
    summary = previous_boot_summary(catalog=catalog, heartbeat=HEARTBEAT,
                                    journal_prev_tail=JOURNAL_CLEAN_TAIL,
                                    pstore_files=["dmesg-ramoops-0"],
                                    reset_source="TEGRA_POWER_ON_RESET")

    assert sorted(summary.keys()) == BOOT_ROW_KEYS
    assert summary["boot_id"] == PREV_BOOT_ID
    assert summary["start"] == PREV_START
    assert summary["end"] == PREV_END
    assert summary["last_heartbeat"] == PREV_END
    assert bool(summary["clean"]) is True
    assert summary["reset_source"] == "TEGRA_POWER_ON_RESET"
    assert summary["pstore"] == ["dmesg-ramoops-0"]
    assert summary["verdict"] is None
    assert summary["confidence"] is None


def test_previous_boot_summary_without_shutdown_marker_is_unclean(tmp_path):
    """Ни одной приметы штатного выключения в журнале → clean=False;
    пустые pstore и reset_source переносятся как есть."""
    catalog = _catalog_with_prev_boot(tmp_path)
    summary = previous_boot_summary(catalog=catalog, heartbeat=HEARTBEAT,
                                    journal_prev_tail=JOURNAL_DIRTY_TAIL,
                                    pstore_files=[], reset_source=None)

    assert sorted(summary.keys()) == BOOT_ROW_KEYS
    assert summary["boot_id"] == PREV_BOOT_ID
    assert bool(summary["clean"]) is False
    assert summary["pstore"] == []
    assert summary["reset_source"] is None
    assert summary["verdict"] is None
    assert summary["confidence"] is None


def test_previous_boot_summary_without_heartbeat_reports_no_last_heartbeat(tmp_path):
    """Heartbeat не найден (SSD/SD без файла) — не исключение: последний
    признак жизни неизвестен, end и last_heartbeat остаются None."""
    catalog = _catalog_with_prev_boot(tmp_path)
    summary = previous_boot_summary(catalog=catalog, heartbeat=None,
                                    journal_prev_tail=JOURNAL_DIRTY_TAIL,
                                    pstore_files=[], reset_source=None)

    assert summary["boot_id"] == PREV_BOOT_ID
    assert summary["start"] == PREV_START
    assert summary["last_heartbeat"] is None
    assert summary["end"] is None
    assert bool(summary["clean"]) is False
