#!/usr/bin/env bash
# Install the reviewed OBS-1 units; never enable or start them implicitly.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${1:---check}"
UNITS=(nas_jetson_nano-blackbox.service nas_jetson_nano-blackbox-boot.service
       nas_jetson_nano-blackbox-archive.service nas_jetson_nano-blackbox-archive.timer)

case "$MODE" in --check|--apply) ;; *) echo 'Use --check or --apply' >&2; exit 2 ;; esac
[[ $# -le 1 ]] || { echo 'Unexpected arguments' >&2; exit 2; }
[[ -r /etc/nas-layout.env ]] || { echo '/etc/nas-layout.env is required' >&2; exit 1; }
[[ -f "${ROOT}/scripts/monitoring/nas-why" ]] || { echo 'nas-why source is required' >&2; exit 1; }
getent group adm >/dev/null || { echo 'Group adm is required' >&2; exit 1; }
for unit in "${UNITS[@]}"; do
    [[ -f "${ROOT}/systemd/${unit}" ]] || { echo 'Missing source unit' >&2; exit 1; }
    target="/etc/systemd/system/${unit}"
    if [[ -e "$target" || -L "$target" ]]; then
        [[ -f "$target" && ! -L "$target" ]] || { echo 'Refusing non-regular target unit' >&2; exit 1; }
    fi
done
CLI=/usr/local/bin/nas-why
if [[ -e "$CLI" || -L "$CLI" ]]; then
    [[ -f "$CLI" && ! -L "$CLI" ]] &&
        grep -Fxq '# Managed by NAS OBS-1 install_blackbox.sh' "$CLI" || {
            echo 'Refusing unmanaged nas-why executable' >&2; exit 1;
        }
fi
systemd-analyze verify "${UNITS[@]/#/${ROOT}/systemd/}"
if [[ "$MODE" == --check ]]; then
    echo 'Units verified; installation will not enable or start services.'
    exit 0
fi
[[ $EUID -eq 0 ]] || { echo 'Run --apply as root' >&2; exit 1; }
mountpoint -q /mnt/storage || { echo 'SSD is not mounted; refusing underlying SD writes' >&2; exit 1; }
for directory in /mnt/storage/blackbox /var/lib/nas-blackbox; do
    [[ ! -L "$directory" ]] || { echo 'Refusing symlink storage root' >&2; exit 1; }
done
BACKUP="${ROOT}/.agent-work/archives/blackbox-install-$(date -u +%Y%m%dT%H%M%SZ)-$$"
install -d -m 0700 "$BACKUP"
if [[ -f "$CLI" ]]; then
    cp -p -- "$CLI" "${BACKUP}/nas-why"
else
    touch "${BACKUP}/cli-absent"
fi
printf '#!/usr/bin/env bash\n# Managed by NAS OBS-1 install_blackbox.sh\nexec /usr/bin/python3 %q "$@"\n' \
    "${ROOT}/scripts/monitoring/nas-why" > "${BACKUP}/nas-why-launcher"
for unit in "${UNITS[@]}"; do
    target="/etc/systemd/system/${unit}"
    [[ ! -L "$target" ]] || { echo 'Refusing existing symlink unit' >&2; exit 1; }
    if [[ -f "$target" ]]; then
        cp -p -- "$target" "${BACKUP}/${unit}"
    else
        printf '%s\n' "$unit" >> "${BACKUP}/absent"
    fi
done

rollback() {
    local status=$?
    trap - ERR
    for unit in "${UNITS[@]}"; do
        if [[ -f "${BACKUP}/${unit}" ]]; then
            cp -p -- "${BACKUP}/${unit}" "/etc/systemd/system/${unit}"
        elif [[ -f "${BACKUP}/absent" ]] && grep -Fxq -- "$unit" "${BACKUP}/absent"; then
            rm -f -- "/etc/systemd/system/${unit}"
        fi
    done
    if [[ -f "${BACKUP}/nas-why" ]]; then
        cp -p -- "${BACKUP}/nas-why" "$CLI"
    elif [[ -f "${BACKUP}/cli-absent" ]]; then
        rm -f -- "$CLI"
    fi
    systemctl daemon-reload || true
    echo 'Installation failed; previous unit files restored. Services were not enabled.' >&2
    exit "$status"
}
trap rollback ERR
install -d -m 0750 -o root -g adm /mnt/storage/blackbox /var/lib/nas-blackbox
for unit in "${UNITS[@]}"; do
    install -m 0644 "${ROOT}/systemd/${unit}" "/etc/systemd/system/${unit}"
done
systemd-analyze verify "${UNITS[@]/#//etc/systemd/system/}"
install -m 0755 "${BACKUP}/nas-why-launcher" "$CLI"
systemctl daemon-reload
trap - ERR
printf 'Installed without enabling services. Prior units: %s\n' "$BACKUP"
