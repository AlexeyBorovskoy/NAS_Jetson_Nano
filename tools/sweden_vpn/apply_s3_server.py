#!/usr/bin/env python3
"""Apply S3 server changeset on VPS Sweden: add 12 v3 users alongside 7 v1 users.

Creates backup, verifies uniqueness, runs sing-box check before atomic swap,
reloads sing-box, and verifies old+new credentials on both HY2 and REALITY.
Never prints secrets.
"""

import base64
import json
import pathlib
import subprocess
import sys
import time


def main():
    staging_path = pathlib.Path(".agent-work/private-releases/sweden-v3/staging_singbox_users_v3.json")
    if not staging_path.exists():
        print(f"ERROR: Missing staging file {staging_path}", file=sys.stderr)
        sys.exit(2)

    b64 = base64.b64encode(staging_path.read_bytes()).decode("ascii")
    utc_tag = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    bash_cmd = f"""set -euo pipefail
BK="/root/backup-v3-{utc_tag}"
mkdir -p "$BK"
chmod 700 "$BK"
cp -a /etc/sing-box/config.json "$BK/config.json.before"
chmod 600 "$BK/config.json.before"
echo "BACKUP_DIR=$BK"

python3 - <<'PY' "{b64}"
import base64, json, os, sys
staging = json.loads(base64.b64decode(sys.argv[1]).decode())
src = '/etc/sing-box/config.json'
new_p = '/etc/sing-box/config.json.new'
with open(src) as f:
    cfg = json.load(f)

for ib in cfg['inbounds']:
    if ib['tag'] == 'vless-reality-in':
        existing_u = {{u['uuid'] for u in ib['users']}}
        existing_n = {{u['name'] for u in ib['users']}}
        for u in staging['vless_users_add']:
            assert u['uuid'] not in existing_u, f"Duplicate UUID for {{u['name']}}"
            assert u['name'] not in existing_n, f"Duplicate name {{u['name']}}"
            ib['users'].append(u)
            existing_u.add(u['uuid'])
            existing_n.add(u['name'])
        print("VLESS_USERS_COUNT=", len(ib['users']))
    elif ib['tag'] == 'hy2-in':
        existing_p = {{u['password'] for u in ib['users']}}
        existing_n = {{u['name'] for u in ib['users']}}
        for u in staging['hy2_users_add']:
            assert u['password'] not in existing_p, f"Duplicate HY2 pass for {{u['name']}}"
            assert u['name'] not in existing_n, f"Duplicate name {{u['name']}}"
            ib['users'].append(u)
            existing_p.add(u['password'])
            existing_n.add(u['name'])
        print("HY2_USERS_COUNT=", len(ib['users']))

st = os.stat(src)
with open(new_p, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\\n')
os.chmod(new_p, st.st_mode & 0o777)
os.chown(new_p, st.st_uid, st.st_gid)
PY

if ! sing-box check -c /etc/sing-box/config.json.new; then
  rm -f /etc/sing-box/config.json.new
  echo "ABORT: sing-box check failed"
  exit 1
fi

mv -f /etc/sing-box/config.json.new /etc/sing-box/config.json
systemctl reload sing-box
sleep 1.5

if ! systemctl is-active --quiet sing-box; then
  echo "ROLLBACK: sing-box not active after reload"
  cp -a "$BK/config.json.before" /etc/sing-box/config.json
  systemctl restart sing-box
  exit 1
fi

echo "SING_BOX_STATUS=$(systemctl is-active sing-box)"
echo "MAIN_PID=$(systemctl show -p MainPID --value sing-box)"
ss -tuln | grep ':443 '

# Functional check on VPS: old v1 user[0] and new v3 user[-1] for both HY2 and REALITY
python3 - <<'PY'
import base64, json, os, subprocess, tempfile, time
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

with open('/etc/sing-box/config.json') as f:
    srv = json.load(f)
vless = next(i for i in srv['inbounds'] if i['tag'] == 'vless-reality-in')
hy2 = next(i for i in srv['inbounds'] if i['tag'] == 'hy2-in')

priv_b = base64.urlsafe_b64decode(vless['tls']['reality']['private_key'] + '==')
priv = x25519.X25519PrivateKey.from_private_bytes(priv_b[:32])
pub_b64 = base64.urlsafe_b64encode(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode().rstrip('=')

def test_out(label, out, port):
    cfg = {{"log": {{"level": "error"}}, "inbounds": [{{"type": "socks", "tag": "s", "listen": "127.0.0.1", "listen_port": port}}], "outbounds": [out]}}
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as tf:
        json.dump(cfg, tf)
        path = tf.name
    p = subprocess.Popen(['sing-box', 'run', '-c', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(1.2)
        c = subprocess.run(['curl', '-sS', '--max-time', '6', '--socks5-hostname', f'127.0.0.1:{{port}}', 'https://api.ipify.org'], capture_output=True, text=True)
        print(f"TEST_{{label}}: rc={{c.returncode}} ip={{c.stdout.strip()!r}}")
        assert c.returncode == 0 and c.stdout.strip() == '45.140.13.178', f"Failed {{label}}"
    finally:
        p.terminate()
        p.wait(timeout=3)
        os.unlink(path)

for tag, idx in [('V1_OLD', 0), ('V3_NEW', -1)]:
    test_out(f"HY2_{{tag}}", {{
        "type": "hysteria2", "tag": "h", "server": "127.0.0.1", "server_port": 443,
        "password": hy2['users'][idx]['password'],
        "tls": {{"enabled": True, "server_name": "vpn.privet.dynv6.net"}}
    }}, 18091)
    test_out(f"REALITY_{{tag}}", {{
        "type": "vless", "tag": "v", "server": "127.0.0.1", "server_port": 443,
        "uuid": vless['users'][idx]['uuid'], "flow": "xtls-rprx-vision",
        "tls": {{
            "enabled": True, "server_name": "www.googletagmanager.com",
            "utls": {{"enabled": True, "fingerprint": "firefox"}},
            "reality": {{"enabled": True, "public_key": pub_b64, "short_id": vless['tls']['reality']['short_id'][0]}}
        }}
    }}, 18092)
PY

echo "=== MONITOR ==="
curl -s http://127.0.0.1:8088/api/status | grep -o '"alerts": \[[^]]*\]'
"""

    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "aeza-sweden", "bash -s"], input=bash_cmd.encode("utf-8"), capture_output=True)
    print(p.stdout.decode("utf-8", errors="replace").strip())
    if p.stderr:
        print(p.stderr.decode("utf-8", errors="replace").strip(), file=sys.stderr)
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
