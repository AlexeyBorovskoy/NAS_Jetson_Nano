# Память разговора @бобик: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** «бобик, что приготовить?» → ответ → «бобик, а без мяса?» — Бобик помнит, о чём речь; «бобик, забудь» начинает с чистого листа.

**Architecture:** память разговоров живёт в процессе NAS API (`app/dialog.py`), история передаётся в существующее поле `context` шлюза — шлюз, фильтр личных данных и квоты не меняются. Группа Telegram — одна общая нить, личка и комната Talk — свои.

**Tech Stack:** Python 3.12 (контейнер NAS API), pytest.

**Spec:** `docs/superpowers/specs/2026-09-19-bobik-dialog-memory-design.md`

## Global Constraints

- Язык кода, сообщений бота и документации — русский; у документа в `docs/` — EN summary (правило №15).
- Память **только в процессе**: на диск и в журнал текст разговоров не пишется (в журнале — метаданные: `user`, длина истории).
- Пределы: 10 реплик на разговор, 30 мин тишины до забывания, 500 символов на реплику, 3000 символов на всю историю.
- В память попадают **только** обращения к Бобику и его ответы. Закачки («скачай», «закачки», «отмени N»), отказы safety gate, уточнения, домашние инструменты и ошибки шлюза — не попадают.
- Safety gate судит **только новый вопрос**, историю он не видит.
- Ключи разговоров: Telegram — `tg:<chat_id>`, Talk — `talk:<room_token>`.
- Тесты — pytest в `tests/nas_api/` (Python 3.12, `asyncio.run`, без pytest-asyncio). Существующие тесты не ослаблять.
- Каждый коммит заканчивается строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`; хук pre-commit прогоняет ворота; `--no-verify` запрещён.
- Выкат — только по «деплой» (пересборка NAS API, ~15 с простоя). VPS не затрагивается.

## Файлы

| Файл | Ответственность |
|---|---|
| `services/nas_jetson_nano-api/app/dialog.py` | память разговоров: `add`, `history`, `forget`; пределы и забывание |
| `services/nas_jetson_nano-api/app/routers/talk_bot.py` (изменение) | `_ask_llm(..., context)`, `ask(..., context)`, `answer(..., dialog)`, `remember(...)`; Talk-цикл передаёт ключ комнаты |
| `services/nas_jetson_nano-api/app/telegram_bot.py` (изменение) | ключ чата и имя говорящего, команда «забудь», справка |
| `tests/nas_api/test_dialog.py` | память |
| `tests/nas_api/test_bobik_answer.py` (изменение) | история в `context`, что запоминается |
| `tests/nas_api/test_telegram_bot.py` (изменение) | ключи, «забудь», закачки не запоминаются |

---

### Task 1: Память разговоров `dialog.py`

**Files:**
- Create: `services/nas_jetson_nano-api/app/dialog.py`
- Create: `tests/nas_api/test_dialog.py`

**Interfaces:**
- Produces: `class DialogMemory(max_turns=10, idle_ttl=1800, max_chars_turn=500, max_chars_total=3000, clock=time.time)` с `add(key: str, speaker: str, text: str) -> None`, `history(key: str) -> str`, `forget(key: str) -> bool`; модульный экземпляр `MEMORY`.

- [ ] **Step 1: падающие тесты**

`tests/nas_api/test_dialog.py`:
```python
"""Память разговора @бобик (спецификация 2026-09-19 §4, §6).

Зачем: семья спрашивает «а без мяса?» вторым сообщением. Память живёт только в процессе —
никакой переписки на диске; забывается через 30 минут тишины, чтобы вечером не всплыл утренний
разговор и чтобы история не съедала квоту GigaChat.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.dialog")


class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def __call__(self):
        return self.t


def test_history_keeps_order_and_speakers():
    d = load()
    m = d.DialogMemory()
    m.add("tg:1", "Оля", "что приготовить на ужин?")
    m.add("tg:1", "Бобик", "Паста с курицей.")
    m.add("tg:1", "Ваня", "а без мяса?")
    assert m.history("tg:1") == "Оля: что приготовить на ужин?\nБобик: Паста с курицей.\nВаня: а без мяса?"


def test_unknown_key_is_empty():
    d = load()
    assert d.DialogMemory().history("tg:нет") == ""


def test_keys_do_not_mix():
    d = load()
    m = d.DialogMemory()
    m.add("tg:1", "Оля", "первый")
    m.add("tg:2", "Ваня", "второй")
    assert m.history("tg:1") == "Оля: первый"
    assert m.history("tg:2") == "Ваня: второй"


def test_only_last_turns_are_kept():
    d = load()
    m = d.DialogMemory(max_turns=4)
    for i in range(6):
        m.add("k", "Оля", "реплика %d" % i)
    lines = m.history("k").split("\n")
    assert len(lines) == 4
    assert lines[0].endswith("реплика 2") and lines[-1].endswith("реплика 5")


def test_conversation_is_forgotten_after_idle():
    d = load()
    c = Clock()
    m = d.DialogMemory(idle_ttl=1800, clock=c)
    m.add("k", "Оля", "привет")
    c.t += 1799
    assert m.history("k") == "Оля: привет"
    c.t += 2
    assert m.history("k") == ""
    m.add("k", "Оля", "снова")
    assert m.history("k") == "Оля: снова"


def test_idle_counts_from_last_turn():
    d = load()
    c = Clock()
    m = d.DialogMemory(idle_ttl=100, clock=c)
    m.add("k", "Оля", "раз")
    c.t += 60
    m.add("k", "Бобик", "два")
    c.t += 60
    assert m.history("k") == "Оля: раз\nБобик: два"


def test_forget_clears_only_that_key():
    d = load()
    m = d.DialogMemory()
    m.add("a", "Оля", "раз")
    m.add("b", "Ваня", "два")
    assert m.forget("a") is True
    assert m.forget("a") is False
    assert m.history("a") == "" and m.history("b") == "Ваня: два"


def test_long_turn_is_trimmed():
    d = load()
    m = d.DialogMemory(max_chars_turn=20)
    m.add("k", "Оля", "я" * 100)
    assert m.history("k") == "Оля: " + "я" * 20


def test_total_history_is_capped_dropping_oldest():
    d = load()
    m = d.DialogMemory(max_turns=10, max_chars_total=60)
    for i in range(5):
        m.add("k", "Оля", "реплика номер %d" % i)
    text = m.history("k")
    assert len(text) <= 60
    assert "номер 4" in text and "номер 0" not in text


def test_whitespace_is_collapsed_and_empty_ignored():
    d = load()
    m = d.DialogMemory()
    m.add("k", "Оля", "  две\n\nстроки  ")
    m.add("k", "Оля", "   ")
    assert m.history("k") == "Оля: две строки"


def test_module_level_memory_exists():
    d = load()
    assert isinstance(d.MEMORY, d.DialogMemory)
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/nas_api/test_dialog.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.dialog'`

- [ ] **Step 3: реализация**

`services/nas_jetson_nano-api/app/dialog.py`:
```python
"""Память разговора @бобик: последние реплики чата, только в оперативной памяти.

Спецификация: docs/superpowers/specs/2026-09-19-bobik-dialog-memory-design.md.
На диск ничего не пишется — переписка семьи не должна оседать на Jetson; перезапуск
контейнера = чистый лист. История уходит в шлюз полем `context`, где её так же
фильтрует redaction, а токены считаются в бюджете человека — поэтому пределы жёсткие.
"""
from __future__ import annotations

import time

MAX_TURNS = 10
IDLE_TTL = 30 * 60
MAX_CHARS_TURN = 500
MAX_CHARS_TOTAL = 3000


class DialogMemory:
    def __init__(self, max_turns=MAX_TURNS, idle_ttl=IDLE_TTL,
                 max_chars_turn=MAX_CHARS_TURN, max_chars_total=MAX_CHARS_TOTAL,
                 clock=time.time):
        self.max_turns = max_turns
        self.idle_ttl = idle_ttl
        self.max_chars_turn = max_chars_turn
        self.max_chars_total = max_chars_total
        self.clock = clock
        self._chats: dict = {}

    def _fresh(self, key: str):
        chat = self._chats.get(key)
        if chat is None:
            return None
        if self.clock() - chat["seen"] > self.idle_ttl:
            del self._chats[key]  # разговор протух: вечером не всплывёт утренняя тема
            return None
        return chat

    def add(self, key: str, speaker: str, text: str) -> None:
        text = " ".join((text or "").split())[: self.max_chars_turn]
        if not key or not text:
            return
        chat = self._fresh(key) or {"seen": self.clock(), "turns": []}
        chat["turns"].append((speaker or "Кто-то", text))
        del chat["turns"][: -self.max_turns]
        chat["seen"] = self.clock()
        self._chats[key] = chat

    def history(self, key: str) -> str:
        chat = self._fresh(key)
        if not chat:
            return ""
        lines, total = [], 0
        for speaker, text in reversed(chat["turns"]):
            line = "%s: %s" % (speaker, text)
            if total + len(line) + 1 > self.max_chars_total:
                break  # старое вытесняем первым
            lines.append(line)
            total += len(line) + 1
        return "\n".join(reversed(lines))

    def forget(self, key: str) -> bool:
        return self._chats.pop(key, None) is not None


MEMORY = DialogMemory()
```

- [ ] **Step 4: тесты проходят**

Run: `python -m pytest -q tests/nas_api/test_dialog.py`
Expected: `11 passed`

- [ ] **Step 5: коммит**

```bash
git add services/nas_jetson_nano-api/app/dialog.py tests/nas_api/test_dialog.py
git commit -m "feat(bobik): in-process conversation memory (10 turns, 30 min idle, capped)" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: История в ответе `@бобик` (`talk_bot`) и Talk-цикл

**Files:**
- Modify: `services/nas_jetson_nano-api/app/routers/talk_bot.py` (`_ask_llm` ~строка 325, `ask` ~417, `answer` ~431, вызов `ask` в Talk-цикле ~535)
- Modify: `tests/nas_api/test_bobik_answer.py` (дописать в конец)

**Interfaces:**
- Consumes: `app.dialog.MEMORY` (Task 1).
- Produces:
  - `async def _ask_llm(question: str, user: str, context: str = "") -> str`
  - `async def ask(question: str, user: str, context: str = "") -> str`
  - `async def answer(question: str, user: str, dialog=None) -> str` — `dialog = (key, speaker)`; при обычном ответе из облака подставляет историю и запоминает две реплики.
  - `def remember(dialog, question: str, reply: str) -> None` — общая запись в память (используется и Talk-циклом).

- [ ] **Step 1: падающие тесты**

Дописать в конец `tests/nas_api/test_bobik_answer.py`:
```python
# ── память разговора (спецификация 2026-09-19) ────────────────────────────────

def test_history_is_sent_as_context_and_turns_are_remembered(monkeypatch):
    bot = load_bot()
    seen = {}

    async def fake_llm(q, u, context=""):
        seen["context"] = context
        return "🐕 Паста с курицей."

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    from app import dialog
    dialog.MEMORY.forget("tg:7")
    assert asyncio.run(bot.answer("что приготовить?", "olga", dialog=("tg:7", "Оля"))) == "🐕 Паста с курицей."
    assert seen["context"] == ""          # первый вопрос — истории ещё нет
    asyncio.run(bot.answer("а без мяса?", "ivan", dialog=("tg:7", "Ваня")))
    assert seen["context"] == "Оля: что приготовить? \nБобик: Паста с курицей.".replace(" \n", "\n")
    assert "Ваня: а без мяса?" in dialog.MEMORY.history("tg:7")


def test_answer_without_dialog_keeps_old_behaviour(monkeypatch):
    bot = load_bot()
    seen = {}

    async def fake_llm(q, u, context=""):
        seen["context"] = context
        return "🐕 ок"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    assert asyncio.run(bot.answer("вопрос", "admin")) == "🐕 ок"
    assert seen["context"] == ""


def test_gate_refusal_is_not_remembered(monkeypatch):
    bot = load_bot()
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_REFUSE, "tool": None, "message": "🐕 Не могу.", "reason": "deny"})
    from app import dialog
    dialog.MEMORY.forget("tg:8")
    asyncio.run(bot.answer("удали всё", "ivan", dialog=("tg:8", "Ваня")))
    assert dialog.MEMORY.history("tg:8") == ""


def test_gateway_failure_is_not_remembered(monkeypatch):
    bot = load_bot()

    async def boom(q, u, context=""):
        raise RuntimeError("шлюз упал")

    monkeypatch.setattr(bot, "_ask_llm", boom)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    from app import dialog
    dialog.MEMORY.forget("tg:9")
    reply = asyncio.run(bot.answer("вопрос", "ivan", dialog=("tg:9", "Ваня")))
    assert "попробуйте позже" in reply
    assert dialog.MEMORY.history("tg:9") == ""


def test_context_is_passed_to_gateway_payload(monkeypatch):
    """Историю должен получить именно шлюз — проверяем тело запроса, а не обёртку."""
    bot = load_bot()
    sent = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"content": "ответ"}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            sent.update(json or {})
            return FakeResponse()

    monkeypatch.setattr(bot.httpx, "AsyncClient", FakeClient)
    asyncio.run(bot._ask_llm("вопрос", "ivan", context="Оля: раз\nБобик: два"))
    assert sent["context"] == "Оля: раз\nБобик: два"
    assert sent["prompt"] == "вопрос"
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/nas_api/test_bobik_answer.py`
Expected: FAIL — `TypeError: answer() got an unexpected keyword argument 'dialog'`

- [ ] **Step 3: реализация**

В `talk_bot.py` заменить сигнатуру и тело формирования payload в `_ask_llm`:
```python
async def _ask_llm(question: str, user: str, context: str = "") -> str:
```
и в словаре `payload` после `"user": user,` добавить:
```python
    }
    if context:
        # История разговора: шлюз фильтрует её вместе с вопросом (safe_full = redact(full)).
        payload["context"] = context
```
(то есть закрыть словарь и дописать поле отдельно, не ломая остальные ключи).

`ask` и `answer` заменить на:
```python
async def ask(question: str, user: str, context: str = "") -> str:
    """Вопрос в облако через шлюз; исключение превращается в вежливый ответ."""
    failed = False
    try:
        reply = await _ask_llm(question, user, context=context)
    except Exception as exc:
        log.exception("bobik LLM call failed")
        _STATE["llm_last_error"] = str(exc)
        reply = "🐕 Не смог получить ответ — попробуйте позже."
        failed = True
    _count_llm_reply(user)
    log.info("bobik LLM replied",
             extra={"fields": {"user": user, "chars": len(question),
                               "context_chars": len(context), "outbound": True}})
    _STATE["llm_failed_last"] = failed
    return reply


def remember(dialog, question: str, reply: str) -> None:
    """Запомнить пару «вопрос-ответ». Неудачный ответ шлюза в историю не пишем."""
    if not dialog or _STATE.get("llm_failed_last"):
        return
    key, speaker = dialog
    dialog_mem.MEMORY.add(key, speaker, question)
    dialog_mem.MEMORY.add(key, "Бобик", reply.lstrip("🐕").strip())


async def answer(question: str, user: str, dialog=None) -> str:
    """Полный путь @бобик для текстового вопроса (без картинок)."""
    early = await gate_reply(question, user)
    if early is not None:
        return early
    context = dialog_mem.MEMORY.history(dialog[0]) if dialog else ""
    reply = await ask(question, user, context=context)
    remember(dialog, question, reply)
    return reply
```
Импорт рядом с остальными: `from app import dialog as dialog_mem`.

В Talk-цикле (`_handle_messages`) строку `reply = await ask(question, user)` заменить на:
```python
            dialog = ("talk:%s" % token, m.get("actorDisplayName") or user)
            reply = await ask(question, user, context=dialog_mem.MEMORY.history(dialog[0]))
            remember(dialog, question, reply)
```

- [ ] **Step 4: тесты проходят**

Run: `python -m pytest -q tests/nas_api`
Expected: все зелёные (включая `test_bot_image_path.py` — ветка фото не менялась).

- [ ] **Step 5: коммит**

```bash
git add services/nas_jetson_nano-api/app/routers/talk_bot.py tests/nas_api/test_bobik_answer.py
git commit -m "feat(bobik): conversation history goes to the gateway context; Talk remembers per room" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Telegram — ключи разговоров, имя говорящего, «забудь»

**Files:**
- Modify: `services/nas_jetson_nano-api/app/telegram_bot.py` (`route`, `handle_update` — ветка `ask` ~строка 259, `HELP`)
- Modify: `tests/nas_api/test_telegram_bot.py` (дописать в конец; `make()` — сигнатура `answer`)

**Interfaces:**
- Consumes: `talk_bot.answer(question, user, dialog=(key, speaker))` (Task 2), `app.dialog.MEMORY` (Task 1).
- Produces: `route()` возвращает также `("forget", None)`; `TelegramBot.handle_update` передаёт `dialog=("tg:<chat_id>", имя)`.

- [ ] **Step 1: падающие тесты**

В `tests/nas_api/test_telegram_bot.py` в функции `make()` заменить объявление `answer` на:
```python
    async def answer(q, user, dialog=None):
        asked.append((q, user, dialog))
        return "🐕 ответ"
```
и во всех существующих проверках `asked == [(...)]` дописать третий элемент `None` там, где диалог не ожидается — **нет**: вместо этого в существующих тестах сравнивать только первые два поля, заменив
`assert asked == [("столица Франции?", "ivan")]` на `assert [a[:2] for a in asked] == [("столица Франции?", "ivan")]` (и так же в остальных местах, где сравнивается `asked`).

Дописать в конец файла:
```python
# ── память разговора (спецификация 2026-09-19) ────────────────────────────────

def test_group_uses_one_key_and_real_speaker_names():
    mod, bot, tg, dl, asked = make()
    m1 = msg("бобик, что приготовить?", uid=SON)
    m1["message"]["from"]["first_name"] = "Ваня"
    m2 = msg("бобик, а без мяса?", uid=OWNER)
    m2["message"]["from"]["first_name"] = "Алексей"
    asyncio.run(bot.handle_update(m1))
    asyncio.run(bot.handle_update(m2))
    assert [a[2] for a in asked] == [("tg:%d" % FAMILY, "Ваня"), ("tg:%d" % FAMILY, "Алексей")]


def test_private_chat_has_its_own_key():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("привет", chat=OWNER, chat_type="private", uid=OWNER)))
    assert asked[0][2][0] == "tg:%d" % OWNER


def test_forget_clears_the_conversation():
    mod, bot, tg, dl, asked = make()
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)
    dialog.MEMORY.add(key, "Ваня", "что приготовить?")
    asyncio.run(bot.handle_update(msg("бобик, забудь")))
    assert dialog.MEMORY.history(key) == ""
    assert asked == []
    assert "Забыл" in tg.texts()[0][1]


def test_downloads_are_not_remembered():
    mod, bot, tg, dl, asked = make()
    from app import dialog
    key = "tg:%d" % FAMILY
    dialog.MEMORY.forget(key)
    asyncio.run(bot.handle_update(msg("бобик, скачай magnet:?xt=urn:btih:ABC")))
    asyncio.run(bot.handle_update(msg("бобик, закачки")))
    assert dialog.MEMORY.history(key) == ""
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/nas_api/test_telegram_bot.py`
Expected: FAIL — `IndexError`/`AssertionError`: третьего поля в `asked` нет, «забудь» не распознан.

- [ ] **Step 3: реализация**

В `route()` перед `return "ask", text.strip()` добавить:
```python
    if low.startswith("забудь"):
        return "forget", None
```

В `handle_update`, в ветке ответа (`else: … sendChatAction … self.answer(...)`) заменить на:
```python
        elif kind == "forget":
            from app import dialog as dialog_mem
            dialog_mem.MEMORY.forget("tg:%s" % chat_id)
            await self._say(chat_id, "🐕 Забыл, начнём сначала.", mid)
        else:
            speaker = (msg.get("from") or {}).get("first_name") or login
            await self.api.call("sendChatAction", chat_id=chat_id, action="typing")
            reply = await self.answer(arg, login, dialog=("tg:%s" % chat_id, speaker))
            await self._say(chat_id, reply, mid)
```

В `HELP` после строки про «отмени N» добавить:
```python
        "• забудь — начать разговор заново\n"
```

- [ ] **Step 4: тесты проходят**

Run: `python -m pytest -q tests/nas_api`
Expected: все зелёные.

- [ ] **Step 5: документация**

В `docs/plans/DEPLOY_DOWNLOADER_2026-09.md` в §9 добавить пункт проверки:
```markdown
6. Память разговора: «бобик, что приготовить на ужин?» → ответ → «бобик, а без мяса?» (ответ учитывает
   предыдущий вопрос) → «бобик, забудь» → «🐕 Забыл, начнём сначала.»
```
и одно предложение об этом в EN summary того же документа.

- [ ] **Step 6: коммит**

```bash
git add services/nas_jetson_nano-api/app/telegram_bot.py tests/nas_api/test_telegram_bot.py docs/plans/DEPLOY_DOWNLOADER_2026-09.md
git commit -m "feat(telegram): per-chat conversation memory, speaker names, «забудь»" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review (выполнено автором плана)

- Спецификация §2 (общая нить группы, 10 реплик/30 мин, только в памяти) → Task 1; §3–§4 (context, компоненты) → Task 2; §5 (поведение, «забудь», что не запоминается) → Task 2–3; §6 (журнал без текста, пределы) → Task 1–2; §7 (тесты) → все задачи; §8 (выкат) → Task 3 Step 5.
- Имена сверены: `DialogMemory`/`MEMORY`/`add`/`history`/`forget`; `_ask_llm(context=)`, `ask(context=)`, `answer(dialog=)`, `remember(dialog, question, reply)`; ключи `tg:<chat_id>` и `talk:<token>`.
- Известное ограничение (в спецификации §6): safety gate историю не видит — опасная просьба, разбитая на реплики, проверяется только по новой реплике.
- Тест `test_history_is_sent_as_context_and_turns_are_remembered` сравнивает историю с точностью до строки — при правке формата `history()` его придётся менять осознанно.
