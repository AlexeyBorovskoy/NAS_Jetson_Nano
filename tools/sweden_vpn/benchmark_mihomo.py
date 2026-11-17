#!/usr/bin/env python3
"""Isolated A/B startup & T_ready benchmark runner for Sweden VPN Mihomo profiles.

Runs mihomo.exe in local SOCKS5/mixed mode (tun.enable=false) so it does not alter
OS routing tables or active VPN adapters. Measures T_ready from process launch
to first verified HTTPS response through Sweden VPS (45.140.13.178).
Never prints or writes secrets (UUID, passwords, keys) to logs or CSV/JSONL.
"""

import argparse
import copy
import csv
import json
import os
import pathlib
import shutil
import socket
import statistics
import subprocess
import time
import urllib.request
import yaml

EXPECTED_EGRESS = "45.140.13.178"
DEFAULT_BASE_PROFILE = pathlib.Path(r"C:\Users\Alexey\.ssh\new-vps-se\FAMILY-SE-Alexey-Windows.yaml")
DEFAULT_MIHOMO_BIN = pathlib.Path(r".agent-work\tmp\mihomo\mihomo.exe")
DEFAULT_WORKDIR = pathlib.Path(r".agent-work\tmp\bench_mihomo")


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return round(sorted_vals[f], 1)
    return round(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f), 1)


def wait_port(host, port, timeout_s=10.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def build_candidate(base_cfg, candidate_name, mixed_port, api_port):
    cfg = copy.deepcopy(base_cfg)
    cfg["mixed-port"] = mixed_port
    cfg["allow-lan"] = False
    cfg["external-controller"] = f"127.0.0.1:{api_port}"
    cfg["secret"] = ""
    cfg["log-level"] = "warning"
    cfg["tun"] = {"enable": False}

    if candidate_name == "v1_current":
        pass
    elif candidate_name == "v1_ip_endpoint_h01":
        for p in cfg.get("proxies", []):
            p["server"] = EXPECTED_EGRESS
    elif candidate_name == "v1_reality_only":
        cfg["proxies"] = [p for p in cfg["proxies"] if p["type"] == "vless"]
        cfg["proxy-groups"] = [{"name": "PROXY", "type": "select", "proxies": ["SE-PRIMARY"]}]
    elif candidate_name == "v1_hy2_only":
        cfg["proxies"] = [p for p in cfg["proxies"] if p["type"] == "hysteria2"]
        cfg["proxy-groups"] = [{"name": "PROXY", "type": "select", "proxies": ["SE-HY2"]}]
    elif candidate_name in ("v2_hy2_first_fallback", "v2_reality_first_fallback"):
        cfg["unified-delay"] = True
        cfg["tcp-concurrent"] = True
        cfg["sniffer"] = {
            "enable": True,
            "parse-pure-ip": True,
            "override-destination": True,
            "sniff": {"HTTP": {"ports": [80, 8080]}, "TLS": {"ports": [443, 8443]}, "QUIC": {"ports": [443]}},
        }
        dns = cfg.setdefault("dns", {})
        dns["respect-rules"] = True
        dns["default-nameserver"] = ["1.1.1.1", "8.8.8.8", "system"]
        dns["proxy-server-nameserver"] = ["1.1.1.1", "8.8.8.8", "system"]
        dns["direct-nameserver"] = ["system"]
        dns["nameserver"] = ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"]
        dns["fallback"] = ["tls://1.1.1.1:853", "tls://8.8.8.8:853"]
        dns["fallback-filter"] = {"geoip": False, "ipcidr": ["240.0.0.0/4"]}
        fip = dns.setdefault("fake-ip-filter", [])
        if "vpn.privet.dynv6.net" not in fip:
            fip.append("vpn.privet.dynv6.net")

        order = ["SE-HY2", "SE-PRIMARY"] if candidate_name == "v2_hy2_first_fallback" else ["SE-PRIMARY", "SE-HY2"]
        cfg["proxy-groups"] = [
            {
                "name": "PROXY",
                "type": "select",
                "proxies": ["AUTO", "SE-PRIMARY", "SE-HY2"],
            },
            {
                "name": "AUTO",
                "type": "fallback",
                "proxies": order,
                "url": "https://www.gstatic.com/generate_204",
                "interval": 120,
                "timeout": 3000,
                "lazy": False,
                "max-failed-times": 2,
            },
        ]
    else:
        raise ValueError(f"Unknown candidate: {candidate_name}")

    return cfg


def query_chosen_transport(api_port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{api_port}/proxies/PROXY", timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
        now = data.get("now")
        if now == "AUTO":
            with urllib.request.urlopen(f"http://127.0.0.1:{api_port}/proxies/AUTO", timeout=2) as r2:
                d2 = json.loads(r2.read().decode("utf-8"))
            return f"AUTO->{d2.get('now')}"
        return str(now)
    except Exception:
        return "UNKNOWN"


def run_single(mihomo_bin, cfg_path, run_dir, mixed_port, api_port, timeout_s=15.0):
    t0 = time.monotonic()
    proc = subprocess.Popen(
        [str(mihomo_bin), "-d", str(run_dir), "-f", str(cfg_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    t_port = None
    t_ready = None
    egress = None
    chosen = "UNKNOWN"
    failure_stage = ""
    error_code = ""
    result = "FAILED"

    try:
        if not wait_port("127.0.0.1", mixed_port, timeout_s=8.0):
            failure_stage = "core_startup"
            error_code = "MIXED_PORT_TIMEOUT"
            return result, None, None, chosen, False, failure_stage, error_code

        t_port = round((time.monotonic() - t0) * 1000, 1)
        deadline = t0 + timeout_s
        while time.monotonic() < deadline:
            rem = max(1.0, deadline - time.monotonic())
            p = subprocess.run(
                [
                    "curl.exe",
                    "-sS",
                    "--max-time",
                    str(min(6, int(rem) + 1)),
                    "--socks5-hostname",
                    f"127.0.0.1:{mixed_port}",
                    "https://api.ipify.org",
                ],
                capture_output=True,
                text=True,
            )
            if p.returncode == 0 and p.stdout.strip() == EXPECTED_EGRESS:
                t_ready = round((time.monotonic() - t0) * 1000, 1)
                egress = p.stdout.strip()
                chosen = query_chosen_transport(api_port)
                result = "PASSED"
                break
            time.sleep(0.15)
        else:
            failure_stage = "https_probe"
            error_code = "T_READY_TIMEOUT"
            chosen = query_chosen_transport(api_port)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)

    return result, t_port, t_ready, chosen, (egress == EXPECTED_EGRESS), failure_stage, error_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", nargs="+", default=[
        "v1_current",
        "v1_ip_endpoint_h01",
        "v1_reality_only",
        "v1_hy2_only",
        "v2_hy2_first_fallback",
        "v2_reality_first_fallback",
    ])
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--cache-state", choices=["cold", "warm"], default="cold")
    ap.add_argument("--network-id", default="windows_via_amnezia_tun2")
    ap.add_argument("--out-csv", default="docs/sweden_vpn_v2/measurements.csv")
    ap.add_argument("--out-jsonl", default="docs/sweden_vpn_v2/measurements.jsonl")
    args = ap.parse_args()

    base_cfg = yaml.safe_load(DEFAULT_BASE_PROFILE.read_text(encoding="utf-8"))
    if DEFAULT_WORKDIR.exists():
        shutil.rmtree(DEFAULT_WORKDIR, ignore_errors=True)
    DEFAULT_WORKDIR.mkdir(parents=True, exist_ok=True)

    out_csv = pathlib.Path(args.out_csv)
    out_jsonl = pathlib.Path(args.out_jsonl)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "run_id", "utc", "device_id", "os", "client_version", "core_version",
        "profile_version", "profile_sha256", "network_id", "scenario", "cache_state",
        "candidate", "chosen_transport", "t_ready_ms", "stage_timings",
        "request_status", "egress_verified", "result", "failure_stage", "error_code",
    ]
    write_header = not out_csv.exists()

    summary = {}
    with out_csv.open("a", newline="", encoding="utf-8") as f_csv, out_jsonl.open("a", encoding="utf-8") as f_js:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for i in range(args.runs):
            for idx, cand in enumerate(args.candidates):
                mixed_port = 17910 + idx * 2
                api_port = 19110 + idx * 2
                cand_dir = DEFAULT_WORKDIR / cand
                if args.cache_state == "cold" and cand_dir.exists():
                    shutil.rmtree(cand_dir, ignore_errors=True)
                cand_dir.mkdir(parents=True, exist_ok=True)

                cfg = build_candidate(base_cfg, cand, mixed_port, api_port)
                cfg_path = cand_dir / "config.yaml"
                cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")

                utc_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                run_id = f"{cand}-{args.cache_state}-{i+1:02d}-{int(time.time())}"
                res, t_port, t_ready, chosen, egress_ok, f_stage, err_code = run_single(
                    DEFAULT_MIHOMO_BIN, cfg_path, cand_dir, mixed_port, api_port
                )
                row = {
                    "run_id": run_id,
                    "utc": utc_now,
                    "device_id": "alexey-windows",
                    "os": "Windows",
                    "client_version": "FlClash-0.9.3+2026110401",
                    "core_version": "Mihomo-v1.19.34",
                    "profile_version": "v2-candidate" if cand.startswith("v2") else "v1",
                    "profile_sha256": "isolated-bench",
                    "network_id": args.network_id,
                    "scenario": f"{args.cache_state}_start",
                    "cache_state": args.cache_state,
                    "candidate": cand,
                    "chosen_transport": chosen,
                    "t_ready_ms": t_ready if t_ready is not None else "",
                    "stage_timings": json.dumps({"core_port_ms": t_port, "t_ready_ms": t_ready}),
                    "request_status": "200" if res == "PASSED" else "TIMEOUT",
                    "egress_verified": egress_ok,
                    "result": res,
                    "failure_stage": f_stage,
                    "error_code": err_code,
                }
                writer.writerow(row)
                f_js.write(json.dumps(row, ensure_ascii=False) + "\n")
                summary.setdefault(cand, []).append((res, t_ready, chosen))

                if cand_dir.exists() and args.cache_state == "cold":
                    shutil.rmtree(cand_dir, ignore_errors=True)

    print("=== BENCHMARK SUMMARY ===")
    for cand, items in summary.items():
        ok_vals = sorted([x[1] for x in items if x[0] == "PASSED" and x[1] is not None])
        transports = sorted(set(x[2] for x in items))
        print(
            f"{cand}: ok={len(ok_vals)}/{len(items)}, "
            f"med={round(statistics.median(ok_vals),1) if ok_vals else None}ms, "
            f"p95={percentile(ok_vals, 95)}ms, "
            f"max={max(ok_vals) if ok_vals else None}ms, "
            f"transports={transports}"
        )


if __name__ == "__main__":
    main()
