"""
/v1/logs — tail recent JSON log entries from the rotating log file.
"""

import json
import logging
from collections import deque
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.config import settings

log = logging.getLogger("nas_jetson_nano_api.logs")
router = APIRouter(prefix="/v1", tags=["Логи"])


def _tail_jsonl(path: str, n: int) -> list[dict]:
    """Read last `n` lines from a JSON-lines file without loading the whole file."""
    p = Path(path)
    if not p.exists():
        return []
    lines: deque[str] = deque(maxlen=n)
    try:
        with p.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return []

    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            result.append({"raw": line})
    return result


@router.get(
    "/logs",
    summary="Последние записи лога",
    description=(
        "Возвращает последние `limit` строк из JSON-лога `nas_jetson_nano-api` "
        "(`/var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl`). "
        "Фильтрация по уровню (`level`) и подстроке сообщения (`q`). "
        "Максимум 500 записей за запрос."
    ),
)
async def get_logs(
    limit: int = Query(default=100, ge=1, le=500, description="Число последних записей"),
    level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = Query(
        default=None, description="Фильтр по уровню"
    ),
    q: Optional[str] = Query(default=None, description="Подстрока в поле msg"),
):
    # Read more than needed so we can filter and still return `limit` entries
    raw = _tail_jsonl(settings.log_file, n=limit * 5)

    filtered = raw
    if level:
        filtered = [e for e in filtered if e.get("level") == level]
    if q:
        q_lower = q.lower()
        filtered = [e for e in filtered if q_lower in str(e.get("msg", "")).lower()]

    # Return last `limit` entries after filtering
    filtered = filtered[-limit:]

    return JSONResponse(
        content={
            "total_returned": len(filtered),
            "log_file": settings.log_file,
            "entries": filtered,
        }
    )
