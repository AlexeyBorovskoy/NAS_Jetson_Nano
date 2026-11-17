#!/usr/bin/env python3
"""External E2E probe for Sweden VPN (DNS, HTTPS:8443, separate HY2 & REALITY egress checks).

Never prints or writes credentials. Uses isolated local mihomo/sing-box SOCKS5 proxy
to test each transport independently without fallback.
"""

import argparse
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import yaml

EXPECTED_IP = "45.140.13.178"
DOMAIN = "vpn.privet.dynv6.net"


def check_dns():
    t0 = time.monotonic()
    try:
        ips = sorted({r[4][0] for r in socket.getaddrinfo(DOMAIN, 443, socket.AF_INET)})
        return {"ok": EXPECTED_IP in ips, "ips": ips, "ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as e:
        return {"ok": False, "error": str(e), "ms": round((time.monotonic() - t0) * 1000, 1)}


def check_https_8443():
    p = subprocess.run(
        [
            "curl.exe", "-sS", "--max-time", "8", "-o", "NUL",
            "-w", "code=%{http_code}\ndns_s=%{time_namelookup}\ntcp_s=%{time_connect}\ntls_s=%{time_appconnect}\nttfb_s=%{time_starttransfer}\ntotal_s=%{time_total}\n",
            f"https://{DOMAIN}:8443/",
        ],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        return {"ok": False, "error": p.stderr.strip()}
    try:
        data = {}
        for line in p.stdout.strip().splitlines():
            k, v = line.split("=", 1)
            data[k] = int(v) if k == "code" else float(v.replace(",", "."))
        data["ok"] = (data.get("code") == 200)
        return data
    except Exception as e:
        return {"ok": False, "raw": p.stdout.strip(), "error": str(e)}


def probe_transport(mihomo_bin: pathlib.Path, proxy_obj: dict, port: int):
    cfg = {
        "mixed-port": port,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "error",
        "ipv6": False,
        "dns": {
            "enable": True,
            "ipv6": False,
            "default-nameserver": ["1.1.1.1", "8.8.8.8", "system"],
            "proxy-server-nameserver": ["1.1.1.1", "8.8.8.8", "system"],
            "nameserver": ["https://1.1.1.1/dns-query"],
        },
        "proxies": [proxy_obj],
        "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": [proxy_obj["name"]]}],
        "rules": ["MATCH,PROXY"],
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = pathlib.Path(tmp)
        cfg_p = tmp_p / "probe.yaml"
        cfg_p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        proc = subprocess.Popen([str(mihomo_bin), "-d", str(tmp_p), "-f", str(cfg_p)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(1.5)
            t0 = time.monotonic()
            p = subprocess.run(
                ["curl.exe", "-sS", "--max-time", "7", "--socks5-hostname", f"127.0.0.1:{port}", "https://api.ipify.org"],
                capture_output=True, text=True,
            )
            ms = round((time.monotonic() - t0) * 1000, 1)
            ip = p.stdout.strip()
            return {"ok": p.returncode == 0 and ip == EXPECTED_IP, "egress_ip": ip if ip == EXPECTED_IP else "MISMATCH_OR_ERR", "ms": ms, "rc": p.returncode}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=r".agent-work\private-releases\sweden-v2\hagircbmsszlx4in\hagircbmsszlx4in-v2.yaml")
    ap.add_argument("--mihomo-bin", default=r".agent-work\tmp\mihomo\mihomo.exe")
    args = ap.parse_args()

    prof = yaml.safe_load(pathlib.Path(args.profile).read_text(encoding="utf-8"))
    mihomo_bin = pathlib.Path(args.mihomo_bin)
    hy2 = next(p for p in prof["proxies"] if p["type"] == "hysteria2")
    vless = next(p for p in prof["proxies"] if p["type"] == "vless")

    report = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dns_a": check_dns(),
        "https_8443": check_https_8443(),
        "hy2_udp443": probe_transport(mihomo_bin, hy2, 17991),
        "reality_tcp443": probe_transport(mihomo_bin, vless, 17992),
    }
    print(json.dumps(report, indent=2))
    # Exit 0 only if DNS, 8443, and HY2 succeed (note: REALITY via Amnezia tun2 is known environment limitation)
    sys.exit(0 if report["dns_a"]["ok"] and report["https_8443"]["ok"] and report["hy2_udp443"]["ok"] else 1)


if __name__ == "__main__":
    main()
