"""OBS-1 «чёрный ящик», задача 3 — хранилище (blackbox/store.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «### Задача 3».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md, раздел 5.
Контракты данных (sample, disk_sample, proc row, event, boot row) — раздел
«Контракты данных» плана.

TDD: пакета services/blackbox ещё нет, поэтому файл обязан падать на импорте
(ModuleNotFoundError при сборе тестов), а не по другой причине.

Не зависит от ОС и часового пояса: все каталоги — tmp_path, время — UTC через
time.gmtime; ни subprocess, ни сети, ни реальных /sys, /proc, /dev.
"""

import gzip
import lzma
import os
import sqlite3
import time

import pytest

from blackbox.store import (
    Catalog,
    DayStore,
    append_gz_lines,
    close_day,
    day_for_ts,
    hot_size_bytes,
    prune_hot,
    read_heartbeat,
    write_heartbeat,
)

DAY = "2026-10-13"
T0 = 1791861274  # 2026-10-13 03:14:34 UTC — ts из контракта данных плана


def _utc_day_name(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def _sample(ts, **over):
    """Строка контракта `sample` (ключи ровно как в плане)."""
    s = {
        "ts": ts, "vin_mv": 5080, "vin_ma": 1450, "cpu_mw": 1200, "gpu_mw": 40,
        "t_cpu": 630, "t_gpu": 605, "t_pmic": 500, "t_ao": 645,
        "cpu_pct": 37.5, "freq_mhz": 1479, "mem_avail_mb": 1327, "swap_mb": 272,
        "zram_mb": 455, "load1": 1.76, "net_rx": 123456789, "net_tx": 98765432,
    }
    s.update(over)
    return s


def _proc_row(ts, pid, comm="bash", owner="host", state="S", wchan="",
              cpu_pct=0.0, rss_mb=1.0, cmd="bash"):
    """Строка контракта `proc row`."""
    return {"ts": ts, "pid": pid, "comm": comm, "owner": owner, "cmd": cmd,
            "state": state, "wchan": wchan, "cpu_pct": cpu_pct, "rss_mb": rss_mb}


def _event(ts, source, kind, subject, severity="info", detail=None):
    """Строка контракта `event`."""
    return {"ts": ts, "source": source, "kind": kind, "subject": subject,
            "severity": severity, "detail": {} if detail is None else detail}


def _boot_row(boot_id, start, **over):
    """Строка контракта `boot row`."""
    b = {"boot_id": boot_id, "start": start, "end": None, "clean": None,
         "last_heartbeat": None, "reset_source": None, "pstore": [],
         "verdict": None, "confidence": None}
    b.update(over)
    return b


# ── day_for_ts ───────────────────────────────────────────────────────────────

def test_day_for_ts_known_value():
    """Строка таблицы: 1791861274 — это 2026-10-13 (00:00 UTC дня = 1791849600)."""
    assert day_for_ts(1791861274) == "2026-10-13"


def test_day_for_ts_rejects_pre_2020():
    """Фокус ревью №3: часы прыгнули (нет RTC-батарейки) — замер «из 1970 года»
    не должен молча создавать каталог 1970-01-01 в «горячем»."""
    with pytest.raises(ValueError):
        day_for_ts(5)


def test_day_for_ts_utc_midnight_boundary():
    """Сутки — по UTC: секундой до полуночи — 12-е, с полуночи — 13-е."""
    assert day_for_ts(1791849599) == "2026-10-12"
    assert day_for_ts(1791849600) == "2026-10-13"


def test_day_for_ts_floor_is_2020_01_01():
    """Порог из интерфейса: ts < 1577836800 → ValueError, ровно порог — валиден."""
    assert day_for_ts(1577836800) == "2020-01-01"
    with pytest.raises(ValueError):
        day_for_ts(1577836799)


# ── DayStore ─────────────────────────────────────────────────────────────────

def test_daystore_samples_roundtrip_in_ts_order(tmp_path):
    """Строка таблицы: 3 замера, flush, новый объект на том же дне —
    samples(…) возвращает 3 в порядке ts."""
    hot = tmp_path / "hot"
    store = DayStore(str(hot), DAY)
    store.add_samples([_sample(T0 + 2), _sample(T0), _sample(T0 + 1)])  # нарочно не по порядку
    store.flush()
    store.close()

    again = DayStore(str(hot), DAY)
    rows = again.samples(T0 - 1, T0 + 3)
    assert [r["ts"] for r in rows] == [T0, T0 + 1, T0 + 2]

    first = rows[0]
    assert first["vin_mv"] == 5080
    assert first["mem_avail_mb"] == 1327
    assert first["t_cpu"] == 630
    assert first["load1"] == 1.76  # в metrics.db хранится ×100, наружу — по контракту
    assert first["net_rx"] == 123456789

    assert again.samples(T0 + 10, T0 + 20) == []
    again.close()
    assert (hot / DAY / "metrics.db").exists()


def test_daystore_second_flush_same_ts_replaces(tmp_path):
    """Строка таблицы: два flush подряд с одинаковым ts — вторая запись
    заменяет первую (PK по ts), без исключения."""
    hot = tmp_path / "hot"
    store = DayStore(str(hot), DAY)
    store.add_samples([_sample(T0)])
    store.flush()
    store.add_samples([_sample(T0, vin_mv=4610, mem_avail_mb=120)])
    store.flush()  # не должно быть исключения

    rows = store.samples(T0 - 1, T0 + 1)
    assert len(rows) == 1
    assert rows[0]["vin_mv"] == 4610
    assert rows[0]["mem_avail_mb"] == 120
    store.close()


def test_daystore_disk_samples_roundtrip(tmp_path):
    """disk_sample — кортеж (ts, disk_id, rios, wios, rsect, wsect, busy_ms);
    disk_id — имя из /dev/disk/by-id."""
    hot = tmp_path / "hot"
    rows_in = [
        (T0, "usb-JMicron_SSD-0:0", 10, 20, 4096, 8192, 130),
        (T0 + 1, "usb-WD_HDD-0:0", 3, 0, 1024, 0, 0),
    ]
    store = DayStore(str(hot), DAY)
    store.add_disk_samples(rows_in)
    store.flush()
    store.close()

    again = DayStore(str(hot), DAY)
    assert again.disk_samples(T0 - 1, T0 + 2) == rows_in
    again.close()


def test_daystore_procs_roundtrip(tmp_path):
    """proc row: D-state с wchan — то, ради чего снимок и делается."""
    hot = tmp_path / "hot"
    store = DayStore(str(hot), DAY)
    store.add_procs([
        _proc_row(T0, 4242, comm="ntfs-3g", state="D", wchan="request_wait_answer",
                  cmd="ntfs-3g /dev/sdb1 /mnt/hdd2tb"),
        _proc_row(T0 + 1, 777, comm="python3", owner="homecloud_immich_microservices",
                  cmd="python3 app.py"),
    ])
    store.flush()
    store.close()

    again = DayStore(str(hot), DAY)
    rows = again.procs(T0 - 1, T0 + 3)
    by_pid = dict((r["pid"], r) for r in rows)
    assert sorted(by_pid) == [777, 4242]

    stuck = by_pid[4242]
    assert stuck["state"] == "D"
    assert stuck["wchan"] == "request_wait_answer"
    assert stuck["comm"] == "ntfs-3g"
    assert stuck["owner"] == "host"

    assert by_pid[777]["owner"] == "homecloud_immich_microservices"
    again.close()
    assert (hot / DAY / "procs.db").exists()


def test_daystore_uses_wal(tmp_path):
    """Интерфейс: flush() — PRAGMA journal_mode=WAL, режим остаётся в файле."""
    hot = tmp_path / "hot"
    store = DayStore(str(hot), DAY)
    store.add_samples([_sample(T0)])
    store.add_procs([_proc_row(T0, 1)])
    store.flush()
    store.close()

    for name in ("metrics.db", "procs.db"):
        conn = sqlite3.connect(str(hot / DAY / name))
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        assert str(mode).lower() == "wal", name


# ── Catalog ──────────────────────────────────────────────────────────────────

def test_catalog_events_source_filter_and_detail_dict(tmp_path):
    """Строка таблицы: events с фильтром source="docker" — только события
    Docker; detail вернулся dict."""
    cat = Catalog(str(tmp_path / "catalog.db"))
    cat.add_events([
        _event(T0, "docker", "die", "homecloud_immich_microservices", "crit",
               {"exitCode": 137, "oom": True}),
        _event(T0 + 1, "docker", "start", "homecloud_stt", "info", {"image": "stt"}),
        _event(T0 + 2, "probe", "dns_down", "dns", "warn", {}),
    ])

    docker_only = cat.events(T0 - 5, T0 + 5, source="docker")
    assert len(docker_only) == 2
    assert sorted(e["subject"] for e in docker_only) == sorted(
        ["homecloud_immich_microservices", "homecloud_stt"])

    die = [e for e in docker_only if e["kind"] == "die"][0]
    assert isinstance(die["detail"], dict)
    assert die["detail"]["exitCode"] == 137
    assert die["severity"] == "crit"

    assert len(cat.events(T0 - 5, T0 + 5)) == 3


def test_catalog_events_subject_filter(tmp_path):
    cat = Catalog(str(tmp_path / "catalog.db"))
    cat.add_events([
        _event(T0, "docker", "start", "homecloud_stt"),
        _event(T0 + 1, "docker", "start", "homecloud_nextcloud"),
    ])
    only = cat.events(T0 - 5, T0 + 5, subject="homecloud_stt")
    assert len(only) == 1
    assert only[0]["subject"] == "homecloud_stt"


def test_catalog_upsert_boot_keeps_single_row_and_updates_fields(tmp_path):
    """Строка таблицы: upsert_boot дважды с одним boot_id — одна строка,
    поля обновлены."""
    cat = Catalog(str(tmp_path / "catalog.db"))
    boot_id = "b-2026-10-13-abc"
    cat.upsert_boot(_boot_row(boot_id, 1791820000))
    cat.upsert_boot(_boot_row(boot_id, 1791820000, end=1791860000, clean=True,
                              last_heartbeat=T0, reset_source="TEGRA_POWER_ON_RESET",
                              pstore=["dmesg-ramoops-0"], verdict="unclean_boot",
                              confidence="fact"))

    assert len(cat.boots()) == 1
    boot = cat.get_boot(boot_id)
    assert boot["boot_id"] == boot_id
    assert boot["end"] == 1791860000
    assert bool(boot["clean"]) is True
    assert boot["last_heartbeat"] == T0
    assert boot["reset_source"] == "TEGRA_POWER_ON_RESET"
    assert boot["pstore"] == ["dmesg-ramoops-0"]
    assert boot["verdict"] == "unclean_boot"
    assert boot["confidence"] == "fact"


def test_catalog_boots_newest_first_and_limited(tmp_path):
    cat = Catalog(str(tmp_path / "catalog.db"))
    for i in range(1, 4):
        cat.upsert_boot(_boot_row("b-%d" % i, 1700000000 + i * 1000))

    assert [b["boot_id"] for b in cat.boots()] == ["b-3", "b-2", "b-1"]
    assert len(cat.boots(limit=2)) == 2


def test_catalog_cursor_unknown_is_none_and_roundtrip(tmp_path):
    """Строка таблицы: get_cursor неизвестного имени — None (курсоры журнала
    и дочитывания логов кладут задачи 4–5)."""
    cat = Catalog(str(tmp_path / "catalog.db"))
    assert cat.get_cursor("journal") is None
    cat.set_cursor("journal", "s=abc123; i=42")
    assert cat.get_cursor("journal") == "s=abc123; i=42"
    cat.set_cursor("journal", "s=def456; i=43")
    assert cat.get_cursor("journal") == "s=def456; i=43"


def test_catalog_archive_lookup_by_day(tmp_path):
    """archive_for_day ищет архив по дню внутри first_day..last_day —
    на этом стоит сбор доказательств nas-why (задача 11)."""
    cat = Catalog(str(tmp_path / "catalog.db"))
    cat.add_archive({
        "week": "2026-W40",
        "path": "/mnt/hdd2tb/backups/blackbox/2026/blackbox-2026-W40.tar.xz",
        "sha256": "a" * 64,
        "first_day": "2026-09-28",
        "last_day": "2026-10-04",
        "created": T0,
        "verified": True,
    })

    archives = cat.archives()
    assert len(archives) == 1
    assert archives[0]["week"] == "2026-W40"

    hit = cat.archive_for_day("2026-10-01")
    assert isinstance(hit, dict)
    assert hit["week"] == "2026-W40"
    assert cat.archive_for_day("2026-11-01") is None


# ── heartbeat ────────────────────────────────────────────────────────────────

def test_heartbeat_roundtrip_leaves_no_tmp_file(tmp_path):
    """Строка таблицы: write_heartbeat → read_heartbeat — тот же boot_id, ts;
    файл после записи цел (временного не осталось)."""
    path = tmp_path / "heartbeat"
    power = {"vin_mv": 5080, "vin_ma": 1450}
    write_heartbeat(str(path), "boot-abc123", T0, power)

    hb = read_heartbeat(str(path))
    assert hb["boot_id"] == "boot-abc123"
    assert hb["ts"] == T0
    assert hb["power"] == power
    assert os.listdir(str(tmp_path)) == ["heartbeat"]


def test_read_heartbeat_empty_file_is_none(tmp_path):
    """Строка таблицы: read_heartbeat на пустом файле — None."""
    path = tmp_path / "heartbeat"
    path.write_bytes(b"")
    assert read_heartbeat(str(path)) is None


def test_read_heartbeat_broken_json_is_none(tmp_path):
    """Интерфейс: повреждённый файл — None, а не исключение."""
    path = tmp_path / "heartbeat"
    path.write_text("{не json", encoding="utf-8")
    assert read_heartbeat(str(path)) is None
    path.write_bytes(b"\x00\x01\x02")
    assert read_heartbeat(str(path)) is None


def test_read_heartbeat_missing_file_is_none(tmp_path):
    """OPS-1 (задача 12) читает heartbeat до первой записи сборщика —
    отсутствие файла не должно быть исключением."""
    assert read_heartbeat(str(tmp_path / "нет-файла")) is None


# ── append_gz_lines ──────────────────────────────────────────────────────────

def test_append_gz_lines_twice_reads_four_lines_in_order(tmp_path):
    """Строка таблицы: дважды по 2 строки — gzip.open(...).read() даёт
    4 строки по порядку."""
    path = tmp_path / "containers" / "homecloud_stt.log.gz"
    path.parent.mkdir(parents=True)
    append_gz_lines(str(path), ["первая строка\n", "вторая строка\n"])
    append_gz_lines(str(path), ["третья строка\n", "четвёртая строка\n"])

    with gzip.open(str(path), "rt", encoding="utf-8") as fh:
        text = fh.read()
    assert text == ("первая строка\nвторая строка\n"
                    "третья строка\nчетвёртая строка\n")
    assert text.splitlines() == ["первая строка", "вторая строка",
                                 "третья строка", "четвёртая строка"]


def test_append_gz_lines_appends_new_block_without_rewriting(tmp_path):
    """«Новый gzip-блок в конец»: после второго дописывания файл начинается
    теми же байтами, что после первого — старый блок не пересобран."""
    path = tmp_path / "ste.log.gz"
    append_gz_lines(str(path), ["a\n", "b\n"])
    first = path.read_bytes()
    append_gz_lines(str(path), ["c\n", "d\n"])
    second = path.read_bytes()
    assert second.startswith(first)
    assert len(second) > len(first)


# ── close_day ────────────────────────────────────────────────────────────────

def test_close_day_compresses_journal_and_removes_source(tmp_path):
    """Строка таблицы: есть journal.log.xz, нет journal.log, содержимое
    совпадает; временных файлов после закрытия дня не осталось."""
    day = "2026-10-12"
    day_dir = tmp_path / "hot" / day
    day_dir.mkdir(parents=True)
    original = ("окт 12 03:14:34 nas kernel: строка журнала\n"
                "окт 12 03:15:34 nas kernel: вторая строка\n")
    (day_dir / "journal.log").write_text(original, encoding="utf-8")

    close_day(str(tmp_path / "hot"), day)

    assert (day_dir / "journal.log.xz").exists()
    assert not (day_dir / "journal.log").exists()
    assert sorted(p.name for p in day_dir.iterdir()) == ["journal.log.xz"]
    with lzma.open(str(day_dir / "journal.log.xz"), "rt", encoding="utf-8") as fh:
        assert fh.read() == original


# ── hot_size_bytes / prune_hot ───────────────────────────────────────────────

def _build_hot(tmp_path, day_ts_list, kb_metrics=200, kb_procs=50, kb_log=10):
    hot = tmp_path / "hot"
    for dts in day_ts_list:
        d = hot / _utc_day_name(dts)
        d.mkdir(parents=True)
        (d / "metrics.db").write_bytes(b"\x00" * (kb_metrics * 1024))
        (d / "procs.db").write_bytes(b"\x00" * (kb_procs * 1024))
        cdir = d / "containers"
        cdir.mkdir()
        (cdir / "x.log.gz").write_bytes(b"\x00" * (kb_log * 1024))
    return hot


def test_hot_size_bytes_sums_whole_tree(tmp_path):
    hot = _build_hot(tmp_path, [T0, T0 - 86400])
    assert hot_size_bytes(str(hot)) == 2 * (200 + 50 + 10) * 1024


def test_prune_hot_oldest_metrics_then_procs_keeps_containers_and_today(tmp_path):
    """Строка таблицы: 9 дней × (metrics.db 200 КБ, procs.db 50 КБ,
    containers/x.log.gz 10 КБ), предел 1 МБ — удалены самые старые metrics.db,
    потом procs.db; ни одного containers/; сегодняшний день цел; итог ≤ предела
    или удалять больше нечего.

    День ровно на границе keep_days не создаётся: формулировка допускает и
    «последние 7 дней», и «старше 7 суток» — без дня на самой границе оба
    прочтения дают один и тот же результат.
    """
    today_start = int(time.time()) // 86400 * 86400
    days = [today_start - k * 86400 for k in (0, 1, 2, 3, 4, 5, 6, 8, 9)]
    hot = _build_hot(tmp_path, days)
    assert hot_size_bytes(str(hot)) == 9 * (200 + 50 + 10) * 1024

    deleted = prune_hot(str(hot), 1024 * 1024, keep_days=7)

    # ровно два самых старых дня и оба их файла; пути — в пределах «горячего»
    oldest = _utc_day_name(days[8])   # возраст 9 суток
    second = _utc_day_name(days[7])   # возраст 8 суток
    got = set(os.path.relpath(str(p), str(hot)) for p in deleted)
    assert got == set([
        os.path.join(oldest, "metrics.db"), os.path.join(second, "metrics.db"),
        os.path.join(oldest, "procs.db"), os.path.join(second, "procs.db"),
    ])

    # внутри каждого вида сначала самые старые
    order = dict((os.path.relpath(str(p), str(hot)), i) for i, p in enumerate(deleted))
    assert order[os.path.join(oldest, "metrics.db")] < order[os.path.join(second, "metrics.db")]
    assert order[os.path.join(oldest, "procs.db")] < order[os.path.join(second, "procs.db")]

    # containers/ не тронуты ни в одном дне
    for dts in days:
        assert (hot / _utc_day_name(dts) / "containers" / "x.log.gz").exists()

    # сегодняшний день цел
    today = _utc_day_name(days[0])
    for name in ("metrics.db", "procs.db", "containers"):
        assert (hot / today / name).exists()

    # защищённые дни целы, самые старые — очищены; предел превышен, но удалять
    # больше нечего (второе плечо «≤ предела или удалять больше нечего»)
    for dts in days[:7]:
        for name in ("metrics.db", "procs.db"):
            assert (hot / _utc_day_name(dts) / name).exists()
    for dts in days[7:]:
        for name in ("metrics.db", "procs.db"):
            assert not (hot / _utc_day_name(dts) / name).exists()
    assert hot_size_bytes(str(hot)) > 1024 * 1024


def test_prune_hot_under_cap_deletes_nothing(tmp_path):
    """Обратный случай: под пределом prune_hot ничего не удаляет."""
    hot = _build_hot(tmp_path, [T0 - 86400])
    assert hot_size_bytes(str(hot)) < 1024 * 1024

    assert prune_hot(str(hot), 1024 * 1024, keep_days=7) == []
    assert (hot / _utc_day_name(T0 - 86400) / "metrics.db").exists()
    assert (hot / _utc_day_name(T0 - 86400) / "procs.db").exists()
