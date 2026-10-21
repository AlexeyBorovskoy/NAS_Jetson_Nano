"""OBS-1 task 12: safe D2 and blackbox-heartbeat alert helpers."""
import importlib.util
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/monitoring/blackbox_alerts.py"


def load():
    spec = importlib.util.spec_from_file_location("blackbox_alerts_test", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reader(values):
    return lambda path: values.get(path)


def heartbeat_path(root):
    return os.path.join(root, "heartbeat")


def test_nas_why_success_is_bounded_and_appended():
    mod = load()
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="диагноз\n", stderr="")

    assert mod.append_nas_why("старый текст", run=run) == (
        "старый текст\n\nДиагностика чёрного ящика:\nдиагноз")
    assert calls[0][0] == ["nas-why", "--boot", "-1", "--short"]
    assert calls[0][1]["timeout"] == 60


def test_nas_why_nonzero_oserror_and_timeout_preserve_old_text():
    mod = load()
    old = "старый текст"
    nonzero = lambda *a, **k: SimpleNamespace(returncode=2, stdout="", stderr="secret")
    failed = lambda *a, **k: (_ for _ in ()).throw(OSError("private"))
    timeout = lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(a[0], 60))
    assert mod.append_nas_why(old, run=nonzero) == old
    assert mod.append_nas_why(old, run=failed) == old
    assert mod.append_nas_why(old, run=timeout) == old


def test_systemctl_active_check_is_bounded_and_private():
    mod = load()
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="active\n", stderr="")

    assert mod.blackbox_service_active(run=run)
    assert calls[0][0] == ["systemctl", "is-active", mod.BLACKBOX_UNIT]
    assert calls[0][1]["timeout"] <= 5
    assert "stderr" in calls[0][1]


def test_fresh_ssd_heartbeat_is_silent():
    mod = load()
    ssd, fallback = "/ssd", "/fallback"
    data = {heartbeat_path(ssd): {"ts": 990, "boot_id": "boot-a"}}
    state = {}
    result = mod.blackbox_heartbeat_note(
        state, 1000, ssd, fallback, "boot-a", True, reader(data))
    assert result is None and state == {}


def test_stale_heartbeat_alerts_once_then_after_61_minutes():
    mod = load()
    data = {heartbeat_path("/ssd"): {"ts": 800, "boot_id": "boot-a"}}
    state = {}
    check = lambda now: mod.blackbox_heartbeat_note(
        state, now, "/ssd", "/fallback", "boot-a", True, reader(data))
    assert check(1000) is not None
    assert check(2800) is None
    assert check(4660) is not None


def test_fresh_fallback_wins_over_stale_ssd():
    mod = load()
    data = {heartbeat_path("/ssd"): {"ts": 700, "boot_id": "boot-a"},
            heartbeat_path("/fallback"): {"ts": 990, "boot_id": "boot-a"}}
    state = {}
    result = mod.blackbox_heartbeat_note(
        state, 1000, "/ssd", "/fallback", "boot-a", True, reader(data))
    assert result is None and state == {}


def test_stale_fallback_is_considered_when_ssd_missing():
    mod = load()
    data = {heartbeat_path("/fallback"): {"ts": 800, "boot_id": "boot-a"}}
    result = mod.blackbox_heartbeat_note(
        {}, 1000, "/ssd", "/fallback", "boot-a", True, reader(data))
    assert result is not None


def test_inactive_unit_suppresses_alert_without_reading_heartbeat():
    mod = load()
    fail_if_read = lambda _path: (_ for _ in ()).throw(AssertionError("read"))
    assert mod.blackbox_heartbeat_note(
        {}, 1000, "/ssd", "/fallback", "boot-a", False, fail_if_read) is None


def test_future_malformed_and_old_boot_heartbeats_are_unknown():
    mod = load()
    values = {heartbeat_path("/ssd"): {"ts": 1001, "boot_id": "boot-a"},
              heartbeat_path("/fallback"): {"ts": "bad", "boot_id": "boot-a"}}
    status, source = mod.heartbeat_status(
        "/ssd", "/fallback", 1000, "boot-a", read_json=reader(values))
    assert (status, source) == ("unknown", None)
    values[heartbeat_path("/fallback")] = {"ts": 800, "boot_id": "old-boot"}
    status, source = mod.heartbeat_status(
        "/ssd", "/fallback", 1000, "boot-a", read_json=reader(values))
    assert (status, source) == ("unknown", None)


def test_bad_json_file_is_unknown(tmp_path):
    mod = load()
    path = tmp_path / "heartbeat"
    path.write_text("{broken", encoding="utf-8")
    assert mod.read_heartbeat(str(path)) is None


def test_oversized_heartbeat_is_unknown(tmp_path):
    mod = load()
    path = tmp_path / 'heartbeat'
    path.write_text('{"ts":800,"extra":"' + 'x' * 5000 + '"}', encoding='utf-8')
    assert mod.read_heartbeat(str(path)) is None


def test_missing_boot_identity_cannot_prove_current_boot_is_alive():
    mod = load()
    values = {heartbeat_path('/ssd'): {'ts': 990}}
    assert mod.heartbeat_status('/ssd', '/fallback', 1000, 'current',
                                read_json=reader(values)) == ('unknown', None)


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
