"""OBS-1, задача 4: клиент Docker-сокета и приведение событий к контракту.

План — docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md (задача 4);
спецификация — docs/superpowers/specs/2026-10-13-blackbox-forensics-design.ru.md.

Подменяемый транспорт (в плане назван только «opener=callable», здесь зафиксирован):

    opener(sock_path, timeout) -> соединение (форма http.client.HTTPConnection)
    соединение: .request(method, path), .getresponse() -> ответ
    ответ: .status, .read() -> bytes; поток /events читается построчно
    (итерация или readline); обрыв потока — исключение из семейства OSError.

Настоящий сокет и сеть в тестах не участвуют — только подставные объекты.
`events()` отдаёт разобранные объекты JSON как есть; приведение к контракту
`event` (source="docker", kind/severity/detail) делает `event_from_docker`.
"""
import json

import pytest

from blackbox.sources.docker_api import DockerClient, event_from_docker

SOCK = "/var/run/docker.sock"
TS = 1791861274  # значение из контракта данных плана (сутки 2026-10-13)
CONTAINER_ID = "0123456789abcdef" * 4  # подставной идентификатор контейнера
NAME = "homecloud_stt"
IMAGE = "homecloud/stt:latest"


class _FakeResponse(object):
    """Ответ с готовым телом (форма http.client.HTTPResponse)."""

    def __init__(self, payload, status=200):
        self.status = status
        self.body = json.dumps(payload).encode("utf-8")
        self._pos = 0

    def getcode(self):
        return self.status

    def read(self, amt=None):
        if amt is None:
            data = self.body[self._pos:]
            self._pos = len(self.body)
        else:
            data = self.body[self._pos:self._pos + amt]
            self._pos += len(data)
        return data

    def readline(self):
        end = self.body.find(b"\n", self._pos)
        if end == -1:
            return self.read()
        end += 1
        data = self.body[self._pos:end]
        self._pos = end
        return data

    def close(self):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line


class _EventStream(object):
    """Ответ /events: поток JSON-объектов по строкам; после последней — обрыв.

    read() намеренно не отдаёт данные: живой поток событий Docker бесконечен,
    читать его целиком нельзя — только построчно.
    """

    def __init__(self, lines):
        self.status = 200
        self._lines = [line.encode("utf-8") + b"\n" for line in lines]

    def getcode(self):
        return self.status

    def readline(self):
        if not self._lines:
            raise ConnectionResetError(10054, "обрыв потока событий Docker")
        return self._lines.pop(0)

    def read(self, *args, **kwargs):
        raise ConnectionResetError(10054, "обрыв потока событий Docker")

    def close(self):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        return self.readline()


class _FakeConnection(object):
    """Соединение подставного транспорта: .request()/.getresponse()."""

    def __init__(self, response):
        self.response = response
        self.requests = []

    def request(self, method, path, *args, **kwargs):
        self.requests.append((method, path))

    def getresponse(self):
        return self.response

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeOpener(object):
    """Подставной транспорт: opener(sock_path, timeout) -> соединение.

    Ответ одноразовый: если opener позвали второй раз, значит клиент
    переподключается сам, чего интерфейс не предполагает (переподключается
    вызывающий), — и тест падает, а не зависает.
    """

    def __init__(self, response):
        self.calls = []
        self.connections = []
        self._responses = [response]

    def __call__(self, sock_path, timeout, **kwargs):
        self.calls.append((sock_path, timeout))
        conn = _FakeConnection(self._responses.pop(0))
        self.connections.append(conn)
        return conn


def _raw_event(action, name=NAME, ts=TS, **attrs):
    """Сырое событие Docker, как из GET /events (Attributes — только строки)."""
    attributes = {"name": name, "image": IMAGE}
    attributes.update(attrs)
    return {"Type": "container", "Action": action,
            "Actor": {"ID": CONTAINER_ID, "Attributes": attributes},
            "time": ts}


def test_containers_maps_names_and_requests_all():
    """Строка таблицы: Names ["/homecloud_stt"] — имя без ведущего слэша."""
    payload = [{"Id": CONTAINER_ID, "Names": ["/" + NAME],
                "Image": IMAGE, "State": "running"}]
    opener = _FakeOpener(_FakeResponse(payload))
    client = DockerClient(SOCK, opener=opener)

    assert client.containers() == [{"id": CONTAINER_ID, "name": NAME,
                                    "image": IMAGE, "state": "running"}]
    assert opener.calls == [(SOCK, 10)]
    assert opener.connections[0].requests == [("GET", "/containers/json?all=1")]


def test_events_yields_three_then_stops_on_break():
    """Строка таблицы: поток из трёх JSON-строк и обрыв — три события, затем
    StopIteration (генератор завершается сам, обрыв наружу не летит)."""
    raws = [_raw_event("start"), _raw_event("die", exitCode="143"),
            _raw_event("restart")]
    stream = _EventStream([json.dumps(raw) for raw in raws])
    opener = _FakeOpener(stream)
    client = DockerClient(SOCK, opener=opener)

    gen = client.events(TS)
    assert next(gen) == raws[0]
    assert next(gen) == raws[1]
    assert next(gen) == raws[2]
    with pytest.raises(StopIteration):
        next(gen)
    assert opener.connections[0].requests == [("GET", "/events?since=%d" % TS)]


def test_event_die_143_is_warn_with_exit_code():
    """Строка таблицы: die с exitCode=143 (строкой, как шлёт Docker) — warn,
    код в detail целым числом."""
    ev = event_from_docker(_raw_event("die", exitCode="143"))
    assert ev["ts"] == TS
    assert ev["source"] == "docker"
    assert ev["kind"] == "die"
    assert ev["subject"] == NAME
    assert ev["severity"] == "warn"
    assert ev["detail"]["exitCode"] == 143
    assert ev["detail"]["image"] == IMAGE


def test_event_oom_is_crit():
    """Строка таблицы: oom — crit."""
    ev = event_from_docker(_raw_event("oom"))
    assert ev["kind"] == "oom"
    assert ev["severity"] == "crit"
    assert ev["subject"] == NAME


def test_event_die_nonzero_is_crit():
    """Интерфейс: die с кодом != 0 и != 143 — crit."""
    ev = event_from_docker(_raw_event("die", exitCode="1"))
    assert ev["kind"] == "die"
    assert ev["severity"] == "crit"
    assert ev["detail"]["exitCode"] == 1


def test_event_die_zero_is_info():
    """Интерфейс: правила crit/warn называют коды != 0 и 143 — die 0 их не
    подпадает, значит info."""
    ev = event_from_docker(_raw_event("die", exitCode="0"))
    assert ev["kind"] == "die"
    assert ev["severity"] == "info"


def test_event_unhealthy_is_warn():
    """Строка таблицы: health_status: unhealthy — kind unhealthy, warn."""
    ev = event_from_docker(_raw_event("health_status: unhealthy"))
    assert ev["kind"] == "unhealthy"
    assert ev["severity"] == "warn"


def test_event_healthy_is_info():
    """Интерфейс: health_status: healthy — в договоре, значит событие, не None."""
    ev = event_from_docker(_raw_event("health_status: healthy"))
    assert ev["kind"] == "healthy"
    assert ev["severity"] == "info"


def test_event_kill_is_warn_with_signal():
    """Интерфейс: kill — warn, сигнал попадает в detail."""
    ev = event_from_docker(_raw_event("kill", signal="9"))
    assert ev["kind"] == "kill"
    assert ev["severity"] == "warn"
    assert str(ev["detail"]["signal"]) == "9"


def test_event_start_stop_restart_are_info():
    """Интерфейс: start/stop/restart — в договоре; ни crit, ни warn им не
    назначены, значит info."""
    for action in ("start", "stop", "restart"):
        ev = event_from_docker(_raw_event(action))
        assert ev["kind"] == action
        assert ev["severity"] == "info"


def test_event_exec_start_is_ignored():
    """Строка таблицы: exec_start — остальное, None."""
    assert event_from_docker(_raw_event("exec_start")) is None


def test_events_skips_malformed_line_without_stopping():
    """Правка круга 1 ревью (ВАЖНОЕ 1): поток «валидная, мусор, валидная» —
    битая строка пропускается, генератор не обрывается ею (обрыв — только
    по настоящему разрыву соединения, см. test_events_yields_three_then_stops_on_break)."""
    raws = [_raw_event("start"), _raw_event("restart")]
    lines = [json.dumps(raws[0]), "это не JSON вовсе {{{", json.dumps(raws[1])]
    stream = _EventStream(lines)
    opener = _FakeOpener(stream)
    client = DockerClient(SOCK, opener=opener)

    gen = client.events(TS)
    assert next(gen) == raws[0]
    assert next(gen) == raws[1]
    with pytest.raises(StopIteration):
        next(gen)
