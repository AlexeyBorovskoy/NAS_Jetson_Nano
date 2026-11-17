#!/usr/bin/env python3
"""Android G1 pilot measurement script via uiautomator2 + adb forward."""

import argparse
import csv
import json
import pathlib
import statistics
import subprocess
import time
import uiautomator2 as u2

SERIAL = "hagircbmsszlx4in"
PKG = "com.follow.clash"
EXPECTED_EGRESS = "45.140.13.178"
LOCAL_PORT = 17891
REMOTE_PORT = 7890


def ensure_forward():
    subprocess.run(["adb", "-s", SERIAL, "forward", f"tcp:{LOCAL_PORT}", f"tcp:{REMOTE_PORT}"], check=True)


def remove_forward():
    subprocess.run(["adb", "-s", SERIAL, "forward", "--remove", f"tcp:{LOCAL_PORT}"], check=False)


def probe_egress(timeout_s=4):
    p = subprocess.run(
        ["curl.exe", "-sS", "--max-time", str(timeout_s), "--socks5-hostname", f"127.0.0.1:{LOCAL_PORT}", "https://api.ipify.org"],
        capture_output=True,
        text=True,
    )
    return p.returncode == 0 and p.stdout.strip() == EXPECTED_EGRESS, p.stdout.strip()


def stop_vpn(d):
    btn = d(description="Стоп")
    if btn.exists:
        btn.click()
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if not d(description="Стоп").exists:
                return True
            time.sleep(0.2)
    return not d(description="Стоп").exists


def find_start_button(d):
    for desc in ("Старт", "Запуск", "Start", "Подключить"):
        el = d(description=desc)
        if el.exists:
            return el
    # Fallback: button inside status card at [743,489,990,736] if label differs
    return None


def measure_runs(d, candidate, runs, network_id, profile_version, out_csv, out_jsonl):
    d.app_start(PKG, wait=True)
    panel_tab = d(description="Панель")
    if panel_tab.exists:
        panel_tab.click()
        time.sleep(0.5)

    fieldnames = [
        "run_id", "utc", "device_id", "os", "client_version", "core_version",
        "profile_version", "profile_sha256", "network_id", "scenario", "cache_state",
        "candidate", "chosen_transport", "t_ready_ms", "stage_timings",
        "request_status", "egress_verified", "result", "failure_stage", "error_code",
    ]
    out_csv_p = pathlib.Path(out_csv)
    out_jsonl_p = pathlib.Path(out_jsonl)
    write_header = not out_csv_p.exists()

    results = []
    with out_csv_p.open("a", newline="", encoding="utf-8") as f_csv, out_jsonl_p.open("a", encoding="utf-8") as f_js:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for i in range(runs):
            stop_vpn(d)
            time.sleep(1.0)
            start_btn = find_start_button(d)
            if not start_btn:
                # Print button descriptions to help identify start button if needed
                btns = [el.info.get("contentDescription") for el in d(className="android.widget.Button")]
                raise RuntimeError(f"Start button not found; visible buttons: {btns}")

            t0 = time.monotonic()
            start_btn.click()
            ensure_forward()

            t_ready = None
            egress_ok = False
            res = "FAILED"
            f_stage = ""
            err_code = ""
            deadline = t0 + 20.0

            while time.monotonic() < deadline:
                ok, out = probe_egress(timeout_s=4)
                if ok:
                    t_ready = round((time.monotonic() - t0) * 1000, 1)
                    egress_ok = True
                    res = "PASSED"
                    break
                time.sleep(0.2)
            else:
                f_stage = "https_probe"
                err_code = "T_READY_TIMEOUT"

            row = {
                "run_id": f"{candidate}-{i+1:02d}-{int(time.time())}",
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "device_id": SERIAL,
                "os": "Android-16",
                "client_version": "FlClash-0.9.3-2026112401",
                "core_version": "Mihomo-embedded",
                "profile_version": profile_version,
                "profile_sha256": "android-device",
                "network_id": network_id,
                "scenario": "reconnect",
                "cache_state": "warm",
                "candidate": candidate,
                "chosen_transport": "FlClash-TUN",
                "t_ready_ms": t_ready if t_ready is not None else "",
                "stage_timings": json.dumps({"t_ready_ms": t_ready}),
                "request_status": "200" if res == "PASSED" else "TIMEOUT",
                "egress_verified": egress_ok,
                "result": res,
                "failure_stage": f_stage,
                "error_code": err_code,
            }
            writer.writerow(row)
            f_js.write(json.dumps(row, ensure_ascii=False) + "\n")
            results.append((res, t_ready))
            print(f"Run {i+1}/{runs}: {res} t_ready={t_ready}ms")

    ok_vals = sorted([x[1] for x in results if x[0] == "PASSED" and x[1] is not None])
    print(f"SUMMARY {candidate}: ok={len(ok_vals)}/{len(results)}, med={round(statistics.median(ok_vals),1) if ok_vals else None}ms, max={max(ok_vals) if ok_vals else None}ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--network-id", default="android_mts_lte")
    ap.add_argument("--profile-version", default="v1")
    ap.add_argument("--out-csv", default="docs/sweden_vpn_v2/measurements.csv")
    ap.add_argument("--out-jsonl", default="docs/sweden_vpn_v2/measurements.jsonl")
    args = ap.parse_args()

    d = u2.connect(SERIAL)
    try:
        measure_runs(d, args.candidate, args.runs, args.network_id, args.profile_version, args.out_csv, args.out_jsonl)
    finally:
        remove_forward()


if __name__ == "__main__":
    main()
