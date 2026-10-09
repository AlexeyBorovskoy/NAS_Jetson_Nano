# 21. Логирование и Status API / Logging & Status API

## DEP-1 — закреплённые зависимости, 2026-10-09

🇷🇺 `requirements.txt` задаёт пять точных прямых версий. `requirements.lock`
фиксирует полный граф (32 пакета с платформенными условиями) и SHA-256 архивов.
Docker устанавливает только бинарные пакеты из lock с `--require-hashes`.
Прямые версии и доступные транзитивные версии сохранены из проверенного окружения.
`passlib[bcrypt]` удалён: во всём NAS API нет его использования, пароли проверяет
Nextcloud. `python-jose==3.5.0` сохранён: API использует encode/decode и JWTError,
HS256 разрешён явно. Переход на другую JWT-библиотеку — отдельная миграция с
проверкой совместимости токенов и обработки ошибок, не механическая замена пина.

Проверено в чистом Windows Python 3.12.15: установка с обязательными хешами,
`pip check` без конфликтов, NAS API 266 passed. Отдельно скачаны бинарные wheels
для всех 31 применимых Linux ARM64 зависимостей с проверкой SHA-256; код на ARM64
этим не запускался. Pip отклонил намеренно неверный хеш в автономной проверке.
Тесты политики — `tests/unit/test_nas_api_dependency_lock.py` (5 tests OK).
Живой образ Jetson не пересобран и не развёрнут.

Обновление: изменить прямые версии, перегенерировать lock закреплённым генератором
`uv==0.12.24`, проверить diff и чистую установку/тесты. Существующий lock хранит
выбранные транзитивные версии; не удалять его перед обычной перегенерацией.
См. [официальную документацию uv](https://docs.astral.sh/uv/pip/compile/).

```bash
uv pip compile services/nas_jetson_nano-api/requirements.txt --universal \
  --python-version 3.12 --generate-hashes --no-header \
  --default-index https://pypi.org/simple \
  -o services/nas_jetson_nano-api/requirements.lock
python -m pip install --require-hashes --only-binary=:all: \
  -r services/nas_jetson_nano-api/requirements.lock
python -m pip check
python -m pip install pytest==9.1.1 pytest-asyncio==1.4.0
python -m pytest tests/nas_api -q
```

Выполнять установку в отдельном окружении внутри `.agent-work/tmp/`, не в системном
Python. Для Windows/Git Bash направить TEMP/TMP/TMPDIR внутрь проекта. Общий
`requirements-test.txt` содержит зависимости нескольких сервисов и не заменяет
проверку чистой установки runtime-lock NAS API. Хеши фиксируют содержимое архива,
но сами по себе не являются аудитом уязвимостей.
Откат — прежние Dockerfile/requirements; рабочий образ этим шагом не менялся.

🇬🇧 DEP-1 pins five direct dependencies and a 32-package platform-aware hashed
lock. Docker requires hashes and binary wheels. Unused passlib/bcrypt is removed;
python-jose remains for explicit HS256 JWT handling. Clean Python 3.12 installation,
pip check and 266 NAS API tests passed; all 31 applicable Linux ARM64 wheels were
downloaded with hash verification. ARM64 execution/deployment remains untested.
Update with uv 0.12.24 and retest in an isolated project-local environment.

> 🇷🇺 Описание подсистемы структурированного логирования и REST API статуса NAS_Jetson_Nano. Актуализировано: 2026-06-27.
>
> 🇬🇧 Structured logging subsystem and Status REST API for NAS_Jetson_Nano. Updated: 2026-06-27.
>
> Сервис / Service: `services/nas_jetson_nano-api/`. Compose: `docker/compose/docker-compose.nas_jetson_nano-api.yml`.

---

## 🇷🇺 Русская секция / Russian section

---

## 1. Мотивация

Без структурированных логов невозможно ретроспективно разобраться в причинах
сбоев: контейнер упал, туннель отвалился, диск переполнился — всё это
обнаруживается только по факту. Подсистема логирования решает три задачи:

1. **Хранение истории событий** — JSON-лог с ротацией на хосте, пережива перезапуск контейнеров.
2. **Программный доступ к статусу** — REST API с Swagger UI для диагностики из браузера или скриптов.
3. **Аудит действий** — каждый запрос к API и каждый ключевой системный事件 записывается в лог.

---

## 2. Архитектура логирования

### 2.1 Уровни записи

```
Событие (контейнер упал, отчёт отправлен, API-запрос)
    │
    ▼
nas_jetson_nano-api (FastAPI)
    │
    ├── stdout ──────────────→  docker logs homecloud_nas_jetson_nano_api
    │   (plain text)
    │
    └── RotatingFileHandler ─→  /var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl
        (JSON-lines)               ← монтируется на хост через volume
```

### 2.2 Формат JSON-строки

Каждая строка лога — валидный JSON (формат JSON-lines):

```json
{
  "ts": "2026-06-21T09:00:01Z",
  "level": "INFO",
  "service": "nas_jetson_nano-api",
  "logger": "nas_jetson_nano_api.system",
  "msg": "metrics polled",
  "ram_used_pct": 42.1,
  "services_ok": true
}
```

| Поле | Всегда | Описание |
|------|--------|----------|
| `ts` | ✅ | UTC ISO-8601 timestamp |
| `level` | ✅ | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `service` | ✅ | Всегда `"nas_jetson_nano-api"` |
| `logger` | ✅ | Python-логгер (например `nas_jetson_nano_api.system`) |
| `msg` | ✅ | Текст сообщения |
| `ram_used_pct` | 📌 | Только в событиях `/v1/metrics` |
| `unhealthy` | 📌 | Только при проблемных контейнерах |
| `exc` | 📌 | Только при исключениях |

### 2.3 Ротация файлов

| Параметр | Значение |
|----------|----------|
| Максимальный размер файла | 10 MB |
| Число бэкапов | 5 |
| Итого на диске | ≤ 60 MB |
| Файлы | `nas_jetson_nano-api.jsonl`, `nas_jetson_nano-api.jsonl.1` … `.5` |

Ротация встроенная (Python `RotatingFileHandler`), `logrotate` не нужен.

### 2.4 Директория логов

```
/var/log/nas_jetson_nano-monitor/       ← хост (Jetson)
├── nas_jetson_nano-api.jsonl           ← текущий лог API
├── nas_jetson_nano-api.jsonl.1         ← предыдущий (после ротации)
├── last-report.txt          ← последний Telegram-отчёт (plain text)
└── last-telegram-send.json  ← ответ Telegram Bot API
```

---

## 3. NAS_Jetson_Nano Status API

### 3.1 Обзор

FastAPI-сервис (`services/nas_jetson_nano-api/`) со Swagger UI. Следует паттернам
сервиса `sp_inventory` (pydantic-settings, теги OpenAPI, кастомный Swagger UI).

| Параметр | Значение |
|----------|----------|
| Порт | 8099 |
| Swagger UI | `http://192.168.0.50:8099/docs` |
| OpenAPI JSON | `http://192.168.0.50:8099/openapi.json` |
| Через VPS | `http://95.163.176.103:8099/docs` (после добавления порта) |
| Docker-образ | `python:3.12-slim` |
| RAM (расчётный) | ~80–100 MB |

### 3.2 Endpoints

| Метод | Путь | Тег | Описание |
|-------|------|-----|----------|
| GET | `/healthcheck` | Служебные | Базовый health-check (Uptime Kuma) |
| GET | `/v1/status` | Служебные | Сводный статус + ссылки на sub-endpoints |
| GET | `/v1/metrics` | Система | CPU, RAM, диск, температура, HTTP сервисов |
| GET | `/v1/containers` | Система | `docker ps -a` с разметкой ожидаемых |
| GET | `/v1/logs` | Логи | Последние N записей лога (с фильтром) |
| POST | `/v1/report/now` | Действия | Ручной запуск Telegram-отчёта (HTTP 202) |

### 3.3 Параметры `/v1/logs`

| Query | Тип | Описание |
|-------|-----|----------|
| `limit` | int 1–500 | Число записей (по умолчанию 100) |
| `level` | enum | Фильтр: DEBUG / INFO / WARNING / ERROR |
| `q` | string | Подстрока в поле `msg` |

Пример — найти все ошибки за последние 500 записей:

```
GET /v1/logs?limit=500&level=ERROR
```

### 3.4 Структура сервиса

```
services/nas_jetson_nano-api/
├── app/
│   ├── main.py            ← FastAPI app, OpenAPI теги, lifespan
│   ├── config.py          ← pydantic-settings (порт, пути, контейнеры)
│   ├── logging_setup.py   ← JSON RotatingFileHandler + stdout handler
│   └── routers/
│       ├── health.py      ← /healthcheck, /v1/status
│       ├── system.py      ← /v1/metrics, /v1/containers
│       ├── logs.py        ← /v1/logs
│       └── actions.py     ← POST /v1/report/now
├── requirements.txt
└── Dockerfile
```

### 3.5 Конфигурация (env)

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `API_LOG_LEVEL` | `INFO` | Уровень логирования |
| `LOG_FILE` | `/var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl` | Путь к файлу |
| `EXPECTED_CONTAINERS` | (список 6 контейнеров) | Ожидаемые имена |
| `LOCAL_SERVICES` | Nextcloud/Immich/LLM GW | URL для HTTP-проверок |

---

## 4. Развёртывание

### 4.1 Сборка и запуск

```bash
cd /home/admin/nas_jetson_nano

# Сборка образа
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml build

# Запуск
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml up -d

# Проверка
curl http://localhost:8099/healthcheck
# → {"status": "ok", "version": "0.1.0", "service": "nas_jetson_nano-api"}
```

### 4.2 Просмотр логов

```bash
# Последние 50 строк через API
curl "http://192.168.0.50:8099/v1/logs?limit=50" | jq .

# Только ошибки
curl "http://192.168.0.50:8099/v1/logs?level=ERROR" | jq .entries[]

# Прямо на хосте (tail -f аналог для JSON-lines)
tail -f /var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(f'{d[\"ts\"]} [{d[\"level\"]}] {d[\"msg\"]}')
"

# Через docker logs (plain text)
docker logs -f homecloud_nas_jetson_nano_api
```

### 4.3 Ручной запуск Telegram-отчёта

```bash
# Через API
curl -X POST http://192.168.0.50:8099/v1/report/now
# → {"accepted": true, "message": "Report dispatched"}

# Результат в логе через ~15 с
curl "http://192.168.0.50:8099/v1/logs?q=report"
```

### 4.4 VPS: добавить порт в UFW и nginx (опционально)

Если нужен внешний доступ к Swagger UI через VPS:

```bash
# На VPS
ufw allow 8099/tcp

# В /opt/nas_jetson_nano/nginx/conf.d/ добавить server block по аналогии с :8080
```

> **Без этого** — API доступен только из LAN (`http://192.168.0.50:8099/docs`).

---

## 5. Разбор ошибок по логам

### Контейнер упал

```bash
curl "http://192.168.0.50:8099/v1/logs?level=WARNING&q=unhealthy"
```

```json
{
  "ts": "2026-06-21T11:23:41Z",
  "level": "WARNING",
  "msg": "unhealthy expected containers: homecloud_uptime_kuma",
  "unhealthy": ["homecloud_uptime_kuma"]
}
```

Действие: `docker start homecloud_uptime_kuma` или `docker compose ... up -d`.

### Высокое использование RAM

```bash
curl "http://192.168.0.50:8099/v1/metrics" | jq .ram
```

```json
{
  "total_mb": 3908,
  "used_mb": 2950,
  "available_mb": 958,
  "used_pct": 75.5
}
```

Если `used_pct > 90` — Jetson близок к OOM. Проверить `docker stats`.

### Туннель отвалился (HTTP-проверка)

```bash
curl "http://192.168.0.50:8099/v1/metrics" | jq .services_http
```

```json
[
  {"service": "Nextcloud", "ok": true, "http_status": 302},
  {"service": "Immich", "ok": false, "http_status": null, "error": "Connection refused"}
]
```

Действие: `systemctl restart nas_jetson_nano-tunnel.service`.

---

## 6. Связанные документы

| Документ | Связь |
|----------|-------|
| `docs/13_MONITORING_RUNBOOK.md` | Runbook ежедневных проверок |
| `docs/17_MONITORING_OBSERVABILITY.md` | Выбор инструментов мониторинга |
| `scripts/monitoring/nas_jetson_nano-daily-report.sh` | Ежедневный отчёт (systemd timer) |
| `docker/compose/docker-compose.monitoring.yml` | Netdata / Uptime Kuma / Portainer |

---
---

## 🇬🇧 English section / Английская секция

---

## 1. Motivation

Without structured logs it is impossible to retroactively diagnose failures:
a container crash, tunnel drop, or disk overflow are only discovered after
the fact. This subsystem addresses three goals:

1. **Event history** — JSON log with rotation on the host, survives container restarts.
2. **Programmatic status access** — REST API with Swagger UI for browser or script diagnostics.
3. **Action audit** — every API request and key system event is recorded.

---

## 2. Logging Architecture

### 2.1 Write paths

```
Event (container down, report sent, API call)
    │
    ▼
nas_jetson_nano-api (FastAPI)
    │
    ├── stdout ──────────────→  docker logs homecloud_nas_jetson_nano_api  (plain text)
    │
    └── RotatingFileHandler ─→  /var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl
        (JSON-lines)               ← volume-mounted on host
```

### 2.2 JSON line format

Each line is a valid JSON (JSON-lines format):

```json
{"ts":"2026-06-21T09:00:01Z","level":"INFO","service":"nas_jetson_nano-api",
 "logger":"nas_jetson_nano_api.system","msg":"metrics polled","ram_used_pct":42.1}
```

### 2.3 Log rotation

| Parameter | Value |
|-----------|-------|
| Max file size | 10 MB |
| Backup count | 5 |
| Total disk footprint | ≤ 60 MB |
| Files | `nas_jetson_nano-api.jsonl`, `nas_jetson_nano-api.jsonl.1` … `.5` |

Rotation is built-in (Python `RotatingFileHandler`). No `logrotate` required.

---

## 3. NAS_Jetson_Nano Status API

### 3.1 Overview

FastAPI service (`services/nas_jetson_nano-api/`) with Swagger UI. Follows patterns from
the `sp_inventory` service (pydantic-settings, OpenAPI tags, custom Swagger UI).

| Parameter | Value |
|-----------|-------|
| Port | 8099 |
| Swagger UI | `http://192.168.0.50:8099/docs` |
| OpenAPI JSON | `http://192.168.0.50:8099/openapi.json` |
| Docker image | `python:3.12-slim` |
| RAM (estimated) | ~80–100 MB |

### 3.2 Endpoints

| Method | Path | Tag | Description |
|--------|------|-----|-------------|
| GET | `/healthcheck` | Служебные | Basic health-check (Uptime Kuma target) |
| GET | `/v1/status` | Служебные | Summary status + sub-endpoint links |
| GET | `/v1/metrics` | Система | CPU, RAM, disk, temperature, HTTP checks |
| GET | `/v1/containers` | Система | `docker ps -a` with expected-container tagging |
| GET | `/v1/logs` | Логи | Last N log entries (filterable) |
| POST | `/v1/report/now` | Действия | Trigger Telegram report immediately (HTTP 202) |

### 3.3 Configuration (env)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_LOG_LEVEL` | `INFO` | Log level |
| `LOG_FILE` | `/var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl` | Log file path |
| `EXPECTED_CONTAINERS` | 6 containers | Space-separated expected names |
| `LOCAL_SERVICES` | Nextcloud/Immich/LLM GW | URLs for HTTP checks |

---

## 4. Deployment

### 4.1 Build and start

```bash
cd /home/admin/nas_jetson_nano
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml build
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml up -d
curl http://localhost:8099/healthcheck
```

### 4.2 View logs

```bash
# Last 50 entries via API
curl "http://192.168.0.50:8099/v1/logs?limit=50" | jq .

# Errors only
curl "http://192.168.0.50:8099/v1/logs?level=ERROR" | jq .entries[]

# Live tail on host
tail -f /var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(f'{d[\"ts\"]} [{d[\"level\"]}] {d[\"msg\"]}')
"
```

---

## 5. Related Documents

| Document | Relation |
|----------|----------|
| `docs/13_MONITORING_RUNBOOK.md` | Daily check runbook |
| `docs/17_MONITORING_OBSERVABILITY.md` | Monitoring tool selection |
| `scripts/monitoring/nas_jetson_nano-daily-report.sh` | Daily Telegram report |
| `docker/compose/docker-compose.monitoring.yml` | Netdata / Uptime Kuma / Portainer |
