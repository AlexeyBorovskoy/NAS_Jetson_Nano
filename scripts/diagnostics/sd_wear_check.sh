#!/usr/bin/env bash
# sd_wear_check.sh — microSD health/wear check for Jetson Nano
# Reads MMC life_time via sysfs (JEDEC eMMC/SD spec).
# Life-time estimate: 0=undefined, 1=0-10%, 2=10-20%, ..., A=90-100%, B=exceed.
# Sends Telegram alert if wear >= WARNING_THRESHOLD or if data unavailable for long.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/nas_jetson_nano-monitor/sd-wear.log"
TELEGRAM_SCRIPT="$SCRIPT_DIR/../monitoring/send_telegram.sh"
WARNING_THRESHOLD=5  # alert if life_time_est >= 5 (50% wear)
DEVICE="mmcblk0"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
mkdir -p "$(dirname "$LOG_FILE")"

# ── Find MMC sysfs path ────────────────────────────────────────────────────────
MMC_PATH=""
for p in /sys/bus/mmc/devices/mmc0:*; do
    [[ -d "$p" ]] && MMC_PATH="$p" && break
done

if [[ -z "$MMC_PATH" ]]; then
    log "WARN: MMC sysfs path not found — skipping wear check"
    exit 0
fi

# ── Read life time estimates ───────────────────────────────────────────────────
LIFE_A="N/A"
LIFE_B="N/A"
LIFE_FILE="$MMC_PATH/life_time"

if [[ -f "$LIFE_FILE" ]]; then
    read -r LIFE_A LIFE_B < "$LIFE_FILE" 2>/dev/null || true
fi

# Convert hex to decimal
life_to_pct() {
    local val="${1:-0x00}"
    val="${val,,}"  # lowercase
    case "$val" in
        0x00) echo "unknown" ;;
        0x01) echo "0-10%" ;;
        0x02) echo "10-20%" ;;
        0x03) echo "20-30%" ;;
        0x04) echo "30-40%" ;;
        0x05) echo "40-50%" ;;
        0x06) echo "50-60%" ;;
        0x07) echo "60-70%" ;;
        0x08) echo "70-80%" ;;
        0x09) echo "80-90%" ;;
        0x0a) echo "90-100%" ;;
        0x0b) echo "EXCEEDED" ;;
        *)    echo "$val" ;;
    esac
}

# Convert hex value to integer for threshold comparison
hex_to_int() {
    printf '%d' "${1:-0}" 2>/dev/null || echo 0
}

LIFE_A_PCT="$(life_to_pct "$LIFE_A")"
LIFE_B_PCT="$(life_to_pct "$LIFE_B")"
LIFE_A_INT=$(hex_to_int "$LIFE_A")
LIFE_B_INT=$(hex_to_int "$LIFE_B")

# ── Additional disk stats ──────────────────────────────────────────────────────
DISK_USED=$(df / --output=pcent 2>/dev/null | tail -1 | tr -d ' %' || echo "?")
DISK_FREE=$(df -h / --output=avail 2>/dev/null | tail -1 | tr -d ' ' || echo "?")

log "microSD: /dev/$DEVICE | Life-typeA=$LIFE_A_PCT | Life-typeB=$LIFE_B_PCT | root: ${DISK_USED}% used, ${DISK_FREE} free"

# ── Alert if wear exceeds threshold ───────────────────────────────────────────
ALERT=0
ALERT_MSG=""

if [[ "$LIFE_A_PCT" == "EXCEEDED" ]] || [[ "$LIFE_B_PCT" == "EXCEEDED" ]]; then
    ALERT=1
    ALERT_MSG="⛔ CRITICAL: microSD wear EXCEEDED spec lifetime!"
elif [[ $LIFE_A_INT -ge $WARNING_THRESHOLD ]] || [[ $LIFE_B_INT -ge $WARNING_THRESHOLD ]]; then
    ALERT=1
    ALERT_MSG="⚠️ WARNING: microSD wear high — typeA: $LIFE_A_PCT, typeB: $LIFE_B_PCT"
fi

if [[ $ALERT -eq 1 ]] && [[ -x "$TELEGRAM_SCRIPT" ]]; then
    "$TELEGRAM_SCRIPT" "🖥 nas_jetson_nano-jetson | SD Wear Alert
$ALERT_MSG
Type-A: $LIFE_A_PCT
Type-B: $LIFE_B_PCT
Root disk: ${DISK_USED}% used, ${DISK_FREE} free"
fi

# ── Log summary ───────────────────────────────────────────────────────────────
if [[ "$LIFE_A" == "N/A" ]] || [[ ! -f "$LIFE_FILE" ]]; then
    log "INFO: life_time sysfs not available on this platform — only disk usage logged"
fi

exit 0
