"""D3: задача сторожа в Cloud.ru. Спецификация §2, §4, §5."""
import datetime
import json
import os

import watchdog_job as wj

ENV = {"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "OWNER_CHAT_ID": "42",
       "VPS_HOST": "vps.example", "SSH_PRIVATE_KEY": "KEY", "SSH_KNOWN_HOSTS": "KH"}
UTC = datetime.timezone.utc


def at(minute):
    return datetime.datetime(2026, 9, 19, 3, minute, tzinfo=UTC)


class FakeSsh:
    def __init__(self, check_rc=0, check_out="", notify_out='{"ok": true, "code": 200}'):
        self.check_rc, self.check_out, self.notify_out = check_rc, check_out, notify_out
        self.calls = []

    def __call__(self, command, stdin_text=None):
        self.calls.append((command, stdin_text))
        if command == "check":
            return self.check_rc, self.check_out
        return 0, self.notify_out


class FakeSend:
    def __init__(self, code=200):
        self.code, self.sent = code, []

    def __call__(self, token, chat_id, text):
        self.sent.append((token, chat_id, text))
        return self.code


def check_json(event, text=""):
    return json.dumps({"event": event, "text": text, "api": 200, "nextcloud": 200}) + "\n"


def test_quiet_when_nothing_happened():
    send = FakeSend()
    log, ok = wj.run_once(ENV, at(5), FakeSsh(check_out=check_json("none")), send)
    assert ok and send.sent == []


def test_event_goes_to_owner_directly():
    send = FakeSend()
    ssh = FakeSsh(check_out=check_json("down", "🔴 NAS не отвечает"))
    log, ok = wj.run_once(ENV, at(25), ssh, send)
    assert ok
    assert send.sent == [("SECRET-TOKEN", "42", "🔴 NAS не отвечает")]
    assert [c for c, _ in ssh.calls] == ["check"]


def test_telegram_unreachable_falls_back_to_vps_relay():
    send = FakeSend(code=0)
    ssh = FakeSsh(check_out=check_json("recovered", "✅ снова на связи"))
    log, ok = wj.run_once(ENV, at(25), ssh, send)
    assert ok
    command, payload = ssh.calls[1]
    assert command == "notify"
    assert json.loads(payload) == {"token": "SECRET-TOKEN", "chat_id": "42",
                                   "text": "✅ снова на связи"}


def test_both_paths_failed_is_reported_as_failure():
    ssh = FakeSsh(check_out=check_json("down", "x"), notify_out='{"ok": false, "code": 0}')
    log, ok = wj.run_once(ENV, at(25), ssh, FakeSend(code=0))
    assert not ok


def test_vps_down_alerts_in_first_ten_minutes_of_hour():
    send = FakeSend()
    log, ok = wj.run_once(ENV, at(3), FakeSsh(check_rc=255), send)
    assert send.sent == [("SECRET-TOKEN", "42", wj.VPS_DOWN_TEXT)]


def test_vps_down_quiet_rest_of_hour():
    send = FakeSend()
    log, ok = wj.run_once(ENV, at(10), FakeSsh(check_rc=255), send)
    assert send.sent == [] and ok


def test_garbage_from_vps_counts_as_vps_down():
    send = FakeSend()
    wj.run_once(ENV, at(0), FakeSsh(check_out="not json"), send)
    assert send.sent[0][2] == wj.VPS_DOWN_TEXT


def test_log_line_never_contains_token_or_text():
    ssh = FakeSsh(check_out=check_json("down", "секретный текст"))
    log, _ = wj.run_once(ENV, at(25), ssh, FakeSend(code=0))
    assert "SECRET-TOKEN" not in log and "секретный" not in log


def test_prepare_ssh_writes_key_and_pins_host(tmp_path):
    cmd = wj.prepare_ssh(ENV, str(tmp_path))
    key = tmp_path / "id"
    assert key.read_text() == "KEY\n"
    assert (tmp_path / "known_hosts").read_text() == "KH\n"
    assert "StrictHostKeyChecking=yes" in cmd and "BatchMode=yes" in cmd
    assert cmd[-1] == "naswatch@vps.example"
    if os.name == "posix":
        assert (key.stat().st_mode & 0o777) == 0o600


def test_dockerfile_runs_unprivileged():
    here = os.path.dirname(os.path.abspath(__file__))
    df = os.path.join(here, "..", "..", "services", "watchdog", "job", "Dockerfile")
    text = open(df, encoding="utf-8").read()
    assert "openssh-client" in text
    assert "USER 10001" in text
