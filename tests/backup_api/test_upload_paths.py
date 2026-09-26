"""BK-1: путь загрузки собирается только из проверенных частей (services/backup-api/app/main.py).

История дефекта (аудит 2026-09-26, BK-1): `backup_id` проверялся только на префикс `bk_`,
а имя файла шло в путь как есть — `backup_id=bk_/../../x` и `filename=../../x` писали за
пределы STORAGE_ROOT, `.hidden` и `..` проходили насквозь. Сервис пока не развёрнут
(решение владельца 2026-09-26 — чинить, не удалять), поэтому проверка живёт в тестах.

⚠️ Гонять отдельным процессом: `python -m pytest tests/backup_api -q`.
Оба сервиса (nas_jetson_nano-api и backup-api) владеют одним именем пакета — `app`, и
каждый тест здесь импортирует его заново из своего каталога. Замер 2026-09-26: общий
прогон `pytest tests/nas_api tests/backup_api` тоже дал 192 passed, то есть катастрофы
нет, но устойчивость держится на переимпорте внутри каждого теста, а не на порядке
сбора — поэтому разделять прогоны дешевле, чем однажды разбираться с этим.
"""
from __future__ import annotations

import hashlib
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "services" / "backup-api"
TOKEN = "test-token-bk1"
BODY = b"BACKUP-DATA"
TRAVERSALS = ["../../x", "..\\..\\x", "/etc/passwd"]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """Модуль читает настройки из окружения при импорте — импортируем заново на каждый тест."""
    monkeypatch.setenv("BACKUP_API_ENABLED", "1")
    monkeypatch.setenv("BACKUP_API_TOKEN", TOKEN)
    monkeypatch.setenv("BACKUP_API_STORAGE_ROOT", str(tmp_path / "root"))
    if str(API) in sys.path:
        sys.path.remove(str(API))
    sys.path.insert(0, str(API))
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.main")


@pytest.fixture()
def client(api):
    from fastapi.testclient import TestClient
    with TestClient(api.app, raise_server_exceptions=False) as c:
        yield c


def root_of(api) -> Path:
    return Path(api.STORAGE_ROOT).resolve()


def upload(client, backup_id, filename, data: bytes = BODY, token: str = TOKEN):
    headers = {"Authorization": "Bearer %s" % token} if token else {}
    return client.post("/api/v1/backups/upload", params={"backup_id": backup_id},
                       files={"file": (filename, data)}, headers=headers)


def all_files(base: Path):
    return {p.resolve() for p in base.rglob("*") if p.is_file()} if base.exists() else set()


# ── нормальная загрузка ───────────────────────────────────────────────────────

def test_upload_is_accepted_and_lands_in_backup_dir(client, api):
    r = upload(client, "bk_abc123", "payload.bin")
    assert r.status_code == 202, r.text
    body = r.json()
    target = root_of(api) / "bk_abc123" / "payload.bin"
    assert body["stored"] is True
    assert body["backup_id"] == "bk_abc123"
    assert body["size_bytes"] == len(BODY)
    assert body["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert Path(body["path"]).resolve() == target
    assert target.read_bytes() == BODY
    assert all_files(root_of(api)) == {target}


@pytest.mark.parametrize("name", ["payload.bin", "Photos 2026-09-26.zip", "a" * 100 + ".tar"])
def test_reasonable_names_are_not_over_filtered(client, api, name):
    r = upload(client, "bk_ok", name)
    assert r.status_code == 202, r.text
    assert (root_of(api) / "bk_ok" / name).is_file()


# ── BK-1: обход каталога ──────────────────────────────────────────────────────

@pytest.mark.parametrize("filename", TRAVERSALS)
def test_traversal_filename_stays_inside_backup_dir(client, api, filename):
    """Файл ложится внутрь root/backup_id и только под базовым именем.

    Проверено пробником 2026-09-26: имя из multipart доезжает до `_safe_target` как есть
    (starlette его не чистит), поэтому проверка ловит дефект, а не поведение парсера.
    """
    root = root_of(api)
    backup_dir = root / "bk_ok1"
    expected = backup_dir / Path(filename.replace("\\", "/")).name

    r = upload(client, "bk_ok1", filename)
    assert r.status_code == 202, r.text
    assert Path(r.json()["path"]).resolve() == expected
    assert expected.read_bytes() == BODY
    # за пределы каталога закачки не вышло ничего — ни файла, ни каталога
    assert all_files(root) == {expected}, all_files(root) - {expected}
    for path in root.rglob("*"):
        assert path.resolve().is_relative_to(backup_dir), path


@pytest.mark.parametrize("filename", TRAVERSALS)
def test_safe_target_returns_only_the_basename(api, filename):
    """Проверка на уровне самой функции: не зависит от того, как разберёт имя multipart."""
    out = api._safe_target("bk_ok1", filename)
    assert out.name == Path(filename.replace("\\", "/")).name
    assert out.parent == (root_of(api) / "bk_ok1").resolve()
    assert out.resolve().is_relative_to((root_of(api) / "bk_ok1").resolve())


def test_symlinked_backup_dir_cannot_escape(api, tmp_path):
    """Вторая проверка `out.relative_to(root/backup_id)` — на случай, если имя пройдёт regex.

    Добраться до неё иначе нечем: `..` и «/» отсекает белый список имён. Подменяем каталог
    закачки символической ссылкой — разрешённый путь оказывается вне STORAGE_ROOT, и такой
    путь обязан быть отвергнут, а не записан «куда получилось».
    """
    root = root_of(api)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "bk_link").mkdir(parents=True)
    (root / "bk_link").rmdir()
    try:
        (root / "bk_link").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("символические ссылки недоступны без прав администратора")

    with pytest.raises(api.HTTPException) as exc:
        api._safe_target("bk_link", "payload.bin")
    assert exc.value.status_code == 400
    assert not (outside / "payload.bin").exists()


def test_traversal_is_real_not_theoretical(tmp_path):
    """Прежний код писал ровно по такому выражению — и оно уводило файл вверх по дереву.

    Без этой проверки тест выше ничего не доказывает: имя без «..» вело бы себя так же,
    и на коде ДО BK-1 он проходил бы, не заметив дефекта. Оба выражения ниже — то, что
    получалось из `STORAGE_ROOT / backup_id / filename` до правки.
    """
    root = (tmp_path / "root").resolve()
    # имя файла с «..»: из каталога закачки — на два уровня вверх, за пределы STORAGE_ROOT
    assert (root / "bk_ok1" / "../../x").resolve() == tmp_path / "x"
    # backup_id с «..»: из корня хранилища — тоже наружу
    assert (root / "bk_/../../x" / "payload.bin").resolve() == tmp_path / "x" / "payload.bin"
    for escaped in ((root / "bk_ok1" / "../../x").resolve(),
                    (root / "bk_/../../x").resolve()):
        assert not escaped.is_relative_to(root), escaped


@pytest.mark.parametrize("bad", ["bk_/../../x", "bk_..", "nobk", "bk_", "", "../bk_x"])
def test_bad_backup_id_is_rejected(client, api, bad):
    r = upload(client, bad, "payload.bin")
    assert r.status_code == 400, r.text
    assert all_files(root_of(api)) == set()


@pytest.mark.parametrize("bad", [".hidden", "..", ".", ".payload.part"])
def test_hidden_or_dotted_filename_is_rejected(client, api, bad):
    r = upload(client, "bk_ok1", bad)
    assert r.status_code == 400, r.text
    assert all_files(root_of(api)) == set()


def test_upload_without_token_is_rejected(client, api):
    r = upload(client, "bk_ok1", "payload.bin", token=None)
    assert r.status_code in (401, 403), r.text
    assert all_files(root_of(api)) == set()


def test_upload_with_wrong_token_is_rejected(client, api):
    r = upload(client, "bk_ok1", "payload.bin", token="not-the-token")
    assert r.status_code in (401, 403), r.text
    assert all_files(root_of(api)) == set()


def test_no_part_files_left_behind(client, api):
    """Запись через `.part` + os.replace: после удачной загрузки промежуточных не остаётся."""
    assert upload(client, "bk_ok1", "payload.bin").status_code == 202
    root = root_of(api)
    assert [p for p in root.rglob("*") if ".part" in p.name] == []
