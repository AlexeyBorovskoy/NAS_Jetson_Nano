"""Хуки aria2 (`services/downloads/on_complete.sh`, `on_stop.sh`) — проверка запуском.

Решение владельца 2026-09-26: недокачанное лежит в `.incomplete/.u/<логин>/`, готовое
хук переносит в `Downloads/<логин>/`. Старый путь без `.u` обязан работать по-старому,
а путь с «..» — игнорироваться (иначе хук вынес бы чужой файл из архива на HDD).
Без bash (например, чистая Windows-машина) проверки пропускаются — не зеленеют молча.
Run: python -m pytest tests/nas_api -q
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "services" / "downloads"
BASH = shutil.which("bash")
LOGIN = "ivan"

pytestmark = pytest.mark.skipif(BASH is None, reason="bash недоступен — хуки не запускаются")


def run_hook(name: str, args: list, env: dict):
    """Запуск хука так же, как его зовёт aria2: bash <хук> GID ЧИСЛО_ФАЙЛОВ ПУТЬ."""
    return subprocess.run([BASH, str(HOOKS / name), *args], capture_output=True, text=True,
                          env={**os.environ, **env})


def layout(tmp_path: Path):
    """Раскладка контейнера downloads: корень HDD, .incomplete и готовое рядом."""
    return tmp_path / "hdd" / ".incomplete", tmp_path / "final"


def env_for(tmp_path: Path) -> dict:
    # Пути — в POSIX-виде: хук сравнивает их как строки с префиксом корня.
    (tmp_path / "final").mkdir(parents=True, exist_ok=True)
    return {"DL_SSD_INCOMPLETE": (tmp_path / "ssd" / ".incomplete").as_posix(),
            "DL_HDD_INCOMPLETE": (tmp_path / "hdd" / ".incomplete").as_posix(),
            "DL_FINAL": (tmp_path / "final").as_posix()}


def user_download(inc: Path, name: str = "Movie") -> Path:
    """Недокачанный торрент в папке человека: .incomplete/.u/<логин>/<имя>/."""
    src = inc / ".u" / LOGIN / name
    src.mkdir(parents=True, exist_ok=True)
    (src / "a.mkv").write_bytes(b"film")
    return src


# ── on_complete.sh: готовое переезжает к человеку ─────────────────────────────

def test_on_complete_moves_user_folder_to_personal_folder(tmp_path):
    inc, final = layout(tmp_path)
    src = user_download(inc)
    r = run_hook("on_complete.sh", ["g1", "1", src.as_posix()], env_for(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (final / LOGIN / "Movie" / "a.mkv").read_bytes() == b"film"
    assert not src.exists()
    # .u — служебная папка: в готовом Downloads её быть не должно
    assert not (final / ".u").exists()


def test_on_complete_moves_single_file_to_personal_folder(tmp_path):
    inc, final = layout(tmp_path)
    (inc / ".u" / LOGIN).mkdir(parents=True)
    src = inc / ".u" / LOGIN / "a.iso"
    src.write_bytes(b"iso")
    r = run_hook("on_complete.sh", ["g2", "1", src.as_posix()], env_for(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (final / LOGIN / "a.iso").read_bytes() == b"iso"
    assert not src.exists()


def test_on_complete_keeps_old_path_without_user_folder(tmp_path):
    # Закачки, поставленные до 2026-09-26, лежат прямо в .incomplete — перенос
    # обязан работать по-старому, в корень готового.
    inc, final = layout(tmp_path)
    src = inc / "Old"
    src.mkdir(parents=True)
    (src / "a.mkv").write_bytes(b"old")
    r = run_hook("on_complete.sh", ["g3", "1", src.as_posix()], env_for(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (final / "Old" / "a.mkv").read_bytes() == b"old"
    assert not src.exists()


def test_on_complete_ignores_dotdot_escape(tmp_path):
    # «…/.incomplete/../secret/Movie» — путь вне корня закачек: хук обязан промолчать.
    inc, final = layout(tmp_path)
    decoy = tmp_path / "hdd" / "secret" / "Movie"
    decoy.mkdir(parents=True)
    (decoy / "keep.mkv").write_bytes(b"secret")
    path = (inc / ".." / "secret" / "Movie").as_posix()
    r = run_hook("on_complete.sh", ["g4", "1", path], env_for(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (decoy / "keep.mkv").read_bytes() == b"secret"
    assert list(final.iterdir()) == []


def test_on_complete_ignores_path_outside_roots(tmp_path):
    inc, final = layout(tmp_path)
    outside = tmp_path / "elsewhere" / "Movie"
    outside.mkdir(parents=True)
    (outside / "x.mkv").write_bytes(b"x")
    r = run_hook("on_complete.sh", ["g5", "1", outside.as_posix()], env_for(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (outside / "x.mkv").exists()
    assert list(final.iterdir()) == []


# ── on_stop.sh: отменённое удаляется, прерванное остаётся ─────────────────────

def fake_wget(tmp_path: Path, status: str) -> str:
    """Подмена wget для ответа RPC: хук спрашивает настоящий статус закачки."""
    path = tmp_path / ("wget-%s.sh" % status)
    path.write_text('#!/bin/bash\necho \'{"jsonrpc":"2.0","id":"stop","result":{"status":"%s"}}\'\n'
                    % status, encoding="utf-8")
    path.chmod(0o755)
    # Только путь: хук раскрывает $DL_WGET без кавычек, и «C:\Program Files\...bash.exe скрипт»
    # рвался на пробеле — статус пустел, и тест «unknown → ничего не удаляем» проходил вхолостую.
    return path.as_posix()


def stop_env(tmp_path: Path, status: str) -> dict:
    conf = tmp_path / "aria2.conf"
    conf.write_text("rpc-secret=ABC\n", encoding="utf-8")
    return {**env_for(tmp_path), "ARIA2_CONF": conf.as_posix(),
            "DL_WGET": fake_wget(tmp_path, status)}


def test_on_stop_removes_cancelled_user_download(tmp_path):
    inc, _ = layout(tmp_path)
    src = user_download(inc)
    ctl = inc / ".u" / LOGIN / "Movie.aria2"
    ctl.write_bytes(b"control")
    r = run_hook("on_stop.sh", ["g6", "1", src.as_posix()], stop_env(tmp_path, "removed"))
    assert r.returncode == 0, r.stderr
    assert not src.exists()
    assert not ctl.exists()


def test_on_stop_keeps_download_whose_status_is_unknown(tmp_path):
    # И3: aria2 зовёт хук и для прерванных закачек (остановка контейнера) — без
    # подтверждённого removed/error не удаляем ничего.
    inc, _ = layout(tmp_path)
    src = user_download(inc)
    r = run_hook("on_stop.sh", ["g7", "1", src.as_posix()], stop_env(tmp_path, "active"))
    assert r.returncode == 0, r.stderr
    assert (src / "a.mkv").read_bytes() == b"film"


def test_on_stop_ignores_dotdot_escape(tmp_path):
    inc, _ = layout(tmp_path)
    decoy = tmp_path / "hdd" / "secret" / "Movie"
    decoy.mkdir(parents=True)
    (decoy / "keep.mkv").write_bytes(b"secret")
    path = (inc / ".." / "secret" / "Movie").as_posix()
    r = run_hook("on_stop.sh", ["g8", "1", path], stop_env(tmp_path, "removed"))
    assert r.returncode == 0, r.stderr
    assert (decoy / "keep.mkv").read_bytes() == b"secret"
