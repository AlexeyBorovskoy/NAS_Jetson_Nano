#!/usr/bin/env bash
# ddns_duckdns.sh — Update DuckDNS record with current VPS public IP.
# Deploy on VPS: cron every 5 min or systemd timer.
# Setup: https://www.duckdns.org — register, get token, create subdomain.
#
# Required env vars (set in /etc/nas_jetson_nano-monitor/ddns.env on VPS):
#   DUCKDNS_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
#   DUCKDNS_DOMAIN=nas_jetson_nano-home          # subdomain only, without .duckdns.org
#
# Optional:
#   NAS_JETSON_NANO_TELEGRAM_TOKEN, NAS_JETSON_NANO_TELEGRAM_CHAT_ID — alert on IP change
set -euo pipefail

CONF="/etc/nas_jetson_nano-monitor/ddns.env"
[[ -f "$CONF" ]] && source "$CONF"

: "${DUCKDNS_TOKEN:?DUCKDNS_TOKEN not set. Add to $CONF}"
: "${DUCKDNS_DOMAIN:?DUCKDNS_DOMAIN not set. Add to $CONF}"

STATE_FILE="/var/lib/nas_jetson_nano-monitor/ddns-last-ip"
LOG_FILE="/var/log/nas_jetson_nano-monitor/ddns.log"
mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }

send_telegram() {
    local msg="$1"
    [[ -z "${NAS_JETSON_NANO_TELEGRAM_TOKEN:-}" || -z "${NAS_JETSON_NANO_TELEGRAM_CHAT_ID:-}" ]] && return
    curl -s -X POST "https://api.telegram.org/bot${NAS_JETSON_NANO_TELEGRAM_TOKEN}/sendMessage" \
        -d "chat_id=${NAS_JETSON_NANO_TELEGRAM_CHAT_ID}" \
        -d "text=${msg}" >/dev/null 2>&1 || true
}

# ── Get current public IP ──────────────────────────────────────────────────────
CURRENT_IP=$(curl -s --max-time 10 https://api.ipify.org 2>/dev/null \
          || curl -s --max-time 10 https://ifconfig.me 2>/dev/null \
          || echo "")

if [[ -z "$CURRENT_IP" ]]; then
    log "ERROR: Could not determine public IP"
    exit 1
fi

LAST_IP=$(cat "$STATE_FILE" 2>/dev/null || echo "")

if [[ "$CURRENT_IP" == "$LAST_IP" ]]; then
    log "IP unchanged: $CURRENT_IP — no update needed"
    exit 0
fi

# ── IP changed — update DuckDNS ───────────────────────────────────────────────
log "IP changed: $LAST_IP → $CURRENT_IP — updating DuckDNS"

RESPONSE=$(curl -s --max-time 10 \
    "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=${CURRENT_IP}")

if [[ "$RESPONSE" == "OK" ]]; then
    echo "$CURRENT_IP" > "$STATE_FILE"
    log "DuckDNS updated OK: ${DUCKDNS_DOMAIN}.duckdns.org → $CURRENT_IP"
    send_telegram "🌐 NAS_Jetson_Nano VPS IP changed: $LAST_IP → $CURRENT_IP
DNS updated: ${DUCKDNS_DOMAIN}.duckdns.org"
else
    log "ERROR: DuckDNS update failed (response: $RESPONSE)"
    send_telegram "⚠️ NAS_Jetson_Nano DDNS update FAILED
IP: $CURRENT_IP | Domain: ${DUCKDNS_DOMAIN}.duckdns.org
Response: $RESPONSE"
    exit 1
fi
