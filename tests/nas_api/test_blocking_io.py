"""API-1: блокирующий I/O по дискам уходит в поток с таймаутом (app/blocking.py).

История дефекта (аудит 2026-09-26, API-1; инцидент 2026-09-20): синхронный
`os.statvfs`/`os.path.exists` по HDD на ntfs-3g зависал навсегда и останавливал цикл
событий целиком. API, Telegram-бот, Talk-бот и качалка живут в одном цикле, поэтому
падало всё сразу, а таймер супервизора не помогал — он тоже стоял.

Проверяются наблюдаемые свойства, а не «вызов ушёл в поток»:
  1) зависший диск даёт `asyncio.TimeoutError` за время ≈ таймаута, а цикл событий жив
     (параллельная корутина продолжает тикать);
  2) пока предыдущий вызов по ключу висит, второй поток НЕ заводится (иначе мёртвый
     диск забил бы пул потоков по одному каждые 30 с); после освобождения — работает;
  3) таймаут = «диска нет»: `Downloads._free` отдаёт (0, 0, True), страж ставит паузу
     с сообщением «HDD недоступен»;
  4) `storage.disk_info` отдаёт mounted=False с «таймаут» в error.

Освобождение зависших потоков — внутри того же цикла событий (`hang.release.set()`),
иначе поток доигрывает уже на закрытом цикле и шумит в вывод; фикстура `hang_guard`
страхует на случай падения теста раньше.

Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"
SHORT = 0.2  # рабочий таймаут в этих тестах; в бою blocking.DISK_TIMEOUT = 5 с


def load(module: str = "app.blocking"):
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "JWT_SECRET": "test-secret",
        "NEXTCLOUD_ADMIN_USER": "admin",
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "API_OWNERS": "alexey",
        "API_CORS_ORIGINS": "",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module(module)


def fast_timeout(monkeypatch, blocking, value: float = SHORT):
    """Укорачивает таймаут для теста.

    ⚠️ `monkeypatch.setattr(blocking, "DISK_TIMEOUT", 0.2)` НЕ работает: значение по
    умолчанию в `run_io(..., timeout=DISK_TIMEOUT)` вычислено один раз, при определении
    функции, и подмена глобальной переменной на него не влияет — замер 2026-09-26:
    вызов без явного timeout ждал 5.1 с, то есть боевые 5, а не подставленные 0.2.
    Поэтому подменяется сам `run_io` тонкой обёрткой: механизм (поток, единый висящий
    future, таймаут) остаётся настоящим, меняется только длительность.
    """
    real = blocking.run_io

    async def fast(key, fn, *args, timeout=value, **kwargs):
        return await real(key, fn, *args, timeout=timeout, **kwargs)

    monkeypatch.setattr(blocking, "run_io", fast)
    return real


class Hang:
    """Функция, которая «висит» до явного освобождения — как statvfs на мёртвом ntfs-3g."""

    def __init__(self, result=("ssd", "hdd")):
        self.release = threading.Event()
        self.calls = 0
        self.result = result

    def __call__(self, *args):
        self.calls += 1
        # 30 с — страховка от вечного зависания прогона, если тест упал до release
        self.release.wait(30)
        return self.result


@pytest.fixture()
def hang_guard():
    """Страховка: какие бы потоки тест ни оставил, к концу он их отпускает."""
    made: list = []
    yield made.append
    for hang in made:
        hang.release.set()


# ── 1. таймаут и живой цикл событий ───────────────────────────────────────────

def test_run_io_times_out_and_keeps_loop_alive(hang_guard):
    blocking = load()
    hang = Hang()
    hang_guard(hang)
    key = "test:timeout"

    async def main():
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        beat = asyncio.ensure_future(ticker())
        started = time.monotonic()
        try:
            with pytest.raises(asyncio.TimeoutError):
                await blocking.run_io(key, hang, timeout=SHORT)
            elapsed = time.monotonic() - started
            assert blocking.busy(key) is True   # поток всё ещё «на диске»
            assert hang.calls == 1
        finally:
            beat.cancel()
            await asyncio.gather(beat, return_exceptions=True)
            hang.release.set()
            await asyncio.sleep(0.05)           # поток возвращается, пока цикл жив
        return elapsed, ticks

    elapsed, ticks = asyncio.run(main())
    # нижняя граница с запасом: таймер цикла событий на Windows имеет шаг ~15.6 мс,
    # поэтому замер чуть-чуть короче номинала; верхняя ловит «ждали не таймаут, а больше»
    assert SHORT * 0.8 <= elapsed < SHORT + 1.0, "ждали %s с при таймауте %s" % (elapsed, SHORT)
    # цикл событий не был занят ожиданием: корутина успела тикнуть много раз
    assert ticks >= 3, "цикл событий стоял: тиков %d" % ticks


def test_run_io_returns_value_when_disk_answers(hang_guard):
    # обратная сторона: живой диск отвечает значением, а не таймаутом
    blocking = load()
    hang = Hang(result=(111, 222))
    hang_guard(hang)
    hang.release.set()

    async def main(key):
        return await blocking.run_io(key, hang, timeout=SHORT)

    assert asyncio.run(main("test:alive")) == (111, 222)
    assert hang.calls == 1


# ── 2. единый висящий вызов на ключ ───────────────────────────────────────────

def test_hanging_call_is_not_duplicated(hang_guard):
    blocking = load()
    hang = Hang()
    hang_guard(hang)
    key = "test:single-flight"

    async def main():
        # два вызова подряд, пока «диск» не отвечает: оба упираются в таймаут
        for _ in range(2):
            with pytest.raises(asyncio.TimeoutError):
                await blocking.run_io(key, hang, timeout=SHORT)
        assert hang.calls == 1, "на висящий ключ заведён второй поток (%d)" % hang.calls
        assert blocking.busy(key) is True

        hang.release.set()
        for _ in range(100):                      # даём потоку вернуться
            if not blocking.busy(key):
                break
            await asyncio.sleep(0.01)
        assert blocking.busy(key) is False

        # освободился — ключ снова рабочий, и это уже новый вызов
        assert await blocking.run_io(key, hang, timeout=SHORT) == ("ssd", "hdd")
        assert hang.calls == 2
        assert blocking.busy(key) is False

    asyncio.run(main())


def test_timeout_does_not_cancel_the_thread(hang_guard):
    # `wait_for(shield(...))` отменяет ТОЛЬКО ожидание: сам вызов остаётся живым, ключ не
    # «отравлен», и результат, который поток отдал позже, не теряется. Без shield висящий
    # вызов отменялся бы на первом же таймауте, и следующий такт заводил бы новый поток.
    blocking = load()
    hang = Hang(result=(1, 2))
    hang_guard(hang)
    key = "test:late-result"

    async def main():
        with pytest.raises(asyncio.TimeoutError):
            await blocking.run_io(key, hang, timeout=SHORT)
        fut = blocking._inflight[key]
        assert fut.cancelled() is False and fut.done() is False

        hang.release.set()
        for _ in range(200):
            if fut.done():
                break
            await asyncio.sleep(0.01)
        assert fut.result() == (1, 2)      # поздний ответ диска не выброшен

        # future завершён — следующее обращение заводит новый поток с честным ответом
        assert await blocking.run_io(key, hang, timeout=SHORT) == (1, 2)
        assert hang.calls == 2

    asyncio.run(main())


# ── 3. качалка: таймаут = «диска нет» ────────────────────────────────────────

class FakeAria2:
    """Минимум для стража: очередь из одной закачки, любой вызов — успех."""

    def __init__(self):
        self.calls = []

    async def call(self, method, *params):
        self.calls.append((method, params))
        if method == "tellActive":
            return [{"gid": "g1"}]
        if method == "tellWaiting":
            return []
        return "OK"


def test_downloads_free_timeout_means_disk_down(hang_guard, tmp_path, monkeypatch):
    dl = load("app.downloads")
    blocking = dl.blocking
    fast_timeout(monkeypatch, blocking)
    hang = Hang()
    hang_guard(hang)

    d = dl.Downloads(aria2=FakeAria2(), ledger=dl.Ledger(str(tmp_path / "l.json")),
                     head=None, disk_free=hang, resolve=lambda host: False)

    async def main():
        try:
            got = await d._free()
        finally:
            hang.release.set()
            await asyncio.sleep(0.05)
        return got

    assert asyncio.run(main()) == (0, 0, True)   # места нет = 0, диск недоступен
    assert hang.calls == 1


def test_guard_pauses_downloads_when_disk_free_hangs(hang_guard, tmp_path, monkeypatch):
    dl = load("app.downloads")
    blocking = dl.blocking
    fast_timeout(monkeypatch, blocking)
    hang = Hang()
    hang_guard(hang)
    aria = FakeAria2()

    d = dl.Downloads(aria2=aria, ledger=dl.Ledger(str(tmp_path / "l.json")),
                     head=None, disk_free=hang, resolve=lambda host: False)
    data = {"g1": {"chat_id": 3, "user": "ivan", "name": "a.iso",
                   "state": "active", "created": 0}}
    meta: dict = {}
    msgs: list = []

    async def main():
        try:
            await d._guard(data, meta, msgs)
        finally:
            hang.release.set()
            await asyncio.sleep(0.05)

    asyncio.run(main())
    assert msgs == [(3, "⏸ Пауза закачек — HDD недоступен.")], msgs
    assert meta.get("paused") is True
    assert ("pause", ("g1",)) in aria.calls
    assert hang.calls == 1, "второй поток на висящем диске"


# ── 4. эндпоинт хранилища ─────────────────────────────────────────────────────

def test_storage_disk_info_reports_timeout(hang_guard, monkeypatch):
    storage = load("app.routers.storage")
    blocking = storage.blocking
    fast_timeout(monkeypatch, blocking)
    hang = Hang(result={"mounted": True})
    hang_guard(hang)
    monkeypatch.setattr(storage, "_disk_info", hang)  # зависший statvfs по /mnt/storage

    async def main():
        try:
            return await storage.disk_info(Path("/mnt/storage"))
        finally:
            hang.release.set()
            await asyncio.sleep(0.05)

    info = asyncio.run(main())
    assert info["mounted"] is False
    assert "таймаут" in info["error"], info
    assert hang.calls == 1


def test_storage_disk_info_passes_through_when_disk_answers(hang_guard, monkeypatch):
    storage = load("app.routers.storage")
    blocking = storage.blocking
    fast_timeout(monkeypatch, blocking)
    hang = Hang(result={"path": "/mnt/storage", "mounted": True, "free_gb": 1.0})
    hang_guard(hang)
    hang.release.set()
    monkeypatch.setattr(storage, "_disk_info", hang)

    async def main():
        return await storage.disk_info(Path("/mnt/storage"))

    assert asyncio.run(main())["mounted"] is True
