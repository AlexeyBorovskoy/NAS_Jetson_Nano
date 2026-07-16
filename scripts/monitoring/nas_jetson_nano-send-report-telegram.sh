#!/usr/bin/env bash
# NAS_Jetson_Nano — send daily report to Telegram via VPS relay
# Jetson cannot reach api.telegram.org directly; we pipe the report
# over SSH to VPS which has unrestricted internet access.
set -euo pipefail

CONF="/etc/nas_jetson_nano-monitor/telegram.env"
REPORT_CMD="/usr/local/sbin/nas_jetson_nano-daily-report.sh"
LOG_DIR="/var/log/nas_jetson_nano-monitor"
REPORT_FILE="${LOG_DIR}/last-report.txt"
SEND_LOG="${LOG_DIR}/last-telegram-send.json"
VPS_HOST="${VPS_HOST:-193.8.215.130}"
VPS_USER="${VPS_USER:-root}"
VPS_KEY="${VPS_KEY:-/home/admin/.ssh/id_ed25519}"

mkdir -p "$LOG_DIR"

if [ ! -f "$CONF" ]; then
    echo "ERROR: $CONF not found"
    exit 1
fi

. "$CONF"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty"
    exit 1
fi

if [ ! -x "$REPORT_CMD" ]; then
    echo "ERROR: $REPORT_CMD not found or not executable"
    exit 1
fi

"$REPORT_CMD" > "$REPORT_FILE"

# Send via VPS relay: token is passed via SSH environment variable (not expanded
# in the command string) to avoid exposure in `ps aux` on the VPS side (SC2029).
# RequireEnvironment must be allowed by VPS sshd (AcceptEnv NAS_Jetson_Nano_*).
# Fallback: if AcceptEnv is not configured, we use a one-shot remote env file.
REMOTE_ENV="/tmp/nas_jetson_nano-tg-$$.env"
ssh -i "$VPS_KEY" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=15 \
    -o BatchMode=yes \
    "${VPS_USER}@${VPS_HOST}" \
    "cat > ${REMOTE_ENV} && chmod 600 ${REMOTE_ENV}" \
    <<EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
EOF

ssh -i "$VPS_KEY" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=15 \
    -o BatchMode=yes \
    "${VPS_USER}@${VPS_HOST}" \
    ". ${REMOTE_ENV}; rm -f ${REMOTE_ENV};
     curl -sS -X POST \"https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/sendMessage\" \
         -d \"chat_id=\${TELEGRAM_CHAT_ID}\" \
         --data-urlencode 'text@-'" \
    < "$REPORT_FILE" \
    | tee "$SEND_LOG" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK, message_id=' + str(d['result']['message_id']) if d.get('ok') else 'FAIL: '+str(d))"
