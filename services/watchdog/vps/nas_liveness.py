#!/usr/bin/env python3
"""D3 — внешний сторож, часть на VPS (forced command пользователя naswatch).

Проверяет через обратный туннель, отвечают ли NAS API и Nextcloud, помнит
состояние и решает, тревожить ли владельца. Отправку делает задача в Cloud.ru;
здесь — только подкоманда notify как запасной путь в Telegram.

Спецификация: docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md.
Одиночный сбой — не тревога; тревога после двух подряд; повтор — раз в сутки;
о выздоровлении сообщаем всегда (как в nas_jetson_nano-talk-alert.py).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

STATE_FILE = os.environ.get("NASWATCH_STATE", "/var/lib/naswatch/state.json")
API_URL = os.environ.get("NASWATCH_API_URL", "http://127.0.0.1:18099/healthcheck")
NC_URL = os.environ.get("NASWATCH_NC_URL", "http://127.0.0.1:18080/status.php")
TG_API = os.environ.get("NASWATCH_TG_API", "https://api.telegram.org")
PROBE_TIMEOUT = 10
FAILS_BEFORE_ALERT = 2
REPEAT_AFTER = 24 * 3600
MSK = 3 * 3600


def _msk(ts):
    return time.strftime("%d.%m %H:%M", time.gmtime(ts + MSK)) + " МСК"


# ── классификация ──────────────────────────────────────────────────────────────

def _describe(name, code):
    return "%s — %s" % (name, "нет ответа" if code is None else "HTTP %d" % code)


def classify(api, nc):
    """Молчат оба — отказал весь дом (туннель, питание, интернет, сам Jetson).
    Отвечает хоть кто-то — туннель жив, болеет сервис."""
    if api is None and nc is None:
        return "tunnel", ("🔴 NAS не отвечает — туннель закрыт "
                          "(питание, интернет дома или сам Jetson).")
    bad = [_describe(n, c) for n, c in (("NAS API", api), ("Nextcloud", nc)) if c != 200]
    if bad:
        return "service", "🟠 Туннель жив, но сервисы отвечают с ошибкой: %s." % "; ".join(bad)
    return None, None


# ── решение о тревоге ──────────────────────────────────────────────────────────

def decide(state, key, text, now):
    st = dict(state or {})
    if key is None:
        if st.get("alerted"):
            mins = int((now - st.get("down_since", now)) // 60)
            return "recovered", "✅ NAS снова на связи, простой %d мин." % mins, {}
        return "none", "", {}

    new = {
        "fails": st.get("fails", 0) + 1,
        "down_since": st.get("down_since") or now,
        "key": key,
        "alerted": bool(st.get("alerted")),
        "last_sent": st.get("last_sent", 0),
    }
    if new["fails"] < FAILS_BEFORE_ALERT:
        return "none", "", new
    since = " С %s." % _msk(new["down_since"])
    if not new["alerted"] or st.get("key") != key:
        new.update(alerted=True, last_sent=now)
        return "down", text + since, new
    if now - new["last_sent"] >= REPEAT_AFTER:
        new["last_sent"] = now
        return "repeat", "Всё ещё: " + text + since, new
    return "none", "", new


# ── состояние ──────────────────────────────────────────────────────────────────

def load_state(path=None):
    path = path or STATE_FILE
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state, path=None):
    path = path or STATE_FILE
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False)
    os.replace(tmp, path)


# ── проверки и команды ─────────────────────────────────────────────────────────

def probe(url, timeout=PROBE_TIMEOUT):
    """HTTP-код или None. None — HTTP-ответа нет вовсе: порт закрыт, туннель
    принял соединение и оборвал, таймаут. Любой код (и 4xx) — сервис ответил."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def cmd_check(now=None, probe_fn=probe, path=None):
    now = time.time() if now is None else now
    api, nc = probe_fn(API_URL), probe_fn(NC_URL)
    key, text = classify(api, nc)
    event, message, new = decide(load_state(path), key, text, now)
    save_state(new, path)
    return {"event": event, "text": message, "api": api, "nextcloud": nc,
            "checked_at": int(now)}


def send_telegram(token, chat_id, text):
    req = urllib.request.Request(
        "%s/bot%s/sendMessage" % (TG_API, token),
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def cmd_notify(raw, send=None):
    """Запасной путь: токен и текст приходят через stdin, на VPS не хранятся."""
    send = send or send_telegram
    try:
        req = json.loads(raw)
        token, chat_id, text = req["token"], req["chat_id"], req["text"]
    except (ValueError, KeyError, TypeError):
        return {"ok": False, "code": 0, "error": "bad request"}
    code = send(token, chat_id, text)
    return {"ok": code == 200, "code": code}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    raw = os.environ.get("SSH_ORIGINAL_COMMAND") or " ".join(argv) or "check"
    cmd = raw.split()[0]
    if cmd == "check":
        out, rc = cmd_check(), 0
    elif cmd == "notify":
        out, rc = cmd_notify(sys.stdin.read()), 0
    else:
        out, rc = {"error": "unknown command"}, 2
    print(json.dumps(out, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
