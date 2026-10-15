"""Клиент сокета Docker: список контейнеров, поток событий (OBS-1, задача 4,
спецификация §4.1, циклы events/logs).

Без процесса `docker` и без сторонних библиотек: HTTP поверх unix-сокета
(`socket` + `http.client`). Транспорт подменяется параметром `opener` —
`opener(sock_path, timeout) -> соединение` (форма `http.client.HTTPConnection`:
`.request(method, path)`, `.getresponse()`); так тесты не открывают настоящий
сокет (`tests/blackbox/test_docker_api.py`, раздел-docstring там же — полный
контракт подставного транспорта).

На Windows `socket.AF_UNIX` может не существовать вовсе — импорт модуля не
должен падать; ошибка возможна только при реальной попытке подключиться
(раздел задания: "используй getattr(socket, 'AF_UNIX', None)").

Python 3.6 (хост Jetson): только стандартная библиотека, без f-строк с `=`,
без `dataclasses`, без `:=`.
"""
import http.client
import json
import socket


class _UnixSocketConnection(http.client.HTTPConnection):
    """HTTP-соединение поверх AF_UNIX сокета Docker (транспорт по умолчанию)."""

    def __init__(self, sock_path, timeout):
        http.client.HTTPConnection.__init__(self, "localhost", timeout=timeout)
        self._sock_path = sock_path

    def connect(self):
        family = getattr(socket, "AF_UNIX", None)
        if family is None:
            raise OSError("AF_UNIX недоступен на этой платформе")
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self._sock_path)
        self.sock = sock


def _default_opener(sock_path, timeout):
    """Транспорт по умолчанию: соединение `http.client` поверх AF_UNIX."""
    return _UnixSocketConnection(sock_path, timeout)


def _map_container(item):
    """Строка `GET /containers/json` -> {"id","name","image","state"}; имя без `/`."""
    names = item.get("Names") or []
    name = names[0].lstrip("/") if names else ""
    return {"id": item.get("Id"), "name": name,
            "image": item.get("Image"), "state": item.get("State")}


class DockerClient(object):
    """Клиент сокета Docker (раздел 4.1): список контейнеров и поток событий.

    `opener` подменяет транспорт целиком — только для тестов; по умолчанию
    используется настоящий unix-сокет `_default_opener`.
    """

    def __init__(self, sock_path, timeout=10, opener=None):
        self.sock_path = sock_path
        self.timeout = timeout
        self._opener = opener if opener is not None else _default_opener

    def _request(self, method, path):
        conn = self._opener(self.sock_path, self.timeout)
        conn.request(method, path)
        return conn, conn.getresponse()

    def containers(self):
        """[{"id","name","image","state"}, ...] (`GET /containers/json?all=1`)."""
        conn, response = self._request("GET", "/containers/json?all=1")
        try:
            payload = json.loads(response.read())
        finally:
            conn.close()
        return [_map_container(item) for item in payload]

    def events(self, since_ts):
        """Генератор событий `GET /events?since=<since_ts>` — построчный JSON.

        Обрыв соединения (исключение семейства `OSError`) -> генератор
        завершается сам (`StopIteration`), наружу ничего не летит;
        переподключение — дело вызывающего (раздел задания).
        """
        conn, response = self._request("GET", "/events?since=%d" % since_ts)
        try:
            for raw_line in response:
                line = raw_line.strip()
                if not line:
                    continue
                yield json.loads(line)
        except OSError:
            return
        finally:
            conn.close()


# ── event_from_docker: сырое событие Docker -> контракт event ──────────────

#: Действия Docker, которые становятся событием как есть (kind == action).
_PLAIN_ACTIONS = ("die", "oom", "kill", "stop", "start", "restart")


def _kind_from_action(action):
    """`Action` сырого события -> `kind` контракта, либо `None` (не в списке)."""
    if action in _PLAIN_ACTIONS:
        return action
    if action == "health_status: unhealthy":
        return "unhealthy"
    if action == "health_status: healthy":
        return "healthy"
    return None


def _detail_from_attrs(attrs):
    """`Actor.Attributes` -> `detail` контракта (`image`, `exitCode`, `signal`)."""
    detail = {}
    if "image" in attrs:
        detail["image"] = attrs["image"]
    if "exitCode" in attrs:
        detail["exitCode"] = int(attrs["exitCode"])
    if "signal" in attrs:
        detail["signal"] = attrs["signal"]
    return detail


def _severity_for(kind, detail):
    """Таблица случаев задания: `oom`/`die`(!=0,143) -> crit; unhealthy/kill/die(143) -> warn."""
    if kind == "oom":
        return "crit"
    if kind == "die":
        exit_code = detail.get("exitCode")
        if exit_code not in (0, 143):
            return "crit"
        return "warn" if exit_code == 143 else "info"
    if kind in ("unhealthy", "kill"):
        return "warn"
    return "info"


def event_from_docker(raw):
    """Сырое событие `GET /events` -> контракт `event`, либо `None`.

    `None` — для действий вне списка (`exec_start` и прочие служебные).
    """
    kind = _kind_from_action(raw.get("Action", ""))
    if kind is None:
        return None
    actor = raw.get("Actor") or {}
    attrs = actor.get("Attributes") or {}
    detail = _detail_from_attrs(attrs)
    return {
        "ts": raw.get("time"),
        "source": "docker",
        "kind": kind,
        "subject": attrs.get("name"),
        "severity": _severity_for(kind, detail),
        "detail": detail,
    }
