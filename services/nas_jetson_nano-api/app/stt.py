"""Клиент распознавания голосовых (E10): OGG/Opus -> homecloud_stt -> текст.

Спецификация: docs/superpowers/specs/2026-09-20-voice-messages-design.md.
Контракт сервиса (services/stt/stt_server.py): POST /stt, тело — сырые байты OGG/Opus,
ответ 200 {"text": "...", "seconds": N}; 413/422/500 — {"error": "..."}.

Правило проекта («таймаут вызывающей стороны строго больше вызываемой»): homecloud_stt
сам себя ограничивает изнутри (~20 с на декодирование + распознавание до 65 с звука при
RTF≈1), settings.stt_timeout (120 с, config.py) — с запасом больше любого из этих пределов.

Однопоточность у homecloud_stt (одно распознавание за раз — инцидент 2026-09-20: два
тяжёлых процесса на двух ядрах кладут систему целиком) продублирована здесь модульным
asyncio.Semaphore(1): не потому что сервис сам не справится (справится — HTTPServer
обслуживает запросы строго по одному, остальные ждут в очереди сокета), а чтобы клиент
не копил открытые httpx-соединения и не множил таймауты, если голосовые пришли пачкой.
Ожидание своей очереди ограничено settings.voice_queue_wait — честный отказ (SttBusy),
а не бесконечное накопление ожидающих.
"""
from __future__ import annotations

import asyncio
import re

import httpx

from app.config import settings

_SEM = asyncio.Semaphore(1)


class SttUnavailable(Exception):
    """Сервис распознавания не ответил, ответил ошибкой или недоступен по сети."""


class SttBusy(Exception):
    """Очередь распознавания не освободилась за settings.voice_queue_wait."""


def _corrections() -> list:
    """Разбирает settings.voice_corrections: пары «было=стало» через «|»."""
    pairs = []
    for part in (settings.voice_corrections or "").split("|"):
        was, _, now = part.partition("=")
        was, now = was.strip(), now.strip()
        if was and now:
            pairs.append((was, now))
    return pairs


def apply_corrections(text: str) -> str:
    """Словарь «было=стало» (идея «словаря терминов» из статьи про Whisper) — типичные
    искажения распознавания (позывной, имена) правятся по целым словам, без учёта
    регистра. Пустой словарь по умолчанию — правится по мере накопления опыта."""
    for was, now in _corrections():
        text = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(was), now, text, flags=re.IGNORECASE)
    return text


async def transcribe(data: bytes) -> str:
    """Отправляет сырые байты OGG/Opus в homecloud_stt, возвращает распознанный текст
    (после apply_corrections). Одно распознавание за раз — см. модуль."""
    try:
        await asyncio.wait_for(_SEM.acquire(), timeout=settings.voice_queue_wait)
    except asyncio.TimeoutError:
        raise SttBusy("очередь распознавания занята")
    try:
        try:
            async with httpx.AsyncClient(timeout=settings.stt_timeout) as client:
                r = await client.post(settings.stt_url, content=data)
        except httpx.HTTPError as exc:
            raise SttUnavailable("сеть: %s" % type(exc).__name__) from exc
        if r.status_code != 200:
            raise SttUnavailable("homecloud_stt: код %s" % r.status_code)
        try:
            body = r.json()
        except ValueError:
            raise SttUnavailable("homecloud_stt: не JSON")
        return apply_corrections((body.get("text") or "").strip())
    finally:
        _SEM.release()
