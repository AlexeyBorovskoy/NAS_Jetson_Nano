#!/usr/bin/env bash
# deploy_usb_fix.sh — установить все USB-fix компоненты на Jetson
# Запускать на Jetson от root: sudo bash scripts/storage/deploy_usb_fix.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "[deploy] Repo: $REPO_DIR"

# Проверяем dos2unix (нормализация CRLF→LF перед деплоем)
if ! command -v dos2unix &>/dev/null; then
    echo "[deploy] Installing dos2unix..."
    apt-get install -y -q dos2unix 2>/dev/null || true
fi

deploy_script() {
    local src="$1" dst="$2" name="$3"
    cp "$src" "$dst"
    # Убираем CRLF если есть (критично для shebang!)
    sed -i 's/\r$//' "$dst"
    chmod +x "$dst"
    echo "[deploy] $name OK"
}

# 1. Watchdog script (исправленный + увеличен POWER_OFF_SECS=45)
deploy_script "$REPO_DIR/scripts/storage/usb_recovery_watchdog.sh" \
    /usr/local/sbin/nas_jetson_nano-usb-watchdog.sh "nas_jetson_nano-usb-watchdog.sh (PORT=2, POWER_OFF_SECS=45)"

# 2. Pre-boot power cycle script
deploy_script "$REPO_DIR/scripts/storage/usb_preboot_cycle.sh" \
    /usr/local/sbin/nas_jetson_nano-usb-preboot.sh "nas_jetson_nano-usb-preboot.sh"

# 3. USB error monitor script
deploy_script "$REPO_DIR/scripts/monitoring/usb_error_monitor.sh" \
    /usr/local/sbin/nas_jetson_nano-usb-monitor.sh "nas_jetson_nano-usb-monitor.sh"

# 4. Systemd units
cp "$REPO_DIR/systemd/nas_jetson_nano-usb-preboot.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/nas_jetson_nano-usb-monitor.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/nas_jetson_nano-usb-watchdog.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/nas_jetson_nano-usb-watchdog.timer" /etc/systemd/system/
echo "[deploy] systemd units OK"

# 5. Reload + enable + start
systemctl daemon-reload
systemctl enable nas_jetson_nano-usb-preboot.service
systemctl enable nas_jetson_nano-usb-monitor.service
systemctl restart nas_jetson_nano-usb-watchdog.timer
systemctl restart nas_jetson_nano-usb-monitor.service
echo "[deploy] services enabled and restarted"

# 6. Verify
echo "[deploy] Verification:"
systemctl is-active nas_jetson_nano-usb-watchdog.timer && echo "  watchdog timer: OK"
systemctl is-active nas_jetson_nano-usb-monitor.service && echo "  usb monitor: OK"
systemctl is-enabled nas_jetson_nano-usb-preboot.service && echo "  preboot: enabled (runs at next boot)"
echo "[deploy] Done."
