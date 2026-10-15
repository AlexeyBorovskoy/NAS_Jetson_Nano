"""OBS-1 «чёрный ящик», задача 11 — команда nas-why (blackbox/why/cli.py).

План: docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md, «### Задача 11».
Спецификация: docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md, раздел 4.4.

Покрытие таблицы случаев задачи 11:
  * окно 2024 года — test_why_window_without_data (фокус ревью №5, имя — из плана);
  * архив повреждён — test_why_corrupt_archive_reports_unknown_with_reason;
  * --short на нештатной загрузке — test_why_short_on_unclean_boot_is_at_most_six_lines_first_is_verdict;
  * --container — test_why_container_shows_only_that_container.
Решения ведущего R1 (record_boot_verdict и флаг --record):
  * test_record_boot_verdict_writes_verdict_and_confidence;
  * test_why_record_flag_updates_catalog.

Пути «чёрного ящика» подставляются через переменные NAS_BLACKBOX_* (load_config,
задача 1): ни /etc/nas-blackbox.json, ни /mnt/storage на машине тестов не нужны.

TDD: пакета services/blackbox ещё нет — файл обязан падать на импорте
(ModuleNotFoundError при сборе). Ни subprocess, ни сети, ни сокетов: все данные —
каталоги в tmp_path, окна — в прошлом (journalctl не зовётся). Windows и Linux.
"""

import gzip
import json
import lzma
import os
import tarfile

from blackbox.config import Config
from blackbox.store import Catalog
from blackbox.why.cli import main, record_boot_verdict
from blackbox.why.evidence import collect_boot
from blackbox.why.rules import evaluate

OCT12 = 1791756480  # 2026-10-12 00:00 UTC


# ── подставное состояние и подстановка путей ─────────────────────────────────


def _env(monkeypatch, tmp_path):
    """Каталоги «чёрного ящика» через переменные NAS_BLACKBOX_* (load_config);
    возвращает каталог SSD, в котором тест готовит состояние."""
    ssd = tmp_path / "ssd"
    ssd.mkdir()
    (tmp_path / "hdd").mkdir()
    monkeypatch.setenv("NAS_BLACKBOX_SSD_ROOT", str(ssd))
    monkeypatch.setenv("NAS_BLACKBOX_HDD_ARCHIVE_ROOT", str(tmp_path / "hdd"))
    monkeypatch.setenv("NAS_BLACKBOX_FALLBACK_ROOT", str(tmp_path / "fallback"))
    return ssd


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


def _unclean_boot(ssd, boot_id):
    """Прошлая загрузка без штатного выключения, с паникой ядра в pstore."""
    _write_boot_snapshot(ssd, boot_id, ["dmesg-ramoops-0"])
    cat = Catalog(os.path.join(str(ssd), "catalog.db"))
    cat.upsert_boot(_boot_row(boot_id, OCT12 + 1000, end=OCT12 + 7200, clean=False,
                              last_heartbeat=OCT12 + 7190,
                              reset_source="TEGRA_POWER_ON_RESET",
                              pstore=["dmesg-ramoops-0"]))
    return cat


def _write_journal_xz(path, lines):
    """День «горячего» задачи 3: закрытый день хранит журнал как journal.log.xz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(lzma.compress(("\n".join(lines) + "\n").encode("utf-8")))


def _write_container_log(ssd, day, name, lines):
    """Журнал контейнера задачи 7: <hot>/<день>/containers/<имя>.log.gz."""
    path = ssd / "hot" / day / "containers" / (name + ".log.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(str(path), "wb") as fh:
        fh.write("".join(lines).encode("utf-8"))


def _make_valid_archive(path, day="2026-09-22"):
    """Валидный недельный архив задачи 9 (день — каталог верхнего уровня);
    в тесте его затем обрезают, чтобы получить повреждённый."""
    day_dir = path.parent / "src" / day
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "metrics.db").write_bytes(b"")
    with tarfile.open(str(path), "w:xz") as tf:
        tf.add(str(day_dir), arcname=day)
    return path


# ── окно, которого нет нигде (фокус ревью №5) ────────────────────────────────


def test_why_window_without_data(tmp_path, capsys, monkeypatch):
    """Строка таблицы и фокус ревью №5: окно 2024 года нет ни в «горячем»,
    ни в каталоге архивов — код 0 и «неизвестно: данных нет за …»,
    а не исключение."""
    ssd = _env(monkeypatch, tmp_path)
    Catalog(os.path.join(str(ssd), "catalog.db"))  # каталог есть, архивов за 2024 нет

    rc = main(["--since", "2024-03-01 00:00", "--until", "2024-03-02 00:00"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "Traceback" not in out
    assert "данных нет за" in out          # текст вердикта класса data
    assert "неизвестно" in out.lower()     # уверенность unknown


# ── архив повреждён ──────────────────────────────────────────────────────────


def test_why_corrupt_archive_reports_unknown_with_reason(tmp_path, capsys, monkeypatch):
    """Строка таблицы: архив повреждён (обрезанный .tar.xz) — вердикт unknown
    с причиной «архив повреждён», без исключения."""
    ssd = _env(monkeypatch, tmp_path)
    archive = tmp_path / "hdd" / "2026" / "blackbox-2026-W39.tar.xz"
    archive.parent.mkdir(parents=True, exist_ok=True)
    _make_valid_archive(archive)
    data = archive.read_bytes()
    archive.write_bytes(data[:len(data) // 2])  # обрезан

    cat = Catalog(os.path.join(str(ssd), "catalog.db"))
    cat.add_archive({"week": "2026-W39", "path": str(archive), "sha256": "b" * 64,
                     "first_day": "2026-09-21", "last_day": "2026-09-27",
                     "created": OCT12, "verified": True})

    rc = main(["--since", "2026-09-22 00:00", "--until", "2026-09-23 00:00"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "Traceback" not in out
    assert "архив повреждён" in out
    assert "неизвестно" in out.lower()


# ── --short на нештатной загрузке ────────────────────────────────────────────


def test_why_short_on_unclean_boot_is_at_most_six_lines_first_is_verdict(tmp_path,
                                                                         capsys,
                                                                         monkeypatch):
    """Строка таблицы: --short на нештатной загрузке — ≤ 6 строк,
    первая — вердикт (для алерта D2, раздел 4.5)."""
    ssd = _env(monkeypatch, tmp_path)
    _unclean_boot(ssd, "boot-2026-10-12-abc")

    rc = main(["--boot", "-1", "--short"])

    assert rc == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) <= 6
    assert "паника ядра" in lines[0]  # verdict: unclean_boot, факт


# ── --container ──────────────────────────────────────────────────────────────


def test_why_container_shows_only_that_container(tmp_path, capsys, monkeypatch):
    """Строка таблицы: --container homecloud_stt — в хронологии только события
    и строки этого контейнера; чужой контейнер не упоминается вовсе."""
    ssd = _env(monkeypatch, tmp_path)
    day = "2026-10-12"
    cat = Catalog(os.path.join(str(ssd), "catalog.db"))
    cat.add_events([
        _event(OCT12 + 3 * 3600 + 1800, "docker", "die", "homecloud_stt", "crit",
               {"exitCode": 1}),
        _event(OCT12 + 3 * 3600 + 2100, "docker", "start", "homecloud_nextcloud",
               "info", {"image": "nextcloud"}),
    ])
    _write_journal_xz(ssd / "hot" / day / "journal.log.xz", [
        "2026-10-12T03:30:01+0000 jetson dockerd[900]: container homecloud_stt died",
        "2026-10-12T03:40:01+0000 jetson dockerd[900]: container homecloud_nextcloud restarted",
    ])
    _write_container_log(ssd, day, "homecloud_stt",
                         ["2026-10-12T03:31:00+0000 homecloud_stt started ok\n"])
    _write_container_log(ssd, day, "homecloud_nextcloud",
                         ["2026-10-12T03:41:00+0000 homecloud_nextcloud started ok\n"])

    rc = main(["--container", "homecloud_stt",
               "--since", "2026-10-12 00:00", "--until", "2026-10-13 00:00"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "homecloud_stt" in out
    assert "homecloud_nextcloud" not in out


# ── решение ведущего R1: вердикт прошлой загрузки в catalog.db ───────────────


def test_record_boot_verdict_writes_verdict_and_confidence(tmp_path):
    """Решение R1: record_boot_verdict(cfg, catalog) оценивает прошлую загрузку
    и записывает verdict/confidence в catalog.db (upsert_boot) — этим пользуется
    снимок загрузки (задача 8) и nas-why --record."""
    cfg = Config(ssd_root=str(tmp_path / "ssd"),
                 fallback_root=str(tmp_path / "fallback"),
                 hdd_archive_root=str(tmp_path / "hdd"))
    boot_id = "boot-2026-10-12-abc"
    cat = _unclean_boot(tmp_path / "ssd", boot_id)

    expected = [v for v in evaluate(collect_boot(cfg, -1), cfg)
                if v["cls"] == "unclean_boot"]
    assert len(expected) == 1  # случай однозначный: pstore есть, питания в окне нет
    expected = expected[0]

    result = record_boot_verdict(cfg, cat)

    boot = cat.get_boot(boot_id)
    assert isinstance(result, dict) and result
    assert boot["confidence"] == expected["confidence"] == "fact"
    # записан либо слаг класса, либо текст вердикта — но не что-то чужое
    assert boot["verdict"] in (expected["cls"], expected["verdict"])


def test_why_record_flag_updates_catalog(tmp_path, capsys, monkeypatch):
    """Решение R1: main(["--boot", "-1", "--record"]) оценивает прошлую загрузку
    и записывает вердикт с уверенностью в catalog.db."""
    ssd = _env(monkeypatch, tmp_path)
    boot_id = "boot-2026-10-12-abc"
    cat = _unclean_boot(ssd, boot_id)
    assert cat.get_boot(boot_id)["verdict"] is None  # до --record вердикта нет

    rc = main(["--boot", "-1", "--record"])

    assert rc == 0
    assert "Traceback" not in capsys.readouterr().out
    boot = Catalog(os.path.join(str(ssd), "catalog.db")).get_boot(boot_id)
    assert boot["confidence"] == "fact"
    assert boot["verdict"]  # записан, не остался пустым
