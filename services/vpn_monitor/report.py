#!/usr/bin/env python3
"""Daily VPN report delivery. Confirmed chunks survive retries and restarts.

Telegram has no idempotency key: a lost acknowledgement can still duplicate a
message. The OS lock prevents concurrent local senders, not that remote ambiguity.
"""
import argparse
from contextlib import contextmanager
from datetime import date
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import vpnmon_query as vq
import vpnmon_render as vr
import vpnmon_store as vs

DB_PATH = "/var/lib/nasa-vpnmon/vpnmon.db"
ENV_PATH = "/etc/nasa-vpnmon/telegram.env"
HTTP_TIMEOUT = 10
RETRY_PAUSES = (30, 60)
SEND_BUDGET = 240  # Leave 60 seconds for systemd shutdown/bookkeeping.
TEST_TEXT = "<pre>🧪 nasa-vpnmon: проверка канала. Отчёт приходит в 10:00 МСК.</pre>"


def read_env(path):
    """Read a local config (or stdin with '-'); never evaluate shell syntax."""
    if path == "-":
        return _env_lines(sys.stdin)
    with open(path, encoding="utf-8") as source:
        return _env_lines(source)


def _env_lines(source):
    out = {}
    for raw in source:
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            out[key.strip()] = value
    return out


def _error(exc):
    # Exception strings may contain the request URL/token, response text or PII.
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTPError: %d" % exc.code
    return type(exc).__name__


def send_message(token, chat_id, text, opener=urllib.request.urlopen):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text,
                                   "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode("utf-8")
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token, data=data)
    try:
        with opener(req, timeout=HTTP_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if not isinstance(body, dict) or body.get("ok") is not True:
            raise RuntimeError("Telegram rejected message")
    except (OSError, ValueError, RuntimeError) as exc:
        raise RuntimeError(_error(exc)) from None


def with_retries(action, sleep=time.sleep, pauses=RETRY_PAUSES, deadline=None):
    error = None
    for pause in (0,) + tuple(pauses):
        if deadline is not None and time.monotonic() + pause + HTTP_TIMEOUT > deadline:
            return False, "delivery budget exhausted"
        if pause:
            sleep(pause)
        try:
            action()
            return True, None
        except (OSError, ValueError, RuntimeError) as exc:
            error = _error(exc)
    return False, error


def deliver(messages, send, sleep=time.sleep):
    for text in messages:
        ok, error = with_retries(lambda t=text: send(t), sleep)
        if not ok:
            return False, error
    return True, None


def _lock_file(db):
    path = db.execute("PRAGMA database_list").fetchone()[2]
    if not path:
        raise ValueError("delivery requires a file-backed database")
    return path + ".report.lock"


def _lock(handle, unlock=False):
    if os.name == "nt":
        import msvcrt
        handle.seek(0)
        mode = msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK
        msvcrt.locking(handle.fileno(), mode, 1)
    else:
        import fcntl
        mode = fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB
        fcntl.flock(handle.fileno(), mode)


@contextmanager
def _sender_lock(db):
    fd = os.open(_lock_file(db), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0")
            handle.flush()
        try:
            _lock(handle)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            _lock(handle, unlock=True)


def _pending(db, now, day, force):
    key = "report_progress:" + day.isoformat()
    saved = vs.get_meta(db, key)
    if saved and not force:
        return key, json.loads(saved)
    pending = {"messages": vr.to_messages(vr.render(vq.build_report(db, day, now))), "next": 0}
    with db:
        vs.set_meta(db, key, json.dumps(pending, ensure_ascii=False))
    return key, pending


def _send_pending(db, key, pending, send, sleep, deadline):
    while pending["next"] < len(pending["messages"]):
        text = pending["messages"][pending["next"]]
        ok, error = with_retries(lambda: send(text), sleep, deadline=deadline)
        if not ok:
            return False, error
        pending["next"] += 1
        with db:
            vs.set_meta(db, key, json.dumps(pending, ensure_ascii=False))
    return True, None


def _finish(db, now, day, key, ok, error):
    with db:
        if ok:
            vs.set_meta(db, "last_report_day", day.isoformat())
            vs.set_meta(db, "report_sent:" + day.isoformat(), "1")
            vs.set_meta(db, "last_report_failed", "")
            db.execute("DELETE FROM meta WHERE key=?", (key,))
            vs.purge_old(db, now)
        else:
            vs.set_meta(db, "last_report_failed", day.isoformat())
            vs.add_event(db, now, "report_failed", {"day": day.isoformat(), "error": error})


def _run_locked(db, now, day, send, force, sleep):
    sent = vs.get_meta(db, "report_sent:" + day.isoformat())
    if not force and (sent or vs.get_meta(db, "last_report_day") == day.isoformat()):
        print("отчёт за %s уже отправлен" % day.isoformat())
        return 0
    key, pending = _pending(db, now, day, force)
    deadline = time.monotonic() + SEND_BUDGET
    ok, error = _send_pending(db, key, pending, send, sleep, deadline)
    _finish(db, now, day, key, ok, error)
    print("отправлено" if ok else "не доставлено: %s" % error,
          file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def run_send(db, now, day, send, force=False, sleep=time.sleep):
    """One local sender at a time, durable cursor for acknowledged chunks."""
    with _sender_lock(db) as acquired:
        if not acquired:
            print("отправка уже выполняется", file=sys.stderr)
            return 1
        return _run_locked(db, now, day, send, force, sleep)


def _parse_args(argv):
    ap = argparse.ArgumentParser(description="Суточный отчёт VPN/VPS в Telegram")
    mode = ap.add_mutually_exclusive_group(required=True)
    for option in ("stdout", "send", "test"):
        mode.add_argument("--" + option, action="store_true")
    ap.add_argument("--day", type=date.fromisoformat)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--env", default=ENV_PATH, help="local config path, or '-' for stdin")
    return ap.parse_args(argv)


def _configured_send(path):
    env = read_env(path)
    token, chat_id = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("missing Telegram configuration")
    return lambda text: send_message(token, chat_id, text)


def _main(args):
    if args.test:
        send = _configured_send(args.env)
        ok, error = with_retries(lambda: send(TEST_TEXT))
        print("проверка: доставлено" if ok else "проверка: не доставлено — %s" % error)
        return 0 if ok else 1
    now = time.time()
    day = args.day or vq.report_day(now)
    db = vs.open_db(args.db)
    try:
        if args.stdout:
            print(vr.render(vq.build_report(db, day, now)))
            return 0
        return run_send(db, now, day, _configured_send(args.env), args.force)
    finally:
        db.close()


def main(argv=None):
    args = _parse_args(argv)
    os.umask(0o077)
    try:
        return _main(args)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print("ошибка отчёта: %s" % _error(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
