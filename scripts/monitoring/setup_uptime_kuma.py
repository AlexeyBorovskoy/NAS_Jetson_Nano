#!/usr/bin/env python3
"""
setup_uptime_kuma.py — initialize Uptime Kuma admin + add 5 service monitors.
Run ON JETSON NANO from ~/nas_jetson_nano:
    python3 scripts/monitoring/setup_uptime_kuma.py

Requires:  pip3 install uptime-kuma-api  (auto-installed if missing)
"""
import os
import subprocess
import sys


def ensure_dep():
    try:
        import uptime_kuma_api  # noqa: F401
    except ImportError:
        print("[setup] Installing uptime-kuma-api...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "uptime-kuma-api", "-q"],
            stdout=sys.stderr,
        )


ensure_dep()

from uptime_kuma_api import UptimeKumaApi, MonitorType  # noqa: E402


# ---------------------------------------------------------------------------
# Config — reads from environment (export vars before running, or set .env)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(SCRIPT_DIR, "../../config/.env")

if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

ADMIN_USER = os.environ.get("UPTIME_KUMA_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("UPTIME_KUMA_ADMIN_PASSWORD", "")
if not ADMIN_PASS:
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    ADMIN_PASS = "".join(secrets.choice(alphabet) for _ in range(20))
    print(f"[setup] Generated password: {ADMIN_PASS}")
    print(f"[setup] Save to config/.env as UPTIME_KUMA_ADMIN_PASSWORD={ADMIN_PASS}")

JETSON_IP = os.environ.get("JETSON_LAN_IP", "192.168.0.50")

MONITORS = [
    {
        "type": MonitorType.HTTP,
        "name": "Nextcloud",
        "url": f"http://{JETSON_IP}:8080/status.php",
        "interval": 60,
        "maxretries": 3,
    },
    {
        "type": MonitorType.HTTP,
        "name": "Immich",
        "url": f"http://{JETSON_IP}:2283/api/server/ping",
        "interval": 60,
        "maxretries": 3,
    },
    {
        "type": MonitorType.HTTP,
        "name": "LLM Gateway",
        "url": f"http://{JETSON_IP}:8090/health",
        "interval": 60,
        "maxretries": 3,
    },
    {
        "type": MonitorType.HTTP,
        "name": "nas_jetson_nano-api",
        "url": f"http://{JETSON_IP}:8099/healthcheck",
        "interval": 60,
        "maxretries": 3,
    },
    {
        "type": MonitorType.HTTP,
        "name": "Netdata",
        "url": f"http://{JETSON_IP}:19999/api/v1/info",
        "interval": 120,
        "maxretries": 3,
    },
]

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
print(f"[setup] Connecting to Uptime Kuma at http://localhost:3001 ...")
api = UptimeKumaApi("http://localhost:3001")

try:
    api.setup(ADMIN_USER, ADMIN_PASS)
    print(f"[setup] Admin user '{ADMIN_USER}' created.")
    # setup() leaves socket in non-authed state — must reconnect
    api.disconnect()
    api = UptimeKumaApi("http://localhost:3001")
    api.login(ADMIN_USER, ADMIN_PASS)
    print("[setup] Logged in after setup.")
except Exception as e:
    err = str(e).lower()
    if any(x in err for x in ("already", "exist", "setup", "admin")):
        print(f"[setup] Admin already exists — logging in as '{ADMIN_USER}'...")
        api.disconnect()
        api = UptimeKumaApi("http://localhost:3001")
        api.login(ADMIN_USER, ADMIN_PASS)
    else:
        print(f"[setup] Error: {e}")
        sys.exit(1)

existing = {m["name"] for m in api.get_monitors()}
print(f"[setup] Existing monitors: {existing or 'none'}")

for m in MONITORS:
    if m["name"] in existing:
        print(f"  [skip] '{m['name']}' already exists")
        continue
    api.add_monitor(**m)
    print(f"  [+] Added: {m['name']}  →  {m['url']}")

api.disconnect()
print()
print("Done.")
print(f"  Uptime Kuma: http://{JETSON_IP}:3001")
print(f"  User: {ADMIN_USER}")
print(f"  Pass: {ADMIN_PASS}")
