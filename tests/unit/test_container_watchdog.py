"""OPS-1: deterministic tests for the local Docker recovery watchdog."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/monitoring/nas_jetson_nano-container-watchdog.py"


def load():
    spec = importlib.util.spec_from_file_location("container_watchdog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def container(status="running", health="healthy", policy="always", maintenance=False):
    return {
        "name": "homecloud_demo",
        "status": status,
        "health": health,
        "policy": policy,
        "maintenance": maintenance,
    }


def test_decision_starts_stopped_and_restarts_unhealthy():
    mod = load()
    assert mod.decide(container(status="exited", health=""), [], 1000) == "start"
    assert mod.decide(container(health="unhealthy"), [], 1000) == "restart"
    assert mod.decide(container(), [], 1000) is None


def test_decision_does_not_touch_policy_opt_out_and_rate_limits():
    mod = load()
    assert mod.decide(container(status="exited", policy="no"), [], 1000) is None
    assert mod.decide(container(health="unhealthy"), [900], 1000) is None
    history = [1000 - i * 100 for i in range(mod.MAX_ACTIONS_PER_HOUR)]
    assert mod.decide(container(status="exited"), history, 2000) == "give_up"


def test_global_pause_prevents_even_container_inventory(tmp_path):
    mod = load()
    pause = tmp_path / "pause"
    pause.touch()
    mod.PAUSE_FILE = str(pause)
    with mock.patch.object(mod, "list_containers", side_effect=AssertionError("must not inspect")):
        assert mod.main() == 0


def test_per_container_marker_and_label_enable_maintenance(tmp_path):
    mod = load()
    mod.PAUSE_DIR = str(tmp_path)
    (tmp_path / "homecloud_demo").touch()
    assert mod.is_paused(container())
    assert mod.is_paused(container(maintenance=True))
    assert not mod.is_paused({**container(), "name": "homecloud_other"})


def test_inventory_reads_only_homecloud_and_maintenance_label():
    mod = load()
    inspected = [{
        "Name": "/homecloud_demo",
        "State": {"Status": "running", "Health": {"Status": "unhealthy"}},
        "HostConfig": {"RestartPolicy": {"Name": "always"}},
        "Config": {"Labels": {"nas.watchdog.maintenance": "true"}},
    }]
    calls = [mock.Mock(stdout="homecloud_demo\n"), mock.Mock(stdout=json.dumps(inspected))]
    with mock.patch.object(mod, "docker", side_effect=calls) as docker:
        assert mod.list_containers() == [container(health="unhealthy", maintenance=True)]
    assert docker.call_args_list[0].args[:4] == (
        "ps", "-a", "--filter", "name=^homecloud_"
    )


def test_systemd_timer_and_installer_contract():
    timer = (ROOT / "systemd/nas_jetson_nano-container-watchdog.timer").read_text(encoding="utf-8")
    service = (ROOT / "systemd/nas_jetson_nano-container-watchdog.service").read_text(encoding="utf-8")
    installer = (ROOT / "scripts/monitoring/install_container_watchdog.sh").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=2min" in timer
    assert "nas_jetson_nano-container-watchdog.py" in service
    assert "enable --now nas_jetson_nano-container-watchdog.timer" in installer
    assert "/etc/nas-watchdog.pause.d" in installer


def test_failed_telegram_delivery_is_reported(tmp_path, capsys):
    mod = load()
    mod.PAUSE_FILE = str(tmp_path / "not-paused")
    alert = SimpleNamespace(
        LAYOUT={"NAS_STATE_DIR": str(tmp_path)},
        ENV_FILE=str(tmp_path / "env"),
        read_env=mock.Mock(side_effect=lambda _path, key, default=None: {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_USERS": "admin:123",
            "TELEGRAM_OWNER_LOGIN": "admin",
            "TELEGRAM_PROXY": "",
        }.get(key, default)),
        resolve_owner_chat_id=mock.Mock(return_value="123"),
        send_with_retries=mock.Mock(return_value=(False, "network timeout")),
    )
    action = mock.Mock(returncode=0, stderr="")
    with mock.patch.object(mod, "_load_boot_alert", return_value=alert), \
            mock.patch.object(mod, "list_containers",
                              return_value=[container(status="exited", health="")]), \
            mock.patch.object(mod, "docker", return_value=action):
        assert mod.main() == 0
    assert "network timeout" in capsys.readouterr().err
