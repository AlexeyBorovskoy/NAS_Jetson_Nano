#!/usr/bin/env bash
# Настроить бэкап конфигурации на Jetson: цель HDD, пароль репозитория, юниты (этап B).
#
# Идемпотентно: существующий пароль и цель не перезаписываются.
# Запуск (root, в окне деплоя, после install_restic.sh):
#   sudo bash scripts/backup/setup_config_backup.sh
#
# 🔴 Пароль репозитория (`/root/.config/nas-backup/hdd.pass`) обязан лежать и ВНЕ
# устройства (менеджер паролей владельца). Без него снапшоты не расшифровать —
# бэкап `.env` бесполезен ровно в тот день, когда умрёт SD-карта.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd)"
CFG=/root/.config/nas-backup
TARGETS="$CFG/targets"
PASS="$CFG/hdd.pass"
REPO_DIR="${NAS_HDD_ROOT:-/mnt/hdd2tb}/backups/restic-config"

[[ $EUID -eq 0 ]] || { echo "нужен root (sudo)" >&2; exit 1; }
command -v restic >/dev/null || { echo "нет restic — сначала install_restic.sh" >&2; exit 1; }
mountpoint -q "${NAS_HDD_ROOT:-/mnt/hdd2tb}" || { echo "HDD не смонтирован" >&2; exit 1; }

install -d -m 700 "$CFG" "$TARGETS"
if [[ ! -s "$PASS" ]]; then
    ( umask 077; head -c 32 /dev/urandom | base64 > "$PASS" )
    echo "создан пароль репозитория: $PASS (скопируйте в менеджер паролей: sudo cat $PASS)"
fi
if [[ ! -f "$TARGETS/hdd.env" ]]; then
    ( umask 077; cat > "$TARGETS/hdd.env" <<EOF
# Цель бэкапа конфигурации — локальный HDD (L1c). Значения в кавычках (правило №8).
RESTIC_REPOSITORY="$REPO_DIR"
RESTIC_PASSWORD_FILE="$PASS"
REQUIRES_MOUNT="${NAS_HDD_ROOT:-/mnt/hdd2tb}"
EOF
    )
    echo "создана цель: $TARGETS/hdd.env"
fi

bash "$ROOT/scripts/backup/config_backup.sh" --init

for u in nas_jetson_nano-config-backup nas_jetson_nano-restore-drill; do
    install -m 0644 "$ROOT/systemd/$u.service" "$ROOT/systemd/$u.timer" /etc/systemd/system/
    sed -i "s|/home/admin/nasa|$ROOT|g" "/etc/systemd/system/$u.service"
done
systemctl daemon-reload
systemctl enable --now nas_jetson_nano-config-backup.timer nas_jetson_nano-restore-drill.timer
systemctl list-timers --no-pager | grep -E "config-backup|restore-drill" || true

echo "Первый прогон вручную:  sudo systemctl start nas_jetson_nano-config-backup.service"
echo "Проверка восстановления: sudo systemctl start nas_jetson_nano-restore-drill.service"
echo "S3 (B3): положить $TARGETS/s3.env (RESTIC_REPOSITORY=s3:..., AWS_*), затем config_backup.sh --init"
