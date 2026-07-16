import socket
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

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
    return {"status": "ok", "version": VERSION, "service": "nas_jetson_nano-api"}


@router.get(
    "/v1/status",
    summary="Расширенный статус NAS_Jetson_Nano",
    description=(
        "Возвращает сводный статус: версию, время работы, hostname "
        "и ссылки на sub-endpoints с подробными метриками."
    ),
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
