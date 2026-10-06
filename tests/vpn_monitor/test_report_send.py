"""Delivery acknowledgement, retries, concurrent claims and private errors."""
from datetime import date
import io
import json
import threading
import urllib.error

import pytest
import report
import vpnmon_store as vs

DAY = date(2026, 10, 4)
NOW = 1_791_183_600.0
TOKEN = "mock-test-token"


@pytest.fixture
def db(tmp_path):
    conn = vs.open_db(str(tmp_path / "vpnmon.db"))
    yield conn
    conn.close()


class Response:
    def __init__(self, body):
        self.body = body

    def read(self):
        return json.dumps(self.body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_local_and_stdin_configuration(tmp_path, monkeypatch):
    text = '# comment\nTELEGRAM_BOT_TOKEN="abc"\nTELEGRAM_CHAT_ID=42\n'
    path = tmp_path / "telegram.env"
    path.write_text(text)
    expected = {"TELEGRAM_BOT_TOKEN": "abc", "TELEGRAM_CHAT_ID": "42"}
    assert report.read_env(path) == expected
    monkeypatch.setattr(report.sys, "stdin", io.StringIO(text))
    assert report.read_env("-") == expected


def test_http_html_and_timeout():
    seen = {}

    def opener(req, timeout):
        seen.update(url=req.full_url, data=req.data.decode(), timeout=timeout)
        return Response({"ok": True})

    report.send_message(TOKEN, "42", "<pre>x</pre>", opener)
    assert seen["url"] == "https://api.telegram.org/bot%s/sendMessage" % TOKEN
    assert "parse_mode=HTML" in seen["data"] and "chat_id=42" in seen["data"]
    assert seen["timeout"] == 10


@pytest.mark.parametrize("body", [{"ok": False, "description": TOKEN}, [], None])
def test_rejected_response_never_exposes_body(body):
    with pytest.raises(RuntimeError) as caught:
        report.send_message(TOKEN, "42", "x", lambda *a, **k: Response(body))
    assert TOKEN not in str(caught.value)


def test_retry_pauses_and_success():
    attempts, pauses = [], []

    def action():
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("secret")

    assert report.with_retries(action, pauses.append) == (True, None)
    assert pauses == [30, 60]


def test_retry_error_redacts_url_and_arbitrary_secrets():
    def action():
        raise urllib.error.HTTPError("https://api.telegram.org/bot" + TOKEN, 401, TOKEN, None, None)

    ok, error = report.with_retries(action, lambda _: None)
    assert not ok and "401" in error and TOKEN not in error


def test_once_per_day_including_out_of_order_reports(db):
    sent = []
    assert report.run_send(db, NOW, DAY, sent.append) == 0
    assert vs.get_meta(db, "last_report_day") == DAY.isoformat()
    report.run_send(db, NOW, date(2026, 10, 5), sent.append)
    assert report.run_send(db, NOW, DAY, sent.append) == 0
    assert len(sent) == 2
    report.run_send(db, NOW, DAY, sent.append, force=True)
    assert len(sent) == 3


def test_partial_delivery_retries_only_failed_chunk_and_resumes(db, monkeypatch):
    monkeypatch.setattr(report.vr, "to_messages", lambda _: ["one", "two", "three"])
    attempts = []

    def send(text):
        attempts.append(text)
        if text == "two":
            raise OSError(TOKEN)

    assert report.run_send(db, NOW, DAY, send, sleep=lambda _: None) == 1
    assert attempts == ["one", "two", "two", "two"]
    assert vs.get_meta(db, "last_report_failed") == DAY.isoformat()
    assert TOKEN not in db.execute("SELECT detail FROM events").fetchone()[0]
    resumed = []
    assert report.run_send(db, NOW, DAY, resumed.append) == 0
    assert resumed == ["two", "three"]
    assert vs.get_meta(db, "last_report_failed") == ""


def test_new_day_announces_failed_report(db):
    def broken(_):
        raise OSError("offline")

    report.run_send(db, NOW, DAY, broken, sleep=lambda _: None)
    sent = []
    report.run_send(db, NOW + 86400, date(2026, 10, 5), sent.append)
    assert "04.10" in sent[0] and "не был доставлен" in sent[0]


def test_concurrent_sender_cannot_deliver(db):
    path = db.execute("PRAGMA database_list").fetchone()[2]
    result = []

    def competing():
        other = vs.open_db(path)
        try:
            result.append(report.run_send(other, NOW, DAY, lambda _: result.append("duplicate")))
        finally:
            other.close()

    def send(_):
        worker = threading.Thread(target=competing)
        worker.start()
        worker.join(timeout=3)
        assert not worker.is_alive()

    assert report.run_send(db, NOW, DAY, send) == 0
    assert result == [1]


def test_interruption_releases_lock_preserves_confirmed_chunk(db, monkeypatch):
    monkeypatch.setattr(report.vr, "to_messages", lambda _: ["one", "two"])

    def interrupted(text):
        if text == "two":
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        report.run_send(db, NOW, DAY, interrupted)
    sent = []
    assert report.run_send(db, NOW, DAY, sent.append) == 0
    assert sent == ["two"]


def test_stdout_needs_no_credentials_or_network(db, monkeypatch, capsys):
    path = db.execute("PRAGMA database_list").fetchone()[2]
    monkeypatch.setattr(report, "read_env", lambda _: pytest.fail("credentials read"))
    assert report.main(["--stdout", "--db", path, "--day", DAY.isoformat()]) == 0
    assert "04.10" in capsys.readouterr().out


def test_test_mode_does_not_create_database(tmp_path, monkeypatch):
    path = tmp_path / "unused.db"
    sent = []
    monkeypatch.setattr(report, "_configured_send", lambda _: sent.append)
    assert report.main(["--test", "--db", str(path)]) == 0
    assert sent == [report.TEST_TEXT] and not path.exists()


def test_configuration_errors_are_private(tmp_path, capsys):
    path = tmp_path / TOKEN.replace(":", "_")
    assert report.main(["--test", "--env", str(path)]) == 1
    assert str(path) not in capsys.readouterr().err


def test_budget_defers_remaining_chunks_without_truncation(db, monkeypatch):
    monkeypatch.setattr(report.vr, "to_messages", lambda _: ["one", "two", "three"])
    clock = [100.0]
    monkeypatch.setattr(report.time, "monotonic", lambda: clock[0])
    sent = []

    def slow(text):
        sent.append(text)
        clock[0] += 120

    assert report.run_send(db, NOW, DAY, slow) == 1
    assert sent == ["one", "two"]
    resumed = []
    assert report.run_send(db, NOW, DAY, resumed.append) == 0
    assert resumed == ["three"]


def test_retry_does_not_sleep_past_budget(monkeypatch):
    monkeypatch.setattr(report.time, "monotonic", lambda: 100)
    pauses = []

    def fail():
        raise OSError()

    assert report.with_retries(fail, pauses.append, deadline=125) == (
        False, "delivery budget exhausted")
    assert pauses == []
