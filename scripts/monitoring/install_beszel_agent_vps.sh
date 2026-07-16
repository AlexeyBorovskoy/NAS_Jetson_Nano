#!/usr/bin/env bash
# NAS_Jetson_Nano — install Beszel agent on VPS (amd64)
# Run on VPS as root after Hub is already running on the same machine.
#
# Usage:
#   bash install_beszel_agent_vps.sh [hub-public-key]
#
# If hub-public-key is not provided, reads it from the Hub data directory.
# Hub data is expected at /opt/nas_jetson_nano/beszel-hub/data/id_ed25519
#
# After install, add VPS in Hub UI (or via API):
#   Name: vps-vienna
#   Host: 127.0.0.1
#   Port: 45877
set -euo pipefail

AGENT_PORT="45877"
BINARY="/usr/local/bin/beszel-agent-vps"
WRAPPER="/usr/local/sbin/start-beszel-agent-vps.sh"
SERVICE="/etc/systemd/system/beszel-agent-vps.service"
HUB_KEY_FILE="/opt/nas_jetson_nano/beszel-hub/data/id_ed25519"

# ── 1. get hub public key ─────────────────────────────────────────────────────
HUB_KEY="${1:-}"
if [ -z "$HUB_KEY" ]; then
    if [ -f "$HUB_KEY_FILE" ]; then
        HUB_KEY=$(ssh-keygen -y -f "$HUB_KEY_FILE")
        echo "[1/4] Hub key read from $HUB_KEY_FILE"
    else
        echo "ERROR: provide hub public key as argument or have Hub data at $HUB_KEY_FILE"
        exit 1
    fi
else
    echo "[1/4] Hub key provided as argument"
fi

# ── 2. download amd64 binary ──────────────────────────────────────────────────
VERSION="v0.18.7"
echo "[2/4] Downloading Beszel agent (amd64, $VERSION)..."
curl -sL "https://github.com/henrygd/beszel/releases/download/${VERSION}/beszel-agent_linux_amd64.tar.gz" \
    | tar -xz -C /tmp/ beszel-agent
mv /tmp/beszel-agent "$BINARY"
chmod +x "$BINARY"
echo "    → $BINARY ($("$BINARY" --version 2>&1))"

# ── 3. wrapper script (avoids ExecStart quoting issues with key spaces) ───────
echo "[3/4] Installing wrapper + systemd service..."
cat > "$WRAPPER" << SCRIPT
#!/bin/bash
exec $BINARY -l 0.0.0.0:${AGENT_PORT} -k '${HUB_KEY}'
SCRIPT
chmod +x "$WRAPPER"

cat > "$SERVICE" << UNIT
[Unit]
Description=Beszel Agent — VPS Vienna monitoring
Documentation=https://beszel.dev
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=$WRAPPER
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable beszel-agent-vps
systemctl restart beszel-agent-vps

# ── 4. verify ─────────────────────────────────────────────────────────────────
echo "[4/4] Checking agent..."
sleep 3
if systemctl is-active --quiet beszel-agent-vps; then
    echo "    ✓ VPS agent running on port ${AGENT_PORT}"
else
    echo "    ✗ Agent failed:"
    journalctl -u beszel-agent-vps --no-pager -n 10
    exit 1
fi

echo ""
echo "VPS agent installed. Add to Hub:"
echo "  Name: vps-vienna"
echo "  Host: 127.0.0.1"
echo "  Port: ${AGENT_PORT}"
echo ""
echo "Or via API (if Hub is running locally on port 8091):"
echo "  python3 /opt/nas_jetson_nano/beszel-hub/add_system_api.py vps-vienna 127.0.0.1 ${AGENT_PORT}"
