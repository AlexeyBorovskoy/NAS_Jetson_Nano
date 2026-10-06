"""Partial aria2 side effects must survive a failed tick."""
import asyncio
import httpx
import pytest

from test_downloads import load, make


@pytest.mark.parametrize("failure", [RuntimeError("removed"), httpx.ReadTimeout("offline")])
def test_third_pause_failure_preserves_progress_and_retries(tmp_path, monkeypatch, failure):
    dl = load()
    d, aria = make(dl, tmp_path, hdd=1)
    for gid in ("g1", "g2", "g3", "g4"):
        aria.status[gid] = {"gid": gid, "status": "active"}
    original = aria.call
    broken = [True]

    async def call(method, *args):
        if method == "pause" and args[0] == "g3" and broken[0]:
            broken[0] = False
            raise failure
        return await original(method, *args)

    async def noop(*args):
        pass

    monkeypatch.setattr(aria, "call", call)
    monkeypatch.setattr(d, "_tick_entries", noop)
    monkeypatch.setattr(d, "_reconcile", noop)
    asyncio.run(d.tick())
    meta = d.ledger.load()["_meta"]
    assert meta["paused"]
    assert meta["paused_gids"][:2] == ["g1", "g2"]
    if isinstance(failure, RuntimeError):
        assert meta["paused_gids"] == ["g1", "g2", "g4"]
    else:
        assert meta["pause_pending"]
        asyncio.run(d.tick())
        assert d.ledger.load()["_meta"]["paused_gids"] == ["g1", "g2", "g3", "g4"]


def test_unexpected_tick_error_saves_mutations_and_outbox(tmp_path, monkeypatch):
    dl = load()
    d, _ = make(dl, tmp_path)

    async def failed(data, meta, msgs):
        data["g1"] = {"state": "done"}
        meta["paused_gids"] = ["g2"]
        msgs.append((7, "finished"))
        raise ValueError("synthetic")

    monkeypatch.setattr(d, "_tick_entries", failed)
    assert asyncio.run(d.tick()) == [(7, "finished")]
    saved = d.ledger.load()
    assert saved["g1"]["state"] == "done"
    assert saved["_meta"]["paused_gids"] == ["g2"]
    assert saved["_outbox"] == [{"chat_id": 7, "text": "finished"}]


def test_partial_resume_preserves_only_not_yet_resumed_gids(tmp_path, monkeypatch):
    dl = load()
    d, aria = make(dl, tmp_path)
    d.ledger.save({"_meta": {"paused": True, "paused_gids": ["g1", "g2", "g3"]}})
    original = aria.call

    async def call(method, *args):
        if method == "unpause" and args[0] == "g2":
            raise httpx.ReadTimeout("synthetic")
        return await original(method, *args)

    async def noop(*args):
        pass

    monkeypatch.setattr(aria, "call", call)
    monkeypatch.setattr(d, "_tick_entries", noop)
    monkeypatch.setattr(d, "_reconcile", noop)
    asyncio.run(d.tick())
    assert d.ledger.load()["_meta"]["paused_gids"] == ["g2", "g3"]


def test_cancelled_and_rpc_missing_gids_do_not_block_resume(tmp_path, monkeypatch):
    dl = load()
    d, aria = make(dl, tmp_path)
    d.ledger.save({"g1": {"state": "cancelled"},
                   "_meta": {"paused": True, "paused_gids": ["g1", "g2"]}})

    async def call(method, *args):
        if method == "unpause":
            raise dl.Aria2Error({"code": 1, "message": "GID #abc123 is not found"})
        return []

    async def noop(*args):
        pass

    monkeypatch.setattr(aria, "call", call)
    monkeypatch.setattr(d, "_tick_entries", noop)
    monkeypatch.setattr(d, "_reconcile", noop)
    asyncio.run(d.tick())
    meta = d.ledger.load()["_meta"]
    assert not meta["paused"]
    assert meta["paused_gids"] == []


def test_generic_resume_rpc_error_remains_for_retry(tmp_path, monkeypatch):
    dl = load()
    d, aria = make(dl, tmp_path)
    d.ledger.save({"_meta": {"paused": True, "paused_gids": ["g1"]}})
    original = aria.call

    async def call(method, *args):
        if method == "unpause":
            raise dl.Aria2Error({"code": 1, "message": "Unauthorized"})
        return await original(method, *args)

    async def noop(*args):
        pass

    monkeypatch.setattr(aria, "call", call)
    monkeypatch.setattr(d, "_tick_entries", noop)
    monkeypatch.setattr(d, "_reconcile", noop)
    asyncio.run(d.tick())
    meta = d.ledger.load()["_meta"]
    assert meta["paused"] and meta["paused_gids"] == ["g1"]
    assert meta["resume_pending"]


@pytest.mark.parametrize("failed_method", ["tellActive", "pause"])
def test_guard_fault_keeps_exactly_one_pause_alert_across_retry(tmp_path, monkeypatch, failed_method):
    dl = load()
    d, aria = make(dl, tmp_path, hdd=1)
    aria.status["g1"] = {"gid": "g1", "status": "active"}
    d.ledger.save({"g1": {"state": "active", "chat_id": 7}})
    original = aria.call
    failed = [False]

    async def call(method, *args):
        if method == failed_method and not failed[0]:
            failed[0] = True
            raise httpx.ReadTimeout("synthetic")
        return await original(method, *args)

    async def noop(*args):
        pass

    monkeypatch.setattr(aria, "call", call)
    monkeypatch.setattr(d, "_tick_entries", noop)
    monkeypatch.setattr(d, "_reconcile", noop)
    first = asyncio.run(d.tick())
    assert len(first) == 1 and first[0][0] == 7
    assert "HDD" in first[0][1]
    assert asyncio.run(d.tick()) == first  # durable outbox, no duplicate notification
    assert d.ledger.load()["_meta"]["paused_gids"] == ["g1"]
