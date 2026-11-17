#!/usr/bin/env python3
"""Unit and integration tests for Sweden VPN v2 generator, validator, and security hygiene."""

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "sweden_vpn"))

import validate_profiles  # noqa: E402


SECRET_PATTERNS = [
    re.compile(r"password\s*:\s*['\"]?[A-Za-z0-9_\-]{12,}", re.I),
    re.compile(r"private[_-]key\s*:", re.I),
]


class TestSwedenVpnV2(unittest.TestCase):
    def test_inventory_and_policy_no_secrets(self):
        for rel in [
            "tools/sweden_vpn/inventory/devices.json",
            "tools/sweden_vpn/templates/policy_v2.yaml",
            "releases/sweden-v2/manifest.json",
        ]:
            p = REPO_ROOT / rel
            self.assertTrue(p.exists(), f"Missing {rel}")
            text = p.read_text(encoding="utf-8")
            for pat in SECRET_PATTERNS:
                self.assertIsNone(pat.search(text), f"Potential secret found in {rel}")

    def test_reproducible_build_and_missing_secrets_fails_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools/sweden_vpn/generate_profiles.py"),
                    "--secrets-dir",
                    str(pathlib.Path(tmp) / "nonexistent"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("secrets directory not found", p.stderr.lower())

    def test_generated_profiles_pass_validator_and_native_mihomo(self):
        rel_dir = REPO_ROOT / ".agent-work/private-releases/sweden-v2"
        mihomo_bin = REPO_ROOT / ".agent-work/tmp/mihomo/mihomo.exe"
        yamls = sorted(rel_dir.rglob("*-v2.yaml"))
        self.assertEqual(len(yamls), 7)
        for yf in yamls:
            errs = validate_profiles.validate_profile(yf, mihomo_bin if mihomo_bin.exists() else None)
            self.assertEqual(errs, [], f"{yf.name} failed validation: {errs}")

    def test_negative_validator_catches_direct_in_auto_and_insecure_tls(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = {
                "mode": "rule",
                "dns": {"enable": True, "default-nameserver": ["https://1.1.1.1/dns-query"]},
                "proxies": [
                    {"name": "SE-PRIMARY", "type": "vless", "server": "vpn.privet.dynv6.net", "port": 443, "tls": True, "servername": "evil.com"},
                    {"name": "SE-HY2", "type": "hysteria2", "server": "vpn.privet.dynv6.net", "port": 443, "skip-cert-verify": True, "sni": "vpn.privet.dynv6.net"},
                ],
                "proxy-groups": [
                    {"name": "PROXY", "type": "select", "proxies": ["AUTO"]},
                    {"name": "AUTO", "type": "fallback", "proxies": ["SE-HY2", "DIRECT"]},
                ],
                "rules": ["MATCH,DIRECT"],
            }
            p = pathlib.Path(tmp) / "bad.yaml"
            p.write_text(yaml.safe_dump(bad), encoding="utf-8")
            errs = validate_profiles.validate_profile(p)
            self.assertTrue(any("skip-cert-verify" in e for e in errs))
            self.assertTrue(any("DIRECT" in e for e in errs))
            self.assertTrue(any("MATCH,PROXY" in e for e in errs))
            self.assertTrue(any("DoH" in e for e in errs))

    def test_v1_yaml_files_remain_untouched(self):
        manifest = json.loads((REPO_ROOT / "releases/sweden-v2/manifest.json").read_text(encoding="utf-8"))
        inv = json.loads((REPO_ROOT / "tools/sweden_vpn/inventory/devices.json").read_text(encoding="utf-8"))
        v1_map = {d["device_id"]: d["v1_sha256"] for d in inv["devices"]}
        for d in manifest["devices"]:
            self.assertEqual(d["v1_sha256"], v1_map[d["device_id"]])


if __name__ == "__main__":
    unittest.main()
