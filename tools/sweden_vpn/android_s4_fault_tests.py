#!/usr/bin/env python3
"""Run isolated failover and fail-closed tests on Android FlClash and restore olga-android-v3.yaml."""

import subprocess
import time
import uiautomator2 as u2

SERIAL = "hagircbmsszlx4in"
PKG = "com.follow.clash"
ADB = r"C:\tools\platform-tools\adb.exe"
LOCAL_PORT = 17891
EXPECTED_EGRESS = "45.140.13.178"


def import_and_activate(d, filename):
    d(description="Профили").click()
    time.sleep(0.8)
    if not d(descriptionContains=filename).exists:
        d(description="Добавить профиль").click()
        time.sleep(0.8)
        d(description="Файл").click()
        time.sleep(2.0)
        if not d(text=filename).exists and d(scrollable=True).exists:
            d(scrollable=True).scroll.forward()
            time.sleep(0.8)
        d(text=filename).click(timeout=5.0)
        time.sleep(1.5)
    if not d(descriptionContains=filename).exists and d(scrollable=True).exists:
        d(scrollable=True).scroll.toEnd()
        time.sleep(0.5)
    d(descriptionContains=filename).click(timeout=5.0)
    time.sleep(2.0)


def probe(url, max_time=5):
    t0 = time.monotonic()
    p = subprocess.run(
        ["curl.exe", "-sS", "--max-time", str(max_time), "--socks5-hostname", f"127.0.0.1:{LOCAL_PORT}", "-w", " HTTP=%{http_code}", url],
        capture_output=True, text=True,
    )
    ms = round((time.monotonic() - t0) * 1000, 1)
    return p.returncode, p.stdout.strip(), ms


def main():
    d = u2.connect(SERIAL)
    d.app_start(PKG, wait=True)
    subprocess.run([ADB, "-s", SERIAL, "forward", f"tcp:{LOCAL_PORT}", "tcp:7890"], check=True)

    try:
        # 1. Failover test (SE-PRIMARY broken -> AUTO must pick SE-HY2)
        import_and_activate(d, "test-failover-v3.yaml")
        t0 = time.monotonic()
        fo_ok = False
        fo_ms = None
        fo_out = ""
        while time.monotonic() < t0 + 12.0:
            rc, out, _ = probe("https://api.ipify.org", max_time=4)
            if rc == 0 and EXPECTED_EGRESS in out:
                fo_ok = True
                fo_ms = round((time.monotonic() - t0) * 1000, 1)
                fo_out = out
                break
            time.sleep(0.3)

        d(description="Прокси").click()
        time.sleep(0.8)
        auto_desc = [e.info.get("contentDescription") for e in d(descriptionContains="AUTO") if e.info.get("contentDescription")]
        print(f"FAILOVER_TEST: ok={fo_ok} switch_ms={fo_ms} out={fo_out!r} ui_auto={auto_desc}")

        # 2. Fail-closed test (both broken -> api.ipify.org MUST fail, ya.ru DIRECT MUST pass)
        import_and_activate(d, "test-failclosed-v3.yaml")
        time.sleep(1.5)
        rc_vpn, out_vpn, ms_vpn = probe("https://api.ipify.org", max_time=5)
        rc_dir, out_dir, ms_dir = probe("https://ya.ru", max_time=5)
        print(f"FAIL_CLOSED_VPN_PROBE: rc={rc_vpn} out={out_vpn!r} ms={ms_vpn}")
        print(f"FAIL_CLOSED_DIRECT_RU: rc={rc_dir} out={out_dir!r} ms={ms_dir}")
    finally:
        # 3. Restore olga-android-v3.yaml
        import_and_activate(d, "olga-android-v3.yaml")
        time.sleep(1.5)
        rc_rest, out_rest, ms_rest = probe("https://api.ipify.org", max_time=6)
        print(f"RESTORED_V3: rc={rc_rest} out={out_rest!r} ms={ms_rest}")
        subprocess.run([ADB, "-s", SERIAL, "forward", "--remove", f"tcp:{LOCAL_PORT}"], check=False)


if __name__ == "__main__":
    main()
