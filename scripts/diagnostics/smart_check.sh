#!/usr/bin/env bash
# smart_check.sh — SMART health check for USB SSD enclosure
#
# Supports JMS583 (JMicron USB 3.2, SAT passthrough) and RTL9210B-CG (SCSI only).
# Run as root. Sends Telegram alert on SMART error.
#
# Usage: sudo bash scripts/diagnostics/smart_check.sh [/dev/sda]

set -uo pipefail

DEV="${1:-/dev/sda}"
LOG_TAG="nas_jetson_nano-smart-check"
LOG_FILE="/var/log/nas_jetson_nano-monitor/smart-check.log"

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
[[ -f /etc/nas_jetson_nano-monitor/telegram.env ]] && source /etc/nas_jetson_nano-monitor/telegram.env

HOSTNAME_SHORT="$(hostname -s)"

log()  { local msg="$1"; echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $msg" | tee -a "$LOG_FILE"; }
warn() { local msg="$1"; echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN]  $msg" | tee -a "$LOG_FILE"; }
err()  { local msg="$1"; echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $msg" | tee -a "$LOG_FILE" >&2; }

tg_send() {
    local msg="$1"
    [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return 0
    curl -sf --max-time 10 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=[${HOSTNAME_SHORT}] ${msg}" \
        -d "parse_mode=HTML" > /dev/null || true
}

mkdir -p "$(dirname "$LOG_FILE")"
log "=== SMART check started: $DEV ==="

if [[ ! -b "$DEV" ]]; then
    err "Device $DEV not found or not a block device"
    tg_send "⚠️ SMART check: $DEV не найден!"
    exit 1
fi

# Detect SMART passthrough mode
# JMS583 (152d:a583): supports SAT passthrough with '-d sat,auto'
# RTL9210B-CG (0bda:9210): only SCSI, SMART unavailable
SMART_TYPE="sat,auto"
RAW_OUTPUT=$(smartctl -d "$SMART_TYPE" -i "$DEV" 2>&1)

# Check if SAT passthrough worked
if echo "$RAW_OUTPUT" | grep -q "SMART support is:.*Unavailable"; then
    log "SAT passthrough: SMART not available (bridge doesn't forward ATA SMART)"
    log "Device info via SCSI passthrough:"
    echo "$RAW_OUTPUT" | grep -E "Vendor|Product|Revision|Capacity|Rotation|Serial" | while IFS= read -r line; do
        log "  $line"
    done
    log "SMART check: PASS (no ATA SMART available — relying on filesystem health)"
    exit 0
fi

# SAT worked — check SMART health
HEALTH=$(smartctl -d "$SMART_TYPE" -H "$DEV" 2>&1)
log "SMART health output:"
echo "$HEALTH" | while IFS= read -r line; do log "  $line"; done

if echo "$HEALTH" | grep -q "PASSED"; then
    log "SMART: PASSED ✅"
    tg_send "✅ SMART check: $DEV — PASSED"
elif echo "$HEALTH" | grep -q "FAILED"; then
    err "SMART: FAILED ❌"
    tg_send "🚨 SMART FAILED: $DEV может выйти из строя! Срочно сделать бэкап данных!"
    exit 2
else
    warn "SMART health status unknown"
    log "Full SMART output:"
    smartctl -d "$SMART_TYPE" -a "$DEV" 2>&1 | while IFS= read -r line; do log "  $line"; done
fi

log "=== SMART check complete ==="
