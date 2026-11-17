#!/usr/bin/env python3
"""Android S4 reconnect/startup timing benchmark via uiautomator2 + adb forward."""

import argparse
import csv
import pathlib
import statistics
import subprocess
import time
import uiautomator2 as u2

SERIAL = "hagircbmsszlx4in"
PKG = "com.follow.clash"
EXPECTED_EGRESS = "45.140.13.178"
LOCAL_PORT = 17891


def scroll_panel_top(d):
    d(description="Панель").click()
    time.sleep(0.5)
    if d(scrollable=True).exists:
        d(scrollable=True).scroll.toBeginning()
        time.sleep(0.4)


def click_vpn_toggle(d):
    for desc in ("Стоп", "Старт", "Запуск", "Start"):
        el = d(description=desc)
        if el.exists:
            b = el.info.get("bounds", {})
            if b.get("top", 0) > 200:
                el.click()
                return desc
    # Fallback by known status card button bounds [743,489,990,736]
    d.click(866, 612)
    return "BOUNDS_CLICK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--network", default="CORP_WIFI_192_168_75")
    ap.add_argument("--out-csv", default="reports/sweden-v3/measurements/android_s4_reconnect.csv")
    args = ap.parse_args()

    d = u2.connect(SERIAL)
    d.app_start(PKG, wait=True)
    scroll_panel_top(d)

    out_p = pathlib.Path(args.out_csv)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fields = ["run_idx", "utc", "network", "profile", "t_ready_ms", "egress_ip", "result"]
    rows = []

    try:
        for i in range(args.runs):
            # Stop if running
            if d(description="Стоп").exists:
                click_vpn_toggle(d)
                time.sleep(1.5)

            # Start & measure t0 -> t_success
            t0 = time.monotonic()
            click_vpn_toggle(d)
            subprocess.run(["adb", "-s", SERIAL, "forward", f"tcp:{LOCAL_PORT}", "tcp:7890"], check=True, stdout=subprocess.DEVNULL)

            t_ready = None
            ip_val = ""
            res = "FAILED"
            deadline = t0 + 15.0
            while time.monotonic() < deadline:
                p = subprocess.run(
                    ["curl.exe", "-sS", "--max-time", "4", "--socks5-hostname", f"127.0.0.1:{LOCAL_PORT}", "https://api.ipify.org"],
                    capture_output=True, text=True,
                )
                if p.returncode == 0 and p.stdout.strip() == EXPECTED_EGRESS:
                    t_ready = round((time.monotonic() - t0) * 1000, 1)
                    ip_val = p.stdout.strip()
                    res = "PASSED"
                    break
                time.sleep(0.15)

            rows.append({
                "run_idx": i + 1,
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "network": args.network,
                "profile": "olga-android-v3",
                "t_ready_ms": t_ready if t_ready is not None else "",
                "egress_ip": ip_val,
                "result": res,
            })
            print(f"Run {i+1}/{args.runs}: {res} t_ready={t_ready}ms")
    finally:
        subprocess.run(["adb", "-s", SERIAL, "forward", "--remove", f"tcp:{LOCAL_PORT}"], check=False, stdout=subprocess.DEVNULL)

    with out_p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    ok_vals = sorted([r["t_ready_ms"] for r in rows if r["result"] == "PASSED"])
    print(f"SUMMARY: ok={len(ok_vals)}/{len(rows)}, min={min(ok_vals) if ok_vals else None}ms, med={round(statistics.median(ok_vals),1) if ok_vals else None}ms, max={max(ok_vals) if ok_vals else None}ms")


if __name__ == "__main__":
    main()
