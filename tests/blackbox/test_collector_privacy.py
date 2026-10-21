"""Synthetic privacy and memory bounds for collector event paths."""
import json
import os
import queue
import threading

from blackbox import collector_events
from blackbox.collector_storage import Storage
from blackbox.config import Config
from blackbox.redact import HIDDEN, TEXT_HIDDEN
from blackbox.store import Catalog

T0 = 1791861274
SECRET = "mock_sentinel_secret_value"


def _cfg(tmp_path):
    return Config(ssd_root=str(tmp_path / "ssd"),
                  fallback_root=str(tmp_path / "fallback"),
                  ssd_mount=str(tmp_path / "mount"),
                  proc_root=str(tmp_path / "proc"))


def test_multiline_flag_scrubbing_and_dict_keys(tmp_path):
    cfg = _cfg(tmp_path)
    text = collector_events.redact_text(
        "", "run --password " + SECRET + "\nnext --token " + SECRET, cfg)
    event = collector_events.redact_event(
        {"ts": T0, "detail": {"token=" + SECRET: "safe"}}, cfg)
    assert SECRET not in text + json.dumps(event)
    assert text.count(HIDDEN) == 2


def test_unknown_owner_journal_masks_family_text_per_line(tmp_path):
    cfg = _cfg(tmp_path)
    store = Storage(cfg, T0, ismount=lambda path: True)
    store.append_journal(["обычная строка\n", "наша семейная запись\n"], T0)
    path = os.path.join(cfg.ssd_root, "hot", "2026-10-13", "journal.log")
    saved = open(path, "r", encoding="utf-8").read()
    assert "обычная строка" in saved
    assert TEXT_HIDDEN in saved and "наша семейная запись" not in saved
    store.close()


def test_tail_redacts_before_byte_truncation(tmp_path):
    cfg = _cfg(tmp_path)
    raw = "safe-prefix " * 5000 + " --password " + SECRET + "\n"
    result = collector_events.bounded_tail([raw], "", cfg, limit=1024)
    assert SECRET not in "".join(result)
    assert sum(len(line.encode("utf-8")) for line in result) <= 1024


def test_producer_rejects_oversize_payload_and_counts_it():
    stopped = threading.Event()
    payloads = [{"value": "x" * collector_events.MAX_EVENT_BYTES}, {"ok": True}]

    class Source(object):
        def events(self, since):
            for item in payloads:
                yield item
            stopped.set()

    out = queue.Queue(maxsize=2)
    dropped = [0]
    collector_events._event_producer(Source(), out, stopped, [T0], dropped, None)
    assert out.qsize() == 1 and dropped[0] == 1


def test_event_buffer_byte_budget_emits_drop_count(tmp_path):
    cfg = _cfg(tmp_path)
    store = Storage(cfg, T0, ismount=lambda path: True)
    for index in range(100):
        store.buffer_event({"ts": T0 + index, "source": "test", "kind": "bulk",
                            "subject": None, "severity": "info",
                            "detail": {"data": "x" * 12000}})
        assert store.event_bytes <= collector_events.EVENT_BUFFER_BYTES_MAX
    assert store.event_drops > 0
    store.flush(T0 + 100)
    events = store.catalog.events(T0, T0 + 200)
    reports = [event for event in events if event["kind"] == "events_dropped"]
    assert reports and reports[0]["detail"]["count"] > 0
    assert max(collector_events.serialized_size(event) for event in events) <= collector_events.MAX_EVENT_BYTES
    store.close()
