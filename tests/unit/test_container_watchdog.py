"""OPS-1/OPS-2: deterministic tests for the local Docker recovery watchdog.

HDD-guard logic itself (hdd_probe/holds_hdd/hdd_status_note) moved to its own
module (scripts/monitoring/hdd_guard.py, review round 1, 2026-10-15) and is
unit-tested there (tests/unit/test_hdd_guard.py). Here we only check the
wiring: the watchdog loads that module via _load_hdd_guard() and must not
start/restart a holder while the mount is unhealthy."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/monitoring/nas_jetson_nano-container-watchdog.py"
HDD_GUARD_SCRIPT = ROOT / "scripts/monitoring/hdd_guard.py"


def load():
    spec = importlib.util.spec_from_file_location("container_watchdog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_hdd_guard():
    spec = importlib.util.spec_from_file_location("hdd_guard_for_watchdog_test", HDD_GUARD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def container(status="running", health="healthy", policy="always", maintenance=False,
             mounts=()):
    return {
        "name": "homecloud_demo",
        "status": status,
        "health": health,
        "policy": policy,
        "maintenance": maintenance,
        "mounts": list(mounts),
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
    hg = load_hdd_guard()
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
            mock.patch.object(mod, "_load_hdd_guard", return_value=hg), \
            mock.patch.object(hg, "hdd_probe", return_value="ok"), \
            mock.patch.object(mod, "list_containers",
                              return_value=[container(status="exited", health="")]), \
            mock.patch.object(mod, "docker", return_value=action):
        assert mod.main() == 0
    assert "network timeout" in capsys.readouterr().err


def test_successful_telegram_delivery_is_reported(tmp_path, capsys):
    mod = load()
    hg = load_hdd_guard()
    mod.PAUSE_FILE = str(tmp_path / "not-paused")
    alert = SimpleNamespace(
        LAYOUT={"NAS_STATE_DIR": str(tmp_path)},
        ENV_FILE=str(tmp_path / "env"),
        read_env=mock.Mock(return_value="configured"),
        resolve_owner_chat_id=mock.Mock(return_value="123"),
        send_with_retries=mock.Mock(return_value=(True, None)),
    )
    action = mock.Mock(returncode=0, stderr="")
    with mock.patch.object(mod, "_load_boot_alert", return_value=alert), \
            mock.patch.object(mod, "_load_hdd_guard", return_value=hg), \
            mock.patch.object(hg, "hdd_probe", return_value="ok"), \
            mock.patch.object(mod, "list_containers",
                              return_value=[container(status="exited", health="")]), \
            mock.patch.object(mod, "docker", return_value=action):
        assert mod.main() == 0
    assert "алерт доставлен" in capsys.readouterr().out


# ── OPS-2: /mnt/hdd2tb — сторож не трогает держателей при hung/absent ────────
# hdd_probe подменён (трогает /proc и subprocess), holds_hdd/hdd_status_note —
# настоящие из hdd_guard.py: это проверка СВЯЗКИ двух модулей, не повтор их
# собственных unit-тестов (они в test_hdd_guard.py).

def test_hung_hdd_blocks_holder_restart_and_alerts(tmp_path):
    mod = load()
    hg = load_hdd_guard()
    mod.PAUSE_FILE = str(tmp_path / "not-paused")
    alert = SimpleNamespace(
        LAYOUT={"NAS_STATE_DIR": str(tmp_path)},
        ENV_FILE=str(tmp_path / "env"),
        read_env=mock.Mock(return_value="configured"),
        resolve_owner_chat_id=mock.Mock(return_value="123"),
        send_with_retries=mock.Mock(return_value=(True, None)),
    )
    holder = container(status="exited", health="", mounts=("/mnt/hdd2tb",))
    with mock.patch.object(mod, "_load_boot_alert", return_value=alert), \
            mock.patch.object(mod, "_load_hdd_guard", return_value=hg), \
            mock.patch.object(hg, "hdd_probe", return_value="hung"), \
            mock.patch.object(mod, "list_containers", return_value=[holder]), \
            mock.patch.object(mod, "docker") as docker_mock:
        assert mod.main() == 0
    docker_mock.assert_not_called()
    sent_text = alert.send_with_retries.call_args[0][2]
    assert "hdd_hang_recover.sh" in sent_text


def test_hung_hdd_does_not_block_non_holder_container(tmp_path):
    mod = load()
    hg = load_hdd_guard()
    mod.PAUSE_FILE = str(tmp_path / "not-paused")
    alert = SimpleNamespace(
        LAYOUT={"NAS_STATE_DIR": str(tmp_path)},
        ENV_FILE=str(tmp_path / "env"),
        read_env=mock.Mock(return_value="configured"),
        resolve_owner_chat_id=mock.Mock(return_value="123"),
        send_with_retries=mock.Mock(return_value=(True, None)),
    )
    plain = container(status="exited", health="", mounts=())
    action = mock.Mock(returncode=0, stderr="")
    with mock.patch.object(mod, "_load_boot_alert", return_value=alert), \
            mock.patch.object(mod, "_load_hdd_guard", return_value=hg), \
            mock.patch.object(hg, "hdd_probe", return_value="hung"), \
            mock.patch.object(mod, "list_containers", return_value=[plain]), \
            mock.patch.object(mod, "docker", return_value=action) as docker_mock:
        assert mod.main() == 0
    docker_mock.assert_called_once_with("start", "homecloud_demo")


if __name__ == "__main__":
    # Ворота запускают tests/unit как "python файл"; без этого блока функции
    # pytest не выполнялись бы вовсе и файл засчитывался бы пройденным.
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
