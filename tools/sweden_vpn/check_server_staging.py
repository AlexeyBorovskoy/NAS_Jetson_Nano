#!/usr/bin/env python3
"""Verify staged v3 sing-box users (7 v1 + 12 v3 = 19) on VPS via isolated /tmp sing-box check."""

import base64
import json
import pathlib
import subprocess
import sys


def main():
    staging_path = pathlib.Path(".agent-work/private-releases/sweden-v3/staging_singbox_users_v3.json")
    if not staging_path.exists():
        print(f"ERROR: Missing staging file {staging_path}", file=sys.stderr)
        sys.exit(2)

    b64 = base64.b64encode(staging_path.read_bytes()).decode("ascii")
    bash_cmd = f"""set -euo pipefail
TMPF=$(mktemp /tmp/sb-staging-XXXXXX.json)
trap 'rm -f "$TMPF"' EXIT
python3 - <<'PY' "$TMPF" "{b64}"
import base64, json, sys
out_path, b64_data = sys.argv[1], sys.argv[2]
staging = json.loads(base64.b64decode(b64_data).decode())
with open('/etc/sing-box/config.json') as f:
    cfg = json.load(f)
for ib in cfg['inbounds']:
    if ib['tag'] == 'vless-reality-in':
        existing = {{u['uuid'] for u in ib['users']}}
        for u in staging['vless_users_add']:
            assert u['uuid'] not in existing, f"Duplicate UUID {{u['name']}}"
            ib['users'].append(u)
        print("STAGING_VLESS_TOTAL=", len(ib['users']))
    elif ib['tag'] == 'hy2-in':
        existing = {{u['password'] for u in ib['users']}}
        for u in staging['hy2_users_add']:
            assert u['password'] not in existing, f"Duplicate HY2 {{u['name']}}"
            ib['users'].append(u)
        print("STAGING_HY2_TOTAL=", len(ib['users']))
with open(out_path, 'w') as f:
    json.dump(cfg, f)
PY
sing-box check -c "$TMPF"
echo "SING_BOX_STAGING_CHECK=PASS"
"""
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "aeza-sweden", "bash -s"], input=bash_cmd.encode("utf-8"), capture_output=True)
    print(p.stdout.decode("utf-8", errors="replace").strip())
    if p.stderr:
        print(p.stderr.decode("utf-8", errors="replace").strip(), file=sys.stderr)
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
