# Точка проекта 2026-09-19 — W0.1 Hardening Sprint завершён

> ⚠️ **Поправка (аудит 2026-09-19, отзыв статусов).** Ниже записано «все 16 тестов прошли ✅» —
> **неверно**: на `d52c11b` падали 2 существующих теста, а каждый чат GigaChat отдавал HTTP 500
> (`full` до присваивания), удалён `_IMG_TAG_RE`. Найдено исполнением эндпоинта через `TestClient`;
> ворота не видели тестов шлюза. Исправлено коммитами `36c4ced` (шлюз, W0.2 доведён) и `b8f50c9` (CI).
> «Все сервисы ✅ Live» в §2 неполно: `nasa-ssd-recovery` был `failed` (исправление — `9ec1b15`, ждёт деплоя).
> Разбор: `docs/audit/2026-09-19_full_audit/REVIEW_GIGACODE_W0_2026-09-19.md`. Текущий план: `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` (сводная редакция).

> **Статус:** W0.1 ✅ в git, ✅ на GitHub  
> **Дата:** 2026-09-19 06:25  
> **Следующий шаг:** W0.2 (gateway auth) или W0.3 (NAS API RBAC)

---

## 1. Что сделано сегодня

### W0.1 — save_path restriction (audit_new G01, P0)

**Файл:** `services/llm-gateway/app/main.py`

**Что было:** `_finish_image` принимал произвольный `save_path` от клиента и писал в любую директорию контейнера. Это позволяло записать файл в persistent volume `/data` или любую доступную директорию.

**Что стало:**
- `IMAGE_OUTPUT_ROOT` env var (default: `/data/images`)
- `_sanitize_save_path(requested)`:
  - `None` → `Path("")` (no save, base64 in response)
  - `""` → 400 (empty filename)
  - `.` / `..` → 400 (invalid names)
  - `null byte` → 400
  - `../../etc/passwd` → `.name` → `passwd` → `/data/images/passwd` (безопасно!)
  - Resolve + `relative_to(root)` → 403 если выходит за root
- Health endpoint: `image_output_root: /data/images`
- Compose: `IMAGE_OUTPUT_ROOT` propagated from env

**Тесты:** 8 новых тестов в `test_smart_routing.py` — все 16 прошли ✅

### Smart routing (бесплатно, freemium)

- 50+ паттернов для определения сложных промптов
- Сложные → `GigaChat-2-Max`, простые → `GigaChat-2`
- Оба модели из одного freemium-ведра — просто умнее использование токенов

### Image presets (+5 семейных)

- `birthday_card`, `family_collage`, `child_drawing`, `postcard`, `meme`
- Итого: 8 пресетов (было 3)

### Документация

- `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` — волна Hardening Sprint W0.5
- `audit_new.md` — полный аудит проекта (24 gap, P0-P3)

---

## 2. Live snapshot (2026-09-19 06:16)

| Сервис | Порт | Статус |
|---|---|---|
| Nextcloud | 8080 | ✅ Live |
| Immich | 2283 | ✅ Live |
| LLM Gateway | 8090 | ✅ Live |
| NAS API | 8099 | ✅ Live |
| Samba | 445 | ✅ Live |
| SSH | 22 | ✅ Live |

### GigaChat баланс

| Модель | Остаток |
|---|---|
| Lite | 249 995 856 / 250M |
| Pro | 40 000 000 / 40M |
| Max | 24 991 737 / 25M |
| Ultra | 50 000 000 / 50M |

### Usage за месяц

| User | Токены | Вызовы |
|---|---|---|
| admin | 1 985 | 24 |
| unknown | 367 | 5 |
| diag | 109 | 2 |
| olga, ivan, alexey | 0 | 0 |

---

## 3. Следующие шаги

### Приоритет: W0.2 — Gateway service auth (P0)

Добавить service token middleware для `/v1/chat` и `/v1/image/*`:
- `LLM_GATEWAY_SERVICE_TOKEN` env var
- Без токена → 401
- С токеном → 200
- Health endpoint — без токена (для мониторинга)

### Приоритет: W0.3 — NAS API RBAC (P0)

Отделить `authenticated user` → `operator` → `owner`:
- Family user → read-only
- Operator → backup, status
- Owner → restart, privileged actions

### Приоритет: W0.4 — Diagnostic endpoints auth (P0)

Закрыть auth'ом: `/logs`, `/metrics`, `/containers`, `/report/now`, Talk status

### Приоритет: W0.5 — Privacy scrub HEAD

Убрать room IDs, family identifiers из current HEAD

---

## 4. Коммит

```
d52c11b feat(w0.1): save_path restriction (G01) + smart routing + 8 image presets + tests
```

---

## 5. Канон

- **План:** `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`
- **Аудит:** `docs/research/audit_new.md`
- **ADR:** `docs/decisions/ADR-0007`, `ADR-0008`, `ADR-0009`
- **Архитектура:** `docs/00_OVERVIEW.md`, `docs/03_ARCHITECTURE.md`

---

## 6. Жёсткие запреты

- ❌ Не трогать Amnezia на VPS
- ❌ Не удалять `nas_jetson_nano-lan` / `192.168.0.50`
- ❌ Не открывать сервисы в интернет
- ❌ Не форматировать HDD 2 ТБ
- ❌ Не деплоить без «деплой»

---

## Итог дня 2026-09-19 (для продолжения после перезагрузки)

**Выкачено на Jetson (все с правилом №13 до/после — VPS не менялся, 19 пиров):**
- **A** — единая раскладка хоста (`scripts/lib/layout.sh`), авто-восстановление SSD снова работает, шлюз починен, сервисный токен шлюза включён.
- **B** — restic-бэкап конфигурации/`.env`/файлов Nextcloud на HDD (ежедневно 03:40, учения 1-го числа — DRILL OK); `backups/` только чтение в Samba/Nextcloud. Пароль репо — Windows Credential Manager `nas-jetson-restic-config-hdd`.
- **C** — NAS API: JWT везде кроме `/healthcheck`, роли семья/владелец (`admin`), CORS выкл.; шлюз не от root, откат на DeepSeek только на 429/5xx; Portainer только localhost; rpcbind выкл. C9 (SSH/пароли) оставлен как есть по решению владельца.

**Следующий шаг:** Telegram-бот. Спецификация утверждена — `docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md`.
Дальше: план реализации (writing-plans) → код с тестами в git → выкат по «деплой».
Токен бота уже в `.env` устройства (600) и в Credential Manager `nas-telegram-bot-token`; ⚠️ перед подключением семьи — Revoke и новый токен через файл, не через чат.

**Ждут решения владельца:** D1–D6 (план §2.2), tenant_id Cloud.ru для S3 (B3), переписывание истории git (C7).

## Вечер 2026-09-19 — E2 и D3 в git, решения владельца

**В git, на устройстве НЕ выкачено (ждёт «деплой»):**
- **E2** — алерт квоты GigaChat в Talk владельцу: порог по каждой модели (2 млн), устаревший опрос (> 50 ч) —
  тоже тревога. `6bd36bf`.
- **D3** — внешний сторож: задача Cloud.ru раз в 10 мин → VPS (`naswatch`, ключ с одной командой) → проверка
  NAS через туннель → Telegram владельцу. Спецификация `126e06b`, план `aa96612`, реализация субагентами
  (5 задач, ревью каждой + финальное ревью Opus), 44 теста. Runbook `DEPLOY_D3_WATCHDOG_2026-09.md`:
  первым шагом — спайк в Cloud.ru (доходит ли до Telegram, есть ли расписание, откуда образ).

**Решения владельца:** S3 (B3) отложен — off-site на Vostro; ИБП отложен; копии архива 1,4 ТБ нет и не
будет — риск принят (B5 закрыт); Immich ML — в Cloud.ru только в пределах free tier (бесплатной VM в
Evolution free tier нет — только Container Apps; спайк E6 после E5).

**Замер:** `getMe` бота `@bobik_borovskoy_bot` — `ok`, `can_read_all_group_messages=false`; `getUpdates` пуст —
`/start` ещё никто не писал, chat_id владельца для D3 пока неизвестен.

**Следующий шаг:** E5 (алерт расходов Cloud.ru) → Telegram-бот (план) → E1, E3, D2. Выкат E2/D3 — по «деплой».

## Ночь 2026-09-19 — качалка и первый срез Telegram-бота (приоритет владельца)

Запрос сына — качалка на Jetson; владелец дал приоритет **рядом с Telegram-ботом** (задача **E9** в плане).
Две спецификации утверждены за пять редакций: `docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md`,
`docs/superpowers/specs/2026-09-19-home-downloader-design.md`.

- **ред. 2:** главный интерфейс — чат с ботом `@bobik_borovskoy_bot` в семейной группе «Боровские» (бот уже
  в группе, `/start` собран у всех 4 человек 2026-09-19 — ID в `docs/local/IDENTIFIERS.md`, вне git).
- **ред. 3:** обращение к боту — **по имени**: «@бобик скачай …» или «бобик, …», как позывной `@бобик` в Talk.
  Из этого следует цена: режим приватности бота в группе выключается (`/setprivacy` → Disable в @BotFather,
  бота перезайти в группу) — иначе Telegram не отдаёт боту слово «@бобик», это не упоминание аккаунта.
  Сообщения без обращения бот отбрасывает сразу: не обрабатывает, не хранит, не пишет в журнал.
- **ред. 4:** размер закачки — **без искусственного предела**; ≤ `DL_SSD_MAX_GB` (20 ГБ) — через SSD,
  больше — сразу на HDD (`/mnt/hdd2tb/Downloads/.incomplete`), без переноса. 20 МБ — предел **только**
  `.torrent`-файла, который бот забирает из чата (лимит Bot API на `getFile`), не самой закачки.
- **ред. 5:** в тот же первый срез бота входят **вопросы к GigaChat** («@бобик <вопрос>» — тот же путь,
  что `@бобик` в Talk: safety gate → шлюз с токеном → квота по логину). Фото — следующим срезом. SOCKS-туннель
  слушает `172.17.0.1:1080` (адрес docker0, не `127.0.0.1`) — замер 2026-09-19 показал, что Jetson напрямую
  до Telegram не доходит (3 из 3 попыток — таймаут).

Качает **Jetson через домашний интернет, не VPS** — VPS держит VPN ~25 человек, жалоба правообладателя
хостеру грозит блокировкой IP (правило №13); заодно на VPS мало места. Замер дисков 2026-09-19: SSD 229 ГБ,
занято 14 ГБ (Immich 13 ГБ), свободно 204 ГБ; HDD свободно 438 ГБ. Steam на Jetson не делаем (SteamCMD
только x86); флешку в Jetson — не на этом этапе (два необъяснённых аппаратных сброса устройства).

**Статус:** обе спецификации утверждены владельцем, реализация — план (writing-plans), выкат — только
по «деплой». Устройство и VPS сегодня ночью не менялись.

---

### EN summary
Stages A, B and C were deployed to the Jetson on 2026-09-19 with the VPN on the VPS untouched each time.
In the evening, two items landed in git and wait for an owner-triggered deploy: E2, a per-model GigaChat
quota alert, and D3, an outside watchdog in which a Cloud.ru job asks the VPS through a single-command key
whether the NAS answers and alerts the owner in Telegram. The owner postponed S3 and the UPS, accepted
having no second copy of the 1.4 TB archive, and allowed Immich ML on Cloud.ru only within the free tier.

Later that night, the owner's son asked for a home downloader, and the owner gave it priority, next to the
Telegram bot (plan item E9). Two specs were approved through five revisions: the bot's main interface is
chat with `@bobik_borovskoy_bot` in the family group, addressed by name ("@бобик ...") like `@бобик` in
Talk — which means the bot's group privacy mode is turned off, and messages without the name are dropped
at once, unstored and unlogged. Downloads have no size cap: up to 20 GB go through the SSD, larger ones
straight to the HDD; the 20 MB Telegram limit applies only to a `.torrent` file sent in chat. GigaChat
questions ("@бобик <question>", the same path as Talk) are part of this same first slice; photos come
later. aria2 downloads over the Jetson's home internet, never the VPS (rule #13). The Jetson cannot reach
Telegram directly (3 of 3 timeouts measured 2026-09-19), so the SOCKS tunnel listens on the docker0 address
172.17.0.1. Status: both specs approved, implementation plan next, deploy only on "деплой". Neither the
device nor the VPS changed tonight.

Next: a Cloud.ru spend alert, the Telegram bot + downloader implementation plan, GigaChat routing and
`@бобик` diagnostics.

## Качалка + первый срез Telegram-бота — реализовано в git (2026-09-19)

- Ветка `feat/downloader-bot` влита в `main` (`90b52bc`). План `docs/superpowers/plans/2026-09-19-home-downloader-telegram.md`,
  6 задач субагентами; каждая — ревью, Task 2/3/4/5 — 1–2 раунда исправлений; финальное ревью (Opus) — 8 Important,
  одна волна исправлений, повторное ревью закрыло всё. Журнал решений — `docs/local/SDD_downloader_progress.md` (вне git).
- Тесты: NAS API 90, хуки aria2 16, инфраструктура 10.
- Найдено ревью и исправлено до выката (ошибки плана): обход SSRF-фильтра числовыми IP; страж снимал паузу с неразложенного
  торрента (ушёл бы на SSD); «@бобикXYZ» уходило в GigaChat; umask 077 делал скачанное нечитаемым для Samba; потеря
  уведомлений при недоступном Telegram (очередь outbox); хук `on_stop` мог стирать недокачанное при перезапуске контейнера
  (теперь удаляет только подтверждённо отменённое); маркер HDD — без него качалка не пишет на SD-карту.
- Оставлено осознанно (журнал, Ruling 12–15): рост очереди уведомлений при мёртвом Telegram; самовосстанавливающийся случай
  metadata→followedBy при сбое RPC; маркер HDD без sudo; RPC-ошибки стража без отдельного перехвата.
- **Выкат — только по «деплой»:** `docs/plans/DEPLOY_DOWNLOADER_2026-09.md` (владелец: @BotFather `/setprivacy` → Disable,
  перезайти бота в группу). Следующее: голосовые сообщения (Vosk — предложение), алерт баланса DeepSeek (3.97 $).

### EN
The downloader and the first Telegram bot slice are implemented and merged to `main` (`90b52bc`), not deployed. Six tasks
ran through subagents with per-task reviews and a final Opus review; eight important findings were fixed before any
rollout. Deploy only on the owner's command using `DEPLOY_DOWNLOADER_2026-09.md`.

## Выкат качалки и бота — 2026-09-19 16:45–17:10 UTC

- Jetson `339db92` → `75a1cc8` (откат: `~/dl-rollback-PREV`); `.env` — копия `config/.env.bak.dl.*`, ключи бота и
  `ARIA2_RPC_SECRET` (копия — Credential Manager `nas-aria2-rpc-secret`).
- SOCKS `nas_jetson_nano-tg-socks` — только `172.17.0.1:1080`, перезапусков 0, Telegram через него 302 (и из контейнера API).
- `homecloud_downloads` (aria2 1.37 + AriaNg 1.3.14): 6 МБ ОЗУ, запись на SSD и HDD проверена, дневной лимит применён (`OK`).
- Владелец: приватность бота выключена, бот перезашёл в группу (`can_read_all_group_messages=True`); хвост из 19 старых
  апдейтов сброшен до запуска бота.
- NAS API пересобран: `telegram connected`, 52/128 МБ, Talk-бот работает. 14 контейнеров, failed 0, доступно 1,65 ГБ.
- Сквозная проверка: HTTP-файл → SSD → перенос на HDD → «✅ Готово» доставлено (владельцу в личку — проверочно); GigaChat «🐕 ок».
- Объявление о возможностях отправлено в «Боровские» (message_id 12). Правило №13: VPS ДО/ПОСЛЕ идентичен, 19 пиров.
- ⚠️ **Найдено по ходу:** dockerd не резолвит имена — ходит на `127.0.1.1:53` (никто не слушает) после смены `resolv.conf`
  18.09 13:57; `daemon.json` `dns` влияет только на контейнеры. Обход: база качалки `alpine:3.19`, уже бывшая на устройстве
  (`75a1cc8`). Лечение — перезапуск Docker (простой всех контейнеров) в окне владельца; до него новые образы не скачать.
- ⚠️ Отзыв утреннего вывода «Jetson напрямую Telegram не видит»: проверка шла тем же сломанным путём? Нет — `curl` на хосте
  резолвит через `127.0.0.53` (работает); таймаут был на соединении. Вывод остаётся, но его стоит перепроверить отдельно.
- Таймеры скорости работают по UTC: «день» = 11:00–02:00 МСК. Поправить на МСК — отдельной правкой.

### EN
The downloader and the Telegram bot were deployed at 17:03 UTC and checked end to end; the family announcement was sent.
Rule #13 held. Found on the way: dockerd cannot resolve names since the resolv.conf change on 2026-09-18 (worked around
with a local base image; fixing it needs a Docker restart in an owner window), and the speed timers run on UTC.

## Точка 2026-09-20 — где остановились (лимит владельца)

**В бою на Jetson:** качалка + Telegram-бот (обращение «бобик» в любой форме), E2 (алерт квоты GigaChat),
сторона VPS для сторожа D3, Docker с починенным DNS. 14 контейнеров, failed 0.

**Память разговора @бобик — ветка `feat/bobik-dialog`** (worktree `../NAS_wt_dlg`, в `main` НЕ влита):
- ✅ Task 1–3 сделаны и прошли ревью (коммиты `3472f06`, `31ac359`, `5b738ca`, `3f010a2`, `32c1b88`), 116 тестов.
- 🟠 Финальное ревью (Opus): **нужны исправления до слияния** — (1) нет ни одного теста Talk-цикла: мутация
  «ключ = константа» (слияние всех 6 комнат в одну нить) проходит все 116 тестов; (2) `test_downloads_are_not_remembered`
  проходит вхолостую; (3) строка в CHANGELOG. Плюс дешёвые мелочи: `llm_failed_last` в инициализаторе `_STATE`,
  обрезка имени говорящего, докстринг. **Волна исправлений запущена субагентом, результат не получен** (лимит).
- Решения владельца 2026-09-20: лимиты токенов подняты (60k/человек, 250k дом, коммит `7f84ce8`); «забудь» — только Telegram.
- Выкат памяти (по «деплой»): `.env` устройства → новые лимиты → **пересоздать** контейнер шлюза (`up -d`, не `restart`)
  → пересобрать NAS API → проверка в группе → через сутки `curl -s :8090/v1/usage`.

**Голосовые сообщения:** запущено исследование субагентом (Vosk / whisper.cpp / SaluteSpeech, роль Kaggle),
результат — `docs/research/VOICE_MESSAGES_RESEARCH_2026-09-20.md`, **не получен** (лимит).

**Kaggle** заведён как ресурс подготовительных работ (`docs/integrations/kaggle/README.md`), ключ — в `.gitignore`
и Credential Manager `nas-kaggle-api`. Исправлена своя ошибка: каталог `kaggle/` не был под игнором.

**Этап G** (инженерный стандарт и чистка репозитория) поставлен в план из мастер-промта с поправками;
G0 (Gitleaks, Dependabot, CodeQL, проверка гигиены) можно делать раньше. Базовая линия: 545 файлов, 20,2 МБ,
docs+assets = 96 % дерева, один скриншот в 6 копиях.

**Статья на Хабр:** журнал доказательств `docs/articles/HABR_PART2_MATERIALS.md`, пополняется по ходу (DoD §3 п. 5).

**Ждёт владельца:** ключ Cloud.ru (Key ID + Secret) для второй половины сторожа D3.

### EN
Stopped on the owner's usage limit. Live on the Jetson: downloader, Telegram bot, E2 quota alert, the VPS half of
the D3 watchdog, Docker DNS fixed. The conversation-memory branch is complete but not merged: the final review
requires a Talk-cycle test (a mutation merging all six Talk rooms into one thread passes all 116 tests), one
vacuous test fixed and a CHANGELOG line; the fix wave and the voice-message research were still running when the
session stopped. Owner decisions recorded: token limits raised, «забудь» stays Telegram-only.

## Память разговора — завершено в git 2026-09-20

Ветка `feat/bobik-dialog` влита в `main` (`5ddd116`), 119 тестов API зелёные. Волна исправлений после
финального ревью (Opus) прошла: добавлен тест Talk-цикла — контроллер проверил его двумя мутациями
(подмена ключа на общий → слияние 6 комнат Talk в одну нить; удаление памяти из Talk-цикла) — обе падают,
код восстановлен. Закрыты также пустой тест закачек и строка CHANGELOG.

**На устройстве не выкачено.** Порядок выката (по «деплой»): `.env` → `LLM_USER_DAILY_TOKEN_LIMIT=60000`,
`LLM_DAILY_TOKEN_LIMIT=250000` → **пересоздать** контейнер шлюза (`up -d`, не `restart`) → пересобрать NAS API
→ проверка в группе (вопрос → уточнение → «бобик, забудь») → через сутки `curl -s :8090/v1/usage`.

Решения владельца: лимиты подняты (замер 2026-09-20: 144 токена на вопрос без истории); «забудь» — только Telegram.
Голосовые сообщения: исследование готово (`docs/research/VOICE_MESSAGES_RESEARCH_2026-09-20.md`), реализация не начата.

### EN
The conversation-memory branch is merged to `main` (`5ddd116`) after the final-review fix wave; the new Talk-cycle
test was verified by the controller against two mutations. Not deployed yet — deploy raises the token limits,
recreates the gateway container so it re-reads `.env`, rebuilds the NAS API and checks the flow in the family group.
