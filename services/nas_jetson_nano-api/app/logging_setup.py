"""
Structured JSON logging with rotating file output.

Two handlers:
  - stdout (plain text, for `docker logs`)
  - rotating file (JSON-lines, for log analysis)
"""

import json
import logging
import logging.handlers
import time
from pathlib import Path


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": "nas_jetson_nano-api",
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        # Allow callers to attach structured fields via `extra={"fields": {...}}`
        if hasattr(record, "fields") and isinstance(record.fields, dict):
            entry.update(record.fields)
        return json.dumps(entry, ensure_ascii=False)


def setup(log_level: str, log_file: str, max_bytes: int, backup_count: int) -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Console handler — plain text for `docker logs`
    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(process)d] %(name)s %(levelname)s: %(message)s")
    )
    root.addHandler(console)

    # Rotating JSON file handler
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(_JsonFormatter())
    root.addHandler(fh)
