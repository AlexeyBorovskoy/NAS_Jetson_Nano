# NAS_Jetson_Nano — API Roadmap

> Документ планирования NAS_Jetson_Nano API.
> Живёт в `docs/plans/`. Обновляется по мере реализации.

---

## Историческое состояние / Historical state — v0.6.0 (проверялось / observed 2026-06-29)

> 🇷🇺 Для подтверждения текущего состояния нужна новая read-only проверка.
>
> 🇬🇧 A new read-only check is required to confirm the current state.

**Стек:** FastAPI 0.138 · Python 3.12 · Pydantic v2 · JWT (Nextcloud OCS) · Swagger UI `:8099/docs`

| Метод | Маршрут | Auth | Статус |
|---|---|---|---|
| GET | `/healthcheck` | — | ✅ |
| GET | `/v1/status` | — | ✅ |
| POST | `/api/auth/login` | — | ✅ |
| GET | `/api/auth/me` | JWT | ✅ |
| GET | `/v1/metrics` | — | ✅ |
| GET | `/v1/containers` | — | ✅ |
| GET | `/v1/storage` | JWT | ✅ |
| GET | `/v1/logs` | — | ✅ |
| POST | `/v1/report/now` | — | ✅ |
| GET | `/v1/talk/rooms` | — | ✅ Talk интеграция |
| GET | `/v1/talk/rooms/{token}` | — | ✅ |
| POST | `/v1/talk/notify` | JWT | ✅ |
| GET | `/v1/users` | JWT | ✅ 5 семейных пользователей |
| GET | `/v1/users/{username}` | JWT | ✅ |
| POST | `/v1/users/{username}/notify` | JWT | ✅ DM через Talk |
| GET | `/v1/photos/stats` | JWT | ✅ Immich v2.7.5: 6484 фото, 210 видео, 4.24 GB |
| GET | `/v1/photos/users` | JWT | ✅ |
| POST | `/v1/actions/containers/{name}/restart` | JWT | ✅ whitelist 10 контейнеров |
| POST | `/v1/actions/backup/now` | JWT | ✅ fire-and-forget |
| GET | `/v1/actions/history` | JWT | ✅ |

**Live:** `http://192.168.0.50:8099/docs` · `http://95.163.176.103:8099/docs`

---

## v0.3.0 — Talk Integration 💬 ✅ Реализовано

**Цель:** API умеет читать чат и отправлять сообщения в семейную группу.

| Метод | Маршрут | Auth | Описание |
|---|---|---|---|
| GET | `/v1/talk/rooms` | — | Список комнат Talk (название, токен, кол-во участников) |
| GET | `/v1/talk/rooms/{token}` | — | Детали комнаты: участники, последнее сообщение |
| POST | `/v1/talk/notify` | JWT | Отправить сообщение в комнату |

- Используется Nextcloud OCS Talk API (`/ocs/v2.php/apps/spreed/api/v4/...`)
- Admin-credentials из env (`NEXTCLOUD_ADMIN_USER`, `NEXTCLOUD_ADMIN_PASSWORD`)
- Семейная комната: токен `37pcobmf`, группа «Семья», 5 участников

---

## v0.4.0 — Control Actions ⚙️ ✅ Реализовано

**Цель:** API не только читает, но и управляет — перезапускает контейнеры, запускает бэкап.

| Метод | Маршрут | Auth | Описание |
|---|---|---|---|
| POST | `/v1/actions/containers/{name}/restart` | JWT | Перезапустить Docker-контейнер |
| POST | `/v1/actions/backup/now` | JWT | Запустить резервное копирование БД немедленно |
| GET | `/v1/actions/history` | JWT | Журнал последних действий (из JSON-лога) |

- Restart — через Docker UNIX socket, whitelist из env `RESTARTABLE_CONTAINERS`
- Backup — `backup_databases.sh` (async, fire-and-forget, 300s timeout)

---

## v0.5.0 — Family Users 👨‍👩‍👧‍👦 ✅ Реализовано

**Цель:** Видеть всех пользователей семейного облака и их статус.

| Метод | Маршрут | Auth | Описание |
|---|---|---|---|
| GET | `/v1/users` | JWT | Список пользователей Nextcloud (имя, группы, last seen) |
| GET | `/v1/users/{username}` | JWT | Детали: квота, использование диска, last seen |
| POST | `/v1/users/{username}/notify` | JWT | Отправить личное сообщение в Talk |

- Данные из Nextcloud OCS API (`/ocs/v1.php/cloud/users`)
- `notify` — DM через Talk API (1-to-1 комната, создаётся автоматически)

---

## v0.6.0 — Photos (Immich) 📷 ✅ Реализовано

**Цель:** Базовая статистика фотоархива семьи.

| Метод | Маршрут | Auth | Описание |
|---|---|---|---|
| GET | `/v1/photos/stats` | JWT | Общая статистика: кол-во фото/видео, альбомы, размер |
| GET | `/v1/photos/users` | JWT | Статистика по каждому пользователю |

- Immich Admin API (`/api/server/statistics`, `x-api-key`)
- API-ключ: env `IMMICH_API_KEY` (name: `nas_jetson_nano-api-monitor`, permission: `all`)

---

## Архитектурные принципы

- **Все эндпоинты возвращают JSON** — никаких HTML
- **Auth через JWT** (Nextcloud OCS) — один токен на все защищённые роуты
- **Fire-and-forget для действий** — HTTP 202 сразу, результат в логах
- **Whitelist для опасных операций** — restart разрешён только для известных контейнеров
- **Admin-credentials в env** — никогда не в коде
- **Все роуты документированы** в OpenAPI/Swagger — description, response_model, example

---

## Будущие идеи (v1.x)

- `GET /v1/metrics/history` — хранить метрики в SQLite, отдавать timeseries
- `POST /v1/actions/containers/{name}/update` — pull нового образа + restart
- `GET /v1/network` — статус туннеля VPS, ping latency
- `POST /v1/talk/broadcast` — отправить одно сообщение во все комнаты
- Rate limiting (slowapi)
- Unit-тесты (pytest + httpx AsyncClient)
- Prometheus `/metrics` endpoint для Grafana

---

## Файловая структура (целевая)

```
services/nas_jetson_nano-api/app/
├── main.py              ← регистрация роутеров, Swagger теги
├── config.py            ← Pydantic Settings (все env vars)
├── logging_setup.py     ← JSON-логгер с ротацией
└── routers/
    ├── health.py        ✅ v0.1
    ├── auth.py          ✅ v0.2
    ├── system.py        ✅ v0.2  (metrics, containers)
    ├── storage.py       ✅ v0.2
    ├── logs.py          ✅ v0.2
    ├── actions.py       ✅ v0.4 (report, restart, backup, history)
    ├── talk.py          ✅ v0.3 (rooms, room detail, notify)
    ├── users.py         ✅ v0.5 (list, detail, DM notify)
    └── photos.py        ✅ v0.6 (server stats, per-user stats)
```
