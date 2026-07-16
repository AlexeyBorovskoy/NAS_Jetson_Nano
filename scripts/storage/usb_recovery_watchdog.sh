#!/usr/bin/env bash
# usb_recovery_watchdog.sh — автовосстановление RTL9210B-CG USB SSD
#
# Эскалация:
#   1. uhubctl power cycle порта 2 (2 попытки по 30с)
#   2. Если SSD не поднялся — отправить Telegram, выполнить reboot
#
# Запускается systemd таймером каждые 3 минуты.
# При успехе — молчит. При эскалации — пишет в журнал и Telegram.

set -euo pipefail

# --- Конфиг ---
SSD_DEV="/dev/sda"
MOUNT_POINT="/mnt/storage"
UHUBCTL="/usr/local/sbin/uhubctl"
HUB_USB2="1-2"
HUB_USB3="2-1"
PORT=2
MAX_SOFT_RETRIES=2
POWER_OFF_SECS=45
WAIT_ENUM_SECS=30
STATE_FILE="/var/lib/nas_jetson_nano-usb-watchdog.state"
LOG_TAG="nas_jetson_nano-usb-watchdog"

# --- Telegram (опционально — берём из env если есть) ---
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

HOSTNAME_SHORT="$(hostname -s)"

log()  { echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $*" | systemd-cat -t "$LOG_TAG" -p info  ; echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO]  $*" >&2; }
warn() { echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN]  $*" | systemd-cat -t "$LOG_TAG" -p warning; echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN]  $*" >&2; }
err()  { echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $*" | systemd-cat -t "$LOG_TAG" -p err   ; echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $*" >&2; }

tg_send() {
    local msg="$1"
    [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && return 0
    curl -sf --max-time 10 \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=[${HOSTNAME_SHORT}] ${msg}" \
        -d "parse_mode=HTML" > /dev/null || true
}

ssd_ok() {
    [[ -b "$SSD_DEV" ]] && mountpoint -q "$MOUNT_POINT"
}

hub_power_cycle() {
    log "Power cycle: port $PORT off (${POWER_OFF_SECS}s)..."
    "$UHUBCTL" -l "$HUB_USB2" -p "$PORT" -a off 2>/dev/null || true
    "$UHUBCTL" -l "$HUB_USB3" -p "$PORT" -a off 2>/dev/null || true
    sleep "$POWER_OFF_SECS"
    log "Power cycle: port $PORT on..."
    "$UHUBCTL" -l "$HUB_USB3" -p "$PORT" -a on 2>/dev/null || true
    "$UHUBCTL" -l "$HUB_USB2" -p "$PORT" -a on 2>/dev/null || true
    log "Waiting ${WAIT_ENUM_SECS}s for enumeration..."
    sleep "$WAIT_ENUM_SECS"
}

# --- Основная логика ---

# SSD в порядке — выходим сразу
if ssd_ok; then
    rm -f "$STATE_FILE"
    exit 0
fi

# Не рестартовать в первые 5 мин после загрузки — SSD ещё инициализируется
UPTIME_SECS=$(awk '{print int($1)}' /proc/uptime)
if [[ "$UPTIME_SECS" -lt 300 ]]; then
    warn "SSD not ready but system uptime is only ${UPTIME_SECS}s — skipping escalation"
    exit 0
fi

warn "SSD ${SSD_DEV} not available or ${MOUNT_POINT} not mounted"

# Читаем счётчик попыток из state файла
# Если state-файл старше 30 мин — сбрасываем счётчик (защита от зависшего цикла)
RETRIES=0
if [[ -f "$STATE_FILE" ]]; then
    if [[ -n "$(find "$STATE_FILE" -mmin +30 2>/dev/null)" ]]; then
        warn "State file older than 30 min, resetting retry counter"
        rm -f "$STATE_FILE"
    else
        RETRIES=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
    fi
fi

if [[ "$RETRIES" -lt "$MAX_SOFT_RETRIES" ]]; then
    RETRIES=$((RETRIES + 1))
    echo "$RETRIES" > "$STATE_FILE"
    log "Attempt ${RETRIES}/${MAX_SOFT_RETRIES}: uhubctl power cycle..."
    hub_power_cycle

    if ssd_ok; then
        log "SSD recovered after power cycle (attempt ${RETRIES})"
        tg_send "✅ SSD recovered via USB power cycle (attempt ${RETRIES})"
        rm -f "$STATE_FILE"
        # Пробуем поднять Docker и монтирование
        systemctl start jetson-nas-mount.service 2>/dev/null || true
        sleep 5
        systemctl start docker 2>/dev/null || true
        exit 0
    fi

    warn "SSD still not available after power cycle ${RETRIES}"
    exit 1
fi

# Все попытки исчерпаны — выполняем reboot
err "SSD not recovered after ${MAX_SOFT_RETRIES} power cycle attempts. Initiating reboot..."
tg_send "🔴 SSD не восстановился после ${MAX_SOFT_RETRIES} попыток USB power cycle. Выполняю reboot Jetson..."
rm -f "$STATE_FILE"
sync
sleep 2
/sbin/reboot
