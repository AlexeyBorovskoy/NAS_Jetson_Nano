#!/usr/bin/env bash
# jms583_health.sh — hourly health monitor for JMS583 USB SSD enclosure
#
# Collects: USB stability, I/O stats, disk health, SMART info
# Logs to: /var/log/nas_jetson_nano-monitor/jms583-health.log
# Telegram: error alerts immediately, daily summary at 09:00
#
# Deploy:
#   sudo cp scripts/monitoring/jms583_health.sh /usr/local/sbin/
#   sudo chmod +x /usr/local/sbin/jms583_health.sh

set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
DEV="/dev/sda"
PART="/dev/sda1"
MOUNT="/mnt/storage"
USB_VID="152d"
USB_PID="a583"
USB_PORT="2-1.3"          # USB 3.0 SuperSpeed port
LOG_FILE="/var/log/nas_jetson_nano-monitor/jms583-health.log"
STATE_DIR="/var/lib/nas_jetson_nano-monitor"
STATE_FILE="$STATE_DIR/jms583-last-run"
DAILY_SENT_FILE="$STATE_DIR/jms583-daily-sent"
LOG_TAG="nas_jetson_nano-jms583"

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
[[ -f /etc/nas_jetson_nano-monitor/telegram.env ]] && source /etc/nas_jetson_nano-monitor/telegram.env

HOSTNAME_SHORT="$(hostname -s)"

# ── Helpers ───────────────────────────────────────────────────────────────────
log() {
    local ts msg
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    msg="$*"
    echo "$ts  $msg" | tee -a "$LOG_FILE"
    echo "$ts $msg" | systemd-cat -t "$LOG_TAG" -p info 2>/dev/null || true
}

tg_send() {
    local msg="$1"
    [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return 0
    curl -sf --max-time 15 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${msg}" \
        -d "parse_mode=HTML" > /dev/null || true
}

# ── Init ──────────────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_FILE")" "$STATE_DIR"
NOW=$(date +%s)
HOUR=$(date +%H)

log "══════════════════════════════════════════════════"
log "JMS583 health check — $(date '+%Y-%m-%d %H:%M:%S')"
log "══════════════════════════════════════════════════"

ERRORS=0
WARNINGS=0
REPORT=""

# ── 1. USB connection ─────────────────────────────────────────────────────────
log "--- USB connection ---"

USB_SPEED=""
USB_DEV_PATH="/sys/bus/usb/devices/${USB_PORT}"
if [[ -d "$USB_DEV_PATH" ]]; then
    USB_SPEED=$(cat "${USB_DEV_PATH}/speed" 2>/dev/null || echo "unknown")
    USB_VID_ACTUAL=$(cat "${USB_DEV_PATH}/idVendor" 2>/dev/null || echo "?")
    USB_PID_ACTUAL=$(cat "${USB_DEV_PATH}/idProduct" 2>/dev/null || echo "?")
    log "USB device at ${USB_PORT}: ${USB_VID_ACTUAL}:${USB_PID_ACTUAL}  speed=${USB_SPEED} Mbps"
    REPORT+="🔌 USB: port ${USB_PORT}, ${USB_SPEED} Mbps\n"

    if [[ "$USB_SPEED" == "5000" ]]; then
        log "USB speed: OK (SuperSpeed 5000 Mbps)"
    elif [[ "$USB_SPEED" == "480" ]]; then
        log "WARNING: USB degraded to USB 2.0 (480 Mbps)!"
        WARNINGS=$((WARNINGS + 1))
        REPORT+="⚠️ USB деградировал до USB 2.0 (480 Mbps)!\n"
    else
        log "WARNING: unexpected USB speed: $USB_SPEED"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log "ERROR: USB device not found at ${USB_PORT}"
    ERRORS=$((ERRORS + 1))
    REPORT+="❌ USB устройство не найдено на порту ${USB_PORT}!\n"
fi

# ── 2. dmesg USB errors since last run ───────────────────────────────────────
log "--- dmesg USB errors ---"

LAST_RUN_UPTIME=0
[[ -f "$STATE_FILE" ]] && LAST_RUN_UPTIME=$(cat "$STATE_FILE" 2>/dev/null || echo 0)

# Current uptime in seconds
UPTIME_SECS=$(awk '{printf "%.0f", $1}' /proc/uptime)
# dmesg timestamps are uptime-relative
RESET_COUNT=$(dmesg 2>/dev/null | grep "usb ${USB_PORT}: reset SuperSpeed" | \
    awk -v last="$LAST_RUN_UPTIME" -F'[][]' '{if ($2+0 > last+0) count++} END {print count+0}')
STREAM_ERR_COUNT=$(dmesg 2>/dev/null | grep "ERROR Transfer event.*stream ring" | \
    awk -v last="$LAST_RUN_UPTIME" -F'[][]' '{if ($2+0 > last+0) count++} END {print count+0}')
ERROR71_COUNT=$(dmesg 2>/dev/null | grep "error -71" | \
    awk -v last="$LAST_RUN_UPTIME" -F'[][]' '{if ($2+0 > last+0) count++} END {print count+0}')

log "USB resets since last check: $RESET_COUNT"
log "UAS stream ring errors: $STREAM_ERR_COUNT"
log "USB error -71: $ERROR71_COUNT"

REPORT+="📊 USB resets: ${RESET_COUNT}, stream errors: ${STREAM_ERR_COUNT}\n"

if [[ "$RESET_COUNT" -gt 5 ]]; then
    log "WARNING: high USB reset count ($RESET_COUNT)"
    WARNINGS=$((WARNINGS + 1))
fi
if [[ "$STREAM_ERR_COUNT" -gt 0 ]]; then
    log "WARNING: UAS stream errors detected — UAS quirk reboot pending?"
    WARNINGS=$((WARNINGS + 1))
fi

# Save current uptime as reference for next run
echo "$UPTIME_SECS" > "$STATE_FILE"

# ── 3. Block device and mount ─────────────────────────────────────────────────
log "--- Block device & mount ---"

if [[ -b "$DEV" ]]; then
    log "Block device: $DEV ✅"
    REPORT+="💾 Диск: $DEV ✅\n"
else
    log "ERROR: $DEV not found!"
    ERRORS=$((ERRORS + 1))
    REPORT+="❌ Диск $DEV не найден!\n"
fi

if mountpoint -q "$MOUNT" 2>/dev/null; then
    log "Mount: $MOUNT ✅"
    REPORT+="📁 Монтирование: $MOUNT ✅\n"
else
    log "ERROR: $MOUNT not mounted!"
    ERRORS=$((ERRORS + 1))
    REPORT+="❌ $MOUNT не смонтирован!\n"
fi

# ── 4. Disk space ─────────────────────────────────────────────────────────────
log "--- Disk space ---"

if mountpoint -q "$MOUNT" 2>/dev/null; then
    DISK_INFO=$(df -h "$MOUNT" | tail -1)
    DISK_TOTAL=$(echo "$DISK_INFO" | awk '{print $2}')
    DISK_USED=$(echo "$DISK_INFO" | awk '{print $3}')
    DISK_FREE=$(echo "$DISK_INFO" | awk '{print $4}')
    DISK_PCT=$(echo "$DISK_INFO" | awk '{print $5}' | tr -d '%')
    log "Disk: total=$DISK_TOTAL  used=$DISK_USED  free=$DISK_FREE  usage=${DISK_PCT}%"
    REPORT+="💿 Диск: ${DISK_USED}/${DISK_TOTAL} (${DISK_PCT}% используется)\n"

    if [[ "$DISK_PCT" -ge 90 ]]; then
        log "ERROR: disk >90% full!"
        ERRORS=$((ERRORS + 1))
        REPORT+="🚨 Диск заполнен на ${DISK_PCT}%!\n"
    elif [[ "$DISK_PCT" -ge 80 ]]; then
        log "WARNING: disk >80% full"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# ── 5. I/O throughput (since boot) ────────────────────────────────────────────
log "--- I/O statistics ---"

if [[ -f /sys/block/sda/stat ]]; then
    # Format: reads_completed reads_merged sectors_read time_reading
    #         writes_completed writes_merged sectors_written time_writing ...
    read -r rd_ios _ rd_sec _ wr_ios _ wr_sec _ < /sys/block/sda/stat
    RD_MB=$(( rd_sec / 2048 ))   # sectors(512B) → MB
    WR_MB=$(( wr_sec / 2048 ))
    log "I/O since boot: read=${RD_MB} MB (${rd_ios} ops)  write=${WR_MB} MB (${wr_ios} ops)"
    REPORT+="📈 I/O с момента загрузки: чтение ${RD_MB} MB, запись ${WR_MB} MB\n"
fi

# ── 6. SMART basic info ───────────────────────────────────────────────────────
log "--- SMART info ---"

SMART_OUT=$(smartctl -d sat,auto -i "$DEV" 2>&1)
if echo "$SMART_OUT" | grep -q "SMART support is:.*Unavailable"; then
    log "SMART: passthrough via smartmontools 6.6 returns 'Unavailable' (known limitation)"
    log "Device identified: $(echo "$SMART_OUT" | grep -E 'Vendor|Product|Serial' | tr '\n' ' ')"
    SMART_STATUS="ℹ️ SMART: базовая info доступна (smartmontools 6.6 — полный SMART только после обновления)"
else
    HEALTH=$(smartctl -d sat,auto -H "$DEV" 2>&1)
    if echo "$HEALTH" | grep -q "PASSED"; then
        log "SMART health: PASSED"
        SMART_STATUS="✅ SMART: PASSED"
    else
        log "SMART health: UNKNOWN/FAILED"
        SMART_STATUS="⚠️ SMART: статус неизвестен"
    fi
fi
REPORT+="${SMART_STATUS}\n"

# ── 7. UAS quirk status ───────────────────────────────────────────────────────
log "--- UAS driver status ---"

UAS_DRIVER=$(readlink /sys/bus/usb/devices/${USB_PORT}:1.0/driver 2>/dev/null || echo "unknown")
if echo "$UAS_DRIVER" | grep -q "uas$"; then
    log "WARNING: UAS driver still active (reboot needed to apply quirk 152d:a583:u)"
    REPORT+="⚠️ UAS драйвер активен — нужен reboot для применения quirk\n"
    REPORT+="   После reboot: write speed вырастет с ~8 до ~100+ MB/s\n"
    WARNINGS=$((WARNINGS + 1))
elif echo "$UAS_DRIVER" | grep -q "usb-storage"; then
    log "Driver: usb-storage (BOT mode) — UAS quirk applied successfully"
    REPORT+="✅ usb-storage BOT режим активен (UAS quirk применён)\n"
else
    log "Driver: $UAS_DRIVER"
fi

# ── 8. Kernel quirk verification ─────────────────────────────────────────────
log "--- Kernel quirks ---"

if grep -q "152d:a583:u" /proc/cmdline 2>/dev/null; then
    log "Kernel quirk 152d:a583:u: ACTIVE (UAS disabled at kernel level)"
    REPORT+="✅ Kernel quirk 152d:a583:u активен\n"
else
    log "Kernel quirk 152d:a583:u: not in /proc/cmdline (pending reboot)"
    REPORT+="⚠️ Quirk в extlinux.conf, но не применён (нужен reboot)\n"
fi

# ── 9. Summary and alerts ─────────────────────────────────────────────────────
log "--- Summary ---"
log "Errors: $ERRORS  Warnings: $WARNINGS"

ICON="✅"
[[ "$WARNINGS" -gt 0 ]] && ICON="⚠️"
[[ "$ERRORS" -gt 0 ]] && ICON="❌"

# Send Telegram on errors immediately
if [[ "$ERRORS" -gt 0 ]]; then
    MSG="🚨 <b>[${HOSTNAME_SHORT}] JMS583 ОШИБКА</b>

${REPORT}

⚠️ Errors: ${ERRORS}, Warnings: ${WARNINGS}
📋 Лог: /var/log/nas_jetson_nano-monitor/jms583-health.log"
    tg_send "$MSG"
fi

# Send daily summary at 09:00 (run by hourly timer)
TODAY=$(date +%Y-%m-%d)
DAILY_SENT=$(cat "$DAILY_SENT_FILE" 2>/dev/null || echo "")
if [[ "$HOUR" == "09" && "$DAILY_SENT" != "$TODAY" ]]; then
    MSG="${ICON} <b>[${HOSTNAME_SHORT}] JMS583 — суточный отчёт</b>
$(date '+%Y-%m-%d %H:%M')

${REPORT}
Errors: ${ERRORS} | Warnings: ${WARNINGS}
Uptime: $(uptime -p 2>/dev/null || awk '{printf "%dd %dh %dm", $1/86400, ($1%86400)/3600, ($1%3600)/60}' /proc/uptime)"
    tg_send "$MSG"
    echo "$TODAY" > "$DAILY_SENT_FILE"
    log "Daily Telegram report sent"
fi

log "Check complete: $ICON errors=$ERRORS warnings=$WARNINGS"
exit 0
