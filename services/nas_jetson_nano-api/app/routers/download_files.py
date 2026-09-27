"""Read-only file delivery for Telegram's short-lived signed links."""
from __future__ import annotations

import html
import urllib.parse
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from app import download_links
from app.config import settings

router = APIRouter(prefix="/downloads", tags=["Downloads"])


def _target(user: str, relative: str) -> tuple[Path, Path]:
    if not user or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in user):
        raise HTTPException(status_code=404, detail="Not found")
    base = Path(settings.dl_hdd_stat_path).resolve()
    raw_root = base / user
    root = raw_root.resolve()
    try:
        root.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    if raw_root.is_symlink():
        raise HTTPException(status_code=404, detail="Not found")
    raw_target = raw_root / relative
    target = raw_target.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    cursor = raw_target
    while cursor != raw_root:
        if cursor.is_symlink():
            raise HTTPException(status_code=404, detail="Not found")
        cursor = cursor.parent
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return root, target


def _authorize(user: str, expires: int | None, sig: str) -> None:
    if expires is None or not download_links.valid_signature(user, expires, sig):
        raise HTTPException(status_code=401, detail="Link expired or invalid")


def _directory_page(root: Path, target: Path, user: str, expires: int, sig: str) -> HTMLResponse:
    items = []
    if target != root:
        parent = target.parent.relative_to(root).as_posix()
        parent_path = "" if parent == "." else parent
        href = f"/downloads/{urllib.parse.quote(user)}/{urllib.parse.quote(parent_path)}?expires={expires}&sig={sig}"
        items.append(f'<li><a href="{html.escape(href, quote=True)}">../</a></li>')
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold())):
        if entry.name.startswith(".") or entry.is_symlink():
            continue
        rel = entry.relative_to(root).as_posix()
        href = f"/downloads/{urllib.parse.quote(user)}/{urllib.parse.quote(rel)}?expires={expires}&sig={sig}"
        label = html.escape(entry.name + ("/" if entry.is_dir() else ""))
        items.append(f'<li><a href="{html.escape(href, quote=True)}">{label}</a></li>')
    body = "<!doctype html><meta charset=utf-8><title>Downloads</title><h1>Downloads</h1><ul>" + "".join(items) + "</ul>"
    return HTMLResponse(body, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})


@router.get("/{user}", include_in_schema=False)
@router.get("/{user}/{relative:path}", include_in_schema=False)
def download(user: str, relative: str = "", expires: int | None = Query(default=None), sig: str = ""):
    _authorize(user, expires, sig)
    root, target = _target(user, relative)
    if target.is_dir():
        return _directory_page(root, target, user, expires, sig)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(target, filename=target.name, headers={"Cache-Control": "private, no-store"})
