"""API-2: static contract for the host-level aria2 egress barrier."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_guard_blocks_private_ranges_and_is_attached_to_docker_paths():
    guard = (ROOT / "scripts/network/dl_egress_guard.sh").read_text(encoding="utf-8")
    for network in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "127.0.0.0/8",
    ):
        assert network in guard
    assert "ESTABLISHED,RELATED" in guard
    assert "for parent in DOCKER-USER INPUT" in guard
    assert 'docker network inspect' in guard
    assert "while read -r -a rule" in guard
    assert "|| true" in guard  # no stale jump is the normal first-install case


def test_watchdog_service_refreshes_guard_before_container_recovery():
    service = (ROOT / "systemd/nas_jetson_nano-container-watchdog.service").read_text(
        encoding="utf-8"
    )
    guard_pos = service.index("dl_egress_guard.sh")
    watchdog_pos = service.index("nas_jetson_nano-container-watchdog.py")
    assert guard_pos < watchdog_pos
