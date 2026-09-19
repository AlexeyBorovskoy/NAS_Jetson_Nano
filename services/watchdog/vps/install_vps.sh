#!/usr/bin/env bash
# D3: установка части сторожа на VPS. Только по команде «деплой», runbook —
# docs/plans/DEPLOY_D3_WATCHDOG_2026-09.md.
#   sudo bash install_vps.sh "ssh-ed25519 AAAA... nas-watchdog"
# Что делает: пользователь naswatch (без sudo), /usr/local/bin/nas-liveness,
# ключ сторожа с единственной командой. sshd не перезапускается: authorized_keys
# читается при каждом входе. Новых портов нет.
set -euo pipefail

PUB="${1:?нужен публичный ключ сторожа одной строкой: ssh-ed25519 ...}"
case "$PUB" in
  *$'\n'*|*$'\r'*) echo "ключ должен быть одной строкой" >&2; exit 2 ;;
esac
case "$PUB" in
  ssh-ed25519\ *) ;;
  *) echo "ожидается ключ ssh-ed25519" >&2; exit 2 ;;
esac
HERE="$(dirname "$(readlink -f "$0")")"

if ! id naswatch >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/naswatch --shell /bin/sh naswatch
fi
usermod -p '*' naswatch

chown naswatch:naswatch /var/lib/naswatch
chmod 0750 /var/lib/naswatch

install -m 0755 -o root -g root "$HERE/nas_liveness.py" /usr/local/bin/nas-liveness
install -d -m 0700 -o naswatch -g naswatch /var/lib/naswatch/.ssh

AK=/var/lib/naswatch/.ssh/authorized_keys
LINE='restrict,command="/usr/local/bin/nas-liveness" '"$PUB"
touch "$AK"
grep -qxF "$LINE" "$AK" || printf '%s\n' "$LINE" >> "$AK"
chown naswatch:naswatch "$AK"
chmod 600 "$AK"

sshd -t
echo "проверка от имени naswatch:"
sudo -u naswatch /usr/local/bin/nas-liveness check
