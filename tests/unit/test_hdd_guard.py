"""OPS-2: deterministic tests for scripts/monitoring/hdd_guard.py.

Moved out of test_container_watchdog.py (review round 1, 2026-10-15) together
with the module itself — the watchdog's own tests now only check the wiring
(_load_hdd_guard), not this logic."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/monitoring/hdd_guard.py"


def load():
    spec = importlib.util.spec_from_file_location("hdd_guard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def container(mounts=()):
    return {"name": "homecloud_demo", "mounts": list(mounts)}


def write_mounts(path, mount="/mnt/hdd2tb", device="/dev/sdb1"):
    path.write_text("%s %s fuseblk rw 0 0\n" % (device, mount), encoding="utf-8")


def write_diskstats(path, dev="sdb1", reads="10", sectors_read="20",
                    writes="30", sectors_written="40"):
    # Поля diskstats 1-индексные: 3=имя устройства, 4=reads, 6=sectors_read,
    # 8=writes, 10=sectors_written (остальные — нули-заполнители).
    path.write_text(
        "   8       0 %s %s 0 %s 0 %s 0 %s 0 0 0 0\n" % (
            dev, reads, sectors_read, writes, sectors_written),
        encoding="utf-8")


# ── hdd_probe: absent / ok / hung, с подтверждением по /proc/diskstats ───────

def test_hdd_probe_absent_when_not_in_proc_mounts(tmp_path):
    mod = load()
    mounts_file = tmp_path / "mounts"
    mounts_file.write_text("", encoding="utf-8")
    assert mod.hdd_probe(mount="/mnt/hdd2tb", mounts_path=str(mounts_file)) == "absent"


def test_hdd_probe_ok_when_stat_answers_without_touching_diskstats(tmp_path):
    mod = load()
    mounts_file = tmp_path / "mounts"
    write_mounts(mounts_file)
    ok_run = mock.Mock(return_value=mock.Mock(returncode=0))
    sleep = mock.Mock()
    status = mod.hdd_probe(mount="/mnt/hdd2tb", mounts_path=str(mounts_file),
                           run=ok_run, sleep=sleep)
    assert status == "ok"
    sleep.assert_not_called()  # stat ответил — сверку по diskstats не запускаем


def test_hdd_probe_hung_when_stat_fails_and_diskstats_do_not_move(tmp_path):
    mod = load()
    mounts_file = tmp_path / "mounts"
    diskstats_file = tmp_path / "diskstats"
    write_mounts(mounts_file)
    write_diskstats(diskstats_file)
    bad_run = mock.Mock(return_value=mock.Mock(returncode=1))
    status = mod.hdd_probe(mount="/mnt/hdd2tb", mounts_path=str(mounts_file),
                           diskstats_path=str(diskstats_file), run=bad_run,
                           sleep=lambda _seconds: None)
    assert status == "hung"


def test_hdd_probe_ok_when_stat_times_out_but_diskstats_keep_moving(tmp_path):
    # «Диск живой, просто медленный» (круг ревью 1): счётчики диска меняются
    # за время пробы, хотя stat не ответил — это НЕ зависание.
    mod = load()
    mounts_file = tmp_path / "mounts"
    diskstats_file = tmp_path / "diskstats"
    write_mounts(mounts_file)
    write_diskstats(diskstats_file, reads="10")
    hung_run = mock.Mock(side_effect=subprocess.TimeoutExpired(cmd="stat", timeout=10))

    def advance_diskstats(_seconds):
        write_diskstats(diskstats_file, reads="11")  # счётчик продвинулся

    status = mod.hdd_probe(mount="/mnt/hdd2tb", mounts_path=str(mounts_file),
                           diskstats_path=str(diskstats_file), run=hung_run,
                           sleep=advance_diskstats)
    assert status == "ok"


def test_hdd_probe_hung_when_device_missing_from_diskstats(tmp_path):
    # Устройство не нашли в /proc/diskstats — подтвердить активность нечем,
    # осторожный вариант: считаем это зависанием, а не "живым".
    mod = load()
    mounts_file = tmp_path / "mounts"
    diskstats_file = tmp_path / "diskstats"
    write_mounts(mounts_file, device="/dev/sdb1")
    write_diskstats(diskstats_file, dev="sda1")  # другое устройство
    bad_run = mock.Mock(return_value=mock.Mock(returncode=1))
    status = mod.hdd_probe(mount="/mnt/hdd2tb", mounts_path=str(mounts_file),
                           diskstats_path=str(diskstats_file), run=bad_run,
                           sleep=lambda _seconds: None)
    assert status == "hung"


# ── holds_hdd ─────────────────────────────────────────────────────────────────

def test_holds_hdd_matches_exact_source_and_subpaths_only():
    mod = load()
    assert mod.holds_hdd(container(mounts=("/mnt/hdd2tb",)))
    assert mod.holds_hdd(container(mounts=("/mnt/hdd2tb/Downloads",)))
    assert not mod.holds_hdd(container(mounts=("/mnt/storage",)))
    assert not mod.holds_hdd(container(mounts=("/mnt/hdd2tb-other",)))
    assert not mod.holds_hdd(container(mounts=()))


# ── hdd_alert_text / hdd_status_note ────────────────────────────────────────

def test_hdd_alert_text_distinguishes_absent_and_hung():
    mod = load()
    absent = mod.hdd_alert_text("absent")
    hung = mod.hdd_alert_text("hung")
    assert "не смонтирован" in absent
    assert "не отвечает" in hung
    assert "hdd_hang_recover.sh" in absent and "hdd_hang_recover.sh" in hung


def test_hdd_status_note_cooldown_and_recovery():
    mod = load()
    state = {}
    first = mod.hdd_status_note(state, "hung", 1000)
    assert first is not None and "hdd_hang_recover.sh" in first

    # repeat 30 min later — silence
    assert mod.hdd_status_note(state, "hung", 1000 + 1800) is None

    # repeat 61 min after the FIRST alert — alerts again
    second = mod.hdd_status_note(state, "hung", 1000 + 3660)
    assert second is not None and "hdd_hang_recover.sh" in second

    # recovery — always reported immediately, regardless of cooldown
    recovered = mod.hdd_status_note(state, "ok", 1000 + 3700)
    assert recovered is not None and "снова отвечает" in recovered

    # staying ok afterwards is silent
    assert mod.hdd_status_note(state, "ok", 1000 + 4000) is None


def test_hdd_status_note_absent_text():
    mod = load()
    note = mod.hdd_status_note({}, "absent", 1000)
    assert note is not None and "не смонтирован" in note


if __name__ == "__main__":
    # Ворота запускают tests/unit как "python файл"; без этого блока функции
    # pytest не выполнялись бы вовсе и файл засчитывался бы пройденным.
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
