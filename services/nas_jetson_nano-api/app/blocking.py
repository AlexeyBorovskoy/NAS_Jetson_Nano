"""Блокирующий I/O по дискам — только отсюда, не прямо в цикле событий.

API, Telegram-бот, Talk-бот и качалка делят один цикл событий. Синхронный `os.statvfs`
на зависшем ntfs-3g (инцидент 2026-09-20) останавливал бы все четыре разом — и
`supervise()` не помог бы: его таймер тоже стоит, пока цикл занят (аудит 2026-09-26, API-1).

Вызов уходит в поток и ждётся с таймаутом. Зависший поток не убить — поэтому пока
предыдущий вызов по тому же ключу не вернулся, новый поток НЕ заводится: следующие
вызовы ждут тот же future и так же упираются в таймаут. Иначе мёртвый диск за
несколько минут забил бы пул потоков по одному каждые 30 с.
"""
from __future__ import annotations

import asyncio

DISK_TIMEOUT = 5.0

_inflight: dict = {}


async def run_io(key: str, fn, *args, timeout: float = DISK_TIMEOUT):
    """Результат fn(*args) из потока; asyncio.TimeoutError — диск не ответил вовремя."""
    fut = _inflight.get(key)
    if fut is None or fut.done():
        fut = asyncio.ensure_future(asyncio.to_thread(fn, *args))
        _inflight[key] = fut
    return await asyncio.wait_for(asyncio.shield(fut), timeout)


def busy(key: str) -> bool:
    """Висит ли ещё предыдущий вызов по ключу — для диагностики и тестов."""
    fut = _inflight.get(key)
    return fut is not None and not fut.done()
