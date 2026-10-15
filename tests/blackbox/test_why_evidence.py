"""OBS-1 «чёрный ящик», задача 11 — сбор доказательств (blackbox/why/evidence.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «### Задача 11».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md, раздел 4.4.
Контракты данных (sample, disk_sample, proc row, event, boot row, verdict) — раздел
«Контракты данных» плана.

Покрытие таблицы случаев задачи 11 (вторая половина — tests/blackbox/test_why_cli.py):
  * окно, которого нет нигде — test_collect_empty_window_returns_empty_evidence_and_unknown_verdict;
  * окно в архиве HDD — test_collect_reads_archive_and_removes_tmp_dir;
  * архив повреждён — test_collect_truncated_archive_does_not_raise;
  * --container — test_collect_container_filter_keeps_only_that_containers_events.

TDD: пакета services/blackbox ещё нет, поэтому файл обязан падать на импорте
(ModuleNotFoundError при сборе тестов), а не по другой причине.

Ни одного настоящего subprocess, сокета или сети: «горячее» и архивы — каталоги
в tmp_path, все окна — в прошлом, поэтому журнал берётся из journal.log[.xz]
(journalctl не зовётся вовсе). Работает на Windows и Linux.
"""

import json
import os
import shutil
import tarfile

from blackbox.config import Config
from blackbox.store import Catalog, DayStore
from blackbox.why.evidence import collect, collect_boot
from blackbox.why.rules import evaluate

# Секунды эпохи UTC (раздел «Общие ограничения»: сутки — по UTC).
OCT1 = 1790812800       # 2026-10-01 00:00 UTC
OCT2 = 1790905920       # 2026-10-02 00:00 UTC
OCT12 = 1791756480      # 2026-10-12 00:00 UTC
MAR1_2024 = 1709251200  # 2024-03-01 00:00 UTC
MAR2_2024 = 1709337600  # 2024-03-02 00:00 UTC


# ── подставное «горячее», архивы, снимки ─────────────────────────────────────


def _cfg(tmp_path, **over):
    """Config «чёрного ящика» с путями в tmp_path (никаких /mnt/storage на машине тестов)."""
    base = dict(
        ssd_root=str(tmp_path / "ssd"),
        hdd_archive_root=str(tmp_path / "hdd"),
        fallback_root=str(tmp_path / "fallback"),
    )
    base.update(over)
    return Config(**base)


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


def _write_day(hot, day, samples):
    """День «горячего» на SSD — ровно так его пишет задача 3 (DayStore)."""
    store = DayStore(str(hot), day)
    store.add_samples(samples)
    store.flush()
    store.close()


def _pack_archive(hot, day, path):
    """Недельный архив задачи 9: дни — каталоги верхнего уровня внутри tar.xz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(path), "w:xz") as tf:
        tf.add(str(hot / day), arcname=day)
    return path


def _archive_row(week, path, first_day, last_day):
    """Строка таблицы archive в catalog.db (контракт задачи 3)."""
    return {"week": week, "path": str(path), "sha256": "a" * 64,
            "first_day": first_day, "last_day": last_day,
            "created": OCT1, "verified": True}


def _write_boot_snapshot(ssd, boot_id, pstore_names):
    """Снимок загрузки задачи 8: boots/<boot_id>/summary.json + копии pstore."""
    snap = ssd / "boots" / boot_id
    (snap / "pstore").mkdir(parents=True)
    for name in pstore_names:
        (snap / "pstore" / name).write_text("ramoops", encoding="utf-8")
    summary = {"boot_id": boot_id, "reset_source": "TEGRA_POWER_ON_RESET",
               "pstore": list(pstore_names)}
    (snap / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return snap


# ── collect: «горячее» и пустое окно ─────────────────────────────────────────


def test_collect_reads_hot_day_samples(tmp_path):
    """Основной путь интерфейса: дни из «горячего» на SSD — в Evidence замеры
    контракта sample с точными значениями."""
    cfg = _cfg(tmp_path)
    _write_day(tmp_path / "ssd" / "hot", "2026-10-12",
               [_sample(OCT12 + 3600), _sample(OCT12 + 7200, vin_mv=4610)])

    ev = collect(cfg, OCT12, OCT12 + 86400)

    assert ev.window == (OCT12, OCT12 + 86400)
    assert [s["ts"] for s in ev.samples] == [OCT12 + 3600, OCT12 + 7200]
    assert ev.samples[0]["vin_mv"] == 5080
    assert ev.samples[0]["mem_avail_mb"] == 1327
    assert ev.samples[1]["vin_mv"] == 4610


def test_collect_empty_window_returns_empty_evidence_and_unknown_verdict(tmp_path):
    """Строка таблицы: окно 2024 года нет ни в «горячем», ни в каталоге архивов —
    Evidence пуст, а вердикт — честное «неизвестно: данных нет за …»
    (фокус ревью №5 на уровне доказательств; вывод команды проверяет
    test_why_window_without_data в test_why_cli.py)."""
    cfg = _cfg(tmp_path)
    os.makedirs(cfg.ssd_root)
    Catalog(os.path.join(cfg.ssd_root, "catalog.db"))  # каталог есть, архивов за 2024 нет

    ev = collect(cfg, MAR1_2024, MAR2_2024)

    assert ev.window == (MAR1_2024, MAR2_2024)
    assert ev.samples == []
    assert ev.disk_samples == []
    assert ev.procs == []
    assert ev.events == []
    assert ev.journal == []

    verdicts = evaluate(ev, cfg)
    assert len(verdicts) == 1
    assert verdicts[0]["cls"] == "data"
    assert verdicts[0]["confidence"] == "unknown"
    assert "данных нет за" in verdicts[0]["verdict"]


# ── collect: архив HDD ───────────────────────────────────────────────────────


def test_collect_reads_archive_and_removes_tmp_dir(tmp_path):
    """Строка таблицы: окно в архиве HDD (подложенный архив) — данные найдены;
    каталог распаковки tmp/<pid> удалён после."""
    cfg = _cfg(tmp_path)
    hot = tmp_path / "ssd" / "hot"
    _write_day(hot, "2026-10-01",
               [_sample(OCT1 + 3600), _sample(OCT1 + 7200, mem_avail_mb=120)])
    archive = _pack_archive(hot, "2026-10-01",
                            tmp_path / "hdd" / "2026" / "blackbox-2026-W40.tar.xz")
    shutil.rmtree(str(hot / "2026-10-01"))  # дни уже ушли с SSD (после сверки sha256)

    cat = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    cat.add_archive(_archive_row("2026-W40", archive, "2026-09-28", "2026-10-04"))

    ev = collect(cfg, OCT1, OCT2)

    assert [s["ts"] for s in ev.samples] == [OCT1 + 3600, OCT1 + 7200]
    assert ev.samples[0]["vin_mv"] == 5080
    assert ev.samples[1]["mem_avail_mb"] == 120

    tmp_root = os.path.join(cfg.ssd_root, "tmp")
    assert not os.path.exists(tmp_root) or os.listdir(tmp_root) == [], \
        "каталог распаковки tmp/<pid> обязан быть удалён после ответа"


def test_collect_truncated_archive_does_not_raise(tmp_path):
    """Строка таблицы: архив повреждён (обрезанный .tar.xz) — исключения нет;
    причина «архив повреждён» доходит до вердикта unknown (test_why_cli.py)."""
    cfg = _cfg(tmp_path)
    hot = tmp_path / "ssd" / "hot"
    _write_day(hot, "2026-10-01", [_sample(OCT1 + 3600)])
    archive = _pack_archive(hot, "2026-10-01",
                            tmp_path / "hdd" / "2026" / "blackbox-2026-W40.tar.xz")
    data = archive.read_bytes()
    archive.write_bytes(data[:len(data) // 2])  # обрезан
    shutil.rmtree(str(hot / "2026-10-01"))

    cat = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    cat.add_archive(_archive_row("2026-W40", archive, "2026-09-28", "2026-10-04"))

    ev = collect(cfg, OCT1, OCT2)  # обязан вернуться, а не бросить ошибку lzma/tarfile

    assert ev.window == (OCT1, OCT2)


# ── collect: фильтр --container ──────────────────────────────────────────────


def test_collect_container_filter_keeps_only_that_containers_events(tmp_path):
    """Строка таблицы: --container homecloud_stt — в Evidence только события
    этого контейнера; чужой контейнер и события других источников отсеяны."""
    cfg = _cfg(tmp_path)
    os.makedirs(cfg.ssd_root)
    cat = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    cat.add_events([
        _event(OCT12 + 3600, "docker", "start", "homecloud_stt", "info",
               {"image": "stt"}),
        _event(OCT12 + 3900, "docker", "start", "homecloud_nextcloud", "info",
               {"image": "nextcloud"}),
        _event(OCT12 + 4200, "docker", "die", "homecloud_stt", "crit",
               {"exitCode": 1}),
        _event(OCT12 + 4300, "probe", "dns_down", "dns", "warn", {}),
    ])

    ev = collect(cfg, OCT12, OCT12 + 86400, container="homecloud_stt")

    assert [e["subject"] for e in ev.events] == ["homecloud_stt", "homecloud_stt"]
    assert [e["kind"] for e in ev.events] == ["start", "die"]
    assert not any(e["subject"] == "homecloud_nextcloud" for e in ev.events)


# ── collect_boot ─────────────────────────────────────────────────────────────


def test_collect_boot_reads_last_boot_snapshot_and_pstore(tmp_path):
    """collect_boot(which=-1): прошлая загрузка собирается из catalog.db и снимка
    boots/<boot_id>/; правило раздела 6 даёт unclean_boot, факт, «паника ядра»
    (на этом стоит nas-why --boot -1 --short)."""
    cfg = _cfg(tmp_path)
    boot_id = "boot-2026-10-12-abc"
    _write_boot_snapshot(tmp_path / "ssd", boot_id, ["dmesg-ramoops-0"])
    cat = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    cat.upsert_boot(_boot_row(boot_id, OCT12 + 1000, end=OCT12 + 7200,
                              clean=False, last_heartbeat=OCT12 + 7190,
                              reset_source="TEGRA_POWER_ON_RESET",
                              pstore=["dmesg-ramoops-0"]))

    ev = collect_boot(cfg, which=-1)

    assert ev.boot is not None
    assert ev.boot["boot_id"] == boot_id
    assert bool(ev.boot["clean"]) is False
    assert "dmesg-ramoops-0" in ev.pstore

    unclean = [v for v in evaluate(ev, cfg) if v["cls"] == "unclean_boot"]
    assert len(unclean) == 1
    assert unclean[0]["confidence"] == "fact"
    assert "паника ядра" in unclean[0]["verdict"]
