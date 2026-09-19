# Качалка + первый срез Telegram-бота: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** семья пишет в Telegram «@бобик скачай <ссылка>» — Jetson качает (SSD или сразу HDD), кладёт в `\\192.168.0.50\hdd2tb\Downloads` и сообщает в тот же чат; «@бобик <вопрос>» — ответ GigaChat тем же путём, что в Talk.

**Architecture:** aria2 в отдельном контейнере (торренты + HTTP, AriaNg в LAN) с хуками переноса и очистки. В контейнере NAS API — модуль `downloads` (ссылки, выбор диска, учёт, страж места, уведомления) и `telegram_bot` (long polling через SSH SOCKS на `172.17.0.1:1080`, белый список, обращение «@бобик», маршрутизация). Вопросы идут через общую функцию `talk_bot.answer()` — вынесенную из Talk-бота цепочку safety gate → шлюз → GigaChat.

**Tech Stack:** Python 3.12 (контейнер NAS API: FastAPI, httpx[socks]), pytest; bash (хуки aria2, скрипт скорости); Alpine + aria2 + AriaNg; systemd; docker compose.

**Spec:** `docs/superpowers/specs/2026-09-19-home-downloader-design.md` (редакции 1–5) и поправка к `docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md`.

## Global Constraints

- Язык комментариев, сообщений бота и документации — **русский**; у документа в `docs/` — EN summary (правило №15).
- Обращение к боту — в начале сообщения: `@бобик` или `бобик,` (регистр не важен), настоящее упоминание `@bobik_borovskoy_bot`, ответ на сообщение бота; в личке — без обращения. Сообщение группы без обращения **отбрасывается без записи в журнал**.
- Команды: `скачай <ссылка>`, `закачки`, `отмени N`, `.torrent`-документ (≤ 20 МБ) с подписью `@бобик скачай`; всё остальное после обращения — вопрос к GigaChat через `talk_bot.answer(question, login)`.
- Белый список: `TELEGRAM_USERS` = `user_id:логин` через пробел; одна группа `TELEGRAM_FAMILY_CHAT_ID`; из чужих групп бот выходит (`leaveChat`); незнакомцу в личке — один ответ «вы не в семейном списке» + сообщение владельцу.
- Прокси Telegram: `socks5://172.17.0.1:1080` (адрес docker0). Jetson напрямую до Telegram не доходит.
- Размер закачки без предела. Цель: ≤ `DL_SSD_MAX_GB`=20 ГБ и помещается на SSD с запасом → SSD; иначе HDD; больше свободного на HDD с запасом → отказ. Запасы: SSD `DL_SSD_MIN_FREE_GB`=40, HDD `DL_HDD_MIN_FREE_GB`=50. Страж раз в 30 с.
- Пути **в контейнере aria2**: SSD-закачки `/downloads/ssd/.incomplete`, HDD-закачки `/downloads/hdd/.incomplete`, готовое `/downloads/hdd`. Хост: `/mnt/storage/downloads` → `/downloads/ssd`, `/mnt/hdd2tb/Downloads` → `/downloads/hdd`. В контейнере NAS API те же каталоги смонтированы **только для чтения** как `/dl/ssd` и `/dl/hdd` (для `statvfs`).
- `file-allocation`: `falloc` на SSD, `none` на HDD (ntfs-3g).
- `seed-time=0`, не больше 2 закачек одновременно, раздача выключена.
- Отклонять ссылки: не `magnet:`/`http://`/`https://`; `localhost`, `*.local`, `*.lan`, `*.internal`; IP из частных, loopback, link-local, reserved, multicast, unspecified.
- Секреты (`TELEGRAM_BOT_TOKEN`, `ARIA2_RPC_SECRET`) — только `config/.env` устройства; в git пустые ключи в `config/.env.example`. Секрет aria2 не попадает в argv процессов (ни `aria2c`, ни `curl`). Telegram ID — только `docs/local/IDENTIFIERS.md` (вне git).
- В журналах — метаданные (кто, тип, размер), без текста сообщений и без полных ссылок.
- VPS: ничего не устанавливается и не меняется; только SSH-сессия SOCKS от Jetson (правило №13).
- Тесты: `tests/nas_api/` (pytest, Python 3.12, `asyncio.run`, без pytest-asyncio) и `tests/unit/` (запуск `python3 файл`, совместимо с Python 3.6). Оба каталога уже в воротах `scripts/quality/preflight.sh` и в CI.
- Каждый коммит заканчивается строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`; хук pre-commit прогоняет ворота; `--no-verify` запрещён.
- Выкат на Jetson — **не в этом плане**, только по «деплой» по runbook из Task 6.

## Файлы

| Файл | Ответственность |
|---|---|
| `services/nas_jetson_nano-api/app/routers/talk_bot.py` (изменение) | вынести `gate_reply()`, `ask()`, `answer()`; Talk-цикл вызывает их |
| `services/nas_jetson_nano-api/app/downloads.py` | ссылки, выбор диска, aria2 JSON-RPC, учёт, страж, тексты |
| `services/nas_jetson_nano-api/app/telegram_bot.py` | Telegram API через SOCKS, обращение, белый список, маршрутизация, циклы |
| `services/nas_jetson_nano-api/app/config.py`, `app/main.py`, `requirements.txt` (изменения) | настройки, запуск циклов, `httpx[socks]` |
| `services/downloads/{Dockerfile,aria2.conf,entrypoint.sh,on_complete.sh,on_stop.sh}` | контейнер aria2 + AriaNg |
| `docker/compose/docker-compose.downloads.yml`; `docker/compose/docker-compose.nas_jetson_nano-api.yml` (изменение) | запуск |
| `systemd/nas_jetson_nano-tg-socks.service` | SOCKS к VPS |
| `scripts/downloads/aria2_speed.sh`, `systemd/nas_jetson_nano-dl-speed-{day,night}.{service,timer}` | дневной лимит скорости |
| `config/.env.example` (изменение) | пустые ключи |
| `tests/nas_api/test_bobik_answer.py`, `test_downloads.py`, `test_telegram_bot.py` | тесты модулей API |
| `tests/unit/test_aria2_hooks.py`, `tests/unit/test_downloader_infra.py` | хуки и инфраструктура |
| `docs/plans/DEPLOY_DOWNLOADER_2026-09.md` | runbook выката |

---

### Task 1: Общая функция ответа `@бобик` (вынос из Talk-бота)

**Files:**
- Modify: `services/nas_jetson_nano-api/app/routers/talk_bot.py` (ветка «2) LLM callsign» в `_handle_messages`, строки ~453–540; новые функции — сразу после `_ask_llm`)
- Create: `tests/nas_api/test_bobik_answer.py`

**Interfaces:**
- Produces:
  - `async def gate_reply(question: str, user: str) -> str | None` — ответ, если всё решилось до облака (лимит, отказ gate, уточнение, домашний инструмент); `None` — gate пропустил как «chat».
  - `async def ask(question: str, user: str) -> str` — вызов `_ask_llm` с перехватом исключения и учётом ответа.
  - `async def answer(question: str, user: str) -> str` — `gate_reply`, иначе `ask`.

- [ ] **Step 1: падающие тесты**

`tests/nas_api/test_bobik_answer.py`:
```python
"""Общая функция ответа @бобик — для Talk и Telegram (план качалки, Task 1).

Зачем: Telegram-бот обязан идти тем же путём, что Talk (safety gate ADR-0011 → шлюз с
сервисным токеном → квота по логину). Копия цепочки разошлась бы с оригиналом; поэтому
цепочка вынесена в talk_bot.answer(), а Talk-цикл вызывает её же.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load_bot():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "TALK_BOT_LLM_TRIGGER": "@бобик",
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "TALK_BOT_LLM_DAILY_REPLIES": "2",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.routers.talk_bot")


def test_refused_question_never_reaches_llm(monkeypatch):
    bot = load_bot()
    called = []

    async def fake_llm(q, u):
        called.append(q)
        return "🐕 ok"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_REFUSE, "tool": None, "message": "🐕 Не могу.", "reason": "t"})
    reply = asyncio.run(bot.answer("удали все файлы", "ivan"))
    assert reply == "🐕 Не могу."
    assert called == []


def test_chat_question_goes_to_llm_and_is_counted(monkeypatch):
    bot = load_bot()

    async def fake_llm(q, u):
        return "🐕 Париж (%s)" % u

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    before = bot._STATE.get("llm_replied", 0)
    assert asyncio.run(bot.answer("столица Франции?", "olga")) == "🐕 Париж (olga)"
    assert bot._STATE["llm_replied"] == before + 1


def test_llm_exception_becomes_polite_reply(monkeypatch):
    bot = load_bot()

    async def boom(q, u):
        raise RuntimeError("шлюз упал")

    monkeypatch.setattr(bot, "_ask_llm", boom)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    assert "попробуйте позже" in asyncio.run(bot.answer("вопрос", "admin"))


def test_daily_reply_limit_is_per_user(monkeypatch):
    bot = load_bot()

    async def fake_llm(q, u):
        return "🐕 ok"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_CHAT, "tool": None, "message": None, "reason": "chat"})
    for _ in range(2):
        assert asyncio.run(bot.answer("q", "ulyana")) == "🐕 ok"
    assert "лимит" in asyncio.run(bot.answer("q", "ulyana"))
    assert asyncio.run(bot.answer("q", "ivan")) == "🐕 ok"


def test_home_tool_answers_locally(monkeypatch):
    bot = load_bot()
    called = []

    async def fake_llm(q, u):
        called.append(q)
        return "x"

    async def fake_tool(tool, user=""):
        return "🐕 Диск: 7%"

    monkeypatch.setattr(bot, "_ask_llm", fake_llm)
    monkeypatch.setattr(bot, "_dispatch_home_tool", fake_tool)
    monkeypatch.setattr(bot, "admit", lambda text, structured_tools=True: {
        "decision": bot.ADMIT_EXECUTE, "tool": "disk", "message": None, "reason": "tool_intent"})
    assert asyncio.run(bot.answer("сколько места?", "admin")) == "🐕 Диск: 7%"
    assert called == []
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/nas_api/test_bobik_answer.py`
Expected: FAIL — `AttributeError: module 'app.routers.talk_bot' has no attribute 'answer'`

- [ ] **Step 3: реализация — новые функции сразу после `_ask_llm`**

```python
# ── общий ответ @бобик (Talk и Telegram) ────────────────────────────────────────

async def gate_reply(question: str, user: str) -> str | None:
    """Всё, что решается до облака: дневной лимит, safety gate (ADR-0011), домашние
    инструменты. Возвращает текст ответа или None — gate пропустил как «chat», и
    вызывающий идёт в LLM (Talk ещё может уйти в ветку картинок)."""
    if not _llm_quota_left(user):
        _STATE["llm_refused"] = _STATE.get("llm_refused", 0) + 1
        return "🐕 На сегодня лимит вопросов исчерпан."
    use_gate = bool(
        getattr(settings, "talk_bot_safety_gate", True)
        or getattr(settings, "talk_bot_structured_tools", True)
    )
    if not use_gate:
        return None
    decision = admit(
        question,
        structured_tools=bool(getattr(settings, "talk_bot_structured_tools", True)),
    )
    d = decision.get("decision")
    if d == ADMIT_REFUSE:
        _STATE["gate_refuse"] = _STATE.get("gate_refuse", 0) + 1
        _STATE["llm_refused"] = _STATE.get("llm_refused", 0) + 1
        log.info("bobik gate refuse",
                 extra={"fields": {"user": user, "reason": decision.get("reason"),
                                   "outbound": False}})
        return decision.get("message") or "🐕 Не могу."
    if d == ADMIT_CLARIFY:
        _STATE["gate_clarify"] = _STATE.get("gate_clarify", 0) + 1
        return decision.get("message") or "🐕 Уточни."
    if d == ADMIT_EXECUTE and decision.get("tool"):
        _STATE["gate_execute"] = _STATE.get("gate_execute", 0) + 1
        try:
            reply = await _dispatch_home_tool(decision["tool"], user=user)
        except Exception as exc:
            log.exception("bobik home tool failed")
            reply = f"🐕 Ошибка локальной команды: {exc}"
        _STATE["replied"] = _STATE.get("replied", 0) + 1
        log.info("bobik home tool",
                 extra={"fields": {"user": user, "tool": decision.get("tool"),
                                   "outbound": False}})
        return reply
    _STATE["gate_chat"] = _STATE.get("gate_chat", 0) + 1
    return None


async def ask(question: str, user: str) -> str:
    """Вопрос в облако через шлюз; исключение превращается в вежливый ответ."""
    try:
        reply = await _ask_llm(question, user)
    except Exception as exc:
        log.exception("bobik LLM call failed")
        _STATE["llm_last_error"] = str(exc)
        reply = "🐕 Не смог получить ответ — попробуйте позже."
    _count_llm_reply(user)
    log.info("bobik LLM replied",
             extra={"fields": {"user": user, "chars": len(question), "outbound": True}})
    return reply


async def answer(question: str, user: str) -> str:
    """Полный путь @бобик для текстового вопроса (без картинок)."""
    early = await gate_reply(question, user)
    if early is not None:
        return early
    return await ask(question, user)
```

- [ ] **Step 4: Talk-цикл вызывает общие функции**

В `_handle_messages` блок, начинающийся строкой `# 2) LLM callsign — the family explicitly asked to go outside.` и заканчивающийся концом цикла (`log.info("talk bot LLM replied", …)`), заменить на:
```python
        # 2) LLM callsign — the family explicitly asked to go outside.
        question = _match_llm(text)
        if question:
            user = _actor(m)
            early = await gate_reply(question, user)
            if early is not None:
                await _send(token, early, settings.talk_bot_llm_display_name)
                continue
            # C6: фото — только ПОСЛЕ решения safety gate (раньше ветка стояла до admit()
            # и сообщение с вложением обходило gate целиком; аудит 2026-09-19, G08).
            if _image_attachment(m):
                await _handle_image_request(token, m, question, user)
                continue
            reply = await ask(question, user)
            await _send(token, reply, settings.talk_bot_llm_display_name)
```

- [ ] **Step 5: тесты проходят, регрессия Talk чистая**

Run: `python -m pytest -q tests/nas_api && python tests/unit/test_bobik_gate.py`
Expected: все зелёные (`test_bot_image_path.py` подтверждает, что фото по-прежнему идёт после gate).

- [ ] **Step 6: коммит**

```bash
git add services/nas_jetson_nano-api/app/routers/talk_bot.py tests/nas_api/test_bobik_answer.py
git commit -m "refactor(bot): shared @бобик answer path (gate → gateway → GigaChat) for Talk and Telegram" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Модуль закачек `downloads`

**Files:**
- Create: `services/nas_jetson_nano-api/app/downloads.py`
- Modify: `services/nas_jetson_nano-api/app/config.py` (поля в конец класса `Settings`, перед методами)
- Create: `tests/nas_api/test_downloads.py`

**Interfaces:**
- Produces:
  - `class LinkError(ValueError)`; `parse_link(text: str) -> str`; `fmt_size(n: int) -> str`; `choose_target(size: int | None, ssd_free: int, hdd_free: int) -> str` (`"ssd"`/`"hdd"`, иначе `LinkError`).
  - `class Aria2(url=None, secret=None, transport=None)`: `async call(method: str, *params)`.
  - `class Ledger(path=None)`: `load() -> dict`, `save(data: dict)`.
  - `class Downloads(aria2=None, ledger=None, head=None, disk_free=None, clock=time.time)`:
    `async add_link(link: str, chat_id: int, user: str) -> str`,
    `async add_torrent(data: bytes, chat_id: int, user: str) -> str`,
    `async list_text() -> str`, `async cancel(n: int) -> str`,
    `async tick() -> list[tuple[int, str]]` — сообщения `(chat_id, текст)` к отправке.
  - `DONE_HINT = "\\\\192.168.0.50\\hdd2tb\\Downloads"`.

- [ ] **Step 1: настройки**

В `class Settings` (`app/config.py`) перед первым `def` добавить:
```python
    # ── Telegram: первый срез бота (качалка + вопросы @бобик) ──────────────────────
    telegram_bot_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_users: str = ""  # "user_id:логин user_id:логин"
    telegram_family_chat_id: str = ""
    telegram_owner_login: str = "admin"
    telegram_proxy: str = ""  # socks5://172.17.0.1:1080 — Jetson напрямую Telegram не видит
    telegram_api: str = "https://api.telegram.org"
    telegram_callsigns: str = "@бобик|бобик,"  # разделитель «|»: запятая — часть позывного
    telegram_state_file: str = "/var/log/nas_jetson_nano-monitor/telegram-state.json"

    # ── Качалка (aria2) ─────────────────────────────────────────────────────────────
    aria2_rpc_url: str = "http://host.docker.internal:6800/jsonrpc"
    aria2_rpc_secret: str = ""
    dl_ssd_dir: str = "/downloads/ssd/.incomplete"  # путь в контейнере aria2
    dl_hdd_dir: str = "/downloads/hdd/.incomplete"
    dl_ssd_stat_path: str = "/dl/ssd"  # тот же диск в контейнере API (ro), для statvfs
    dl_hdd_stat_path: str = "/dl/hdd"
    dl_ssd_min_free_gb: int = 40
    dl_hdd_min_free_gb: int = 50
    dl_ssd_max_gb: int = 20
    dl_ledger_file: str = "/var/log/nas_jetson_nano-monitor/downloads-ledger.json"
```

- [ ] **Step 2: падающие тесты**

`tests/nas_api/test_downloads.py`:
```python
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
```

- [ ] **Step 3: убедиться, что падают**

Run: `python -m pytest -q tests/nas_api/test_downloads.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.downloads'`

- [ ] **Step 4: реализация**

`services/nas_jetson_nano-api/app/downloads.py`:
```python
"""Домашняя качалка: закачки через aria2 по командам из чата.

Спецификация: docs/superpowers/specs/2026-09-19-home-downloader-design.md.
Малое (≤ DL_SSD_MAX_GB и помещается на SSD с запасом) качается на SSD и переносится
хуком aria2 на HDD; большое — сразу на HDD (канал ≈ 11 МБ/с, ntfs-3g ≈ 90 МБ/с).
Страж раз в 30 с держит запас на SSD (Immich/Nextcloud) и HDD (архив 1,4 ТБ).
"""
from __future__ import annotations

import base64
import ipaddress
import json
import logging
import os
import re
import time
import urllib.parse

import httpx

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.downloads")

GB = 1024 ** 3
DONE_HINT = "\\\\192.168.0.50\\hdd2tb\\Downloads"
_LINK_RE = re.compile(r"(magnet:\?\S+|https?://\S+)", re.IGNORECASE)
_BAD_SUFFIXES = (".local", ".lan", ".internal", ".localdomain")
_KEYS = ["gid", "status", "totalLength", "completedLength", "downloadSpeed",
         "files", "bittorrent", "followedBy", "errorMessage"]
_RESUME_MARGIN = 5 * GB  # гистерезис стража: продолжаем, когда запас восстановлен с лихвой


class LinkError(ValueError):
    """Ссылку ставить нельзя; текст исключения показывается человеку."""


def fmt_size(n: int) -> str:
    if n >= GB:
        return "%.1f ГБ" % (n / GB)
    return "%d МБ" % (n // (1024 * 1024))


def parse_link(text: str) -> str:
    m = _LINK_RE.search(text or "")
    if not m:
        raise LinkError("нужна magnet- или http(s)-ссылка")
    link = m.group(1).rstrip(").,;»\"'")
    if link.lower().startswith("magnet:"):
        if "xt=urn:btih:" not in link.lower():
            raise LinkError("в magnet-ссылке нет xt=urn:btih")
        return link
    host = (urllib.parse.urlsplit(link).hostname or "").lower()
    if not host:
        raise LinkError("в ссылке нет адреса")
    if host == "localhost" or host.endswith(_BAD_SUFFIXES):
        raise LinkError("ссылки во внутреннюю сеть запрещены")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return link
    if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified):
        raise LinkError("ссылки во внутреннюю сеть запрещены")
    return link


def choose_target(size, ssd_free: int, hdd_free: int) -> str:
    ssd_room = ssd_free - settings.dl_ssd_min_free_gb * GB
    hdd_room = hdd_free - settings.dl_hdd_min_free_gb * GB
    if size is None:
        if ssd_room > 0:
            return "ssd"
        if hdd_room > 0:
            return "hdd"
        raise LinkError("нет места ни на SSD, ни на HDD")
    if size > hdd_room:
        raise LinkError("не помещается: нужно %s, на HDD доступно %s"
                        % (fmt_size(size), fmt_size(max(hdd_room, 0))))
    if size <= settings.dl_ssd_max_gb * GB and size <= ssd_room:
        return "ssd"
    return "hdd"


def _options(target: str) -> dict:
    if target == "ssd":
        return {"dir": settings.dl_ssd_dir, "file-allocation": "falloc"}
    return {"dir": settings.dl_hdd_dir, "file-allocation": "none"}


def _disk_free() -> tuple:
    ssd = os.statvfs(settings.dl_ssd_stat_path)
    hdd = os.statvfs(settings.dl_hdd_stat_path)
    return ssd.f_bavail * ssd.f_frsize, hdd.f_bavail * hdd.f_frsize


async def _head_size(url: str):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.head(url)
        n = int(r.headers.get("content-length", "0"))
        return n or None
    except Exception:
        return None


def _name(st: dict, fallback: str = "") -> str:
    info = (st.get("bittorrent") or {}).get("info") or {}
    if info.get("name"):
        return info["name"]
    files = st.get("files") or []
    if files and files[0].get("path"):
        return os.path.basename(files[0]["path"])
    return fallback or st.get("gid", "?")


class Aria2:
    """aria2 JSON-RPC. Секрет — первым параметром (`token:…`), в журнал не пишется."""

    def __init__(self, url=None, secret=None, transport=None):
        self.url = url or settings.aria2_rpc_url
        self.secret = settings.aria2_rpc_secret if secret is None else secret
        self._transport = transport

    async def call(self, method: str, *params):
        body = {"jsonrpc": "2.0", "id": "nas", "method": "aria2." + method,
                "params": ["token:" + self.secret, *params]}
        async with httpx.AsyncClient(timeout=15, transport=self._transport) as c:
            r = await c.post(self.url, json=body)
        data = r.json()
        if "error" in data:
            raise RuntimeError("aria2: %s" % data["error"].get("message"))
        return data["result"]


class Ledger:
    """Учёт «GID → кто и откуда поставил»; атомарная запись, битый файл = пусто."""

    def __init__(self, path=None):
        self.path = path or settings.dl_ledger_file

    def load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: dict) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, self.path)


class Downloads:
    def __init__(self, aria2=None, ledger=None, head=None, disk_free=None, clock=time.time):
        self.aria2 = aria2 or Aria2()
        self.ledger = ledger or Ledger()
        self.head = head or _head_size
        self.disk_free = disk_free or _disk_free
        self.clock = clock

    def _free(self) -> tuple:
        try:
            return self.disk_free()
        except OSError:
            return 0, 0  # диск недоступен = места нет: страж остановит закачки

    def _record(self, gid: str, chat_id: int, user: str, name: str, state: str) -> None:
        data = self.ledger.load()
        data[gid] = {"chat_id": chat_id, "user": user, "name": name, "state": state,
                     "created": int(self.clock())}
        self.ledger.save(data)

    async def add_link(self, link: str, chat_id: int, user: str) -> str:
        if link.lower().startswith("magnet:"):
            gid = await self.aria2.call("addUri", [link], {"dir": settings.dl_ssd_dir})
            self._record(gid, chat_id, user, "magnet", "metadata")
            log.info("download queued", extra={"fields": {"user": user, "type": "magnet"}})
            return "⏬ Принял, получаю описание торрента…"
        name = os.path.basename(urllib.parse.urlsplit(link).path) or "файл"
        size = await self.head(link)
        ssd, hdd = self._free()
        try:
            target = choose_target(size, ssd, hdd)
        except LinkError as exc:
            return "❌ %s" % exc
        gid = await self.aria2.call("addUri", [link], _options(target))
        self._record(gid, chat_id, user, name, "active")
        log.info("download queued", extra={"fields": {"user": user, "type": "http",
                                                      "size": size, "target": target}})
        size_txt = fmt_size(size) if size else "размер неизвестен"
        return "⏬ Принял: %s — %s, на %s" % (name, size_txt, target.upper())

    async def add_torrent(self, data: bytes, chat_id: int, user: str) -> str:
        b64 = base64.b64encode(data).decode("ascii")
        gid = await self.aria2.call("addTorrent", b64, [], {"pause": "true"})
        self._record(gid, chat_id, user, "torrent", "await_dir")
        log.info("download queued", extra={"fields": {"user": user, "type": "torrent"}})
        return "⏬ Принял торрент, проверяю размер…"

    async def _route_paused(self, gid: str, entry: dict, st: dict, msgs: list) -> None:
        size = int(st.get("totalLength") or 0)
        if not size:
            return  # размер ещё неизвестен — подождём следующего такта
        name = _name(st, entry.get("name", ""))
        entry["name"] = name
        ssd, hdd = self._free()
        try:
            target = choose_target(size, ssd, hdd)
        except LinkError as exc:
            await self.aria2.call("forceRemove", gid)
            entry["state"] = "error"
            msgs.append((entry["chat_id"], "❌ %s: %s" % (name, exc)))
            return
        await self.aria2.call("changeOption", gid, _options(target))
        await self.aria2.call("unpause", gid)
        entry["state"] = "active"
        msgs.append((entry["chat_id"], "⏬ Качаю: %s — %s, на %s"
                     % (name, fmt_size(size), target.upper())))

    async def tick(self) -> list:
        msgs: list = []
        data = self.ledger.load()
        meta = data.pop("_meta", {})
        for gid in list(data):
            entry = data[gid]
            if entry.get("state") in ("done", "error", "cancelled"):
                continue
            try:
                st = await self.aria2.call("tellStatus", gid, _KEYS)
            except RuntimeError:
                entry["state"] = "error"
                continue
            if entry["state"] == "metadata":
                if st.get("status") == "complete" and st.get("followedBy"):
                    new = st["followedBy"][0]
                    data[new] = dict(entry, state="await_dir")
                    del data[gid]
                    st2 = await self.aria2.call("tellStatus", new, _KEYS)
                    await self._route_paused(new, data[new], st2, msgs)
                elif st.get("status") == "error":
                    entry["state"] = "error"
                    msgs.append((entry["chat_id"], "❌ Не скачалось: %s — %s"
                                 % (entry["name"], st.get("errorMessage") or "ошибка")))
                continue
            if entry["state"] == "await_dir":
                await self._route_paused(gid, entry, st, msgs)
                continue
            name = _name(st, entry.get("name", ""))
            if st.get("status") == "complete":
                entry["state"] = "done"
                msgs.append((entry["chat_id"], "✅ Готово: %s — %s" % (name, DONE_HINT)))
            elif st.get("status") == "error":
                entry["state"] = "error"
                msgs.append((entry["chat_id"], "❌ Не скачалось: %s — %s"
                             % (name, st.get("errorMessage") or "ошибка")))
            elif st.get("status") == "removed":
                entry["state"] = "cancelled"
        await self._guard(data, meta, msgs)
        data["_meta"] = meta
        self.ledger.save(data)
        return msgs

    async def _guard(self, data: dict, meta: dict, msgs: list) -> None:
        ssd, hdd = self._free()
        ssd_min = settings.dl_ssd_min_free_gb * GB
        hdd_min = settings.dl_hdd_min_free_gb * GB
        chats = sorted({e["chat_id"] for e in data.values()
                        if e.get("state") in ("active", "metadata", "await_dir")})
        if ssd < ssd_min or hdd < hdd_min:
            if not meta.get("paused"):
                await self.aria2.call("pauseAll")
                meta["paused"] = True
                need = []
                if ssd < ssd_min:
                    need.append("SSD: нужно ещё %s" % fmt_size(ssd_min - ssd))
                if hdd < hdd_min:
                    need.append("HDD: нужно ещё %s" % fmt_size(hdd_min - hdd))
                text = "⏸ Пауза закачек — мало места (%s)." % "; ".join(need)
                msgs.extend((c, text) for c in chats)
        elif meta.get("paused") and ssd >= ssd_min + _RESUME_MARGIN and hdd >= hdd_min + _RESUME_MARGIN:
            await self.aria2.call("unpauseAll")
            meta["paused"] = False
            msgs.extend((c, "▶️ Место есть — продолжаю закачки.") for c in chats)

    async def _queue(self) -> list:
        active = await self.aria2.call("tellActive", _KEYS)
        waiting = await self.aria2.call("tellWaiting", 0, 50, _KEYS)
        return list(active) + list(waiting)

    async def list_text(self) -> str:
        items = await self._queue()
        ledger = self.ledger.load()
        lines = []
        for i, st in enumerate(items, 1):
            total = int(st.get("totalLength") or 0)
            done = int(st.get("completedLength") or 0)
            pct = int(done * 100 / total) if total else 0
            speed = int(st.get("downloadSpeed") or 0) / (1024 * 1024)
            name = _name(st, (ledger.get(st["gid"]) or {}).get("name", ""))
            mark = " ⏸" if st.get("status") == "paused" else ""
            left = fmt_size(total - done) if total else "?"
            lines.append("%d. %s — %d%% · %.1f МБ/с · осталось %s%s"
                         % (i, name, pct, speed, left, mark))
        ssd, hdd = self._free()
        free = "Свободно: SSD %s, HDD %s (с учётом запаса)" % (
            fmt_size(max(ssd - settings.dl_ssd_min_free_gb * GB, 0)),
            fmt_size(max(hdd - settings.dl_hdd_min_free_gb * GB, 0)))
        if not lines:
            return "Закачек нет.\n" + free
        return "\n".join(lines + [free])

    async def cancel(self, n: int) -> str:
        items = await self._queue()
        if n < 1 or n > len(items):
            return "❌ Нет закачки с номером %d — посмотрите «@бобик закачки»." % n
        st = items[n - 1]
        ledger = self.ledger.load()
        name = _name(st, (ledger.get(st["gid"]) or {}).get("name", ""))
        await self.aria2.call("forceRemove", st["gid"])
        if st["gid"] in ledger:
            ledger[st["gid"]]["state"] = "cancelled"
            self.ledger.save(ledger)
        return "🗑 Отменил: %s" % name
```

> Примечание к тесту `test_list_shows_progress_and_free_space`: свободно SSD 150 − 40 = 110 ГБ, HDD 400 − 50 = 350 ГБ.

- [ ] **Step 5: тесты проходят**

Run: `python -m pytest -q tests/nas_api/test_downloads.py`
Expected: все зелёные.

- [ ] **Step 6: коммит**

```bash
git add services/nas_jetson_nano-api/app/downloads.py services/nas_jetson_nano-api/app/config.py tests/nas_api/test_downloads.py
git commit -m "feat(downloads): aria2 client, disk routing by size, ledger, space guard, chat texts" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Telegram-фронт и запуск циклов

**Files:**
- Create: `services/nas_jetson_nano-api/app/telegram_bot.py`
- Modify: `services/nas_jetson_nano-api/app/main.py` (функция `lifespan`)
- Modify: `services/nas_jetson_nano-api/requirements.txt` (`httpx>=0.27` → `httpx[socks]>=0.27`)
- Create: `tests/nas_api/test_telegram_bot.py`

**Interfaces:**
- Consumes: `talk_bot.answer(question, user) -> str` (Task 1); `downloads.Downloads`, `parse_link`, `LinkError` (Task 2); настройки `telegram_*` (Task 2, Step 1).
- Produces:
  - `class TgError(Exception)` (`.code`, `.retry_after`); `class TgApi(token, proxy=None, base=None, transport=None)`: `async call(method, **params)`, `async file_bytes(file_id, limit) -> bytes`.
  - `parse_users(s: str) -> dict[int, str]`; `addressed_text(msg: dict, bot_username: str, callsigns: list[str]) -> str | None`; `route(text: str) -> tuple[str, object]`.
  - `class TelegramBot(api, downloads, answer=None, state_path=None)`: `async handle_update(upd: dict)`, `async poll_forever()`, `async downloads_forever(interval=30)`.
  - `async def run() -> None` — точка входа для `lifespan`.

- [ ] **Step 1: падающие тесты**

`tests/nas_api/test_telegram_bot.py`:
```python
"""Telegram-фронт @бобик: обращение, белый список, маршрутизация, опрос (спецификация §4, §7).
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

import httpx

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"
FAMILY = -100123
OWNER, SON, STRANGER = 111, 222, 999


def load():
    os.environ.update({
        "LOG_FILE": os.path.join(tempfile.mkdtemp(), "api.jsonl"),
        "NEXTCLOUD_ADMIN_PASSWORD": "x",
        "TELEGRAM_USERS": "%d:admin %d:ivan" % (OWNER, SON),
        "TELEGRAM_FAMILY_CHAT_ID": str(FAMILY),
        "TELEGRAM_OWNER_LOGIN": "admin",
    })
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.telegram_bot")


class FakeTelegram:
    """httpx.MockTransport: отвечает как Bot API, записывает запросы."""

    def __init__(self, updates=None, file_bytes=b"d8:announce1:xe"):
        self.sent = []
        self.updates = updates or []
        self.file_bytes = file_bytes

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/file/bot" in path:
            return httpx.Response(200, content=self.file_bytes)
        method = path.rsplit("/", 1)[-1]
        body = json.loads(request.content or b"{}")
        self.sent.append((method, body))
        if method == "getMe":
            return httpx.Response(200, json={"ok": True, "result": {"id": 1, "username": "bobik_borovskoy_bot"}})
        if method == "getUpdates":
            ups, self.updates = self.updates, []
            return httpx.Response(200, json={"ok": True, "result": ups})
        if method == "getFile":
            return httpx.Response(200, json={"ok": True, "result": {"file_path": "docs/x.torrent", "file_size": 20}})
        return httpx.Response(200, json={"ok": True, "result": True})

    def texts(self):
        return [(b.get("chat_id"), b.get("text")) for m, b in self.sent if m == "sendMessage"]


class FakeDownloads:
    def __init__(self):
        self.calls = []

    async def add_link(self, link, chat_id, user):
        self.calls.append(("link", link, chat_id, user))
        return "⏬ Принял: x"

    async def add_torrent(self, data, chat_id, user):
        self.calls.append(("torrent", data, chat_id, user))
        return "⏬ Принял торрент, проверяю размер…"

    async def list_text(self):
        return "Закачек нет."

    async def cancel(self, n):
        self.calls.append(("cancel", n))
        return "🗑 Отменил: x"

    async def tick(self):
        return [(FAMILY, "✅ Готово: x")]


def make(tg=None):
    mod = load()
    tg = tg or FakeTelegram()
    api = mod.TgApi("TOKEN", base="https://tg.test", transport=httpx.MockTransport(tg.handler))
    asked = []

    async def answer(q, user):
        asked.append((q, user))
        return "🐕 ответ"

    dl = FakeDownloads()
    bot = mod.TelegramBot(api, dl, answer=answer,
                          state_path=os.path.join(tempfile.mkdtemp(), "tg.json"))
    bot.bot_username = "bobik_borovskoy_bot"
    return mod, bot, tg, dl, asked


def msg(text, chat=FAMILY, chat_type="supergroup", uid=SON, **extra):
    m = {"message_id": 5, "chat": {"id": chat, "type": chat_type},
         "from": {"id": uid, "first_name": "Ваня"}, "text": text}
    m.update(extra)
    return {"update_id": 10, "message": m}


# ── обращение ─────────────────────────────────────────────────────────────────

def test_addressed_text_variants():
    mod = load()
    cs = ["@бобик", "бобик,"]
    g = {"chat": {"type": "supergroup"}}
    assert mod.addressed_text(dict(g, text="@Бобик скачай x"), "bobik_borovskoy_bot", cs) == "скачай x"
    assert mod.addressed_text(dict(g, text="бобик, закачки"), "bobik_borovskoy_bot", cs) == "закачки"
    assert mod.addressed_text(dict(g, text="@bobik_borovskoy_bot привет"), "bobik_borovskoy_bot", cs) == "привет"
    assert mod.addressed_text(dict(g, text="ответ", reply_to_message={"from": {"username": "bobik_borovskoy_bot"}}),
                              "bobik_borovskoy_bot", cs) == "ответ"
    assert mod.addressed_text(dict(g, text="бобик молодец"), "bobik_borovskoy_bot", cs) is None
    assert mod.addressed_text({"chat": {"type": "private"}, "text": "привет"}, "bobik_borovskoy_bot", cs) == "привет"


def test_route():
    mod = load()
    assert mod.route("скачай magnet:?xt=urn:btih:A") == ("download", "magnet:?xt=urn:btih:A")
    assert mod.route("Закачки") == ("list", None)
    assert mod.route("отмени 2") == ("cancel", 2)
    assert mod.route("какая погода?") == ("ask", "какая погода?")


def test_parse_users():
    mod = load()
    assert mod.parse_users("1:admin 2:ivan bad 3:") == {1: "admin", 2: "ivan"}


# ── поведение ─────────────────────────────────────────────────────────────────

def test_unaddressed_group_message_is_ignored_silently():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("мам, купи хлеба")))
    assert tg.texts() == [] and asked == [] and dl.calls == []


def test_download_command_from_son_in_group():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик скачай magnet:?xt=urn:btih:ABC")))
    assert dl.calls == [("link", "magnet:?xt=urn:btih:ABC", FAMILY, "ivan")]
    assert tg.texts() == [(FAMILY, "⏬ Принял: x")]


def test_bad_link_explained():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик скачай http://192.168.0.50/x")))
    assert dl.calls == []
    assert tg.texts()[0][1].startswith("❌")


def test_question_goes_to_gigachat_path_with_login():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("бобик, столица Франции?")))
    assert asked == [("столица Франции?", "ivan")]
    assert ("sendChatAction", {"chat_id": FAMILY, "action": "typing"}) in tg.sent
    assert tg.texts() == [(FAMILY, "🐕 ответ")]


def test_list_and_cancel():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик закачки")))
    asyncio.run(bot.handle_update(msg("@бобик отмени 3")))
    assert ("cancel", 3) in dl.calls
    assert [t for _, t in tg.texts()] == ["Закачек нет.", "🗑 Отменил: x"]


def test_torrent_document_with_caption():
    mod, bot, tg, dl, asked = make()
    upd = msg(None, caption="@бобик скачай",
              document={"file_id": "F1", "file_name": "distro.torrent", "file_size": 20})
    upd["message"].pop("text")
    asyncio.run(bot.handle_update(upd))
    assert dl.calls and dl.calls[0][0] == "torrent" and dl.calls[0][1] == b"d8:announce1:xe"


def test_torrent_over_20mb_refused():
    mod, bot, tg, dl, asked = make()
    upd = msg(None, caption="@бобик скачай",
              document={"file_id": "F1", "file_name": "big.torrent", "file_size": 21 * 1024 * 1024})
    upd["message"].pop("text")
    asyncio.run(bot.handle_update(upd))
    assert dl.calls == []
    assert "20 МБ" in tg.texts()[0][1]


def test_stranger_in_private_gets_one_reply_and_owner_is_told():
    mod, bot, tg, dl, asked = make()
    for _ in range(2):
        asyncio.run(bot.handle_update(msg("/start", chat=STRANGER, chat_type="private", uid=STRANGER)))
    texts = tg.texts()
    assert sum(1 for c, _ in texts if c == STRANGER) == 1
    assert any(c == OWNER and str(STRANGER) in t for c, t in texts)
    assert asked == []


def test_foreign_group_is_left():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.handle_update(msg("@бобик привет", chat=-555)))
    assert ("leaveChat", {"chat_id": -555}) in tg.sent
    assert asked == []


def test_poll_saves_offset_after_processing(tmp_path):
    tg = FakeTelegram(updates=[dict(msg("@бобик закачки"), update_id=41)])
    mod, bot, tg, dl, asked = make(tg)
    asyncio.run(bot.poll_once())
    assert json.load(open(bot.state_path, encoding="utf-8"))["offset"] == 42


def test_retry_after_is_respected():
    mod = load()

    def handler(request):
        return httpx.Response(429, json={"ok": False, "error_code": 429,
                                         "parameters": {"retry_after": 7}})

    api = mod.TgApi("TOKEN", base="https://tg.test", transport=httpx.MockTransport(handler))
    try:
        asyncio.run(api.call("sendMessage", chat_id=1, text="x"))
    except mod.TgError as exc:
        assert exc.retry_after == 7
    else:
        raise AssertionError("ожидался TgError")


def test_download_notifications_are_sent():
    mod, bot, tg, dl, asked = make()
    asyncio.run(bot.downloads_once())
    assert tg.texts() == [(FAMILY, "✅ Готово: x")]


def test_token_never_logged(caplog):
    mod, bot, tg, dl, asked = make()
    with caplog.at_level("DEBUG"):
        asyncio.run(bot.handle_update(msg("@бобик скачай magnet:?xt=urn:btih:ABC")))
    assert "TOKEN" not in caplog.text
    assert "magnet:?xt" not in caplog.text
```

- [ ] **Step 2: убедиться, что падают**

Run: `python -m pytest -q tests/nas_api/test_telegram_bot.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.telegram_bot'`

- [ ] **Step 3: реализация**

`services/nas_jetson_nano-api/app/telegram_bot.py`:
```python
"""Telegram-фронт @бобик: первый срез (закачки + вопросы к GigaChat).

Спецификации: docs/superpowers/specs/2026-09-19-home-downloader-design.md,
docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md.
Jetson напрямую до Telegram не доходит — long polling идёт через SSH SOCKS на VPS
(`TELEGRAM_PROXY=socks5://172.17.0.1:1080`). Обращение — «@бобик …» / «бобик, …»;
всё без обращения в группе отбрасывается без записи в журнал.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re

import httpx

from app import downloads as downloads_mod
from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.telegram")
# httpx на INFO пишет URL запроса, а в URL Bot API — токен: в журнал его не пускаем.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TORRENT_LIMIT = 20 * 1024 * 1024  # предел Bot API getFile — на сам .torrent, не на закачку
HELP = ("🐕 Я Бобик. Пишите «@бобик» и дальше:\n"
        "• скачай <magnet или ссылка> — скачаю домой, в \\\\192.168.0.50\\hdd2tb\\Downloads\n"
        "• .torrent-файл с подписью «@бобик скачай»\n"
        "• закачки — что качается и сколько места\n"
        "• отмени N — отменить закачку N\n"
        "• любой другой вопрос — отвечу через GigaChat")
STRANGER_TEXT = "🐕 Вы не в семейном списке — я отвечаю только своим."


class TgError(Exception):
    def __init__(self, code: int, description: str = "", retry_after: int = 0):
        super().__init__("telegram %s: %s" % (code, description))
        self.code = code
        self.retry_after = retry_after


class TgApi:
    """Bot API через прокси. Токен живёт только в URL запроса и в журнал не попадает."""

    def __init__(self, token: str, proxy=None, base=None, transport=None):
        self._token = token
        self._base = (base or settings.telegram_api).rstrip("/")
        kw = {"timeout": 45}
        if transport is not None:
            kw["transport"] = transport
        elif proxy:
            kw["proxy"] = proxy
        self._client = httpx.AsyncClient(**kw)

    async def call(self, method: str, **params):
        r = await self._client.post("%s/bot%s/%s" % (self._base, self._token, method), json=params)
        try:
            data = r.json()
        except ValueError:
            raise TgError(r.status_code, "не JSON")
        if not data.get("ok"):
            raise TgError(data.get("error_code", r.status_code), data.get("description", ""),
                          (data.get("parameters") or {}).get("retry_after", 0))
        return data["result"]

    async def file_bytes(self, file_id: str, limit: int = TORRENT_LIMIT) -> bytes:
        info = await self.call("getFile", file_id=file_id)
        if int(info.get("file_size") or 0) > limit:
            raise TgError(413, "файл больше предела")
        r = await self._client.get("%s/file/bot%s/%s" % (self._base, self._token, info["file_path"]))
        if len(r.content) > limit:
            raise TgError(413, "файл больше предела")
        return r.content


def parse_users(s: str) -> dict:
    users = {}
    for part in (s or "").split():
        uid, _, login = part.partition(":")
        if uid.lstrip("-").isdigit() and login:
            users[int(uid)] = login
    return users


def addressed_text(msg: dict, bot_username: str, callsigns: list):
    text = (msg.get("text") or msg.get("caption") or "").strip()
    low = text.lower()
    for cs in list(callsigns) + ["@" + bot_username.lower()]:
        if cs and low.startswith(cs.lower()):
            return text[len(cs):].lstrip(" ,:—-\t")
    reply_from = ((msg.get("reply_to_message") or {}).get("from") or {}).get("username", "")
    if reply_from.lower() == bot_username.lower():
        return text
    if (msg.get("chat") or {}).get("type") == "private":
        return text
    return None


def route(text: str):
    low = (text or "").strip().lower()
    if low.startswith("скачай"):
        return "download", text.strip()[len("скачай"):].strip()
    if low.startswith("закачки"):
        return "list", None
    m = re.match(r"отмени\s+(\d+)", low)
    if m:
        return "cancel", int(m.group(1))
    return "ask", text.strip()


class TelegramBot:
    def __init__(self, api: TgApi, downloads, answer=None, state_path=None):
        self.api = api
        self.downloads = downloads
        if answer is None:
            from app.routers import talk_bot
            answer = talk_bot.answer
        self.answer = answer
        self.state_path = state_path or settings.telegram_state_file
        self.users = parse_users(settings.telegram_users)
        self.family = int(settings.telegram_family_chat_id) if settings.telegram_family_chat_id else None
        self.callsigns = [c.strip() for c in settings.telegram_callsigns.split("|") if c.strip()]
        self.bot_username = ""
        self.state = self._load()

    # ── состояние ─────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.state_path)), exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh)
        os.replace(tmp, self.state_path)

    def _owner_chat(self):
        for uid, login in self.users.items():
            if login == settings.telegram_owner_login:
                return uid
        return None

    async def _say(self, chat_id: int, text: str, reply_to=None) -> None:
        params = {"chat_id": chat_id, "text": text}
        if reply_to:
            params["reply_to_message_id"] = reply_to
        await self.api.call("sendMessage", **params)

    # ── обработка ─────────────────────────────────────────────────────────────
    async def handle_update(self, upd: dict) -> None:
        mcm = upd.get("my_chat_member")
        if mcm:
            chat = mcm.get("chat") or {}
            if chat.get("type") in ("group", "supergroup") and chat.get("id") != self.family:
                await self.api.call("leaveChat", chat_id=chat["id"])
            return
        msg = upd.get("message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat.get("type") in ("group", "supergroup") and chat_id != self.family:
            await self.api.call("leaveChat", chat_id=chat_id)
            return
        text = addressed_text(msg, self.bot_username, self.callsigns)
        if text is None:
            return  # не нам: не обрабатываем, не храним, не пишем в журнал
        uid = (msg.get("from") or {}).get("id")
        login = self.users.get(uid)
        if login is None:
            await self._stranger(msg, chat)
            return
        doc = msg.get("document")
        kind, arg = route(text)
        log.info("telegram command", extra={"fields": {
            "user": login, "chat_type": chat.get("type"),
            "kind": "torrent" if doc else kind}})
        mid = msg.get("message_id")
        if text in ("", "/start") or text.startswith("/start@") or text == "/help":
            await self._say(chat_id, HELP)
            return
        if doc and (doc.get("file_name") or "").lower().endswith(".torrent"):
            if kind != "download" and chat.get("type") != "private":
                return
            if int(doc.get("file_size") or 0) > TORRENT_LIMIT:
                await self._say(chat_id, "❌ .torrent-файл больше 20 МБ — пришлите magnet-ссылку.", mid)
                return
            data = await self.api.file_bytes(doc["file_id"])
            await self._say(chat_id, await self.downloads.add_torrent(data, chat_id, login), mid)
            return
        if kind == "download":
            try:
                link = downloads_mod.parse_link(arg)
            except downloads_mod.LinkError as exc:
                await self._say(chat_id, "❌ %s" % exc, mid)
                return
            await self._say(chat_id, await self.downloads.add_link(link, chat_id, login), mid)
        elif kind == "list":
            await self._say(chat_id, await self.downloads.list_text(), mid)
        elif kind == "cancel":
            await self._say(chat_id, await self.downloads.cancel(arg), mid)
        else:
            await self.api.call("sendChatAction", chat_id=chat_id, action="typing")
            await self._say(chat_id, await self.answer(arg, login), mid)

    async def _stranger(self, msg: dict, chat: dict) -> None:
        if chat.get("type") != "private":
            return
        uid = (msg.get("from") or {}).get("id")
        seen = self.state.setdefault("strangers", [])
        if uid in seen:
            return
        seen.append(uid)
        self._save()
        await self._say(chat["id"], STRANGER_TEXT)
        owner = self._owner_chat()
        if owner:
            name = (msg.get("from") or {}).get("first_name", "")
            await self._say(owner, "🐕 Боту написал незнакомый аккаунт: %s (user_id %s). "
                                   "Если это семья — добавьте в TELEGRAM_USERS." % (name, uid))

    # ── циклы ─────────────────────────────────────────────────────────────────
    async def poll_once(self) -> None:
        offset = self.state.get("offset", 0)
        updates = await self.api.call("getUpdates", offset=offset, timeout=30,
                                      allowed_updates=["message", "my_chat_member"])
        for upd in updates:
            try:
                await self.handle_update(upd)
            except Exception:
                log.exception("telegram update failed")
            self.state["offset"] = upd["update_id"] + 1
            self._save()

    async def poll_forever(self) -> None:
        backoff = 1
        while True:
            try:
                await self.poll_once()
                backoff = 1
            except TgError as exc:
                await asyncio.sleep(exc.retry_after or backoff)
                backoff = min(backoff * 2, 60)
            except (httpx.HTTPError, OSError) as exc:
                log.warning("telegram unreachable: %s", type(exc).__name__)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def downloads_once(self) -> None:
        for chat_id, text in await self.downloads.tick():
            await self._say(chat_id, text)

    async def downloads_forever(self, interval: int = 30) -> None:
        while True:
            try:
                await self.downloads_once()
            except Exception:
                log.exception("downloads tick failed")
            await asyncio.sleep(interval)


async def run() -> None:
    api = TgApi(settings.telegram_bot_token, proxy=settings.telegram_proxy or None)
    bot = TelegramBot(api, downloads_mod.Downloads())
    while not bot.bot_username:
        try:
            bot.bot_username = (await api.call("getMe"))["username"]
        except (TgError, httpx.HTTPError, OSError):
            await asyncio.sleep(30)
    await asyncio.gather(bot.poll_forever(), bot.downloads_forever())
```

> ⚠️ Журнал httpx на уровне INFO пишет URL каждого запроса — а в URL Bot API стоит токен.
> Поэтому модуль приглушает логгер `httpx` до WARNING (строка после `log = …`); тест
> `test_token_never_logged` это ловит.

- [ ] **Step 4: запуск в `lifespan`**

В `app/main.py`, в `lifespan`, после блока запуска Talk-бота:
```python
    tg_task: asyncio.Task | None = None
    if settings.telegram_bot_enabled and settings.telegram_bot_token:
        from app import telegram_bot
        tg_task = asyncio.create_task(telegram_bot.run())
        log.info("Telegram bot enabled")
```
и после `yield`, рядом с остановкой Talk-бота:
```python
    if tg_task is not None:
        tg_task.cancel()
        try:
            await tg_task
        except asyncio.CancelledError:
            pass
```
В `requirements.txt` строку `httpx>=0.27` заменить на `httpx[socks]>=0.27`.

- [ ] **Step 5: тесты проходят**

Run: `pip install "httpx[socks]>=0.27" && python -m pytest -q tests/nas_api`
Expected: все зелёные (включая `test_api_access.py`: новых HTTP-маршрутов нет).

- [ ] **Step 6: коммит**

```bash
git add services/nas_jetson_nano-api/app/telegram_bot.py services/nas_jetson_nano-api/app/main.py services/nas_jetson_nano-api/requirements.txt tests/nas_api/test_telegram_bot.py
git commit -m "feat(telegram): @бобик front — callsign, whitelist, downloads commands, GigaChat questions via SOCKS" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Контейнер aria2 + AriaNg и хуки

**Files:**
- Create: `services/downloads/Dockerfile`, `services/downloads/aria2.conf`, `services/downloads/entrypoint.sh`, `services/downloads/on_complete.sh`, `services/downloads/on_stop.sh`
- Create: `tests/unit/test_aria2_hooks.py`

**Interfaces:**
- Produces: хук `on_complete.sh GID NUM PATH` и `on_stop.sh GID NUM PATH` (аргументы aria2); переменные для тестов `DL_SSD_INCOMPLETE`, `DL_HDD_INCOMPLETE`, `DL_FINAL`.

- [ ] **Step 1: падающие тесты**

`tests/unit/test_aria2_hooks.py`:
```python
#!/usr/bin/env python3
"""Хуки aria2 качалки: перенос готового на HDD и уборка отменённого.

ЗАЧЕМ. Готовое должно само оказаться в Downloads (иначе сын не найдёт его в шаре), а
отменённые 100 ГБ не должны остаться на HDD рядом с семейным архивом. Хук работает с
путями из аргументов aria2 — ошибка в разборе пути = rm -rf не того каталога, поэтому
границы проверены тестами.
Запуск: python3 tests/unit/test_aria2_hooks.py   (Python 3.6+, без pytest)
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HOOKS = os.path.join(REPO, "services", "downloads")
BASH = shutil.which("bash") or "bash"


def fwd(p):
    return p.replace("\\", "/")


class Hooks(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.ssd = os.path.join(self.t, "ssd", ".incomplete")
        self.hddi = os.path.join(self.t, "hdd", ".incomplete")
        self.final = os.path.join(self.t, "hdd")
        for d in (self.ssd, self.hddi):
            os.makedirs(d)
        # bash (в т.ч. Git Bash на Windows) сравнивает пути по «/» — отдаём прямые слэши
        self.env = dict(os.environ, DL_SSD_INCOMPLETE=fwd(self.ssd),
                        DL_HDD_INCOMPLETE=fwd(self.hddi), DL_FINAL=fwd(self.final))

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def run_hook(self, name, path):
        p = subprocess.run([BASH, os.path.join(HOOKS, name), "gid1", "1", fwd(path)],
                           env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        return p.returncode

    def touch(self, *parts):
        path = os.path.join(*parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("x")
        return path

    def test_single_file_from_ssd_lands_in_final(self):
        f = self.touch(self.ssd, "debian 12 — образ.iso")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(os.path.join(self.final, "debian 12 — образ.iso")))
        self.assertFalse(os.path.exists(f))

    def test_multi_file_torrent_moves_top_directory(self):
        f = self.touch(self.hddi, "Distro", "disc1", "a.bin")
        self.touch(self.hddi, "Distro", "b.bin")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(os.path.join(self.final, "Distro", "disc1", "a.bin")))
        self.assertTrue(os.path.exists(os.path.join(self.final, "Distro", "b.bin")))
        self.assertFalse(os.path.exists(os.path.join(self.hddi, "Distro")))

    def test_name_taken_gets_suffix_without_overwrite(self):
        self.touch(self.final, "a.iso")
        f = self.touch(self.ssd, "a.iso")
        self.assertEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(os.path.join(self.final, "a (2).iso")))
        with open(os.path.join(self.final, "a.iso")) as fh:
            self.assertEqual(fh.read(), "x")

    def test_path_outside_download_roots_is_ignored(self):
        outside = self.touch(self.t, "elsewhere", "keep.txt")
        self.assertEqual(self.run_hook("on_complete.sh", outside), 0)
        self.assertTrue(os.path.exists(outside))

    def test_metadata_without_path_is_ignored(self):
        self.assertEqual(self.run_hook("on_complete.sh", ""), 0)

    def test_final_unavailable_keeps_file_and_fails(self):
        f = self.touch(self.ssd, "a.iso")
        shutil.rmtree(self.final)
        self.assertNotEqual(self.run_hook("on_complete.sh", f), 0)
        self.assertTrue(os.path.exists(f))

    def test_on_stop_removes_partial_top_item(self):
        f = self.touch(self.hddi, "Big", "part.bin")
        self.touch(self.hddi, "Big.aria2")
        self.assertEqual(self.run_hook("on_stop.sh", f), 0)
        self.assertFalse(os.path.exists(os.path.join(self.hddi, "Big")))
        self.assertFalse(os.path.exists(os.path.join(self.hddi, "Big.aria2")))
        self.assertTrue(os.path.isdir(self.hddi))

    def test_on_stop_never_touches_final_or_outside(self):
        kept = self.touch(self.final, "done.iso")
        outside = self.touch(self.t, "other", "x")
        self.assertEqual(self.run_hook("on_stop.sh", kept), 0)
        self.assertEqual(self.run_hook("on_stop.sh", outside), 0)
        self.assertTrue(os.path.exists(kept) and os.path.exists(outside))

    def test_on_stop_rejects_dot_dot(self):
        victim = self.touch(self.t, "victim.txt")
        self.assertEqual(self.run_hook("on_stop.sh", os.path.join(self.hddi, "..", "..", "victim.txt")), 0)
        self.assertTrue(os.path.exists(victim))


if __name__ == "__main__":
    unittest.main(verbosity=1)
```

- [ ] **Step 2: убедиться, что падают**

Run: `python tests/unit/test_aria2_hooks.py`
Expected: FAIL (скриптов нет — `bash: …/on_complete.sh: No such file or directory`, ненулевые коды).

- [ ] **Step 3: хуки**

`services/downloads/on_complete.sh`:
```bash
#!/bin/bash
# aria2 on-download-complete: переносит готовое (файл или верхний каталог многофайлового
# торрента) из .incomplete в Downloads. С SSD — копированием на HDD, с HDD — переименованием.
# Аргументы aria2: GID, число файлов, путь первого файла. Имя занято — суффикс « (N)».
set -u
SSD_INC="${DL_SSD_INCOMPLETE:-/downloads/ssd/.incomplete}"
HDD_INC="${DL_HDD_INCOMPLETE:-/downloads/hdd/.incomplete}"
FINAL="${DL_FINAL:-/downloads/hdd}"
path="${3:-}"
[ -n "$path" ] || exit 0   # метаданные magnet: файла нет

src="" top=""
for root in "$SSD_INC" "$HDD_INC"; do
  case "$path" in
    "$root"/*)
      rel="${path#"$root"/}"
      top="${rel%%/*}"
      src="$root/$top"
      break ;;
  esac
done
case "$top" in ""|"."|"..") exit 0 ;; esac
[ -e "$src" ] || exit 0
[ -d "$FINAL" ] || { echo "on_complete: нет $FINAL — оставляю $src" >&2; exit 1; }

dst="$FINAL/$top"
n=2
while [ -e "$dst" ]; do
  if [ -d "$src" ]; then
    dst="$FINAL/$top ($n)"
  else
    base="${top%.*}"; ext=".${top##*.}"
    [ "$base" = "$top" ] && ext=""
    dst="$FINAL/$base ($n)$ext"
  fi
  n=$((n + 1))
done
mv -- "$src" "$dst" || { echo "on_complete: не перенёс $src" >&2; exit 1; }
```

`services/downloads/on_stop.sh`:
```bash
#!/bin/bash
# aria2 on-download-stop (отмена или ошибка; готовое обрабатывает on_complete.sh):
# удаляет недокачанное из .incomplete, чтобы отменённые 100 ГБ не остались на HDD.
# Трогает ТОЛЬКО верхний элемент внутри .incomplete; «..» и пути вне корней — игнор.
set -u
SSD_INC="${DL_SSD_INCOMPLETE:-/downloads/ssd/.incomplete}"
HDD_INC="${DL_HDD_INCOMPLETE:-/downloads/hdd/.incomplete}"
path="${3:-}"
[ -n "$path" ] || exit 0
case "$path" in *"/../"*|*"/.."|"../"*) exit 0 ;; esac

for root in "$SSD_INC" "$HDD_INC"; do
  case "$path" in
    "$root"/*)
      rel="${path#"$root"/}"
      top="${rel%%/*}"
      case "$top" in ""|"."|"..") exit 0 ;; esac
      rm -rf -- "$root/$top" "$root/$top.aria2"
      exit 0 ;;
  esac
done
exit 0
```

- [ ] **Step 4: образ**

`services/downloads/aria2.conf`:
```ini
# Домашняя качалка (спецификация 2026-09-19). rpc-secret дописывает entrypoint в копию
# конфига — в argv процесса секрета нет.
dir=/downloads/ssd/.incomplete
input-file=/config/aria2.session
save-session=/config/aria2.session
save-session-interval=60
enable-rpc=true
rpc-listen-all=true
rpc-listen-port=6800
rpc-allow-origin-all=true
max-concurrent-downloads=2
continue=true
file-allocation=falloc
disk-cache=16M
seed-time=0
max-overall-upload-limit=1M
bt-save-metadata=false
pause-metadata=true
follow-torrent=true
bt-enable-lpd=false
enable-dht=true
on-download-complete=/usr/local/bin/on_complete.sh
on-download-stop=/usr/local/bin/on_stop.sh
```

`services/downloads/entrypoint.sh`:
```sh
#!/bin/sh
# Запуск aria2 + страница AriaNg. Секрет — из окружения в копию конфига (права 600),
# не в аргументы процесса: argv контейнера виден в `ps` хоста.
set -eu
: "${ARIA2_RPC_SECRET:?нужен ARIA2_RPC_SECRET}"
mkdir -p /downloads/ssd/.incomplete /downloads/hdd/.incomplete /config
touch /config/aria2.session
umask 077
cp /etc/aria2/aria2.conf /tmp/aria2.conf
printf 'rpc-secret=%s\n' "$ARIA2_RPC_SECRET" >> /tmp/aria2.conf
httpd -p 6880 -h /www
exec aria2c --conf-path=/tmp/aria2.conf
```

`services/downloads/Dockerfile`:
```dockerfile
# Домашняя качалка: aria2 (торренты + HTTP) и AriaNg (запасной веб-интерфейс в LAN).
# Собирается на Jetson (arm64). Версия AriaNg и SHA-256 архива закреплены.
FROM alpine:3.20
ARG ARIANG_VERSION=1.3.10
ARG ARIANG_SHA256=__FILL_AT_TASK_4__
RUN apk add --no-cache aria2 bash busybox-extras \
 && wget -q -O /tmp/ariang.zip "https://github.com/mayswind/AriaNg/releases/download/${ARIANG_VERSION}/AriaNg-${ARIANG_VERSION}-AllInOne.zip" \
 && echo "${ARIANG_SHA256}  /tmp/ariang.zip" | sha256sum -c - \
 && mkdir -p /www && unzip -q /tmp/ariang.zip -d /www && rm /tmp/ariang.zip \
 && adduser -D -u 1000 dl
COPY aria2.conf /etc/aria2/aria2.conf
COPY entrypoint.sh on_complete.sh on_stop.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/on_complete.sh /usr/local/bin/on_stop.sh
USER 1000
EXPOSE 6800 6880
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```
`ARIANG_SHA256` — **вычислить в этой задаче**: скачать `https://github.com/mayswind/AriaNg/releases/download/1.3.10/AriaNg-1.3.10-AllInOne.zip` и взять `sha256sum`; если версии 1.3.10 нет — взять последнюю из `https://api.github.com/repos/mayswind/AriaNg/releases/latest` и заменить обе строки. В отчёте указать версию и хэш. `httpd` в Alpine — из `busybox-extras`.

- [ ] **Step 5: тесты проходят**

Run: `python tests/unit/test_aria2_hooks.py && bash -n services/downloads/on_complete.sh && bash -n services/downloads/on_stop.sh && sh -n services/downloads/entrypoint.sh`
Expected: `OK`, синтаксис без вывода.

- [ ] **Step 6: коммит**

```bash
git add services/downloads tests/unit/test_aria2_hooks.py
git commit -m "feat(downloads): aria2 + AriaNg image, move-to-HDD and cleanup hooks" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Инфраструктура — compose, SOCKS, лимит скорости, ключи `.env`

**Files:**
- Create: `docker/compose/docker-compose.downloads.yml`
- Modify: `docker/compose/docker-compose.nas_jetson_nano-api.yml` (environment и volumes)
- Create: `systemd/nas_jetson_nano-tg-socks.service`
- Create: `scripts/downloads/aria2_speed.sh`, `systemd/nas_jetson_nano-dl-speed-day.service`, `systemd/nas_jetson_nano-dl-speed-day.timer`, `systemd/nas_jetson_nano-dl-speed-night.service`, `systemd/nas_jetson_nano-dl-speed-night.timer`
- Modify: `config/.env.example` (в конец)
- Create: `tests/unit/test_downloader_infra.py`

**Interfaces:**
- Consumes: образ из `services/downloads` (Task 4); настройки `TELEGRAM_*`, `ARIA2_RPC_SECRET`, `DL_*` (Task 2).

- [ ] **Step 1: падающие тесты**

`tests/unit/test_downloader_infra.py`:
```python
#!/usr/bin/env python3
"""Инфраструктура качалки и Telegram-бота — статические гарантии.

ЗАЧЕМ. SOCKS на 0.0.0.0 открыл бы прокси всей LAN; секрет aria2 в argv виден в `ps`
хоста; контейнер без предела памяти на Jetson 4 ГБ может выдавить Immich; каталоги,
смонтированные в API на запись, дали бы боту удалять файлы семьи.
Запуск: python3 tests/unit/test_downloader_infra.py   (Python 3.6+, без pytest)
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def read(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class Infra(unittest.TestCase):
    def test_downloads_compose_limits_and_mounts(self):
        t = read("docker/compose/docker-compose.downloads.yml")
        self.assertIn("mem_limit: 192m", t)
        self.assertIn("/mnt/storage/downloads:/downloads/ssd", t)
        self.assertIn("/mnt/hdd2tb/Downloads:/downloads/hdd", t)
        self.assertIn("ARIA2_RPC_SECRET: ${ARIA2_RPC_SECRET:?", t)
        self.assertIn('"6800:6800"', t)
        self.assertIn('"6880:6880"', t)

    def test_api_sees_download_dirs_read_only(self):
        t = read("docker/compose/docker-compose.nas_jetson_nano-api.yml")
        self.assertIn("/mnt/storage/downloads:/dl/ssd:ro", t)
        self.assertIn("/mnt/hdd2tb/Downloads:/dl/hdd:ro", t)
        for key in ("TELEGRAM_BOT_ENABLED", "TELEGRAM_BOT_TOKEN", "TELEGRAM_USERS",
                    "TELEGRAM_FAMILY_CHAT_ID", "TELEGRAM_PROXY", "ARIA2_RPC_SECRET"):
            self.assertIn(key + ":", t)
        self.assertIn("socks5://172.17.0.1:1080", t)

    def test_socks_unit_binds_docker0_only(self):
        t = read("systemd/nas_jetson_nano-tg-socks.service")
        self.assertIn("-D 172.17.0.1:1080", t)
        self.assertNotRegex(t, r"-D\s+(0\.0\.0\.0:)?1080\b")
        for opt in ("ExitOnForwardFailure=yes", "BatchMode=yes", "ServerAliveInterval="):
            self.assertIn(opt, t)
        self.assertIn("Restart=always", t)

    def test_entrypoint_keeps_secret_out_of_argv(self):
        t = read("services/downloads/entrypoint.sh")
        self.assertNotIn("--rpc-secret", t)
        self.assertIn("rpc-secret=", t)

    def test_env_example_has_empty_keys(self):
        t = read("config/.env.example")
        for key in ("TELEGRAM_BOT_ENABLED=", "TELEGRAM_USERS=", "TELEGRAM_FAMILY_CHAT_ID=",
                    "ARIA2_RPC_SECRET=", "DL_SSD_MIN_FREE_GB=", "DL_HDD_MIN_FREE_GB=",
                    "DL_SSD_MAX_GB=", "DL_DAY_LIMIT="):
            self.assertIn(key, t)
        self.assertRegex(t, r"(?m)^ARIA2_RPC_SECRET=\s*$")
        self.assertRegex(t, r"(?m)^TELEGRAM_USERS=\s*$")

    def test_speed_timers(self):
        self.assertIn("OnCalendar=*-*-* 08:00:00", read("systemd/nas_jetson_nano-dl-speed-day.timer"))
        self.assertIn("OnCalendar=*-*-* 23:00:00", read("systemd/nas_jetson_nano-dl-speed-night.timer"))
        self.assertIn("aria2_speed.sh day", read("systemd/nas_jetson_nano-dl-speed-day.service"))
        self.assertIn("aria2_speed.sh night", read("systemd/nas_jetson_nano-dl-speed-night.service"))

    def test_speed_script_sends_secret_on_stdin_only(self):
        tmp = tempfile.mkdtemp()
        try:
            bindir = os.path.join(tmp, "bin")
            os.makedirs(bindir)
            stub = os.path.join(bindir, "curl")
            with io.open(stub, "w", encoding="utf-8", newline="\n") as fh:
                fh.write('#!/usr/bin/env bash\nprintf "%s\\n" "$*" > "$STUB_ARGS"\ncat > "$STUB_BODY"\n'
                         'printf \'{"result":"OK"}\'\n')
            os.chmod(stub, 0o755)
            env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""),
                       ARIA2_RPC_SECRET="S3CR3T", DL_DAY_LIMIT="6M",
                       STUB_ARGS=os.path.join(tmp, "args"), STUB_BODY=os.path.join(tmp, "body"))
            bash = shutil.which("bash") or "bash"
            for mode, limit in (("day", '"6M"'), ("night", '"0"')):
                p = subprocess.run([bash, os.path.join(REPO, "scripts", "downloads", "aria2_speed.sh"), mode],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                args = io.open(env["STUB_ARGS"], encoding="utf-8").read()
                body = io.open(env["STUB_BODY"], encoding="utf-8").read()
                self.assertNotIn("S3CR3T", args)
                self.assertIn('"token:S3CR3T"', body)
                self.assertIn('"max-overall-download-limit":' + limit, body)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=1)
```

- [ ] **Step 2: убедиться, что падают**

Run: `python tests/unit/test_downloader_infra.py`
Expected: FAIL (`FileNotFoundError` для compose/unit/скрипта).

- [ ] **Step 3: compose качалки**

`docker/compose/docker-compose.downloads.yml`:
```yaml
# Домашняя качалка (спецификация docs/superpowers/specs/2026-09-19-home-downloader-design.md).
# RPC 6800 и AriaNg 6880 — в LAN (как остальные сервисы), доступ по ARIA2_RPC_SECRET.
name: homecloud-downloads
services:
  downloads:
    build:
      context: ../../services/downloads
    container_name: homecloud_downloads
    restart: always
    mem_limit: 192m
    ports:
      - "6800:6800"
      - "6880:6880"
    volumes:
      - /mnt/storage/downloads:/downloads/ssd
      - /mnt/hdd2tb/Downloads:/downloads/hdd
      - /mnt/storage/downloads/.config:/config
    environment:
      ARIA2_RPC_SECRET: ${ARIA2_RPC_SECRET:?ARIA2_RPC_SECRET не задан в config/.env}
```

- [ ] **Step 4: compose NAS API**

В `docker/compose/docker-compose.nas_jetson_nano-api.yml` в `volumes:` сервиса добавить:
```yaml
      # Качалка: только для statvfs (свободное место), на запись боту не нужно
      - /mnt/storage/downloads:/dl/ssd:ro
      - /mnt/hdd2tb/Downloads:/dl/hdd:ro
```
в `environment:` добавить:
```yaml
      # Telegram-бот, первый срез (качалка + вопросы @бобик)
      TELEGRAM_BOT_ENABLED: ${TELEGRAM_BOT_ENABLED:-false}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-}
      TELEGRAM_USERS: ${TELEGRAM_USERS:-}
      TELEGRAM_FAMILY_CHAT_ID: ${TELEGRAM_FAMILY_CHAT_ID:-}
      TELEGRAM_PROXY: ${TELEGRAM_PROXY:-socks5://172.17.0.1:1080}
      ARIA2_RPC_SECRET: ${ARIA2_RPC_SECRET:-}
      DL_SSD_MIN_FREE_GB: ${DL_SSD_MIN_FREE_GB:-40}
      DL_HDD_MIN_FREE_GB: ${DL_HDD_MIN_FREE_GB:-50}
      DL_SSD_MAX_GB: ${DL_SSD_MAX_GB:-20}
```

- [ ] **Step 5: SOCKS-юнит**

`systemd/nas_jetson_nano-tg-socks.service`:
```ini
[Unit]
Description=NAS_Jetson_Nano — SOCKS к Telegram через VPS (Jetson напрямую Telegram не видит)
# Слушает только docker0 (172.17.0.1): контейнер NAS API видит хост по этому адресу,
# в LAN прокси не открыт. Рабочий обратный туннель (nasa-tunnel) не трогается.
After=network-online.target docker.service
Wants=network-online.target

[Service]
User=admin
Environment=VPS_HOST=95.163.176.103
EnvironmentFile=-/opt/nasa/config/.env
ExecStart=/usr/bin/ssh -N -D 172.17.0.1:1080 -o ExitOnForwardFailure=yes -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -i /home/admin/.ssh/id_ed25519 root@${VPS_HOST}
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 6: лимит скорости**

`scripts/downloads/aria2_speed.sh`:
```bash
#!/usr/bin/env bash
# Дневной лимит скорости качалки: day — DL_DAY_LIMIT (по умолчанию 6M ≈ 48 Мбит/с,
# половина домашнего канала), night — без лимита. Секрет — в теле запроса через stdin,
# не в аргументах curl (argv виден в `ps`).
set -euo pipefail
mode="${1:?использование: aria2_speed.sh day|night}"

if [ -z "${ARIA2_RPC_SECRET:-}" ]; then
  _nas_lay="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/layout.sh"
  [[ -r "$_nas_lay" ]] || _nas_lay=/usr/local/lib/nas_jetson_nano/layout.sh
  # shellcheck source=/dev/null
  source "$_nas_lay"
  ARIA2_RPC_SECRET="$(grep '^ARIA2_RPC_SECRET=' "$NAS_ENV_FILE" | cut -d= -f2- | tr -d '"')"
  DL_DAY_LIMIT="${DL_DAY_LIMIT:-$(grep '^DL_DAY_LIMIT=' "$NAS_ENV_FILE" | cut -d= -f2- | tr -d '"' || true)}"
fi

case "$mode" in
  day) limit="${DL_DAY_LIMIT:-6M}" ;;
  night) limit="0" ;;
  *) echo "режим: day или night" >&2; exit 2 ;;
esac

printf '{"jsonrpc":"2.0","id":"speed","method":"aria2.changeGlobalOption","params":["token:%s",{"max-overall-download-limit":"%s"}]}' \
  "$ARIA2_RPC_SECRET" "$limit" \
  | curl -s -m 10 -H 'Content-Type: application/json' -d @- http://127.0.0.1:6800/jsonrpc
echo
```

`systemd/nas_jetson_nano-dl-speed-day.service`:
```ini
[Unit]
Description=NAS_Jetson_Nano — дневной лимит скорости качалки

[Service]
Type=oneshot
User=admin
ExecStart=/bin/bash /home/admin/nasa/scripts/downloads/aria2_speed.sh day
```
`systemd/nas_jetson_nano-dl-speed-day.timer`:
```ini
[Unit]
Description=Дневной лимит скорости качалки в 08:00

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true
Unit=nas_jetson_nano-dl-speed-day.service

[Install]
WantedBy=timers.target
```
`systemd/nas_jetson_nano-dl-speed-night.service`:
```ini
[Unit]
Description=NAS_Jetson_Nano — ночью качалка без лимита

[Service]
Type=oneshot
User=admin
ExecStart=/bin/bash /home/admin/nasa/scripts/downloads/aria2_speed.sh night
```
`systemd/nas_jetson_nano-dl-speed-night.timer`:
```ini
[Unit]
Description=Снять лимит скорости качалки в 23:00

[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=true
Unit=nas_jetson_nano-dl-speed-night.service

[Install]
WantedBy=timers.target
```

- [ ] **Step 7: ключи `.env`**

В конец `config/.env.example`:
```bash

# ── Telegram-бот @бобик, первый срез: качалка + вопросы (спецификация 2026-09-19) ──
TELEGRAM_BOT_ENABLED=false
TELEGRAM_BOT_TOKEN=
# user_id:логин через пробел (значения — docs/local/IDENTIFIERS.md, вне git)
TELEGRAM_USERS=
TELEGRAM_FAMILY_CHAT_ID=
TELEGRAM_PROXY=socks5://172.17.0.1:1080
# ── Качалка aria2 ──
ARIA2_RPC_SECRET=
DL_SSD_MIN_FREE_GB=40
DL_HDD_MIN_FREE_GB=50
DL_SSD_MAX_GB=20
DL_DAY_LIMIT=6M
```

- [ ] **Step 8: тесты и ворота**

Run: `python tests/unit/test_downloader_infra.py && bash -n scripts/downloads/aria2_speed.sh && python tests/unit/test_container_hardening.py`
Expected: `OK`.

- [ ] **Step 9: коммит**

```bash
git add docker/compose/docker-compose.downloads.yml docker/compose/docker-compose.nas_jetson_nano-api.yml systemd/nas_jetson_nano-tg-socks.service systemd/nas_jetson_nano-dl-speed-*.service systemd/nas_jetson_nano-dl-speed-*.timer scripts/downloads/aria2_speed.sh config/.env.example tests/unit/test_downloader_infra.py
git commit -m "feat(downloads): compose, SOCKS unit on docker0, day/night speed timers, env keys" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Runbook выката

**Files:**
- Create: `docs/plans/DEPLOY_DOWNLOADER_2026-09.md`

- [ ] **Step 1: runbook**

`docs/plans/DEPLOY_DOWNLOADER_2026-09.md`:
````markdown
# Выкат качалки и Telegram-бота / Downloader and Telegram bot rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; расхождение — стоп.
> Спецификация: `docs/superpowers/specs/2026-09-19-home-downloader-design.md`. EN summary — в конце.

**Простой:** NAS API ~15 с (пересборка). Nextcloud, Immich, Samba не трогаются. На VPS — только SSH-сессия SOCKS.

## 1. Правило №13 — ДО
Как в `DEPLOY_STAGE_A_2026-09.md` §1: StartedAt `amnezia-*`, число пиров, внешние порты — записать.

## 2. Код и тесты на устройстве
```bash
cd ~/nasa && git pull --ff-only && git rev-parse --short HEAD
for t in tests/unit/test_aria2_hooks.py tests/unit/test_downloader_infra.py; do python3 "$t" >/dev/null 2>&1 && echo "ok $t" || echo "FAIL $t"; done
```

## 3. Секреты и ключи `.env` (значения не печатать)
- `ARIA2_RPC_SECRET` — сгенерировать (`openssl rand -hex 24`), записать в `config/.env` и в Windows Credential Manager `nas-aria2-rpc-secret`.
- `TELEGRAM_USERS`, `TELEGRAM_FAMILY_CHAT_ID` — из `docs/local/IDENTIFIERS.md`; `TELEGRAM_BOT_ENABLED=true`. Токен уже в `.env`.
- Проверка кавычек: `python3 scripts/quality/check_env_syntax.py config/.env` (правило №8).

## 4. Каталоги
```bash
sudo -S mkdir -p /mnt/storage/downloads/.incomplete /mnt/storage/downloads/.config /mnt/hdd2tb/Downloads/.incomplete
sudo -S chown -R 1000:1000 /mnt/storage/downloads
ls -ld /mnt/hdd2tb/Downloads   # NTFS: права задаёт ntfs-3g; запись проверяется в §6
```

## 5. SOCKS к VPS
```bash
sudo -S cp systemd/nas_jetson_nano-tg-socks.service /etc/systemd/system/ && sudo -S systemctl daemon-reload
sudo -S systemctl enable --now nas_jetson_nano-tg-socks.service
ss -tlnH | grep 1080                                   # только 172.17.0.1:1080
curl -s -o /dev/null -w "tg via socks: %{http_code}\n" --socks5-hostname 172.17.0.1:1080 https://api.telegram.org/   # 302
```
Если юнит в рестартах (ssh не смог занять `172.17.0.1:1080` — `ExitOnForwardFailure`) — стоп, разбор по `journalctl -u nas_jetson_nano-tg-socks`.

## 6. Контейнер качалки
```bash
docker compose -f docker/compose/docker-compose.downloads.yml --env-file config/.env up -d --build
docker exec homecloud_downloads sh -c 'touch /downloads/hdd/.w && rm /downloads/hdd/.w && echo hdd-writable'
docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" homecloud_downloads
sudo -S cp systemd/nas_jetson_nano-dl-speed-* /etc/systemd/system/ && sudo -S systemctl daemon-reload
sudo -S systemctl enable --now nas_jetson_nano-dl-speed-day.timer nas_jetson_nano-dl-speed-night.timer
```

## 7. Режим приватности (владелец)
@BotFather → `/setprivacy` → @bobik_borovskoy_bot → **Disable**. Затем убрать бота из группы «Боровские» и добавить снова.
Проверка: `getMe` → `can_read_all_group_messages: true`.

## 8. NAS API
```bash
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
docker logs --since 2m homecloud_nasa_api 2>&1 | grep -i telegram     # "Telegram bot enabled", без ошибок
```

## 9. Проверка в группе «Боровские»
1. «@бобик привет» → ответ GigaChat. «мам, привет» (без обращения) → тишина.
2. «@бобик скачай <magnet небольшого легального образа Linux>» → «⏬ Принял…» → «⏬ Качаю: … на SSD» → «✅ Готово».
3. «@бобик скачай https://…/файл» (HTTP) → то же. «@бобик закачки» → список и свободное место.
4. Файлы видны с Windows: `\\192.168.0.50\hdd2tb\Downloads`.
5. `docker ps` — 14 контейнеров, здоровы; `free -m` — доступно ≥ 1 ГБ.

## 10. Правило №13 — ПОСЛЕ; откат
| Что | Команда |
|---|---|
| бот | `TELEGRAM_BOT_ENABLED=false` в `.env` → `up -d` API (не `restart`: `.env` перечитывается только при пересоздании) |
| качалка | `docker compose -f docker/compose/docker-compose.downloads.yml down` |
| SOCKS | `sudo systemctl disable --now nas_jetson_nano-tg-socks.service` |
| приватность | @BotFather `/setprivacy` → Enable, перезайти бота в группу |

## EN summary
Owner-triggered rollout. Record the VPN baseline, pull and run the on-device tests, add the aria2 secret and
the Telegram whitelist to the device `.env`, create the download directories, start the SOCKS unit bound to
docker0 and check Telegram through it, build and start the aria2 container and the day/night speed timers.
The owner turns the bot's group privacy off and re-adds it to the family group. Rebuild the NAS API, then test
a question, a magnet link, an HTTP link and the list in the group, and confirm the files appear in the Samba
share. Compare the VPN state after. Rollback steps are listed per component.
````

- [ ] **Step 2: коммит**

```bash
git add docs/plans/DEPLOY_DOWNLOADER_2026-09.md
git commit -m "docs(downloads): rollout runbook (SOCKS, aria2, privacy mode, NAS API, checks)" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review (выполнено автором плана)

- Спецификация: §2 (где/чем/интерфейс/обращение/приватность/кому/транспорт/порядок/размер) → Task 2–5; §4 команды → Task 3; §5 компоненты → Task 2–5 (`on_start.sh` заменён стражем в модуле и `on_stop.sh` — редакция 5); §6 конфигурация → Task 2 Step 1, Task 5 Step 7; §7 безопасность → Task 2 (`parse_link`), Task 3 (белый список, чужие группы, журнал), Task 5 (SOCKS на docker0, секрет не в argv, ro-монтирование); §8 тесты → все Task; §9 выкат → Task 6.
- Известные ограничения (записать в runbook при необходимости): имя хоста, резолвящееся во внутренний IP, `parse_link` не ловит (проверяется только литерал) — aria2 сам ходит в сеть; обходится только осознанно. Оповещение владельца о долгой недоступности SOCKS — не в этом срезе.
- Найдено самопроверкой и исправлено в тексте: утечка токена через журнал httpx (приглушён логгер, есть тест); пути с `\` в тестах хуков на Windows (`fwd()`); разделитель позывных «|», потому что запятая — часть позывного «бобик,».
- Имена сверены между задачами: `answer`/`gate_reply`/`ask`; `Downloads.add_link/add_torrent/list_text/cancel/tick`; `parse_link`/`LinkError`; `TgApi.call/file_bytes`; `TelegramBot.handle_update/poll_once/downloads_once`; настройки `telegram_*`, `aria2_*`, `dl_*`.
````
