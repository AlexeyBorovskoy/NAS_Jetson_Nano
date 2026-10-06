"""A stalled HDD must not consume another worker on each signed link refresh."""
import asyncio
import importlib
import threading
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException
import pytest

from test_download_links import load


def test_hanging_probe_times_out_and_repeated_users_start_one_thread(tmp_path, monkeypatch):
    links, _ = load(tmp_path, monkeypatch)
    files = importlib.import_module("app.routers.download_files")
    entered, release = threading.Event(), threading.Event()
    calls = []

    def stalled(*args):
        calls.append(args)
        entered.set()
        release.wait(3)
        return "first user's response"

    monkeypatch.setattr(files, "_prepare_download", stalled)
    run_io = files.blocking.run_io

    async def short_wait(*args):
        return await run_io(*args, timeout=0.02)

    monkeypatch.setattr(files.blocking, "run_io", short_wait)

    async def scenario():
        try:
            for user in ("ivan", "olga", "ivan"):
                query = parse_qs(urlsplit(links.user_url(user)).query)
                with pytest.raises(HTTPException) as exc:
                    await files.download(user, "", int(query["expires"][0]), query["sig"][0])
                assert exc.value.status_code == 503
            assert entered.is_set()
            assert len(calls) == 1
        finally:
            release.set()
            await files.blocking._inflight["download_files"]

    asyncio.run(scenario())


def test_invalid_signature_does_not_probe_disk(tmp_path, monkeypatch):
    load(tmp_path, monkeypatch)
    files = importlib.import_module("app.routers.download_files")
    monkeypatch.setattr(files, "_prepare_download", lambda *args: pytest.fail("unauthorized disk access"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(files.download("ivan", "", 1, "bad"))
    assert exc.value.status_code == 401
