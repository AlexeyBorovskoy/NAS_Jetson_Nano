"""Тесты services/stt/stt_server.py — голосовые сообщения семьи (E10). Без сети, без Vosk.

История, из которой выросли эти проверки:
* `vosk` — нативный модуль, в тестовой среде его нет. Подменяется фейком в `sys.modules`
  ДО импорта сервиса: `Model`, `KaldiRecognizer` (AcceptWaveform/FinalResult), `SetLogLevel`.
* `opusdec` — внешняя программа. `subprocess.run` подменяется функцией, которая пишет в dst
  настоящий WAV через `wave`: проверяется вся арифметика `decode_ogg` (частота, каналы,
  ширина сэмпла), а не заглушка.
* 2026-09-20: два тяжёлых процесса на двух ядрах положили Jetson целиком — отсюда лимиты
  и «одно распознавание за раз». Поэтому проверяется, что отказ приходит ДО запуска
  opusdec и до распознавания, а не после.
* Приватность: в группе распознаётся каждое голосовое, и почти все адресованы не боту,
  поэтому текст в журнал не пишется НИКОГДА — только длительность и число символов.
  Правило тихо отменят первой же правкой, если его не проверять отдельным тестом.
* Один плохой запрос не должен ронять сервис: исключение внутри распознавания — это 500,
  и следующий запрос обязан обслужиться.

Код сервиса этими тестами не меняется.
Run: python -m pytest tests/stt -q
"""
from __future__ import annotations

import http.client
import json
import logging
import os
import struct
import subprocess
import sys
import threading
import types
import wave
from http.server import HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICE_DIR = ROOT / "services" / "stt"
RATE = 16000
TEXT = "кофе-пароль-42"  # заведомо узнаваемая строка: её не должно быть в журнале


# ── фейковый vosk: подставляется до импорта сервиса ───────────────────────────

class FakeModel:
    """Заглушка `vosk.Model`: поведение задаёт тест, счётчики — то, что проверяем."""

    def __init__(self, text: str = "", boom: bool = False):
        self.text = text
        self.boom = boom
        self.recognizers = 0
        self.last = None

    def __repr__(self):  # удобнее в отчёте о падении, чем адрес объекта
        return "FakeModel(text=%r, boom=%s)" % (self.text, self.boom)


class FakeKaldiRecognizer:
    """Заглушка распознавателя: складывает куски в один буфер, как настоящий Vosk."""

    def __init__(self, model: FakeModel, rate: int):
        self.model = model
        self.rate = rate
        self.audio = b""
        model.recognizers += 1
        model.last = self

    def AcceptWaveform(self, data: bytes) -> bool:
        if self.model.boom:
            raise RuntimeError("распознавание сломалось")  # не SttError: сервис обязан ответить 500 и выжить
        self.audio += data
        return False

    def FinalResult(self) -> str:
        return json.dumps({"text": self.model.text}, ensure_ascii=False)


def _install_fake_vosk() -> None:
    fake = types.ModuleType("vosk")
    fake.Model = FakeModel
    fake.KaldiRecognizer = FakeKaldiRecognizer
    fake.SetLogLevel = lambda level: None
    sys.modules["vosk"] = fake


_install_fake_vosk()
sys.path.insert(0, str(SERVICE_DIR))
import stt_server  # noqa: E402  — импорт намеренно после подмены vosk


# ── подмена opusdec: пишем в dst настоящий WAV ────────────────────────────────

def pcm_bytes(seconds: float, channels: int = 1, sample: int = 100) -> bytes:
    """PCM 16 бит: `frames` сэмплов на канал."""
    return struct.pack("<h", sample) * int(seconds * RATE) * channels


def write_wav(path: str, frames: bytes, rate: int = RATE, channels: int = 1, sampwidth: int = 2) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(frames)


def fake_opusdec(monkeypatch, frames: bytes = None, *, seconds: float = 0.1, channels: int = 1,
                 rate: int = RATE, sampwidth: int = 2, exc: Exception = None, seen: list = None):
    """Подмена `subprocess.run` внутри stt_server: вместо opusdec пишем в dst настоящий WAV."""
    def run(argv, **kwargs):
        with open(argv[-2], "rb") as fh:  # вход, который сервис отдал бы opusdec
            src = fh.read()
        if seen is not None:
            seen.append({"argv": list(argv), "kwargs": kwargs, "src": src})
        if exc is not None:
            raise exc
        write_wav(argv[-1], frames if frames is not None else pcm_bytes(seconds, channels),
                  rate=rate, channels=channels, sampwidth=sampwidth)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(stt_server.subprocess, "run", run)
    return run


# ── HTTP: настоящий Handler на свободном порту 127.0.0.1 ──────────────────────

@pytest.fixture
def http_server():
    """Настоящий HTTPServer в потоке. Останавливается всегда — иначе поток переживёт тест."""
    srv = HTTPServer(("127.0.0.1", 0), stt_server.Handler)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


@pytest.fixture
def model(monkeypatch):
    fake = FakeModel(text=TEXT)
    monkeypatch.setattr(stt_server.Handler, "model", fake)
    return fake


def request(srv, method: str, path: str, body: bytes = None):
    """Один запрос на своё соединение: сервер отвечает по HTTP/1.0 и закрывает его."""
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    try:
        conn.request(method, path, body=body)
        resp = conn.getresponse()
        return resp.status, json.loads(resp.read().decode("utf-8"))
    finally:
        conn.close()


def request_over_limit(srv, path: str = "/stt", length: int = None):
    """Отправляем только заголовок: заявленный размер больше лимита, тело не идёт вовсе.

    Сервис обязан отказать по одному числу из заголовка — то есть не читать мегабайты
    в память и не декодировать их. Отправлять тело вслед за заголовком нельзя: сервис
    закрывает соединение, не дочитав его, и на Windows клиент получает RST вместо
    ответа (проверено — падение теста именно на этом, а не на коде сервиса).
    """
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    try:
        conn.putrequest("POST", path)
        conn.putheader("Content-Length", str(length if length is not None else stt_server.MAX_BYTES + 1))
        conn.endheaders()
        resp = conn.getresponse()
        return resp.status, json.loads(resp.read().decode("utf-8"))
    finally:
        conn.close()


# ── decode_ogg ────────────────────────────────────────────────────────────────

def test_decode_ogg_returns_mono_pcm_of_expected_length(monkeypatch):
    # 0.1 с при 16 кГц 16 бит = 1600 сэмплов = 3200 байт
    fake_opusdec(monkeypatch, seconds=0.1)
    assert len(stt_server.decode_ogg(b"ogg")) == 3200


def test_decode_ogg_calls_opusdec_with_16k_and_no_stdin(monkeypatch):
    seen = []
    fake_opusdec(monkeypatch, seconds=0.1, seen=seen)
    stt_server.decode_ogg(b"OGGDATA")
    call = seen[0]
    assert call["argv"][0] == "opusdec"
    assert call["argv"][call["argv"].index("--rate") + 1] == "16000"
    assert call["argv"][-2].endswith(".ogg") and call["argv"][-1].endswith(".wav")
    assert call["src"] == b"OGGDATA"  # opusdec получает ровно то, что пришло в теле
    # stdin закрыт: opusdec, как и ffmpeg, иначе съедает stdin вместе с остатком обработчика
    assert call["kwargs"]["stdin"] is subprocess.DEVNULL
    assert call["kwargs"]["timeout"] == stt_server.DECODE_TIMEOUT


def test_decode_ogg_takes_left_channel_from_stereo(monkeypatch):
    # Стерео 0.1 с: 3200 сэмплов = 6400 байт, левый канал = 1000, правый = 2000
    frames = struct.pack("<hh", 1000, 2000) * int(0.1 * RATE)
    fake_opusdec(monkeypatch, frames=frames, channels=2)
    pcm = stt_server.decode_ogg(b"ogg")
    assert len(pcm) == 3200  # вдвое меньше исходного: голосовые моно, лишний канал выброшен
    assert set(struct.unpack("<%dh" % (len(pcm) // 2), pcm)) == {1000}


def test_decode_ogg_rejects_unexpected_rate(monkeypatch):
    fake_opusdec(monkeypatch, seconds=0.1, rate=8000)
    with pytest.raises(stt_server.SttError) as exc:
        stt_server.decode_ogg(b"ogg")
    assert exc.value.code == 422


def test_decode_ogg_rejects_8_bit_samples(monkeypatch):
    # Vosk ждёт 16 бит; 8-битный WAV прошёл бы дальше и дал бы мусор вместо текста
    fake_opusdec(monkeypatch, frames=b"\x80" * 1600, sampwidth=1)
    with pytest.raises(stt_server.SttError) as exc:
        stt_server.decode_ogg(b"ogg")
    assert exc.value.code == 422


def test_decode_ogg_rejects_more_than_two_channels(monkeypatch):
    fake_opusdec(monkeypatch, frames=pcm_bytes(0.01, channels=3), channels=3)
    with pytest.raises(stt_server.SttError) as exc:
        stt_server.decode_ogg(b"ogg")
    assert exc.value.code == 422


@pytest.mark.parametrize("fail", [
    subprocess.CalledProcessError(1, "opusdec"),          # opusdec вернул ненулевой код
    subprocess.TimeoutExpired("opusdec", stt_server.DECODE_TIMEOUT),  # завис
    FileNotFoundError("opusdec"),                          # не установлен / нет в PATH
])
def test_decode_ogg_reports_422_when_opusdec_fails(monkeypatch, fail):
    fake_opusdec(monkeypatch, exc=fail)
    with pytest.raises(stt_server.SttError) as exc:
        stt_server.decode_ogg(b"ogg")
    assert exc.value.code == 422


# ── HTTP: /health, /stt, отказы ───────────────────────────────────────────────

def test_health_returns_model_name(http_server):
    status, body = request(http_server, "GET", "/health")
    assert status == 200
    assert body == {"status": "ok", "model": os.path.basename(stt_server.MODEL_DIR)}


def test_stt_returns_recognized_text_and_duration(http_server, model, monkeypatch):
    seen = []
    fake_opusdec(monkeypatch, seconds=1.0, seen=seen)
    status, body = request(http_server, "POST", "/stt", body=b"OGGDATA")
    assert status == 200
    assert body == {"text": TEXT, "seconds": 1.0}
    assert seen[0]["src"] == b"OGGDATA"      # в декодер ушло именно тело запроса
    assert model.recognizers == 1
    assert len(model.last.audio) == RATE * 2  # в распознавание ушли все 32 000 байт, ничего не потеряно


def test_stt_rejects_empty_body(http_server, model, monkeypatch):
    seen = []
    fake_opusdec(monkeypatch, seen=seen)
    status, body = request(http_server, "POST", "/stt", body=b"")
    assert status == 413
    assert "error" in body
    assert seen == [] and model.recognizers == 0  # отказ раньше, чем запущен opusdec


def test_stt_rejects_body_over_max_bytes(http_server, model, monkeypatch):
    # Заявлено MAX_BYTES + 1 — настоящего лимита, без подмены константы
    seen = []
    fake_opusdec(monkeypatch, seen=seen)
    status, body = request_over_limit(http_server)
    assert status == 413
    assert "error" in body
    assert seen == [] and model.recognizers == 0  # opusdec не запущен: тело даже не читалось


def test_stt_rejects_audio_longer_than_max_seconds(http_server, model, monkeypatch):
    monkeypatch.setattr(stt_server, "MAX_SECONDS", 0.5)
    seen = []
    fake_opusdec(monkeypatch, seconds=1.0, seen=seen)
    status, _ = request(http_server, "POST", "/stt", body=b"OGGDATA")
    assert status == 413
    assert len(seen) == 1          # раскодировали — иначе длительность неизвестна
    assert model.recognizers == 0  # а распознавать не стали


def test_unknown_path_returns_404(http_server):
    assert request(http_server, "GET", "/nope")[0] == 404
    assert request(http_server, "POST", "/nope", body=b"x")[0] == 404


def test_recognizer_failure_returns_500_and_server_survives(http_server, monkeypatch):
    monkeypatch.setattr(stt_server.Handler, "model", FakeModel(boom=True))
    fake_opusdec(monkeypatch, seconds=1.0)
    status, body = request(http_server, "POST", "/stt", body=b"OGGDATA")
    assert status == 500
    assert body == {"error": "внутренняя ошибка"}  # наружу — без текста исключения
    # один плохой запрос не роняет сервис: следующий обслуживается как обычно
    monkeypatch.setattr(stt_server.Handler, "model", FakeModel(text="жив"))
    assert request(http_server, "POST", "/stt", body=b"OGGDATA") == (200, {"text": "жив", "seconds": 1.0})


# ── журнал: текст не покидает сервис ──────────────────────────────────────────

def test_log_keeps_numbers_only_without_recognized_text(http_server, model, monkeypatch, caplog):
    fake_opusdec(monkeypatch, seconds=1.0)
    with caplog.at_level(logging.INFO, logger="stt"):
        assert request(http_server, "POST", "/stt", body=b"OGGDATA")[0] == 200
    entries = [r.getMessage() for r in caplog.records if r.name == "stt"]
    assert entries, "успешное распознавание обязано оставить запись в журнале"
    assert any("распознано" in m for m in entries)
    assert TEXT not in caplog.text  # ни в тексте, ни в %s-аргументах: в журнале только числа
    assert all(TEXT not in str(r.args) for r in caplog.records if r.name == "stt")
