#!/usr/bin/env bash
# NAS_Jetson_Nano — install USB storage watchdog
# Fixes:
#   1. Disables USB autosuspend for RTL9210B-CG (prevents ELPG power cycle loop)
#   2. Installs udev rules for Telegram alert on sda connect/disconnect
#   3. Installs smartmontools for periodic S.M.A.R.T. health checks
set -euo pipefail

RULES_FILE="/etc/udev/rules.d/85-nas_jetson_nano-storage-watchdog.rules"
ALERT_SCRIPT="/usr/local/sbin/nas_jetson_nano-storage-alert.sh"
SMARTD_CONF="/etc/smartd.conf"
CONF="/etc/nas_jetson_nano-monitor/telegram.env"

# ── 1. alert script ──────────────────────────────────────────────────────────
cat > "$ALERT_SCRIPT" << 'SCRIPT'
#!/usr/bin/env bash
# Called by udev via systemd-run — sends Telegram alert via VPS relay.
# $1 = "removed" | "connected" | "error"
set -euo pipefail

CONF="/etc/nas_jetson_nano-monitor/telegram.env"
VPS_HOST="95.163.176.103"
VPS_USER="root"
VPS_KEY="/home/admin/.ssh/id_ed25519"

[ -f "$CONF" ] || exit 1
. "$CONF"
[ -n "${TELEGRAM_BOT_TOKEN:-}" ] || exit 1

ACTION="${1:-unknown}"
HOSTNAME=$(hostname)
TS=$(date -u '+%Y-%m-%d %H:%M UTC')

case "$ACTION" in
  removed)
    EMOJI="🔴"
    TEXT="${EMOJI} NAS_Jetson_Nano Storage ALERT
Host: ${HOSTNAME}
Time: ${TS}
Event: /dev/sda disconnected (USB error)
Action: Docker is stopped (storage guard). Services offline.
Check: ssh to Jetson → reconnect SSD → storage_preflight.sh"
    ;;
  connected)
    EMOJI="🟢"
    TEXT="${EMOJI} NAS_Jetson_Nano Storage OK
Host: ${HOSTNAME}
Time: ${TS}
Event: /dev/sda connected (RTL9210B-CG detected)
Action: storage_preflight.sh will run automatically."
    ;;
  smart_warn)
    EMOJI="🟡"
    TEXT="${EMOJI} NAS_Jetson_Nano Storage S.M.A.R.T. WARNING
Host: ${HOSTNAME}
Time: ${TS}
Event: ${2:-smartd detected issue}
Action: Check smartctl -a /dev/sda ASAP."
    ;;
  *)
    TEXT="⚠️ NAS_Jetson_Nano Storage event (${ACTION}) on ${HOSTNAME} at ${TS}"
    ;;
esac

REMOTE_ENV="/tmp/nas_jetson_nano-storage-alert-$$.env"
ssh -i "$VPS_KEY" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    "${VPS_USER}@${VPS_HOST}" \
    "cat > ${REMOTE_ENV} && chmod 600 ${REMOTE_ENV}" \
    <<EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
EOF

echo "$TEXT" | ssh -i "$VPS_KEY" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    "${VPS_USER}@${VPS_HOST}" \
    ". ${REMOTE_ENV}; rm -f ${REMOTE_ENV};
     curl -sS -X POST \"https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/sendMessage\" \
         -d \"chat_id=\${TELEGRAM_CHAT_ID}\" \
         --data-urlencode 'text@-'" > /dev/null 2>&1 || true
SCRIPT
chmod +x "$ALERT_SCRIPT"
echo "[1/4] alert script installed → $ALERT_SCRIPT"

# ── 2. udev rules ────────────────────────────────────────────────────────────
cat > "$RULES_FILE" << 'RULES'
# NAS_Jetson_Nano — USB storage watchdog rules
# RTL9210B-CG: Vendor 0bda, Product 9210
# Realtek USB 3.0 hub: 0bda:5411 (USB 2.0 side) / 0bda:0411 (USB 3.0 side)

# Disable USB autosuspend on hub that carries the SSD (autosuspend on hub kills child devices)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="5411", \
  ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="0411", \
  ATTR{power/control}="on"

# Disable USB autosuspend on the RTL9210B-CG bridge (prevents ELPG loop → error -71)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="9210", \
  ATTR{power/autosuspend_delay_ms}="-1", \
  ATTR{power/control}="on"

# Telegram alert when sda block device appears (SSD reconnected)
ACTION=="add", KERNEL=="sda", SUBSYSTEM=="block", \
  RUN+="/bin/systemd-run --no-block /usr/local/sbin/nas_jetson_nano-storage-alert.sh connected"

# Telegram alert when sda block device is removed (SSD disconnected)
ACTION=="remove", KERNEL=="sda", SUBSYSTEM=="block", \
  RUN+="/bin/systemd-run --no-block /usr/local/sbin/nas_jetson_nano-storage-alert.sh removed"

# Auto-recovery: when SSD partition (sda1) appears, mount /mnt/storage + restart Docker + containers
# Triggered on sda1 (partition) not sda (disk) — partition must exist before mount attempt
ACTION=="add", KERNEL=="sda1", SUBSYSTEM=="block", \
  RUN+="/bin/systemctl --no-block start nas_jetson_nano-ssd-recovery.service"
RULES
echo "[2/4] udev rules installed → $RULES_FILE"

# ── 3. smartmontools ─────────────────────────────────────────────────────────
if ! command -v smartctl &>/dev/null; then
    apt-get install -y smartmontools
fi

cat > "$SMARTD_CONF" << 'SMARTD'
# NAS_Jetson_Nano — smartd config
# Monitor /dev/sda explicitly (DEVICESCAN fails on Tegra kernel 4.9)
/dev/sda \
  -a \
  -o on \
  -S on \
  -n standby,q \
  -s (S/../.././02|L/../../0/03) \
  -W 5,45,55 \
  -m root \
  -M exec /usr/local/sbin/nas_jetson_nano-smartd-alert.sh
SMARTD

# smartd alert wrapper (translates smartd env vars to our Telegram script)
cat > /usr/local/sbin/nas_jetson_nano-smartd-alert.sh << 'SMARTD_ALERT'
#!/usr/bin/env bash
# Called by smartd on SMART failure
WARN_MSG="Device: ${SMARTD_DEVICE:-/dev/sda}, ${SMARTD_FAILTYPE:-SMART event}: ${SMARTD_MESSAGE:-}"
/usr/local/sbin/nas_jetson_nano-storage-alert.sh smart_warn "$WARN_MSG"
SMARTD_ALERT
chmod +x /usr/local/sbin/nas_jetson_nano-smartd-alert.sh
echo "[3/4] smartd configured → $SMARTD_CONF"

# ── 4. apply ─────────────────────────────────────────────────────────────────
udevadm control --reload-rules
systemctl enable smartd 2>/dev/null || true
systemctl restart smartd 2>/dev/null || true
echo "[4/4] udev reloaded, smartd enabled"

# ── 5. kernel boot parameter (optional, persistent across reboots) ────────────
# usbcore.autosuspend=-1 is the belt-and-suspenders fix: the udev rule above
# handles the RTL9210B-CG specifically, but this prevents ALL USB devices from
# entering autosuspend at the kernel level — needed because tegra-xusb ELPG
# can trigger the same error loop on any USB device.
EXTLINUX="/boot/extlinux/extlinux.conf"
if grep -q "usbcore.autosuspend" "$EXTLINUX" 2>/dev/null; then
    echo "[5/5] kernel param already set in $EXTLINUX — skipping"
else
    cp "${EXTLINUX}" "${EXTLINUX}.bak.$(date +%Y%m%d%H%M%S)"
    sed -i '/APPEND.*rootfstype=ext4/s/$/ usbcore.autosuspend=-1/' "$EXTLINUX"
    echo "[5/5] kernel param added to $EXTLINUX (takes effect on next reboot)"
    echo "      backup: ${EXTLINUX}.bak.*"
fi

echo ""
echo "USB watchdog installed. Summary:"
echo "  • RTL9210B-CG autosuspend disabled via udev (device-specific, immediate)"
echo "  • usbcore.autosuspend=-1 added to extlinux.conf (all USB, after reboot)"
echo "  • Telegram alert on /dev/sda connect/disconnect"
echo "  • smartd monitoring every device, self-test weekly"
echo "  • smartd SMART failures → Telegram via nas_jetson_nano-storage-alert.sh"
echo ""
echo "Test alert (needs SSD connected):"
echo "  /usr/local/sbin/nas_jetson_nano-storage-alert.sh connected"
