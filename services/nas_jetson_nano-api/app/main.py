import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import logging_setup
from app.config import settings
from app.routers import actions, auth, health, logs, photos, storage, system, talk, talk_bot, users

log = logging.getLogger("nas_jetson_nano_api")

# ---------------------------------------------------------------------------
# OpenAPI tag registry — order = section order in Swagger UI
# ---------------------------------------------------------------------------
OPENAPI_TAGS = [
    {
        "name": "Служебные",
        "description": "Базовый healthcheck и сводный статус сервиса.",
    },
    {
        "name": "Авторизация",
        "description": (
            "JWT-авторизация через Nextcloud OCS. "
            "`POST /api/auth/login` → Bearer token → используй в **Authorize 🔒** выше. "
            "Логин/пароль — те же что в Nextcloud."
        ),
    },
    {
        "name": "Система",
        "description": (
            "Метрики Jetson Nano: CPU load, RAM, диск, температурные зоны. "
            "Статус Docker-контейнеров (`docker ps -a`)."
        ),
    },
    {
        "name": "Хранилище",
        "description": (
            "Статус SSD `/mnt/storage`: смонтирован ли, использование, "
            "наличие и возраст резервных копий БД. **Требует JWT.**"
        ),
    },
    {
        "name": "Talk — Чат",
        "description": (
            "Интеграция с Nextcloud Talk: список комнат, участники, "
            "отправка сообщений в семейный чат. "
            "`POST /v1/talk/notify` — отправить алерт или уведомление в группу «Семья». "
            "Использует OCS Talk API v4 с admin-правами. "
            "`POST /v1/talk/notify` **требует JWT.**"
        ),
    },
    {
        "name": "Пользователи",
        "description": (
            "Управление семейными аккаунтами через Nextcloud OCS API: "
            "список пользователей, использование диска, время последнего входа. "
            "`POST /v1/users/{username}/notify` — личное сообщение в Talk. "
            "**Все эндпоинты требуют JWT.**"
        ),
    },
    {
        "name": "Фото — Immich",
        "description": (
            "Статистика семейного фотоархива Immich: "
            "количество фото/видео, альбомы, занятое место — по серверу и по каждому пользователю. "
            "Требует переменной `IMMICH_API_KEY` в конфигурации. "
            "**Все эндпоинты требуют JWT.**"
        ),
    },
    {
        "name": "Логи",
        "description": (
            "Чтение последних записей структурированного JSON-лога "
            "(`/var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl`). "
            "Поддерживает фильтрацию по уровню и подстроке."
        ),
    },
    {
        "name": "Действия",
        "description": (
            "Управляющие действия: Telegram-отчёт, перезапуск контейнеров, резервное копирование, "
            "журнал действий. "
            "Опасные действия (restart, backup) **требуют JWT.** "
            "Все действия fire-and-forget (HTTP 202) кроме `GET /v1/actions/history`."
        ),
    },
]

OPENAPI_DESCRIPTION = """\
## NAS_Jetson_Nano — Status & Control API

Сервис мониторинга и управления домашним облаком на базе Jetson Nano.

### Авторизация

Часть эндпоинтов защищена JWT (🔒). Порядок:
1. `POST /api/auth/login` — введи Nextcloud-логин и пароль → получи `access_token`
2. Нажми кнопку **Authorize 🔒** вверху страницы → вставь токен
3. Защищённые эндпоинты станут доступны

### Что доступно

| Группа | Эндпоинты | Auth |
|--------|-----------|------|
| Система | RAM, CPU, диск, температура, контейнеры | — |
| Хранилище | SSD статус, бэкапы | 🔒 |
| Talk | Комнаты, участники, отправка сообщений | частично 🔒 |
| Пользователи | Список, детали, личные DM | 🔒 |
| Фото | Статистика Immich по серверу и пользователям | 🔒 |
| Действия | Restart контейнера, бэкап, Telegram-отчёт | частично 🔒 |
| Логи | Последние записи лога с фильтрами | — |

### Внешний доступ

`http://193.8.215.130:8099/docs`

### Версия

| Версия | Что добавлено |
|--------|---------------|
| v0.1.0 | health, status |
| v0.2.0 | auth, metrics, containers, storage, logs, report |
| v0.3.0 | **Talk: rooms, notify** |
| v0.4.0 | **Actions: container restart, backup** |
| v0.5.0 | **Users: list, detail, DM notify** |
| v0.6.0 | **Photos: Immich stats** |
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging_setup.setup(
        log_level=settings.api_log_level,
        log_file=settings.log_file,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )
    log.info("nas_jetson_nano-api starting", extra={"fields": {"port": settings.api_port}})

    bot_task: asyncio.Task | None = None
    if settings.talk_bot_enabled:
        bot_task = asyncio.create_task(talk_bot.run_bot_loop())
        log.info(
            "Talk bot enabled",
            extra={"fields": {"room": settings.talk_bot_room or settings.talk_family_room}},
        )

    yield

    if bot_task is not None:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
    log.info("nas_jetson_nano-api stopped")


app = FastAPI(
    lifespan=lifespan,
    title="NAS_Jetson_Nano — Status & Control API",
    version="0.6.0",
    description=OPENAPI_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    contact={
        "name": "NAS_Jetson_Nano",
        "url": "https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano",
    },
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 1,
        "docExpansion": "list",
        "filter": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(system.router)
app.include_router(storage.router)
app.include_router(talk.router)
app.include_router(talk_bot.router)
app.include_router(users.router)
app.include_router(photos.router)
app.include_router(logs.router)
app.include_router(actions.router)
