"""Качалка: ссылки, выбор диска, учёт, страж места (спецификация §2, §4, §5, §7).
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"
GB = 1024 ** 3


def load():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "DL_SSD_MIN_FREE_GB": "40", "DL_HDD_MIN_FREE_GB": "50", "DL_SSD_MAX_GB": "20",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.downloads")


class FakeAria2:
    """Имитация aria2 JSON-RPC: хранит закачки, записывает вызовы."""

    def __init__(self):
        self.calls = []
        self.status = {}
        self.n = 0

    async def call(self, method, *params):
        self.calls.append((method, params))
        if method in ("addUri", "addTorrent"):
            self.n += 1
            gid = "g%d" % self.n
            self.status[gid] = {"gid": gid, "status": "active", "totalLength": "0",
                                "completedLength": "0", "downloadSpeed": "0", "files": []}
            return gid
        if method == "tellStatus":
            return self.status[params[0]]
        if method == "tellActive":
            return [s for s in self.status.values() if s["status"] == "active"]
        if method == "tellWaiting":
            return [s for s in self.status.values() if s["status"] in ("waiting", "paused")]
        if method in ("forceRemove", "unpause", "changeOption", "pauseAll",
                      "unpauseAll", "removeDownloadResult"):
            return "OK"
        raise AssertionError(method)


def make(dl, tmp, ssd=150 * GB, hdd=400 * GB, size=None):
    aria = FakeAria2()

    async def head(url):
        return size

    d = dl.Downloads(aria2=aria, ledger=dl.Ledger(str(tmp / "ledger.json")),
                     head=head, disk_free=lambda: (ssd, hdd))
    return d, aria


# ── ссылки ────────────────────────────────────────────────────────────────────

def test_parse_link_accepts_magnet_and_http():
    dl = load()
    assert dl.parse_link("скачай magnet:?xt=urn:btih:ABC&dn=x").startswith("magnet:")
    assert dl.parse_link("вот https://example.org/f.iso.") == "https://example.org/f.iso"


@pytest.mark.parametrize("bad", [
    "file:///etc/passwd", "http://localhost/x", "http://192.168.0.50:8080/",
    "http://10.0.0.1/", "http://127.0.0.1/", "http://nas.local/f", "http://[::1]/",
    "http://169.254.1.1/", "magnet:?dn=no-hash", "просто текст",
])
def test_parse_link_rejects_internal_and_junk(bad):
    dl = load()
    with pytest.raises(dl.LinkError):
        dl.parse_link(bad)


# ── выбор диска ───────────────────────────────────────────────────────────────

def test_choose_target_small_goes_to_ssd():
    dl = load()
    assert dl.choose_target(19 * GB, 150 * GB, 400 * GB) == "ssd"


def test_choose_target_big_goes_to_hdd():
    dl = load()
    assert dl.choose_target(100 * GB, 150 * GB, 400 * GB) == "hdd"


def test_choose_target_small_but_ssd_tight_goes_to_hdd():
    dl = load()
    assert dl.choose_target(10 * GB, 45 * GB, 400 * GB) == "hdd"


def test_choose_target_refuses_when_hdd_cannot_hold_it():
    dl = load()
    with pytest.raises(dl.LinkError) as e:
        dl.choose_target(400 * GB, 150 * GB, 400 * GB)
    assert "ГБ" in str(e.value)


def test_choose_target_unknown_size_prefers_ssd():
    dl = load()
    assert dl.choose_target(None, 150 * GB, 400 * GB) == "ssd"
    assert dl.choose_target(None, 30 * GB, 400 * GB) == "hdd"


# ── постановка ────────────────────────────────────────────────────────────────

def test_http_link_sized_and_routed(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=100 * GB)
    reply = asyncio.run(d.add_link("https://example.org/big.iso", 42, "ivan"))
    method, params = aria.calls[-1]
    assert method == "addUri"
    assert params[1]["dir"] == "/downloads/hdd/.incomplete"
    assert params[1]["file-allocation"] == "none"
    assert "HDD" in reply and "big.iso" in reply
    entry = dl.Ledger(str(tmp_path / "ledger.json")).load()["g1"]
    assert entry["chat_id"] == 42 and entry["user"] == "ivan" and entry["state"] == "active"


def test_http_link_refused_when_too_big(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=500 * GB)
    reply = asyncio.run(d.add_link("https://example.org/huge.iso", 42, "ivan"))
    assert reply.startswith("❌")
    assert not any(c[0] == "addUri" for c in aria.calls)


def test_magnet_waits_for_metadata_then_routes_by_size(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path)
    reply = asyncio.run(d.add_link("magnet:?xt=urn:btih:ABC", 7, "olga"))
    assert "Принял" in reply
    # метаданные получены: aria2 создал закачку g2 на паузе (pause-metadata)
    aria.status["g1"].update(status="complete", followedBy=["g2"])
    aria.status["g2"] = {"gid": "g2", "status": "paused", "totalLength": str(30 * GB),
                         "completedLength": "0", "downloadSpeed": "0",
                         "bittorrent": {"info": {"name": "Distro"}}, "files": []}
    msgs = asyncio.run(d.tick())
    assert ("changeOption", ("g2", {"dir": "/downloads/hdd/.incomplete",
                                    "file-allocation": "none"})) in aria.calls
    assert ("unpause", ("g2",)) in aria.calls
    assert msgs == [(7, "⏬ Качаю: Distro — 30.0 ГБ, на HDD")]


def test_torrent_file_added_paused_then_routed(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path)
    asyncio.run(d.add_torrent(b"d8:announce...e", 5, "admin"))
    method, params = aria.calls[-1]
    assert method == "addTorrent" and params[2] == {"pause": "true"}
    aria.status["g1"].update(status="paused", totalLength=str(2 * GB),
                             bittorrent={"info": {"name": "Small"}})
    msgs = asyncio.run(d.tick())
    assert ("changeOption", ("g1", {"dir": "/downloads/ssd/.incomplete",
                                    "file-allocation": "falloc"})) in aria.calls
    assert msgs == [(5, "⏬ Качаю: Small — 2.0 ГБ, на SSD")]


# ── завершение и учёт ─────────────────────────────────────────────────────────

def test_completion_notified_once_to_origin_chat(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=GB)
    asyncio.run(d.add_link("https://example.org/a.iso", 99, "ivan"))
    aria.status["g1"].update(status="complete", files=[{"path": "/downloads/ssd/.incomplete/a.iso"}])
    first = asyncio.run(d.tick())
    second = asyncio.run(d.tick())
    assert first == [(99, "✅ Готово: a.iso — " + dl.DONE_HINT)]
    assert second == []


def test_error_reported_with_reason(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=GB)
    asyncio.run(d.add_link("https://example.org/a.iso", 99, "ivan"))
    aria.status["g1"].update(status="error", errorMessage="404 Not Found")
    assert asyncio.run(d.tick()) == [(99, "❌ Не скачалось: a.iso — 404 Not Found")]


def test_ledger_survives_restart_and_broken_file(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=GB)
    asyncio.run(d.add_link("https://example.org/a.iso", 1, "ivan"))
    assert "g1" in dl.Ledger(str(tmp_path / "ledger.json")).load()
    (tmp_path / "ledger.json").write_text("{битый", encoding="utf-8")
    assert dl.Ledger(str(tmp_path / "ledger.json")).load() == {}


# ── страж места ───────────────────────────────────────────────────────────────

def test_guard_pauses_all_once_and_resumes(tmp_path):
    dl = load()
    free = {"ssd": 150 * GB, "hdd": 400 * GB}
    aria = FakeAria2()

    async def head(url):
        return GB

    d = dl.Downloads(aria2=aria, ledger=dl.Ledger(str(tmp_path / "l.json")), head=head,
                     disk_free=lambda: (free["ssd"], free["hdd"]))
    asyncio.run(d.add_link("https://example.org/a.iso", 3, "ivan"))
    free["hdd"] = 45 * GB
    msgs = asyncio.run(d.tick())
    assert ("pauseAll", ()) in aria.calls
    assert msgs and msgs[0][0] == 3 and msgs[0][1].startswith("⏸")
    aria.calls.clear()
    assert asyncio.run(d.tick()) == []          # повторно не шлём
    assert ("pauseAll", ()) not in aria.calls
    free["hdd"] = 400 * GB
    msgs = asyncio.run(d.tick())
    assert ("unpauseAll", ()) in aria.calls
    assert msgs == [(3, "▶️ Место есть — продолжаю закачки.")]


def test_disk_unavailable_counts_as_no_space(tmp_path):
    dl = load()
    aria = FakeAria2()

    def broken():
        raise OSError("Transport endpoint is not connected")

    d = dl.Downloads(aria2=aria, ledger=dl.Ledger(str(tmp_path / "l.json")),
                     head=None, disk_free=broken)
    asyncio.run(d.tick())
    assert ("pauseAll", ()) in aria.calls


# ── список и отмена ───────────────────────────────────────────────────────────

def test_list_shows_progress_and_free_space(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=10 * GB)
    asyncio.run(d.add_link("https://example.org/a.iso", 1, "ivan"))
    aria.status["g1"].update(totalLength=str(10 * GB), completedLength=str(5 * GB),
                             downloadSpeed=str(2 * 1024 * 1024),
                             files=[{"path": "/downloads/ssd/.incomplete/a.iso"}])
    text = asyncio.run(d.list_text())
    assert "1. a.iso — 50%" in text
    assert "2.0 МБ/с" in text
    assert "Свободно: SSD 110.0 ГБ, HDD 350.0 ГБ" in text


def test_list_empty(tmp_path):
    dl = load()
    d, _ = make(dl, tmp_path)
    assert asyncio.run(d.list_text()).startswith("Закачек нет.")


def test_cancel_by_number(tmp_path):
    dl = load()
    d, aria = make(dl, tmp_path, size=GB)
    asyncio.run(d.add_link("https://example.org/a.iso", 1, "ivan"))
    assert asyncio.run(d.cancel(1)) == "🗑 Отменил: a.iso"
    assert ("forceRemove", ("g1",)) in aria.calls
    assert asyncio.run(d.cancel(5)).startswith("❌")
