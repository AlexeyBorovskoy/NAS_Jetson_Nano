#!/usr/bin/env python3
"""Negative & security regression tests for Sweden VPN v2 using isolated mihomo.exe."""

import copy
import pathlib
import shutil
import subprocess
import sys
import time
import yaml

MIHOMO_BIN = pathlib.Path(r".agent-work\tmp\mihomo\mihomo.exe")
BASE_V2 = pathlib.Path(r".agent-work\private-releases\sweden-v2\alexey-windows\alexey-windows-v2.yaml")
WORKDIR = pathlib.Path(r".agent-work\tmp\negative_tests")


def run_mihomo_case(name, cfg, mixed_port, target_url="https://api.ipify.org"):
    d = WORKDIR / name
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    cfg_p = d / "config.yaml"
    cfg_p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")

    proc = subprocess.Popen(
        [str(MIHOMO_BIN), "-d", str(d), "-f", str(cfg_p)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(1.5)
        res = subprocess.run(
            ["curl.exe", "-sS", "--max-time", "5", "--socks5-hostname", f"127.0.0.1:{mixed_port}", target_url],
            capture_output=True,
            text=True,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def main():
    if not BASE_V2.exists():
        print("ERROR: Generate v2 profiles first", file=sys.stderr)
        sys.exit(2)

    base = yaml.safe_load(BASE_V2.read_text(encoding="utf-8"))
    base["tun"] = {"enable": False}
    base["allow-lan"] = False
    base["log-level"] = "warning"

    # Case 1: Both transports unreachable -> MUST fail, NO DIRECT leak
    c1 = copy.deepcopy(base)
    c1["mixed-port"] = 17980
    for p in c1["proxies"]:
        p["server"] = "127.0.0.1"
        p["port"] = 44399
    rc1, out1, err1 = run_mihomo_case("both_down_no_direct_leak", c1, 17980)
    print(f"[1] both_down_no_direct_leak: rc={rc1} out={out1!r} err={err1[:100]!r}")
    assert rc1 != 0 and out1 == "", f"LEAK or unexpected success: rc={rc1} out={out1!r}"

    # Case 2: Wrong SNI on HY2 -> MUST reject TLS (no skip-cert-verify fallback)
    c2 = copy.deepcopy(base)
    c2["mixed-port"] = 17981
    hy2 = copy.deepcopy(next(p for p in c2["proxies"] if p["type"] == "hysteria2"))
    hy2["sni"] = "wrong-sni.invalid"
    c2["proxies"] = [hy2]
    c2["proxy-groups"] = [{"name": "PROXY", "type": "select", "proxies": ["SE-HY2"]}]
    rc2, out2, err2 = run_mihomo_case("hy2_wrong_sni_rejected", c2, 17981)
    print(f"[2] hy2_wrong_sni_rejected: rc={rc2} out={out2!r} err={err2[:100]!r}")
    assert rc2 != 0 and out2 == "", f"TLS verification did not reject wrong SNI: rc={rc2} out={out2!r}"

    # Case 3: Direct rule (.ru) succeeds even when VPN transports are down
    c3 = copy.deepcopy(c1)
    c3["mixed-port"] = 17982
    rc3, out3, err3 = run_mihomo_case("direct_ru_works_when_proxy_down", c3, 17982, "https://ya.ru")
    print(f"[3] direct_ru_works_when_proxy_down: rc={rc3} bytes={len(out3)}")
    assert rc3 == 0, f"DIRECT .ru rule failed: rc={rc3} err={err3}"

    print("ALL NEGATIVE & BOUNDARY TESTS PASSED")


if __name__ == "__main__":
    main()
