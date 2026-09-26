import socket
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers.auth import require_auth

VERSION = "0.1.0"
_START = time.monotonic()

router = APIRouter(tags=["Служебные"])


@router.get(
    "/healthcheck",
    summary="Состояние сервиса",
    description=(
        "Базовая проверка доступности API. "
        "HTTP 200 означает что nas_jetson_nano-api запущен. "
        "Используется load-balancer / Uptime Kuma."
    ),
)
async def healthcheck():
    body = {"status": "ok", "version": VERSION, "service": "nas_jetson_nano-api"}
    if settings.telegram_bot_enabled and settings.telegram_bot_token:
        # Бот живёт в том же процессе: без этого поля глухой бот выглядел «здоровым» (20–26.09).
        from app.telegram_bot import STATUS
        last = STATUS.get("last_ok") or 0
        body["telegram"] = {"state": STATUS.get("state"), "restarts": STATUS.get("restarts", 0),
                            "last_ok_age_s": int(time.time() - last) if last else None}
    return body


@router.get(
    "/v1/status",
    summary="Расширенный статус NAS_Jetson_Nano",
    description=(
        "Возвращает сводный статус: версию, время работы, hostname "
        "и ссылки на sub-endpoints с подробными метриками. **Требует JWT** (C1)."
    ),
    dependencies=[Depends(require_auth)],
)
async def status():
    return JSONResponse(
        content={
            "version": VERSION,
            "status": "ok",
            "hostname": socket.gethostname(),
            "uptime_seconds": int(time.monotonic() - _START),
            "endpoints": {
                "metrics": "/v1/metrics",
                "containers": "/v1/containers",
                "logs": "/v1/logs",
                "report_now": "POST /v1/report/now",
            },
        }
    )
