# NAS_Jetson_Nano — Talk AI Roadmap

> План развития: семейный ИИ-ассистент внутри Nextcloud Talk.
> Живёт в `docs/plans/`. Обновляется по мере реализации.

---

## Идея

Пишешь в семейный чат «Семья» обычным языком — бот отвечает:

- «сколько места на диске?»
- «сколько фото загрузилось за неделю?»
- «перезапусти immich»
- «почему тормозит?» (свободный вопрос)

Позже — то же самое **голосом** (голосовые сообщения / звонок).

**Ключевое:** это не новый компонент с нуля, а склейка трёх уже работающих кубиков проекта. Не хватает только «мозга», связывающего вход → разбор намерения → ответ.

---

## Существующая база (что уже есть)

| Кубик | Порт | Что умеет | Статус |
|---|---|---|---|
| **Nextcloud Talk** | 8080 (spreed) | Семейный чат/звонки, комната «Семья» (токен `37pcobmf`, 5 участников) | ✅ интегрирован |
| **LLM Gateway** | 8090 | FastAPI → DeepSeek, privacy-контур: redaction email/телефонов/секретов, mock без ключа, raw-mode запрещён | ✅ Stage 1 |
| **nas_jetson_nano-api** | 8099 | JWT-оркестратор: `/v1/talk/notify`, `/v1/users/{u}/notify`, метрики, фото (Immich), сторедж, действия (restart, backup) | ✅ v0.6.0 |

---

## Архитектура потока

```
Сообщение в комнате «Семья»
      │  (Nextcloud Talk Bot API: webhook + shared secret, HMAC-подпись)
      ▼
nas_jetson_nano-api  POST /v1/talk/bot/webhook          ← новый роутер talk_bot.py
      │
      ├─ намерение = команда/данные  →  API сам обрабатывает локально
      │                                  (метрики, фото, restart, backup) — в облако НЕ уходит
      │
      └─ намерение = свободный вопрос →  LLM Gateway /v1/chat (redaction) → DeepSeek
      ▼
Ответ обратно в комнату (Talk Bot API: reply)
```

---

## Фазы

| Фаза | Что | Компоненты | Сложность |
|---|---|---|---|
| **A. Текстовый бот (MVP)** ✅ работает | Фоновый опрос комнаты (polling, admin-OCS), команды `ping` / `статус` / `диск` / `фото` | `app/routers/talk_bot.py`, `TALK_BOT_ENABLED` | низкая |
| **B. Умные команды** | NL → действия API: статус, диск, фото, `restart X`, backup — с whitelist и подтверждением опасных операций | связка с существующими `/v1/*` | средняя |
| **C. Свободные вопросы** ✅ **РАБОТАЕТ на устройстве** | Отдельный позывной **`@бобик`** уходит в DeepSeek через redaction-шлюз | `talk_bot.py` + `TALK_BOT_LLM_TRIGGER` | средняя |
| **D. Голос («talk»)** | Ответ на голосовые сообщения: STT + TTS | Piper (TTS, лёгкий) + whisper.cpp / Vosk (STT) | высокая (4 ГБ тесно) |
| **E. Проактивность** | Бот сам пишет в чат: диск заполнен, USB-ошибка, ночной сводный отчёт | сейчас алерты идут в Telegram — свести в Talk | низкая |

---

## Два позывных — граница приватности проходит по слову (Фаза C, 2026-08-10)

Вместо одного бота, который сам решает, что считать локально, а что отправить наружу,
сделано **два явных позывных**. Выбор делает человек, а не эвристика:

| Позывной | Пример | Что происходит |
|---|---|---|
| `нас` (`TALK_BOT_TRIGGER`) | `нас диск` | Считается **дома**. Исходящих запросов нет вообще |
| **`@бобик`** (`TALK_BOT_LLM_TRIGGER`) | `@бобик что приготовить из курицы?` | Уходит наружу через redaction-шлюз |

Ответы визуально различаются: локальные — 📊/💾/📷, ответы Бобика — 🐕. Разные
`actorDisplayName`, поэтому в чате сразу видно, кто ответил.

**Почему так, а не «умный автовыбор»:** любая эвристика однажды ошибётся и отправит
наружу то, что не следовало. Здесь ошибиться может только человек, и он видит,
что делает. Плюс это честно объясняется семье одной фразой: «пишешь `нас` — никуда
не уходит, пишешь `@бобик` — уходит».

**Защита от петли:** ответы бота начинаются с эмодзи, а позывной должен стоять
**первым словом** — поэтому бот не реагирует на собственные сообщения.

**Двойной лимит:** `TALK_BOT_LLM_DAILY_REPLIES` (ответов в сутки на уровне бота) и
`LLM_DAILY_TOKEN_LIMIT` / `LLM_MONTHLY_COST_LIMIT_USD` (на уровне шлюза, fail-closed).

## Приватность (критично для семейного чата)

1. **Команды и данные** (диск, фото, restart) обрабатываются **локально** — в облако DeepSeek не уходят вообще.
2. В DeepSeek уходят **только свободные вопросы** и только **после redaction** (email / телефоны / секреты уже вырезаются в шлюзе — см. `services/llm-gateway/app/main.py`).
3. **Stretch-goal:** локальная маленькая модель (1–3B, quantized, `llama.cpp`) для полностью приватного режима. На 4 ГБ при 13 контейнерах — медленно; держать как эксперимент, не как базу.

---

## Реализм по железу

- Nano 4 ГБ уже нагружен: 13 контейнеров, `immich-microservices` ограничен `mem_limit 512m`.
- Фазы **A–C** ложатся на облачный DeepSeek — по ресурсам почти бесплатно.
- Фаза **D** (голос) — самая тяжёлая по CPU/RAM, ставится последней, после разгрузки памяти и подключения 2 ТБ HDD.

---

## Предлагаемый порядок (ближайшие 3 шага)

1. **Фаза A + E** — быстрый видимый результат: бот в чате + перенос алертов (диск / USB) из Telegram в семейный Talk. Мало кода, сразу польза.
2. **Фаза B** — команды `статус`, `диск`, `фото`, `перезапусти X`. Опирается на готовые `/v1/*`.
3. **Фаза C** — свободные вопросы через redaction-шлюз.

Голос (D) и локальная модель — после.

---

## Целевая структура кода

```
services/nas_jetson_nano-api/app/routers/
└── talk_bot.py          ← ✅ РЕАЛИЗОВАН (фаза A): polling комнаты + разбор команд + ответ
                            (переиспользует system.py / storage.py / photos.py / talk.py)

services/llm-gateway/app/
└── main.py              ← уже готов: /v1/chat с redaction (фаза C)
```

## Как включить фазу A (после деплоя кода)

1. Задеплоить API на Jetson (`git pull` + rebuild/restart контейнера `homecloud_nas_jetson_nano_api`).
2. В `config/.env` выставить `TALK_BOT_ENABLED=true` (опц. `TALK_BOT_TRIGGER=нас`).
3. Перезапустить контейнер API.
4. Проверить: `GET http://192.168.0.50:8099/v1/talk/bot/status` → `running: true`.
5. В семейном чате написать `статус` / `диск` / `фото` / `пинг` — бот ответит.

> Пока `TALK_BOT_ENABLED=false` (по умолчанию) код полностью пассивен — деплой ничего не меняет.

---

## Параллельные треки развития проекта

| Трек | Задача | Источник |
|---|---|---|
| Надёжность | Restic off-site backup после подключения 2 ТБ HDD | CLAUDE.md |
| Доступ | Tailscale вместо проброса через VPS | `TAILSCALE_ACCESS_PLAN.md` |
| Наблюдаемость | `GET /v1/metrics/history` в SQLite → timeseries; Prometheus `/metrics` для Grafana | API roadmap «Будущие идеи v1.x» |
| API-hardening | Rate limiting (slowapi), unit-тесты (pytest + httpx), `/v1/actions/.../update` | API roadmap |
| Мобильное | доработка `API_MOBILE_PLAN.md` | план |
| Публикация | статьи Habr / Hackaday (WIP в `docs/articles/`) | идёт |

---

## English summary

A family AI assistant living inside **Nextcloud Talk**. It is glue between three existing building blocks — Nextcloud Talk (chat), the **LLM Gateway** (`:8090`, DeepSeek behind a redaction boundary), and **nas_jetson_nano-api** (`:8099`, JWT orchestrator that already reads metrics/photos/storage and performs actions).

Flow: a message in the "Семья" room → Talk Bot webhook → `nas_jetson_nano-api /v1/talk/bot/webhook` → intent routing: **commands/data are handled locally** (never leave the box), **open questions go to DeepSeek only after redaction**. Later: voice via Piper (TTS) + whisper.cpp/Vosk (STT).

Phases: **A** text bot MVP → **B** smart commands → **C** free-form questions → **D** voice → **E** proactive alerts (move disk/USB alerts from Telegram into Talk). Phases A–C are cheap on the 4 GB Nano (cloud LLM); phase D and any local model are stretch goals after the 2 TB HDD is attached.
