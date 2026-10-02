"""Stage 15: longer LLM waits must not trigger Telegram's hang watchdog."""
import asyncio

from test_telegram_bot import FakeTelegram, load, make


def test_poll_heartbeat_is_refreshed_between_updates(monkeypatch):
    mod, bot, _, _, _ = make(FakeTelegram(updates=[{"update_id": 1}, {"update_id": 2}]))
    clock, seen = [100.0], []
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock[0])

    async def handle(_update):
        seen.append(bot.beats.get("poll"))
        clock[0] += 240

    monkeypatch.setattr(bot, "handle_update", handle)
    asyncio.run(bot.poll_once())
    assert seen == [100.0, 340.0]


def test_poll_watchdog_allows_voice_then_llm(monkeypatch):
    mod = load()
    for name, value in (("voice_queue_wait", 120), ("stt_timeout", 120),
                        ("talk_bot_llm_timeout", 240)):
        monkeypatch.setattr(mod.settings, name, value)
    # getFile + download + queue + STT + sendChatAction + LLM + sendMessage.
    work = 45 + 45 + 120 + 120 + 45 + 240 + 45
    assert mod.poll_stale_after() > work
    assert mod.STALE_AFTER == 300, "downloads watchdog retains its existing limit"


def test_run_uses_poll_budget_only_for_poll(monkeypatch):
    mod, bot, _, _, _ = make()
    calls = []

    async def connected(*args):
        pass

    async def supervise(name, factory, beats, **kwargs):
        calls.append((name, kwargs.get("stale_after", mod.STALE_AFTER)))

    monkeypatch.setattr(mod, "TgApi", lambda *args, **kwargs: bot.api)
    monkeypatch.setattr(mod, "TelegramBot", lambda *args: bot)
    monkeypatch.setattr(mod, "connect", connected)
    monkeypatch.setattr(mod, "supervise", supervise)
    asyncio.run(mod.run())
    assert dict(calls) == {"poll": mod.poll_stale_after(), "downloads": 300}
