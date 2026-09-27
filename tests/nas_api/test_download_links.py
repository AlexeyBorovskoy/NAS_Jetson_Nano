"""Signed LAN links used in Telegram completion notifications."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "nas_jetson_nano-api"


def load(tmp_path: Path, monkeypatch):
    for key, value in {
        "JWT_SECRET": "download-test-secret",
        "DOWNLOAD_BASE_URL": "http://192.168.0.50:8099",
        "DOWNLOAD_LINK_TTL_SECONDS": "300",
        "DL_HDD_STAT_PATH": str(tmp_path),
    }.items():
        monkeypatch.setenv(key, value)
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    links = importlib.import_module("app.download_links")
    files = importlib.import_module("app.routers.download_files")
    app = FastAPI()
    app.include_router(files.router)
    return links, TestClient(app)


def test_signed_link_lists_and_downloads_personal_files(tmp_path, monkeypatch):
    folder = tmp_path / "ivan"
    folder.mkdir()
    (folder / "файл с пробелом.txt").write_text("ok", encoding="utf-8")
    links, client = load(tmp_path, monkeypatch)

    url = links.user_url("ivan", now=1000)
    assert url.startswith("http://192.168.0.50:8099/downloads/ivan?")
    # Generate a currently valid URL for the HTTP request.
    url = links.user_url("ivan")
    response = client.get(url)
    assert response.status_code == 200
    assert "файл с пробелом.txt" in response.text

    href = response.text.split('href="', 1)[1].split('"', 1)[0].replace("&amp;", "&")
    downloaded = client.get(href)
    assert downloaded.status_code == 200
    assert downloaded.content == b"ok"
    assert "attachment" in downloaded.headers["content-disposition"]


def test_owner_link_lists_family_folders_but_hides_incomplete(tmp_path, monkeypatch):
    (tmp_path / "ivan").mkdir()
    (tmp_path / ".incomplete").mkdir()
    links, client = load(tmp_path, monkeypatch)

    response = client.get(links.owner_url())
    assert response.status_code == 200
    assert "ivan/" in response.text
    assert ".incomplete" not in response.text


def test_invalid_expired_and_cross_user_links_are_denied(tmp_path, monkeypatch):
    (tmp_path / "ivan").mkdir()
    (tmp_path / "olga").mkdir()
    links, client = load(tmp_path, monkeypatch)
    url = links.user_url("ivan")

    assert client.get(url.replace("sig=", "sig=x")).status_code == 401
    assert client.get(url.replace("/ivan?", "/olga?")).status_code == 401
    assert client.get("/downloads/ivan?expires=1&sig=bad").status_code == 401


def test_traversal_and_symlink_escape_are_denied(tmp_path, monkeypatch):
    folder = tmp_path / "ivan"
    folder.mkdir()
    outside = tmp_path.parent / "private.txt"
    outside.write_text("secret", encoding="utf-8")
    links, client = load(tmp_path, monkeypatch)
    query = links.user_url("ivan").split("?", 1)[1]

    assert client.get(f"/downloads/ivan/%2e%2e/private.txt?{query}").status_code == 404
    try:
        (folder / "escape").symlink_to(outside)
    except OSError:
        return
    assert client.get(f"/downloads/ivan/escape?{query}").status_code == 404
