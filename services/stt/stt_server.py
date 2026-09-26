"""homecloud_stt — распознавание голосовых сообщений семьи (E10), только дома.

Спецификация: docs/superpowers/specs/2026-09-20-voice-messages-design.md.
Движок — Vosk small-ru (замер на Jetson 2026-09-20: WER 17 % против 62 % у whisper tiny).

POST /stt  — тело: OGG/Opus (голосовое Telegram), ответ: {"text": "...", "seconds": N}
GET  /health

Намеренно простой однопоточный HTTPServer: запросы обслуживаются строго по одному —
это и есть требование «одно распознавание за раз» (инцидент 2026-09-20: два тяжёлых
процесса на двух ядрах кладут систему целиком). Остальные ждут в очереди сокета.

Текст распознанного НЕ пишется в журнал никогда — только длительность и время работы:
в группе распознаётся каждое голосовое, и почти все они адресованы не боту.
Порт не публикуется наружу — сервис доступен только из внутренней сети Docker.
"""
import json
import logging
import os
import subprocess
import tempfile
import time
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

from vosk import KaldiRecognizer, Model, SetLogLevel

MODEL_DIR = os.environ.get("STT_MODEL_DIR", "/opt/model")
PORT = int(os.environ.get("STT_PORT", "8790"))
MAX_BYTES = int(os.environ.get("STT_MAX_BYTES", str(2 * 1024 * 1024)))
MAX_SECONDS = float(os.environ.get("STT_MAX_SECONDS", "65"))  # бот режет на 60 с, запас на округление
DECODE_TIMEOUT = 20
RATE = 16000

logging.basicConfig(level=logging.INFO, format="%(asctime)s stt %(levelname)s %(message)s")
log = logging.getLogger("stt")
SetLogLevel(-1)


class SttError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def decode_ogg(data: bytes) -> bytes:
    """OGG/Opus -> PCM 16 кГц моно через opusdec (opus-tools: в 9 раз легче ffmpeg)."""
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = os.path.join(tmp, "in.ogg"), os.path.join(tmp, "out.wav")
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            subprocess.run(["opusdec", "--quiet", "--rate", str(RATE), src, dst],
                           check=True, timeout=DECODE_TIMEOUT,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            raise SttError(422, "не удалось раскодировать звук")
        with wave.open(dst, "rb") as w:
            if w.getsampwidth() != 2 or w.getframerate() != RATE:
                raise SttError(422, "неожиданный формат после декодирования")
            frames = w.readframes(w.getnframes())
            channels = w.getnchannels()
        if channels == 2:  # голосовые моно, но на всякий случай — берём левый канал
            frames = b"".join(frames[i:i + 2] for i in range(0, len(frames), 4))
        elif channels != 1:
            raise SttError(422, "неожиданное число каналов")
        return frames


def recognize(model: Model, pcm: bytes) -> str:
    rec = KaldiRecognizer(model, RATE)
    step = RATE * 2  # секунда звука
    for i in range(0, len(pcm), step):
        rec.AcceptWaveform(pcm[i:i + step])
    return (json.loads(rec.FinalResult()).get("text") or "").strip()


class Handler(BaseHTTPRequestHandler):
    model: Model = None

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):  # стандартный журнал http.server — без путей и адресов
        pass

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "model": os.path.basename(MODEL_DIR)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/stt":
            self._send(404, {"error": "not found"})
            return
        t0 = time.monotonic()
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BYTES:
                raise SttError(413, "пустое или слишком большое тело")
            pcm = decode_ogg(self.rfile.read(length))
            seconds = len(pcm) / (RATE * 2)
            if seconds > MAX_SECONDS:
                raise SttError(413, "слишком длинное голосовое")
            text = recognize(self.model, pcm)
        except SttError as exc:
            log.info("отказ %s за %.1f с", exc.code, time.monotonic() - t0)
            self._send(exc.code, {"error": str(exc)})
            return
        except Exception as exc:  # один плохой запрос не должен ронять сервис
            log.warning("сбой %s за %.1f с", type(exc).__name__, time.monotonic() - t0)
            self._send(500, {"error": "внутренняя ошибка"})
            return
        took = time.monotonic() - t0
        log.info("распознано: звук %.1f с, работа %.1f с, символов %d", seconds, took, len(text))
        self._send(200, {"text": text, "seconds": round(seconds, 1)})


def main():
    t0 = time.monotonic()
    Handler.model = Model(MODEL_DIR)
    log.info("модель загружена за %.1f с, порт %d", time.monotonic() - t0, PORT)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
