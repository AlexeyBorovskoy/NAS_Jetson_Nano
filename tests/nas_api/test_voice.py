"""Голосовой путь @бобик (E10): приватность, отказы, очередь распознавания.

Спецификация: docs/superpowers/specs/2026-09-20-voice-messages-design.md (§5, §6, §8, §9).
Run: python -m pytest tests/nas_api -q

Фейки TgApi/Downloads и фабрика текстовых сообщений переиспользуются из test_telegram_bot
(свой обработчик бота второй раз не пишем — иначе тесты разойдутся с живым кодом).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import httpx
import pytest

from test_telegram_bot import FAMILY, OWNER, SON, STRANGER, _until, load, make

# Ни одна проверка приватности не должна проходить на пустом совпадении: текст, который
# обязан нигде не сохраниться, специально не похож ни на ключи state, ни на служебные строки.
SECRET = "тайное слово бульбулятор"

_VMID = [900000]


# ── вспомогательное ───────────────────────────────────────────────────────────

def voice_msg(*, chat=FAMILY, chat_type="supergroup", uid=SON, duration=5,
              file_id="VOICE1", file_size=1000, **extra) -> dict:
    """Апдейт с голосовым — так его отдаёт Telegram (message.voice, без text)."""
    _VMID[0] += 1
    m = {"message_id": _VMID[0], "chat": {"id": chat, "type": chat_type},
         "from": {"id": uid, "first_name": "Ваня"},
         "voice": {"file_id": file_id, "duration": duration, "file_size": file_size}}
    m.update(extra)
    return {"update_id": _VMID[0], "message": m}


def run_bot(coro, timeout: float = 2.0):
    """Гоняет корутину с потолком по времени: зависший бот обязан упасть тестом (§8)."""
    async def guarded():
        return await asyncio.wait_for(coro, timeout)
    return asyncio.run(guarded())


def stt_spy(monkeypatch, mod, text="бобик, привет", exc=None) -> list:
    """Подменяет распознавание (bot зовёт app.stt.transcribe) и записывает поданные байты."""
    calls = []

    async def fake(data):
        calls.append(data)
        if exc is not None:
            raise exc
        return text

    monkeypatch.setattr(mod.stt_mod, "transcribe", fake)
    return calls


def file_spy(monkeypatch, bot, content=b"OGG") -> list:
    """Следит, скачивался ли файл голосового вообще (спецификация §8: «файл не скачивается»)."""
    calls = []

    async def fake(file_id, limit=None):
        calls.append(file_id)
        return content

    monkeypatch.setattr(bot.api, "file_bytes", fake)
    return calls


def records_dump(caplog) -> str:
    """Журнал целиком, вместе с extra-полями: текст мог бы уехать и в них, не в сообщение."""
    return "\n".join("%s|%s|%r" % (r.name, r.getMessage(), r.__dict__) for r in caplog.records)


VOICE_COUNTERS = ("voice_ok", "voice_ignored", "voice_failed", "voice_too_long")


def voice_counters(bot) -> dict:
    """Только счётчики (§5: остаётся счётчик без содержимого), без отметки времени уведомления."""
    return {k: v for k, v in bot.state.items() if k in VOICE_COUNTERS}


def state_raw(bot) -> str:
    """Файл состояния целиком — проверяется отсутствие подстроки, а не только ключей."""
    return Path(bot.state_path).read_text(encoding="utf-8")


def _client_returning(response):
    """httpx-клиент, который всегда отвечает заданным ответом (сеть не нужна)."""

    class Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, content=None):
            return response

    return Client


class FakeClock:
    """Подмена модуля time внутри telegram_bot: интервал уведомлений — без ожидания."""

    def __init__(self, now: float):
        self.now = now

    def time(self) -> float:
        return self.now

    def monotonic(self) -> float:
        return time.monotonic()


# ── §5/§9.1 приватность: в группе без «бобика» — молчание и нигде ни строчки ────

def test_group_voice_without_callsign_is_silent_and_stores_nothing(monkeypatch, caplog):
    mod, bot, tg, dl, asked = make()
    stt = stt_spy(monkeypatch, mod, text=SECRET)
    file_spy(monkeypatch, bot)
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)

    with caplog.at_level(logging.DEBUG):
        run_bot(bot.handle_update(voice_msg(uid=SON, duration=6)))

    assert stt == [b"OGG"], "распознавание обязано было состояться, иначе проверка пустая"
    assert "voice ignored" in caplog.text, "журнал обязан ловиться — иначе проверка ниже пустая"
    assert tg.texts() == [], "в группе на голосовое без «бобика» бот молчит"
    assert [m for m, _ in tg.sent] == [], "наружу не уходит ничего, включая sendChatAction"
    assert asked == [], "вопрос без «бобика» не уходит в модель"
    assert dialog.MEMORY.history(key) == "", "память диалога не тронута"
    assert voice_counters(bot) == {"voice_ignored": 1}, "остаётся только счётчик без содержимого"
    assert SECRET not in state_raw(bot)
    assert SECRET not in json.dumps(bot.state, ensure_ascii=False)
    assert SECRET not in caplog.text
    assert SECRET not in records_dump(caplog)


def test_group_voice_without_callsign_on_second_message_still_stores_nothing(monkeypatch):
    # Счётчик растёт, а содержимое не копится: во втором прогоне проверяем, что накопление
    # не появилось где-то ещё (например, в «answered» или в записи диалога).
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text=SECRET)
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)

    for _ in range(2):
        run_bot(bot.handle_update(voice_msg(uid=SON, duration=6)))

    assert voice_counters(bot) == {"voice_ignored": 2}
    assert dialog.MEMORY.history(key) == ""
    assert SECRET not in state_raw(bot)
    assert tg.texts() == [] and asked == []
    assert "answered" not in bot.state, "игнорируемое голосовое не помечается как отвеченное"


# ── §6/§9.2 голосовое длиннее 60 с: отказ, файл не скачивается ─────────────────

def test_voice_too_long_in_private_is_refused_without_download(monkeypatch):
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod)

    run_bot(bot.handle_update(voice_msg(chat=OWNER, chat_type="private", uid=OWNER, duration=61)))

    assert tg.texts() == [(OWNER, mod.VOICE_TOO_LONG_TEXT)]
    assert files == [], "длинное голосовое не скачивается вовсе"
    assert stt == [], "и не распознаётся"
    assert voice_counters(bot) == {"voice_too_long": 1}
    assert asked == []


def test_voice_too_long_in_group_is_silent_without_download(monkeypatch):
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod)

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=61)))

    assert tg.texts() == [], "в группе отказ не спамим"
    assert files == [] and stt == []
    assert voice_counters(bot) == {"voice_too_long": 1}


def test_voice_exactly_60_seconds_is_still_recognized(monkeypatch):
    # Граница: предел — «больше 60», а не «60 и больше» (спецификация §6).
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod, text="бобик, привет")

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=60)))

    assert files == ["VOICE1"] and stt == [b"OGG"]
    assert voice_counters(bot) == {"voice_ok": 1}
    assert asked == [("привет", "ivan", ("tg:%d" % FAMILY, "Ваня"))]


def test_voice_over_size_limit_is_refused_like_too_long(monkeypatch):
    # Длительность в норме, но файл больше voice_max_bytes: в Telegram это независимые
    # величины, и 60 с опус может весить больше 2 МБ.
    mod, bot, tg, dl, asked = make()
    files = file_spy(monkeypatch, bot)
    stt = stt_spy(monkeypatch, mod)

    run_bot(bot.handle_update(voice_msg(
        chat=OWNER, chat_type="private", uid=OWNER, duration=10,
        file_size=mod.settings.voice_max_bytes + 1)))

    assert tg.texts() == [(OWNER, mod.VOICE_TOO_LONG_TEXT)]
    assert files == [] and stt == []
    assert voice_counters(bot) == {"voice_too_long": 1}


# ── §6/§8/§9.3 «скачай» голосом не выполняется ────────────────────────────────

def test_voice_download_command_is_not_executed(monkeypatch):
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text="бобик, скачай magnet:?xt=urn:btih:AAA")
    parse_calls = []

    def parse_spy(text):
        parse_calls.append(text)
        raise AssertionError("ссылку из голоса разбирать нельзя — закачка не того")

    monkeypatch.setattr(mod.downloads_mod, "parse_link", parse_spy)

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=8)))

    assert dl.calls == [], "add_link/add_torrent не вызываются"
    assert parse_calls == []
    texts = tg.texts()
    assert len(texts) == 1 and texts[0][0] == FAMILY
    assert "Расслышал" in texts[0][1], "человек видит, что именно услышал бот"
    assert "magnet:?xt=urn:btih:AAA" in texts[0][1]
    assert "текстом" in texts[0][1], "и получает просьбу прислать ссылку текстом"
    assert voice_counters(bot) == {"voice_ok": 1}


# ── §8/§9.4 сбой распознавания: бот отвечает, а не виснет ─────────────────────

def test_stt_failure_in_private_asks_to_write_text(monkeypatch):
    # Отказ виден человеку (правило «тишина ≠ успех»): «не разобрал» и просьба написать.
    for name in ("SttUnavailable", "SttBusy"):
        mod, bot, tg, dl, asked = make()
        stt_spy(monkeypatch, mod, exc=getattr(mod.stt_mod, name)("сбой"))

        run_bot(bot.handle_update(voice_msg(chat=OWNER, chat_type="private", uid=OWNER, duration=4)))

        assert tg.texts() == [(OWNER, mod.VOICE_FAILED_TEXT)], name
        assert voice_counters(bot) == {"voice_failed": 1}, name
        assert asked == [] and dl.calls == [], name


def test_stt_failure_in_group_is_silent_and_notifies_owner_once_an_hour(monkeypatch, caplog):
    mod, bot, tg, dl, asked = make()
    clock = FakeClock(1_000_000)
    monkeypatch.setattr(mod, "time", clock)
    stt_spy(monkeypatch, mod, exc=mod.stt_mod.SttUnavailable("сеть: ConnectError"))

    with caplog.at_level(logging.DEBUG):
        for _ in range(2):
            run_bot(bot.handle_update(voice_msg(uid=SON, duration=4)))

    assert "voice recognition failed" in caplog.text, "журнал обязан ловиться"
    assert [t for c, t in tg.texts() if c == FAMILY] == [], "в группе на сбой не отвечаем"
    owner = [t for c, t in tg.texts() if c == OWNER]
    assert owner == [mod.VOICE_UNAVAILABLE_OWNER_TEXT], "владельцу — одно уведомление, не два"
    assert bot.state["voice_unavailable_notified_at"] == 1_000_000
    assert voice_counters(bot) == {"voice_failed": 2}

    clock.now += mod.VOICE_UNAVAILABLE_NOTIFY_INTERVAL - 1
    run_bot(bot.handle_update(voice_msg(uid=SON, duration=4)))
    assert len([t for c, t in tg.texts() if c == OWNER]) == 1, "в пределах часа — молчание"

    clock.now += 2
    run_bot(bot.handle_update(voice_msg(uid=SON, duration=4)))
    assert len([t for c, t in tg.texts() if c == OWNER]) == 2, "прошёл час — уведомляем снова"


def test_voice_notify_interval_lives_in_state_not_in_process_memory(monkeypatch):
    # Интервал переживает перезапуск контейнера: иначе каждое падение бота заново
    # открывало бы владельцу право на уведомление, и спам возвращался бы.
    mod, bot, tg, dl, asked = make()
    clock = FakeClock(1_000_000)
    monkeypatch.setattr(mod, "time", clock)
    stt_spy(monkeypatch, mod, exc=mod.stt_mod.SttUnavailable("сеть: ConnectError"))

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=4)))
    restarted = mod.TelegramBot(bot.api, bot.downloads, answer=bot.answer, state_path=bot.state_path)
    run_bot(restarted.handle_update(voice_msg(uid=SON, duration=4)))

    assert len([t for c, t in tg.texts() if c == OWNER]) == 1


# ── §6/§9.5 очередь: второе распознавание не идёт параллельно ─────────────────

async def _permits(sem, limit: int = 5) -> int:
    """Сколько разрешений реально свободно. Лишнее разрешение в семафоре — это ровно то,
    от чего защищались 2026-09-20: два тяжёлых распознавания разом на двух ядрах."""
    taken = 0
    while taken < limit:
        try:
            await asyncio.wait_for(sem.acquire(), 0.02)
        except asyncio.TimeoutError:
            break
        taken += 1
    for _ in range(taken):
        sem.release()
    return taken


def test_busy_queue_refuses_and_starts_no_parallel_recognition(monkeypatch):
    mod, bot, tg, dl, asked = make()
    monkeypatch.setattr(mod.settings, "voice_queue_wait", 0.05)
    started = []

    class GuardClient:
        """Настоящее распознавание начиналось бы с создания httpx-клиента."""

        def __init__(self, *a, **kw):
            started.append(1)

    monkeypatch.setattr(mod.stt_mod.httpx, "AsyncClient", GuardClient)

    async def scenario():
        await mod.stt_mod._SEM.acquire()          # очередь занята первым распознаванием
        try:
            await asyncio.wait_for(bot.handle_update(voice_msg(uid=SON, duration=5)), 2)
            await asyncio.wait_for(bot.handle_update(voice_msg(uid=OWNER, duration=5)), 2)
        finally:
            mod.stt_mod._SEM.release()
        assert await _permits(mod.stt_mod._SEM) == 1

    asyncio.run(scenario())

    assert started == [], "второе распознавание не должно было начаться"
    assert voice_counters(bot) == {"voice_failed": 2}
    assert [t for c, t in tg.texts() if c == FAMILY] == []
    assert [t for c, t in tg.texts() if c == OWNER] == [mod.VOICE_UNAVAILABLE_OWNER_TEXT]


def test_second_voice_while_first_is_still_recognizing(monkeypatch):
    # Живой сценарий: первое голосовое уже в распознавании, приходит второе. Оно обязано
    # получить честный отказ (а не встать вторым тяжёлым процессом рядом).
    mod, bot, tg, dl, asked = make()
    monkeypatch.setattr(mod.settings, "voice_queue_wait", 0.05)
    started, finished = [], []
    release = asyncio.Event()

    class SlowClient:
        def __init__(self, *a, **kw):
            started.append(1)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, content=None):
            await release.wait()                  # первое распознавание держит очередь
            finished.append(1)
            return httpx.Response(200, json={"text": "бобик, привет", "seconds": 3})

    monkeypatch.setattr(mod.stt_mod.httpx, "AsyncClient", SlowClient)
    monkeypatch.setattr(mod, "time", FakeClock(1_000_000))

    async def scenario():
        first = asyncio.ensure_future(bot.handle_update(voice_msg(uid=SON, duration=3)))
        assert await _until(lambda: started, 1.0), "первое голосовое не дошло до распознавания"
        await asyncio.wait_for(bot.handle_update(voice_msg(uid=OWNER, duration=3)), 2)
        parallel = len(started)
        release.set()
        await asyncio.wait_for(first, 2)
        return parallel

    parallel = asyncio.run(scenario())

    assert parallel == 1, "второе распознавание стартовало параллельно первому"
    assert finished == [1], "первое распознавание обязано доработать, а не быть срезанным"
    assert voice_counters(bot) == {"voice_ok": 1, "voice_failed": 1}
    assert [t for c, t in tg.texts() if c == OWNER] == [mod.VOICE_UNAVAILABLE_OWNER_TEXT]
    assert [t for c, t in tg.texts() if c == FAMILY] == [
        "🎤 Расслышал: бобик, привет\n\n🐕 ответ"], "успешное голосовое всё равно доходит до ответа"


# ── §7/§9.6 ответ начинается с «Расслышал: …» ────────────────────────────────

def test_voice_reply_starts_with_the_heard_text(monkeypatch):
    mod, bot, tg, dl, asked = make()
    heard = "бобик, столица Франции?"
    stt_spy(monkeypatch, mod, text=heard)

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=7)))

    assert [a[:2] for a in asked] == [("столица Франции?", "ivan")]
    assert tg.texts() == [(FAMILY, "🎤 Расслышал: %s\n\n🐕 ответ" % heard)]


def test_voice_prefix_covers_every_reply_not_just_questions(monkeypatch):
    # Префикс добавляет общая точка ответа reply(), а не ветка вопроса: иначе на «закачки»
    # человек не увидел бы, что бот расслышал, и молча получил бы чужой список.
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text="бобик, закачки")

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=4)))

    assert tg.texts() == [(FAMILY, "🎤 Расслышал: бобик, закачки\n\nЗакачек нет.")]
    assert asked == []


# ── незнакомцы: голос не распознаётся вовсе ──────────────────────────────────

def test_stranger_voice_in_group_is_not_transcribed(monkeypatch):
    mod, bot, tg, dl, asked = make()
    stt = stt_spy(monkeypatch, mod)
    files = file_spy(monkeypatch, bot)

    run_bot(bot.handle_update(voice_msg(uid=STRANGER, duration=5)))

    assert stt == [] and files == [], "голос незнакомца не тратит распознавание и не утекает"
    # В группе такой голос выходит молча и о владельце не сообщает: пока текст не распознан,
    # неизвестно, обращались ли к боту вообще (в группе болтают и мимо него — шуметь нечем).
    assert tg.texts() == [], "в группе на голос незнакомца бот не отвечает и владельца не дёргает"
    assert voice_counters(bot) == {}, "до голосовых счётчиков дело не доходит"
    assert asked == []


def test_stranger_voice_in_private_gets_refusal_without_transcription(monkeypatch):
    mod, bot, tg, dl, asked = make()
    stt = stt_spy(monkeypatch, mod)
    files = file_spy(monkeypatch, bot)

    run_bot(bot.handle_update(voice_msg(chat=STRANGER, chat_type="private", uid=STRANGER)))

    assert [t for c, t in tg.texts() if c == STRANGER] == [mod.STRANGER_TEXT]
    assert stt == [] and files == []
    assert voice_counters(bot) == {}


# ── §8 пустой результат распознавания ────────────────────────────────────────

def test_empty_recognition_in_private_asks_to_repeat(monkeypatch):
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text="")
    from app import dialog
    key = "tg:%d" % OWNER
    dialog.MEMORY.forget(key)

    run_bot(bot.handle_update(voice_msg(chat=OWNER, chat_type="private", uid=OWNER, duration=3)))

    assert tg.texts() == [(OWNER, mod.VOICE_EMPTY_TEXT)]
    assert voice_counters(bot) == {"voice_failed": 1}
    assert asked == [] and dialog.MEMORY.history(key) == "", "в память диалога ничего не пишется"


def test_empty_recognition_in_group_is_silent_and_does_not_alarm_owner(monkeypatch):
    # Пустой результат — не отказ сервиса: владельца будить нечем, в группе не отвечаем.
    mod, bot, tg, dl, asked = make()
    stt_spy(monkeypatch, mod, text="")
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)

    run_bot(bot.handle_update(voice_msg(uid=SON, duration=3)))

    assert tg.texts() == []
    assert voice_counters(bot) == {"voice_failed": 1}
    assert dialog.MEMORY.history(key) == ""
    assert "voice_unavailable_notified_at" not in bot.state


# ── словарь правок распознавания (app/stt.py) ────────────────────────────────

def test_apply_corrections_whole_words_case_insensitive(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod.settings, "voice_corrections", "бобик=Бобик|вася=Вася")
    fix = mod.stt_mod.apply_corrections

    assert fix("БОБИК, привет") == "Бобик, привет"
    assert fix("бобик привет") == "Бобик привет"
    assert fix("подбобиком шёл") == "подбобиком шёл", "правится слово целиком, не кусок"
    assert fix("бобикXYZ молчит") == "бобикXYZ молчит", "латиница после имени — не то слово"
    assert fix("Вася пришёл") == "Вася пришёл"
    assert fix("побоVaся") == "побоVaся"

    monkeypatch.setattr(mod.settings, "voice_corrections", "")
    assert fix("бобик привет") == "бобик привет", "пустой словарь по умолчанию ничего не трогает"


def test_stt_failed_service_reports_unavailable(monkeypatch):
    # Коды 413/422/500 контракта homecloud_stt — это «не разобрал», а не «пустой текст»:
    # иначе человек получил бы «повторите» вместо «напишите текстом» (спецификация §8).
    mod = load()
    monkeypatch.setattr(mod.settings, "voice_corrections", "")

    for reply in (httpx.Response(500), httpx.Response(413), httpx.Response(200, text="не json")):
        monkeypatch.setattr(mod.stt_mod.httpx, "AsyncClient", _client_returning(reply))
        with pytest.raises(mod.stt_mod.SttUnavailable):
            asyncio.run(mod.stt_mod.transcribe(b"OGG"))


def test_stt_network_error_reports_unavailable(monkeypatch):
    mod = load()

    class BrokenClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, content=None):
            raise httpx.ConnectError("нет соединения")

    monkeypatch.setattr(mod.stt_mod.httpx, "AsyncClient", BrokenClient)
    with pytest.raises(mod.stt_mod.SttUnavailable):
        asyncio.run(mod.stt_mod.transcribe(b"OGG"))


def test_transcribe_applies_corrections_and_strips(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod.settings, "voice_corrections", "бобик=Бобик")
    monkeypatch.setattr(mod.stt_mod.httpx, "AsyncClient",
                        _client_returning(httpx.Response(200, json={"text": "  бобик, привет  "})))

    assert asyncio.run(mod.stt_mod.transcribe(b"OGG")) == "Бобик, привет"
