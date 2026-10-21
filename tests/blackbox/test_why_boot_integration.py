"""End-to-end boot evidence tests with synthetic Catalog and DayStore files."""
import json
import os

from blackbox.config import Config
from blackbox.store import Catalog, DayStore
from blackbox.why.cli import main
from blackbox.why.evidence import collect_boot
from blackbox.why.rules import evaluate


def _config(root):
    return Config(ssd_root=str(root / "ssd"), fallback_root=str(root / "fallback"),
                  ssd_mount=str(root / "ssd"))


def _boot_catalog(cfg, start, end):
    os.makedirs(cfg.ssd_root)
    catalog = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    catalog.upsert_boot({"boot_id": "boot-old", "start": start - 10000,
                         "end": end, "clean": False, "last_heartbeat": end,
                         "reset_source": "unknown", "pstore": [],
                         "verdict": None, "confidence": None})
    catalog.set_cursor("boot-heartbeat:boot-old", json.dumps({
        "boot_id": "boot-old", "ts": end,
        "power": {"vin_mv": 4610, "vin_ma": 1200, "not_allowed": "secret"}}))
    catalog.close()


def test_boot_includes_recent_daystore_samples_and_short_power(tmp_path, capsys):
    cfg = _config(tmp_path)
    start, end = 1791756480, 1791763680
    _boot_catalog(cfg, start, end)
    day = "2026-10-12"
    store = DayStore(os.path.join(cfg.ssd_root, "hot"), day)
    store.add_samples([{"ts": end - 10, "vin_mv": 4610, "vin_ma": 1200}])
    store.add_procs([{"ts": end - 5, "pid": 44, "comm": "worker", "owner": "host",
                      "cmd": "worker", "state": "D", "wchan": "fuse_wait",
                      "cpu_pct": 0.0, "rss_mb": 1.0}])
    store.flush()
    store.close()

    evidence = collect_boot(cfg, -1)
    _assert_boot_evidence(evidence, cfg)

    assert main(["--boot", "-1", "--short"], cfg=cfg) == 0
    output = capsys.readouterr().out
    assert "last seen:" in output and "power: vin_mv=4610" in output
    assert "not_allowed" not in output and "secret" not in output


def _assert_boot_evidence(evidence, cfg):
    assert evidence.samples[-1]["vin_mv"] == 4610
    assert evidence.procs[-1]["state"] == "D"
    assert evidence.heartbeat["power"]["vin_mv"] == 4610
    verdicts = evaluate(evidence, cfg)
    assert any(item["cls"] == "unclean_boot" and item["confidence"] == "probable"
               for item in verdicts)


def test_boot_merge_prefers_fresh_ssd_active_and_closed_fallback_row(tmp_path):
    cfg = _config(tmp_path)
    os.makedirs(cfg.ssd_root)
    os.makedirs(cfg.fallback_root)
    ssd = Catalog(os.path.join(cfg.ssd_root, "catalog.db"))
    _upsert(ssd, "current", 1791765000, None, None)
    _upsert(ssd, "previous", 1791750000, None, None)
    ssd.set_cursor("active_boot", "current")
    ssd.close()
    fallback = Catalog(os.path.join(cfg.fallback_root, "catalog.db"))
    _upsert(fallback, "current", 1791764000, None, None)
    _upsert(fallback, "previous", 1791750000, 1791763680, 1791763670)
    fallback.set_cursor("active_boot", "current")
    fallback.close()

    evidence = collect_boot(cfg, -1)
    assert evidence.boot["boot_id"] == "previous"
    assert evidence.boot["end"] == 1791763680


def _upsert(catalog, boot_id, start, end, last_heartbeat):
    catalog.upsert_boot({"boot_id": boot_id, "start": start, "end": end,
                         "clean": False if end else None,
                         "last_heartbeat": last_heartbeat,
                         "reset_source": "unknown", "pstore": [],
                         "verdict": None, "confidence": None})
