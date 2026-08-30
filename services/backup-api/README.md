# Backup API (Stage 2 placeholder) / Backup API (заготовка Stage 2)

🇷🇺 Минимальный FastAPI-скелет API для будущего Android-клиента семейного облака.

🇬🇧 A minimal FastAPI skeleton for the future Android client of the family cloud.

> 🇷🇺 **Stage 1: НЕ разворачивать на боевом Jetson.** Сервис работает только в
> mock-режиме (`BACKUP_API_ENABLED=0`) и предназначен для:
> - стабилизации API-контракта до Stage 2;
> - локального запуска и unit-тестов;
> - демо/презентаций.
>
> Stage 2 добавит реальную работу с диском, БД и authn — после отдельного RFC.

> 🇬🇧 **Stage 1: do NOT deploy on the production Jetson.** The service runs in
> mock mode only (`BACKUP_API_ENABLED=0`) and is intended for:
> - stabilising the API contract ahead of Stage 2;
> - local runs and unit tests;
> - demos and presentations.
>
> Stage 2 will add real disk, database, and authn work — after a separate RFC.

## Эндпоинты / Endpoints

| Method | Path | Назначение / Purpose |
|---|---|---|
| GET  | `/health` | Состояние и режим (real/mock) / Status and mode (real/mock) |
| POST | `/api/v1/devices/register` | Регистрация устройства, возвращает `device_id` / Device registration, returns `device_id` |
| POST | `/api/v1/backups/create` | Создать бэкап, возвращает `backup_id` + upload URL / Create a backup, returns `backup_id` + upload URL |
| POST | `/api/v1/backups/upload?backup_id=…` | Загрузка файла (multipart) / File upload (multipart) |
| GET  | `/api/v1/backups/list?device_id=…` | Список бэкапов / List of backups |
| POST | `/api/v1/restore/plan` | План восстановления / Restore plan |

🇷🇺 Все эндпоинты, кроме `/health`, требуют `Authorization: Bearer <BACKUP_API_TOKEN>`
(в mock-режиме токен не проверяется).

🇬🇧 Every endpoint except `/health` requires `Authorization: Bearer <BACKUP_API_TOKEN>`
(in mock mode the token is not verified).

## Запуск локально (для разработки) / Running locally (for development)

```bash
cd services/backup-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Mock-режим (по умолчанию) / Mock mode (default)
uvicorn app.main:app --host 127.0.0.1 --port 8095

# Реальный режим (только для Stage 2) / Real mode (Stage 2 only)
export BACKUP_API_ENABLED=1
export BACKUP_API_TOKEN="$(openssl rand -hex 32)"
export BACKUP_API_STORAGE_ROOT=/tmp/backups
uvicorn app.main:app --host 127.0.0.1 --port 8095
```

## Безопасность / Security

🇷🇺

- Не принимать запросы из публичного интернета — только через VPN.
- Не логировать содержимое загружаемых файлов или Bearer-токен.
- Не отправлять во внешние LLM содержимое бэкапов (см. `config/llm-policy.yaml`).

🇬🇧

- Do not accept requests from the public internet — VPN only.
- Do not log the contents of uploaded files or the Bearer token.
- Do not send backup contents to external LLMs (see `config/llm-policy.yaml`).
