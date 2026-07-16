#!/usr/bin/env bash
# NAS_Jetson_Nano — install Beszel agent as systemd binary (no Docker needed)
# Run on Jetson after Hub is started on VPS and Hub SSH key is known.
#
# Usage:
#   sudo bash install_beszel_agent.sh <hub-public-key>
#
# <hub-public-key> — ed25519 public key from VPS:
#   ssh root@193.8.215.130 "cat /opt/nas_jetson_nano/beszel-hub/data/ssh_host_ed25519_key.pub"
#
# After install, add Jetson in Hub UI:
#   Name: jetson-nano
#   Host: 127.0.0.1:45876   (VPS-side tunnel address)
set -euo pipefail

AGENT_PORT="45876"
BINARY="/usr/local/bin/beszel-agent"
ENV_FILE="/etc/beszel-agent.env"
SERVICE="/etc/systemd/system/beszel-agent.service"

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: run as root (sudo bash $0 <key>)"
    exit 1
fi

HUB_KEY="${1:-}"
if [ -z "$HUB_KEY" ]; then
    echo "Usage: sudo bash $0 '<hub-ssh-public-key>'"
    echo ""
    echo "Get key from VPS:"
    echo "  ssh root@193.8.215.130 \"cat /opt/nas_jetson_nano/beszel-hub/data/ssh_host_ed25519_key.pub\""
    exit 1
fi

# ── 1. download arm64 binary ─────────────────────────────────────────────────
echo "[1/4] Downloading Beszel agent (arm64)..."
LATEST=$(curl -sS "https://api.github.com/repos/henrygd/beszel/releases/latest" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null \
    || echo "latest")

curl -sL "https://github.com/henrygd/beszel/releases/download/${LATEST}/beszel-agent_linux_arm64.tar.gz" \
    | tar -xz -C /tmp/ beszel-agent 2>/dev/null \
    || curl -sL "https://github.com/henrygd/beszel/releases/latest/download/beszel-agent_linux_arm64.tar.gz" \
    | tar -xz -C /tmp/ beszel-agent

mv /tmp/beszel-agent "$BINARY"
chmod +x "$BINARY"
echo "    → $BINARY (version: $("$BINARY" --version 2>&1 || echo 'unknown'))"

# ── 2. env file with Hub public key ─────────────────────────────────────────
echo "[2/4] Writing env file..."
cat > "$ENV_FILE" << EOF
# Beszel agent configuration — do not commit
BESZEL_HUB_KEY=${HUB_KEY}
BESZEL_LISTEN=0.0.0.0:${AGENT_PORT}
EOF
chmod 600 "$ENV_FILE"
echo "    → $ENV_FILE"

# ── 3. systemd service ───────────────────────────────────────────────────────
echo "[3/4] Installing systemd service..."
cat > "$SERVICE" << 'UNIT'
[Unit]
Description=Beszel Agent — NAS_Jetson_Nano metrics
Documentation=https://beszel.dev
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/beszel-agent.env
ExecStart=/usr/local/bin/beszel-agent \
    -l ${BESZEL_LISTEN} \
    -k ${BESZEL_HUB_KEY}
Restart=always
RestartSec=10
# Allow reading /proc, /sys for metrics
AmbientCapabilities=CAP_NET_RAW CAP_DAC_READ_SEARCH

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable beszel-agent
systemctl restart beszel-agent
echo "    → beszel-agent.service enabled and started"

# ── 4. verify ────────────────────────────────────────────────────────────────
echo "[4/4] Checking agent..."
sleep 3
if systemctl is-active --quiet beszel-agent; then
    echo "    ✓ Agent running on port ${AGENT_PORT}"
else
    echo "    ✗ Agent failed to start:"
    journalctl -u beszel-agent --no-pager -n 20
    exit 1
fi

echo ""
echo "Agent installed. Now:"
echo "  1. Open http://193.8.215.130:8091 in browser"
echo "  2. Add system: Name=jetson-nano, Host=127.0.0.1:${AGENT_PORT}"
echo "  3. Status should turn green within 30 seconds"
