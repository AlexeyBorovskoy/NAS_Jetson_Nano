#!/usr/bin/env bash
# vps_amnezia_monitor.sh — Monitor Amnezia VPN containers on VPS.
# Sends Telegram alert if any Amnezia container is not running.
# Deploy on VPS as cron: */5 * * * * /root/nas_jetson_nano/scripts/monitoring/vps_amnezia_monitor.sh
#
# IMPORTANT: NEVER stop/restart Amnezia containers — only monitor.
# ~25 family VPN clients depend on them. Alert only; human fixes.
set -euo pipefail

TELEGRAM_BOT_TOKEN="${NAS_JETSON_NANO_TELEGRAM_TOKEN:-}"
TELEGRAM_CHAT_ID="${NAS_JETSON_NANO_TELEGRAM_CHAT_ID:-}"
STATE_FILE="/var/lib/nas_jetson_nano-monitor/amnezia-state"
LOG_FILE="/var/log/nas_jetson_nano-monitor/amnezia-monitor.log"

mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }

send_telegram() {
    local msg="$1"
    [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && { log "WARN: Telegram not configured"; return; }
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${msg}" \
        -d "parse_mode=HTML" >/dev/null 2>&1 || true
}

# ── Find Amnezia containers ────────────────────────────────────────────────────
# Amnezia uses container names starting with "amnezia" or image names with "amnezia"
AMNEZIA_CONTAINERS=$(docker ps -a --format '{{.Names}} {{.Status}}' 2>/dev/null \
    | grep -i amnezia || true)

if [[ -z "$AMNEZIA_CONTAINERS" ]]; then
    log "WARN: No Amnezia containers found — docker may be down or containers renamed"
    PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || echo "ok")
    if [[ "$PREV_STATE" != "no_containers" ]]; then
        send_telegram "⚠️ <b>VPS Amnezia Monitor</b>
No Amnezia containers found!
Docker may be down or containers were renamed.
Check: ssh root@\$(hostname) 'docker ps -a | grep amnezia'"
        echo "no_containers" > "$STATE_FILE"
    fi
    exit 0
fi

# ── Check each Amnezia container is running ────────────────────────────────────
DOWN_CONTAINERS=""
while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    status=$(echo "$line" | awk '{print $2}')
    if [[ "$status" != "Up" ]]; then
        DOWN_CONTAINERS="$DOWN_CONTAINERS\n  ⛔ $name: $status"
        log "DOWN: $name ($status)"
    else
        log "OK: $name (running)"
    fi
done <<< "$AMNEZIA_CONTAINERS"

PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || echo "ok")

if [[ -n "$DOWN_CONTAINERS" ]]; then
    if [[ "$PREV_STATE" != "down" ]]; then
        send_telegram "🚨 <b>VPS Amnezia VPN DOWN!</b>
$(echo -e "$DOWN_CONTAINERS")

⚠️ ~25 family VPN clients affected.
DO NOT restart automatically — check manually.
Host: $(hostname)"
        echo "down" > "$STATE_FILE"
    fi
else
    if [[ "$PREV_STATE" == "down" ]]; then
        send_telegram "✅ <b>VPS Amnezia VPN restored</b>
All Amnezia containers running again.
Host: $(hostname)"
    fi
    echo "ok" > "$STATE_FILE"
fi

exit 0
