#!/usr/bin/env python3
"""OPS-2 regression: operational scripts must not fall back to a stale VPS IP."""

import io
import os
import sys
import unittest

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
TARGETS = (
    "scripts/monitoring/nas_jetson_nano-send-report-telegram.sh",
    "scripts/monitoring/nas_jetson_nano-daily-report.sh",
    "scripts/setup/nas-offsite-backup.sh",
)


def read(path):
    with io.open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


class VpsHostConfigTest(unittest.TestCase):
    def test_target_scripts_have_no_literal_vps_ipv4(self):
        old_address = ".".join(("95", "163", "176", "103"))
        for path in TARGETS:
            self.assertNotIn(old_address, read(path), path)

    def test_target_scripts_read_vps_host_from_config(self):
        for path in TARGETS:
            text = read(path)
            self.assertIn("VPS_HOST", text, path)
            self.assertRegex(text, r"/opt/[^\n]*/config/\.env", path)
            self.assertIn("VPS config is not readable", text, path)
            self.assertIn("VPS_HOST is missing or invalid", text, path)

    def test_daily_report_has_no_legacy_server_ip_fallback(self):
        text = read("scripts/monitoring/nas_jetson_nano-daily-report.sh")
        self.assertNotIn("SERVER_IP", text)
        self.assertIn('"${VPS_USER}@${VPS_HOST}"', text)

    def test_offsite_proxy_uses_configured_host(self):
        text = read("scripts/setup/nas-offsite-backup.sh")
        self.assertIn("${VPS_USER}@${VPS_HOST}", text)
        self.assertIn('OFFSITE_SSH_KEY="${OFFSITE_SSH_KEY:-', text)

    def test_daily_report_installer_uses_host_layout(self):
        text = read("scripts/monitoring/install_daily_report.sh")
        self.assertIn('source "${ROOT}/scripts/lib/layout.sh"', text)
        self.assertIn('${NAS_SBIN_PREFIX}-send-report-telegram.sh', text)
        self.assertIn('${NAS_UNIT_PREFIX}-daily-report-telegram', text)
        self.assertIn('enable --now "${unit}.timer"', text)


if __name__ == "__main__":
    result = unittest.main(exit=False)
    failures = len(result.result.failures) + len(result.result.errors)
    print("[OK] OPS-2 VPS config" if not failures else "[FAIL] OPS-2 VPS config")
    sys.exit(1 if failures else 0)
