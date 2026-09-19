"""D3: сторож на VPS. Спецификация — docs/superpowers/specs/2026-09-19-cloudru-watchdog-design.md §4."""
import json
import os

import nas_liveness as nl

T0 = 1_790_000_000.0  # произвольная точка отсчёта


def test_classify_both_silent_is_tunnel():
    key, text = nl.classify(None, None)
    assert key == "tunnel"
    assert "туннель" in text


def test_classify_service_error_names_service_and_code():
    key, text = nl.classify(200, 503)
    assert key == "service"
    assert "Nextcloud" in text and "503" in text
    assert "NAS API" not in text


def test_classify_one_silent_is_service_not_tunnel():
    key, text = nl.classify(None, 200)
    assert key == "service"
    assert "NAS API" in text and "нет ответа" in text


def test_classify_all_ok():
    assert nl.classify(200, 200) == (None, None)


def test_single_failure_is_quiet():
    key, text = nl.classify(None, None)
    event, msg, st = nl.decide({}, key, text, T0)
    assert event == "none" and msg == ""
    assert st["fails"] == 1 and st["down_since"] == T0


def test_second_failure_alerts_with_msk_time():
    key, text = nl.classify(None, None)
    _, _, st = nl.decide({}, key, text, T0)
    event, msg, st = nl.decide(st, key, text, T0 + 600)
    assert event == "down"
    assert "МСК" in msg
    assert st["alerted"] is True and st["last_sent"] == T0 + 600


def test_ongoing_problem_repeats_only_after_a_day():
    key, text = nl.classify(None, None)
    st = {}
    for i in range(2):
        _, _, st = nl.decide(st, key, text, T0 + i * 600)
    event, _, st = nl.decide(st, key, text, T0 + 3600)
    assert event == "none"
    event, msg, st = nl.decide(st, key, text, T0 + 600 + nl.REPEAT_AFTER)
    assert event == "repeat" and "Всё ещё" in msg


def test_problem_kind_change_while_alerted_sends_new_down():
    k1, t1 = nl.classify(200, 503)
    st = {}
    for i in range(2):
        _, _, st = nl.decide(st, k1, t1, T0 + i * 600)
    k2, t2 = nl.classify(None, None)
    event, msg, _ = nl.decide(st, k2, t2, T0 + 1200)
    assert event == "down" and "туннель" in msg


def test_recovery_after_alert_reports_downtime():
    key, text = nl.classify(None, None)
    st = {}
    for i in range(2):
        _, _, st = nl.decide(st, key, text, T0 + i * 600)
    event, msg, st = nl.decide(st, None, None, T0 + 47 * 60)
    assert event == "recovered"
    assert "47 мин" in msg
    assert st == {}


def test_recovery_without_alert_is_quiet():
    key, text = nl.classify(None, None)
    _, _, st = nl.decide({}, key, text, T0)
    event, msg, st = nl.decide(st, None, None, T0 + 600)
    assert event == "none" and st == {}


def test_state_roundtrip_is_atomic(tmp_path):
    path = str(tmp_path / "state.json")
    nl.save_state({"fails": 1}, path)
    assert nl.load_state(path) == {"fails": 1}
    assert os.listdir(tmp_path) == ["state.json"]


def test_broken_state_reads_as_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{битый", encoding="utf-8")
    assert nl.load_state(str(path)) == {}
    path.write_text(json.dumps([1, 2]), encoding="utf-8")
    assert nl.load_state(str(path)) == {}


def test_missing_state_reads_as_empty(tmp_path):
    assert nl.load_state(str(tmp_path / "нет.json")) == {}
