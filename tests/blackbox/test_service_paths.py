"""Allow degraded service startup before Python chooses SD fallback storage."""
import configparser
from pathlib import Path

import pytest


@pytest.mark.parametrize("suffix", ("", "-boot", "-archive"))
def test_units_can_start_with_ssd_directory_absent(suffix):
    root = Path(__file__).resolve().parents[2]
    unit = root / "systemd" / ("nas_jetson_nano-blackbox%s.service" % suffix)
    config = configparser.ConfigParser(interpolation=None)
    config.read(str(unit), encoding="utf-8")
    service = config["Service"]
    paths = service["ReadWritePaths"].split()
    # The installer creates the SD state directory; the HDD mountpoint remains
    # present when unmounted. The SSD-only subdirectory need not exist.
    existing = {"/var/lib/nas-blackbox", "/mnt/hdd2tb"}
    missing_required = [path for path in paths
                        if not path.startswith("-") and path not in existing]
    assert not missing_required
    assert "/var/lib/nas-blackbox" in paths
    assert "/mnt/storage/blackbox" in {path.lstrip("-") for path in paths}
    assert service["ProtectSystem"] == "strict"
