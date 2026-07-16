#!/usr/bin/env bash
set -euo pipefail

# storage_preflight.sh - fail-closed checks before starting storage-backed services.
# It prints metadata only: no personal filenames, no secret values.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
fi

STORAGE_ROOT="${STORAGE_ROOT:-/mnt/storage}"
NEXTCLOUD_DATA="${NEXTCLOUD_DATA:-${STORAGE_ROOT}/nextcloud/data}"
IMMICH_UPLOAD_LOCATION="${IMMICH_UPLOAD_LOCATION:-${STORAGE_ROOT}/immich/library}"
NEXTCLOUD_DB_DATA="${NEXTCLOUD_DB_DATA:-${STORAGE_ROOT}/db/nextcloud-postgres}"
IMMICH_DB_DATA_LOCATION="${IMMICH_DB_DATA_LOCATION:-${STORAGE_ROOT}/db/immich-postgres}"
BACKUP_ROOT="${BACKUP_ROOT:-${STORAGE_ROOT}/backups}"

ERRORS=0
WARNINGS=0

fail() {
    log "ERROR: $*"
    ERRORS=$((ERRORS + 1))
}

warn() {
    log "WARNING: $*"
    WARNINGS=$((WARNINGS + 1))
}

path_meta() {
    local path="$1"
    if [[ -e "${path}" ]]; then
        stat -c '  %n | type=%F | owner=%U:%G | mode=%a | size=%s' "${path}" 2>/dev/null \
            || warn "Cannot stat ${path}"
    else
        fail "Missing path: ${path}"
    fi
}

fstab_source_for_storage() {
    awk -v target="${STORAGE_ROOT}" '$2 == target {print $1; exit}' /etc/fstab 2>/dev/null || true
}

log "=== NAS_Jetson_Nano storage preflight started ==="

if (( EUID != 0 )); then
    warn "Run with sudo for authoritative checks of service-owned directories"
fi

if ! command -v mountpoint >/dev/null 2>&1; then
    fail "mountpoint command is not available"
elif ! mountpoint -q "${STORAGE_ROOT}" 2>/dev/null; then
    fail "${STORAGE_ROOT} is not a mount point"
fi

storage_source=""
storage_fstype=""
storage_options=""
if command -v findmnt >/dev/null 2>&1; then
    storage_source="$(findmnt -n -T "${STORAGE_ROOT}" -o SOURCE 2>/dev/null || true)"
    storage_fstype="$(findmnt -n -T "${STORAGE_ROOT}" -o FSTYPE 2>/dev/null || true)"
    storage_options="$(findmnt -n -T "${STORAGE_ROOT}" -o OPTIONS 2>/dev/null || true)"
else
    fail "findmnt command is not available"
fi

if [[ -n "${storage_source}" ]]; then
    log "Storage source: ${storage_source}"
    log "Storage fstype: ${storage_fstype:-unknown}"
    log "Storage options: ${storage_options:-unknown}"

    if [[ "${storage_source}" == /dev/mmcblk* ]]; then
        fail "${STORAGE_ROOT} is backed by ${storage_source}; refusing to use microSD as data storage"
    fi

    if [[ "${storage_fstype}" != "ext4" ]]; then
        warn "${STORAGE_ROOT} fstype is ${storage_fstype:-unknown}; expected ext4 for working storage"
    fi

    if [[ ",${storage_options}," == *,ro,* ]]; then
        fail "${STORAGE_ROOT} is mounted read-only"
    fi
else
    fail "Cannot resolve backing device for ${STORAGE_ROOT}"
fi

fstab_source="$(fstab_source_for_storage)"
if [[ -n "${fstab_source}" ]]; then
    log "fstab source for ${STORAGE_ROOT}: ${fstab_source}"
    if [[ "${fstab_source}" == UUID=* ]]; then
        expected_uuid="${fstab_source#UUID=}"
        if ! blkid -U "${expected_uuid}" >/dev/null 2>&1; then
            fail "fstab UUID ${expected_uuid} is not present as a block device"
        fi
    fi
else
    warn "No /etc/fstab entry found for ${STORAGE_ROOT}"
fi

if [[ -n "${STORAGE_DEVICE:-}" ]]; then
    if [[ -b "${STORAGE_DEVICE}" ]]; then
        log "STORAGE_DEVICE exists: ${STORAGE_DEVICE}"
    else
        warn "STORAGE_DEVICE is set but not a block device: ${STORAGE_DEVICE}"
    fi
else
    warn "STORAGE_DEVICE is not set"
fi

log "Critical path metadata:"
path_meta "${STORAGE_ROOT}"
path_meta "${NEXTCLOUD_DATA}"
path_meta "${IMMICH_UPLOAD_LOCATION}"
path_meta "${NEXTCLOUD_DB_DATA}"
path_meta "${IMMICH_DB_DATA_LOCATION}"
path_meta "${BACKUP_ROOT}"

if [[ -d "${NEXTCLOUD_DATA}" ]]; then
    if [[ -f "${NEXTCLOUD_DATA}/.ncdata" ]]; then
        path_meta "${NEXTCLOUD_DATA}/.ncdata"
    else
        fail "Missing Nextcloud marker file: ${NEXTCLOUD_DATA}/.ncdata"
    fi
fi

log "=== NAS_Jetson_Nano storage preflight finished: errors=${ERRORS}, warnings=${WARNINGS} ==="
if (( ERRORS > 0 )); then
    exit 1
fi
