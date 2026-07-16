"""
/v1/actions — Control actions: reports, container management, backups.

Endpoints:
  POST /v1/report/now                       — trigger Telegram report (no auth)
  POST /v1/actions/containers/{name}/restart — restart Docker container (JWT)
  POST /v1/actions/backup/now               — trigger DB backup (JWT)
  GET  /v1/actions/history                  — recent action log entries (JWT)
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.routers.auth import require_auth

log = logging.getLogger("nas_jetson_nano_api.actions")
router = APIRouter(tags=["Действия"])

_SOCKET = "/var/run/docker.sock"


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _docker_post(path: str) -> int:
    """POST to Docker socket, return HTTP status code."""
    if not Path(_SOCKET).exists():
        raise HTTPException(status_code=503, detail="Docker socket not available")
    try:
        transport = httpx.AsyncHTTPTransport(uds=_SOCKET)
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
            r = await client.post(f"http://docker/{path.lstrip('/')}")
        return r.status_code
    except Exception as exc:
        log.error("docker socket error: %s", exc)
        raise HTTPException(status_code=503, detail=f"Docker socket error: {exc}")


# ── Pydantic models ────────────────────────────────────────────────────────────

class RestartResponse(BaseModel):
    accepted: bool
    container: str
    message: str


class BackupResponse(BaseModel):
    accepted: bool
    message: str


class ActionLogEntry(BaseModel):
    ts: str
    level: str
    msg: str
    fields: dict = Field(default_factory=dict)


class ActionHistoryResponse(BaseModel):
    total_returned: int
    entries: list[ActionLogEntry]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/v1/report/now",
    summary="Отправить Telegram-отчёт немедленно",
    description=(
        "Запускает `nas_jetson_nano-send-report-telegram.sh` в фоне. "
        "Возвращает HTTP 202 сразу; фактическая отправка занимает ~10–15 с. "
        "Результат — в `/v1/logs` (уровень INFO/ERROR, logger `nas_jetson_nano_api.actions`). "
        "Авторизация не требуется."
    ),
    status_code=202,
    tags=["Действия"],
)
async def trigger_report():
    async def _run():
        try:
            proc = await asyncio.create_subprocess_exec(
                settings.report_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            output = stdout.decode().strip()
            if proc.returncode == 0:
                log.info(
                    "Telegram report sent on demand",
                    extra={"fields": {"output": output[-200:]}},
                )
            else:
                log.error(
                    "Telegram report failed (rc=%d)", proc.returncode,
                    extra={"fields": {"output": output[-500:]}},
                )
        except asyncio.TimeoutError:
            log.error("Telegram report timed out after 60s")
        except Exception as exc:
            log.error("Telegram report error: %s", exc)

    asyncio.get_event_loop().create_task(_run())
    return JSONResponse(status_code=202, content={"accepted": True, "message": "Report dispatched"})


@router.post(
    "/v1/actions/containers/{name}/restart",
    response_model=RestartResponse,
    summary="Перезапустить Docker-контейнер",
    description=(
        "Перезапускает указанный контейнер через Docker UNIX socket. "
        "Разрешены только контейнеры из whitelist (`RESTARTABLE_CONTAINERS`). "
        "**Требует JWT.** Контейнер продолжает работать — это graceful restart (SIGTERM → SIGKILL). "
        "\n\nДоступные контейнеры:\n"
        "- `homecloud_nextcloud`\n"
        "- `homecloud_immich_server`\n"
        "- `homecloud_immich_microservices`\n"
        "- `homecloud_llm_gateway`\n"
        "- `homecloud_nas_jetson_nano_api`\n"
        "- `homecloud_samba`\n"
        "- `homecloud_netdata`\n"
        "- `homecloud_uptime_kuma`\n"
        "- `homecloud_nextcloud_db` · `homecloud_nextcloud_redis`"
    ),
    status_code=202,
    tags=["Действия"],
)
async def restart_container(
    name: str,
    username: Annotated[str, Depends(require_auth)],
):
    whitelist = set(settings.restartable_containers.split())
    if name not in whitelist:
        raise HTTPException(
            status_code=403,
            detail=f"Container '{name}' is not in the restart whitelist. Allowed: {sorted(whitelist)}",
        )

    log.info(
        "container restart requested by %s: %s", username, name,
        extra={"fields": {"action": "restart", "container": name, "by": username}},
    )

    status_code = await _docker_post(f"containers/{name}/restart?t=10")
    if status_code not in (204, 200):
        raise HTTPException(
            status_code=502,
            detail=f"Docker restart returned HTTP {status_code} for container '{name}'",
        )

    log.info("container restarted: %s", name, extra={"fields": {"action": "restart_ok", "container": name}})
    return RestartResponse(
        accepted=True,
        container=name,
        message=f"Container '{name}' restart initiated (graceful, 10s timeout)",
    )


@router.post(
    "/v1/actions/backup/now",
    response_model=BackupResponse,
    summary="Запустить резервное копирование БД немедленно",
    description=(
        "Запускает `backup_databases.sh` в фоновом режиме (fire-and-forget). "
        "HTTP 202 возвращается сразу. Прогресс и результат — в `/v1/logs`. "
        "**Требует JWT.** Бэкап сохраняется в `/mnt/storage/backups/` на SSD."
    ),
    status_code=202,
    tags=["Действия"],
)
async def trigger_backup(username: Annotated[str, Depends(require_auth)]):
    async def _run():
        try:
            proc = await asyncio.create_subprocess_exec(
                settings.backup_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
            output = stdout.decode().strip()
            if proc.returncode == 0:
                log.info(
                    "on-demand backup completed by %s", username,
                    extra={"fields": {"action": "backup_ok", "by": username, "output": output[-300:]}},
                )
            else:
                log.error(
                    "on-demand backup failed (rc=%d) by %s", proc.returncode, username,
                    extra={"fields": {"action": "backup_fail", "by": username, "output": output[-500:]}},
                )
        except asyncio.TimeoutError:
            log.error("backup timed out (300s) — triggered by %s", username)
        except Exception as exc:
            log.error("backup error: %s (triggered by %s)", exc, username)

    log.info("backup triggered by %s", username, extra={"fields": {"action": "backup_start", "by": username}})
    asyncio.get_event_loop().create_task(_run())
    return BackupResponse(accepted=True, message="Backup started in background. Check /v1/logs for result.")


@router.get(
    "/v1/actions/history",
    response_model=ActionHistoryResponse,
    summary="Журнал последних действий",
    description=(
        "Читает последние записи из JSON-лога, содержащие поле `action` — "
        "т.е. все события: restart, backup, report, notify. "
        "Позволяет увидеть кто и когда запускал управляющие команды. "
        "**Требует JWT.**"
    ),
    tags=["Действия"],
)
async def action_history(
    limit: int = 50,
    _: Annotated[str, Depends(require_auth)] = None,
):
    log_path = Path(settings.log_file)
    if not log_path.exists():
        return ActionHistoryResponse(total_returned=0, entries=[])

    entries: list[ActionLogEntry] = []
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                fields = rec.get("fields", {})
                if "action" not in fields:
                    continue
                entries.append(ActionLogEntry(
                    ts=rec.get("ts", ""),
                    level=rec.get("level", ""),
                    msg=rec.get("msg", ""),
                    fields=fields,
                ))
                if len(entries) >= limit:
                    break
            except json.JSONDecodeError:
                continue
    except OSError as exc:
        log.warning("could not read log file: %s", exc)

    return ActionHistoryResponse(total_returned=len(entries), entries=entries)
