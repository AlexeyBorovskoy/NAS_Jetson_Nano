#!/usr/bin/env python3
"""D3 — внешний сторож, часть в Cloud.ru (Container Job раз в 10 мин).

Идёт по ssh на VPS (ключ с единственной командой nas-liveness), получает
событие и пересылает его владельцу в Telegram. Если Telegram из Cloud.ru
недоступен — просит VPS отправить (nas-liveness notify). Если молчит сам VPS,
состояние хранить негде: тревога только в запуске с минутой 00–09 — раз в час
(решение владельца 2026-09-19).

В журнал — только событие и коды; токен и текст сообщений не печатаются.
Спецификация: docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md.
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

VPS_DOWN_TEXT = ("🔴 VPS не отвечает: у семьи нет внешнего доступа к NAS и VPN. "
                 "Повтор — раз в час, пока не ответит.")
ALERT_EVENTS = ("down", "repeat", "recovered")
TG_API = "https://api.telegram.org"


def send_telegram(token, chat_id, text):
    # Копия nas_liveness.send_telegram: образы разные, общего модуля нет намеренно.
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


def _last_json(out):
    try:
        data = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    return data if isinstance(data, dict) else None


def run_once(env, now, ssh, send):
    token, chat_id = env["TELEGRAM_BOT_TOKEN"], env["OWNER_CHAT_ID"]
    rc, out = ssh("check")
    result = _last_json(out) if rc == 0 else None
    if result is None or "event" not in result:
        if now.minute < 10:
            code = send(token, chat_id, VPS_DOWN_TEXT)
            return "vps_down alerted tg=%d" % code, code == 200
        return "vps_down quiet (не первый запуск часа)", True

    event = result["event"]
    if event not in ALERT_EVENTS:
        return "ok event=%s api=%s nc=%s" % (event, result.get("api"), result.get("nextcloud")), True

    code = send(token, chat_id, result["text"])
    if code == 200:
        return "sent event=%s tg=200" % event, True
    payload = json.dumps({"token": token, "chat_id": chat_id, "text": result["text"]})
    _, out2 = ssh("notify", payload)
    relayed = (_last_json(out2) or {}).get("ok") is True
    return "event=%s tg=%d relay=%s" % (event, code, "ok" if relayed else "fail"), relayed


def prepare_ssh(env, workdir):
    key = os.path.join(workdir, "id")
    known = os.path.join(workdir, "known_hosts")
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(env["SSH_PRIVATE_KEY"].strip() + "\n")
    with open(known, "w") as fh:
        fh.write(env["SSH_KNOWN_HOSTS"].strip() + "\n")
    return ["ssh", "-i", key, "-o", "UserKnownHostsFile=" + known,
            "-o", "StrictHostKeyChecking=yes", "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=15",
            "%s@%s" % (env.get("VPS_USER", "naswatch"), env["VPS_HOST"])]


def make_ssh(base):
    def run(command, stdin_text=None):
        try:
            p = subprocess.run(base + [command], input=stdin_text,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=40)
            return p.returncode, p.stdout
        except (subprocess.TimeoutExpired, OSError):
            return 255, ""
    return run


def main():
    env = dict(os.environ)
    with tempfile.TemporaryDirectory() as workdir:
        ssh = make_ssh(prepare_ssh(env, workdir))
        log, ok = run_once(env, datetime.datetime.now(datetime.timezone.utc), ssh, send_telegram)
    print(log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
