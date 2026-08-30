# NAS_Jetson_Nano — Talk AI Roadmap

> 🇷🇺 План развития: семейный ИИ-ассистент внутри Nextcloud Talk.
> Живёт в `docs/plans/`. Обновляется по мере реализации.
>
> 🇬🇧 Development plan: a family AI assistant inside Nextcloud Talk.
> Lives in `docs/plans/`. Updated as it is implemented.

---

## Идея / The idea

🇷🇺 Пишешь в семейный чат «Семья» обычным языком — бот отвечает:

- «сколько места на диске?»
- «сколько фото загрузилось за неделю?»
- «перезапусти immich»
- «почему тормозит?» (свободный вопрос)

Позже — то же самое **голосом** (голосовые сообщения / звонок).

🇬🇧 You write in the "Семья" (Family) chat in plain language — the bot replies:

- "how much disk space is left?"
- "how many photos were uploaded this week?"
- "restart immich"
- "why is it slow?" (open-ended question)

Later — the same thing **by voice** (voice messages / a call).

🇷🇺 **Ключевое:** это не новый компонент с нуля, а склейка трёх уже работающих кубиков проекта. Не хватает только «мозга», связывающего вход → разбор намерения → ответ.

🇬🇧 **Key point:** this is not a new component built from scratch, but glue between three already-working building blocks of the project. What is missing is only the "brain" that connects input → intent parsing → reply.

---

## Существующая база (что уже есть) / Existing foundation (what already exists)

| Кубик / Block | Порт / Port | Что умеет / What it does | Статус / Status |
|---|---|---|---|
| **Nextcloud Talk** | 8080 (spreed) | Семейный чат/звонки, комната «Семья» (токен `37pcobmf`, 5 участников) / Family chat/calls, "Семья" room (token `37pcobmf`, 5 participants) | ✅ интегрирован / integrated |
| **LLM Gateway** | 8090 | FastAPI → DeepSeek, privacy-контур: redaction email/телефонов/секретов, mock без ключа, raw-mode запрещён / FastAPI → DeepSeek, privacy layer: redaction of email/phone/secrets, mock without a key, raw mode forbidden | ✅ Stage 1 |
| **nas_jetson_nano-api** | 8099 | JWT-оркестратор: `/v1/talk/notify`, `/v1/users/{u}/notify`, метрики, фото (Immich), сторедж, действия (restart, backup) / JWT orchestrator: `/v1/talk/notify`, `/v1/users/{u}/notify`, metrics, photos (Immich), storage, actions (restart, backup) | ✅ v0.6.0 |

---

## Архитектура потока / Flow architecture

🇷🇺 Схема ниже показывает путь сообщения от чата до ответа.

🇬🇧 The diagram below shows the message path from chat to reply.

```
Сообщение в комнате «Семья» / Message in the "Семья" room
      │  (Nextcloud Talk Bot API: webhook + shared secret, HMAC-подпись / webhook + shared secret, HMAC signature)
      ▼
nas_jetson_nano-api  POST /v1/talk/bot/webhook          ← новый роутер talk_bot.py / new router talk_bot.py
      │
      ├─ намерение = команда/данные  →  API сам обрабатывает локально
      │     (intent = command/data → the API handles it locally itself)
      │                                  (метрики, фото, restart, backup) — в облако НЕ уходит
      │                                  (metrics, photos, restart, backup) — never leaves the cloud
      │
      └─ намерение = свободный вопрос →  LLM Gateway /v1/chat (redaction) → DeepSeek
            (intent = open-ended question → LLM Gateway /v1/chat (redaction) → DeepSeek)
      ▼
Ответ обратно в комнату (Talk Bot API: reply) / Reply back into the room (Talk Bot API: reply)
```

---

## Фазы / Phases

| Фаза / Phase | Что / What | Компоненты / Components | Сложность / Complexity |
|---|---|---|---|
| **A. Текстовый бот (MVP) / Text bot (MVP)** ✅ работает / working | Фоновый опрос комнаты (polling, admin-OCS), команды `ping` / `статус` / `диск` / `фото` / Background room polling (polling, admin-OCS), commands `ping` / `статус` (status) / `диск` (disk) / `фото` (photo) | `app/routers/talk_bot.py`, `TALK_BOT_ENABLED` | низкая / low |
| **B. Умные команды / Smart commands** | NL → действия API: статус, диск, фото, `restart X`, backup — с whitelist и подтверждением опасных операций / NL → API actions: status, disk, photos, `restart X`, backup — with a whitelist and confirmation for dangerous operations | связка с существующими `/v1/*` / wired into existing `/v1/*` | средняя / medium |
| **C. Свободные вопросы / Free-form questions** ✅ **РАБОТАЕТ на устройстве / WORKS on the device** | Отдельный позывной **`@бобик`** уходит в DeepSeek через redaction-шлюз / A separate callsign **`@бобик`** goes to DeepSeek through the redaction gateway | `talk_bot.py` + `TALK_BOT_LLM_TRIGGER` | средняя / medium |
| **D. Голос («talk») / Voice ("talk")** | Ответ на голосовые сообщения: STT + TTS / Replying to voice messages: STT + TTS | Piper (TTS, лёгкий / lightweight) + whisper.cpp / Vosk (STT) | высокая (4 ГБ тесно) / high (tight on 4 GB) |
| **E. Проактивность / Proactivity** | Бот сам пишет в чат: диск заполнен, USB-ошибка, ночной сводный отчёт / The bot writes into the chat on its own: disk full, USB error, nightly summary report | сейчас алерты идут в Telegram — свести в Talk / alerts currently go to Telegram — consolidate into Talk | низкая / low |

---

## Два позывных — граница приватности проходит по слову (Фаза C, 2026-08-10) / Two callsigns — the privacy boundary runs through a word (Phase C, 2026-08-10)

🇷🇺 Вместо одного бота, который сам решает, что считать локально, а что отправить наружу,
сделано **два явных позывных**. Выбор делает человек, а не эвристика:

🇬🇧 Instead of one bot that decides for itself what counts as local and what goes out,
**two explicit callsigns** were made. The choice is made by the person, not by a heuristic:

| Позывной / Callsign | Пример / Example | Что происходит / What happens |
|---|---|---|
| `нас` (`TALK_BOT_TRIGGER`) | `нас диск` | Считается **дома**. Исходящих запросов нет вообще / Computed **at home**. There are no outgoing requests at all |
| **`@бобик`** (`TALK_BOT_LLM_TRIGGER`) | `@бобик что приготовить из курицы?` | Уходит наружу через redaction-шлюз / Goes out through the redaction gateway |

🇷🇺 Ответы визуально различаются: локальные — 📊/💾/📷, ответы Бобика — 🐕. Разные
`actorDisplayName`, поэтому в чате сразу видно, кто ответил.

🇬🇧 Replies look visually different: local ones use 📊/💾/📷, Bobik's replies use 🐕. Different
`actorDisplayName` values, so it is immediately visible in the chat who answered.

🇷🇺 **Почему так, а не «умный автовыбор»:** любая эвристика однажды ошибётся и отправит
наружу то, что не следовало. Здесь ошибиться может только человек, и он видит,
что делает. Плюс это честно объясняется семье одной фразой: «пишешь `нас` — никуда
не уходит, пишешь `@бобик` — уходит».

🇬🇧 **Why this way and not a "smart auto-choice":** any heuristic will eventually get it wrong
and send out something it should not have. Here only the person can make the mistake, and
they see what they are doing. It also explains honestly to the family in one sentence:
"write `нас` — nothing leaves, write `@бобик` — it leaves."

🇷🇺 **Защита от петли:** ответы бота начинаются с эмодзи, а позывной должен стоять
**первым словом** — поэтому бот не реагирует на собственные сообщения.

🇬🇧 **Loop protection:** the bot's replies start with an emoji, and the callsign must be
the **first word** — so the bot does not react to its own messages.

🇷🇺 **Двойной лимит:** `TALK_BOT_LLM_DAILY_REPLIES` (ответов в сутки на уровне бота) и
`LLM_DAILY_TOKEN_LIMIT` / `LLM_MONTHLY_COST_LIMIT_USD` (на уровне шлюза, fail-closed).

🇬🇧 **Dual limit:** `TALK_BOT_LLM_DAILY_REPLIES` (replies per day at the bot level) and
`LLM_DAILY_TOKEN_LIMIT` / `LLM_MONTHLY_COST_LIMIT_USD` (at the gateway level, fail-closed).

## Приватность (критично для семейного чата) / Privacy (critical for the family chat)

🇷🇺
1. **Команды и данные** (диск, фото, restart) обрабатываются **локально** — в облако DeepSeek не уходят вообще.
2. В DeepSeek уходят **только свободные вопросы** и только **после redaction** (email / телефоны / секреты уже вырезаются в шлюзе — см. `services/llm-gateway/app/main.py`).
3. **Stretch-goal:** локальная маленькая модель (1–3B, quantized, `llama.cpp`) для полностью приватного режима. На 4 ГБ при 13 контейнерах — медленно; держать как эксперимент, не как базу.

🇬🇧
1. **Commands and data** (disk, photos, restart) are processed **locally** — they never go to the DeepSeek cloud at all.
2. Only **open-ended questions** go to DeepSeek, and only **after redaction** (email / phone numbers / secrets are already stripped in the gateway — see `services/llm-gateway/app/main.py`).
3. **Stretch goal:** a small local model (1–3B, quantized, `llama.cpp`) for a fully private mode. On 4 GB with 13 containers — slow; keep it as an experiment, not as the baseline.

---

## Реализм по железу / Hardware realism

🇷🇺
- Nano 4 ГБ уже нагружен: 13 контейнеров, `immich-microservices` ограничен `mem_limit 512m`.
- Фазы **A–C** ложатся на облачный DeepSeek — по ресурсам почти бесплатно.
- Фаза **D** (голос) — самая тяжёлая по CPU/RAM, ставится последней, после разгрузки памяти и подключения 2 ТБ HDD.

🇬🇧
- The 4 GB Nano is already loaded: 13 containers, `immich-microservices` capped at `mem_limit 512m`.
- Phases **A–C** rest on the cloud DeepSeek — resource-wise almost free.
- Phase **D** (voice) is the heaviest on CPU/RAM, placed last, after memory is freed up and the 2 TB HDD is attached.

---

## Предлагаемый порядок (ближайшие 3 шага) / Proposed order (next 3 steps)

🇷🇺
1. **Фаза A + E** — быстрый видимый результат: бот в чате + перенос алертов (диск / USB) из Telegram в семейный Talk. Мало кода, сразу польза.
2. **Фаза B** — команды `статус`, `диск`, `фото`, `перезапусти X`. Опирается на готовые `/v1/*`.
3. **Фаза C** — свободные вопросы через redaction-шлюз.

Голос (D) и локальная модель — после.

🇬🇧
1. **Phase A + E** — a fast visible result: a bot in the chat + moving alerts (disk / USB) from Telegram into the family Talk. Little code, immediate benefit.
2. **Phase B** — commands `статус` (status), `диск` (disk), `фото` (photos), `перезапусти X` (restart X). Builds on the already-ready `/v1/*`.
3. **Phase C** — open-ended questions through the redaction gateway.

Voice (D) and a local model — later.

---

## Целевая структура кода / Target code structure

```
services/nas_jetson_nano-api/app/routers/
└── talk_bot.py          ← ✅ РЕАЛИЗОВАН (фаза A): polling комнаты + разбор команд + ответ
                            (IMPLEMENTED (phase A): room polling + command parsing + reply)
                            (переиспользует system.py / storage.py / photos.py / talk.py)
                            (reuses system.py / storage.py / photos.py / talk.py)

services/llm-gateway/app/
└── main.py              ← уже готов: /v1/chat с redaction (фаза C)
                            (already ready: /v1/chat with redaction (phase C))
```

## Как включить фазу A (после деплоя кода) / How to enable phase A (after deploying the code)

🇷🇺
1. Задеплоить API на Jetson (`git pull` + rebuild/restart контейнера `homecloud_nas_jetson_nano_api`).
2. В `config/.env` выставить `TALK_BOT_ENABLED=true` (опц. `TALK_BOT_TRIGGER=нас`).
3. Перезапустить контейнер API.
4. Проверить: `GET http://192.168.0.50:8099/v1/talk/bot/status` → `running: true`.
5. В семейном чате написать `статус` / `диск` / `фото` / `пинг` — бот ответит.

> Пока `TALK_BOT_ENABLED=false` (по умолчанию) код полностью пассивен — деплой ничего не меняет.

🇬🇧
1. Deploy the API on the Jetson (`git pull` + rebuild/restart the `homecloud_nas_jetson_nano_api` container).
2. Set `TALK_BOT_ENABLED=true` in `config/.env` (optionally `TALK_BOT_TRIGGER=нас`).
3. Restart the API container.
4. Verify: `GET http://192.168.0.50:8099/v1/talk/bot/status` → `running: true`.
5. In the family chat, write `статус` (status) / `диск` (disk) / `фото` (photos) / `пинг` (ping) — the bot will reply.

> While `TALK_BOT_ENABLED=false` (default) the code is fully passive — deploying it changes nothing.

---

## Параллельные треки развития проекта / Parallel project development tracks

| Трек / Track | Задача / Task | Источник / Source |
|---|---|---|
| Надёжность / Reliability | Restic off-site backup после подключения 2 ТБ HDD / Restic off-site backup after the 2 TB HDD is attached | CLAUDE.md |
| Доступ / Access | Tailscale вместо проброса через VPS / Tailscale instead of forwarding through the VPS | `TAILSCALE_ACCESS_PLAN.md` |
| Наблюдаемость / Observability | `GET /v1/metrics/history` в SQLite → timeseries; Prometheus `/metrics` для Grafana / `GET /v1/metrics/history` into SQLite → timeseries; Prometheus `/metrics` for Grafana | API roadmap «Будущие идеи v1.x» / API roadmap "Future ideas v1.x" |
| API-hardening | Rate limiting (slowapi), unit-тесты (pytest + httpx), `/v1/actions/.../update` / Rate limiting (slowapi), unit tests (pytest + httpx), `/v1/actions/.../update` | API roadmap |
| Мобильное / Mobile | доработка `API_MOBILE_PLAN.md` / refining `API_MOBILE_PLAN.md` | план / plan |
| Публикация / Publication | статьи Habr / Hackaday (WIP в `docs/articles/`) / Habr / Hackaday articles (WIP in `docs/articles/`) | идёт / in progress |

---

## English summary

A family AI assistant living inside **Nextcloud Talk**. It is glue between three existing building blocks — Nextcloud Talk (chat), the **LLM Gateway** (`:8090`, DeepSeek behind a redaction boundary), and **nas_jetson_nano-api** (`:8099`, JWT orchestrator that already reads metrics/photos/storage and performs actions).

Flow: a message in the "Семья" room → Talk Bot webhook → `nas_jetson_nano-api /v1/talk/bot/webhook` → intent routing: **commands/data are handled locally** (never leave the box), **open questions go to DeepSeek only after redaction**. Later: voice via Piper (TTS) + whisper.cpp/Vosk (STT).

Phases: **A** text bot MVP → **B** smart commands → **C** free-form questions → **D** voice → **E** proactive alerts (move disk/USB alerts from Telegram into Talk). Phases A–C are cheap on the 4 GB Nano (cloud LLM); phase D and any local model are stretch goals after the 2 TB HDD is attached.
