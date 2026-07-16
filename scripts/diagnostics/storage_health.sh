#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# storage_health.sh — check storage health for NAS_Jetson_Nano
# ---------------------------------------------------------------------------
# Returns exit code 1 if storage is critically full or /mnt/storage not mounted.
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
fi

# ---- Defaults (overridden by .env) -----------------------------------------
STORAGE_ROOT="${STORAGE_ROOT:-/mnt/storage}"
NEXTCLOUD_DATA="${NEXTCLOUD_DATA:-${STORAGE_ROOT}/nextcloud/data}"
IMMICH_UPLOAD_LOCATION="${IMMICH_UPLOAD_LOCATION:-${STORAGE_ROOT}/immich/library}"
NEXTCLOUD_DB_DATA="${NEXTCLOUD_DB_DATA:-${STORAGE_ROOT}/db/nextcloud-postgres}"
IMMICH_DB_DATA_LOCATION="${IMMICH_DB_DATA_LOCATION:-${STORAGE_ROOT}/db/immich-postgres}"
BACKUP_ROOT="${BACKUP_ROOT:-${STORAGE_ROOT}/backups}"
ALERT_THRESHOLD="${STORAGE_ALERT_THRESHOLD:-85}"

ERRORS=0

# ---------------------------------------------------------------------------
# 1. Check /mnt/storage is mounted
# ---------------------------------------------------------------------------
log "=== Storage health check started ==="

if ! mountpoint -q "${STORAGE_ROOT}" 2>/dev/null; then
    log "CRITICAL: ${STORAGE_ROOT} is NOT mounted!"
    exit 1
fi
log "Mount point ${STORAGE_ROOT}: OK"

# ---------------------------------------------------------------------------
# 2. Disk usage per section
# ---------------------------------------------------------------------------
check_dir_usage() {
    local label="$1"
    local path="$2"

    if [[ ! -d "${path}" ]]; then
        log "WARNING: Directory does not exist: ${path}"
        ERRORS=$(( ERRORS + 1 ))
        return
    fi

    local used_pct size_human
    used_pct="$(df "${path}" --output=pcent 2>/dev/null | tail -1 | tr -d ' %')"
    size_human="$(df -h "${path}" --output=used,size,avail,pcent 2>/dev/null | tail -1)"

    local alert=""
    if (( used_pct > ALERT_THRESHOLD )); then
        alert="  <<< ALERT: above ${ALERT_THRESHOLD}%"
        ERRORS=$(( ERRORS + 1 ))
    fi

    printf "  %-30s  %s%s\n" "${label}" "${size_human}" "${alert}"
}

echo ""
echo "  Directory                         Used     Size     Avail    Use%"
echo "  -----------------------------------------------------------------------"
check_dir_usage "nextcloud/data"      "${NEXTCLOUD_DATA}"
check_dir_usage "immich/library"      "${IMMICH_UPLOAD_LOCATION}"
check_dir_usage "db/nextcloud-pg"     "${NEXTCLOUD_DB_DATA}"
check_dir_usage "db/immich-pg"        "${IMMICH_DB_DATA_LOCATION}"
check_dir_usage "backups"             "${BACKUP_ROOT}"
check_dir_usage "storage root"        "${STORAGE_ROOT}"
echo ""

# ---------------------------------------------------------------------------
# 3. Inode check on storage root
# ---------------------------------------------------------------------------
log "Inode usage on ${STORAGE_ROOT}:"
df -i "${STORAGE_ROOT}" | tail -1 | awk '{printf "  Inodes: total=%s  used=%s  free=%s  (%s)\n", $2, $3, $4, $5}'

# ---------------------------------------------------------------------------
# 4. Last database dump timestamp
# ---------------------------------------------------------------------------
DUMP_DIR="${BACKUP_ROOT}/database-dumps"
if [[ -d "${DUMP_DIR}" ]]; then
    log "Last database dumps in ${DUMP_DIR}:"
    local_nc="$(ls -t "${DUMP_DIR}"/nextcloud_*.sql.gz 2>/dev/null | head -1 || echo "none")"
    local_im="$(ls -t "${DUMP_DIR}"/immich_*.sql.gz    2>/dev/null | head -1 || echo "none")"
    if [[ "${local_nc}" != "none" ]]; then
        printf "  nextcloud: %s  (%s)\n" "$(basename "${local_nc}")" "$(date -r "${local_nc}" '+%Y-%m-%d %H:%M:%S')"
    else
        log "  WARNING: No Nextcloud dump found"
        ERRORS=$(( ERRORS + 1 ))
    fi
    if [[ "${local_im}" != "none" ]]; then
        printf "  immich:    %s  (%s)\n" "$(basename "${local_im}")" "$(date -r "${local_im}" '+%Y-%m-%d %H:%M:%S')"
    else
        log "  WARNING: No Immich dump found"
        ERRORS=$(( ERRORS + 1 ))
    fi
else
    log "WARNING: Dump directory does not exist: ${DUMP_DIR}"
    ERRORS=$(( ERRORS + 1 ))
fi

# ---------------------------------------------------------------------------
# 5. Non-empty check for critical data directories
# ---------------------------------------------------------------------------
echo ""
log "Critical directory presence check:"
for dir in "${NEXTCLOUD_DATA}" "${IMMICH_UPLOAD_LOCATION}" "${NEXTCLOUD_DB_DATA}" "${IMMICH_DB_DATA_LOCATION}"; do
    if [[ -d "${dir}" ]] && [[ -n "$(ls -A "${dir}" 2>/dev/null)" ]]; then
        printf "  OK      %s\n" "${dir}"
    else
        printf "  MISSING %s\n" "${dir}"
        ERRORS=$(( ERRORS + 1 ))
    fi
done

# ---------------------------------------------------------------------------
# 6. SMART disk health (requires smartmontools + STORAGE_DEVICE in .env)
# ---------------------------------------------------------------------------
echo ""
log "HDD SMART health:"
STORAGE_DEVICE="${STORAGE_DEVICE:-}"  # e.g. /dev/sda — set in config/.env
STORAGE_SMART_DEVICE_TYPE="${STORAGE_SMART_DEVICE_TYPE:-}"  # e.g. sat/scsi for USB bridges

if ! command -v smartctl &>/dev/null; then
    log "  smartctl not installed. Run: sudo apt install smartmontools"
elif [[ -z "${STORAGE_DEVICE}" ]]; then
    log "  STORAGE_DEVICE not set. Add STORAGE_DEVICE=/dev/sdX to config/.env"
elif [[ ! -b "${STORAGE_DEVICE}" ]]; then
    log "  WARNING: ${STORAGE_DEVICE} is not a block device (HDD not connected?)"
    ERRORS=$(( ERRORS + 1 ))
else
    SMARTCTL_ARGS=()
    if [[ -n "${STORAGE_SMART_DEVICE_TYPE}" ]]; then
        SMARTCTL_ARGS=(-d "${STORAGE_SMART_DEVICE_TYPE}")
    fi

    smart_raw="$(smartctl "${SMARTCTL_ARGS[@]}" -H "${STORAGE_DEVICE}" 2>&1 || true)"
    if echo "${smart_raw}" | grep -Eq "PASSED|SMART Health Status:[[:space:]]*OK"; then
        log "  ${STORAGE_DEVICE}: SMART OK"
    elif echo "${smart_raw}" | grep -Eq "FAILED|SMART Health Status:.*(FAIL|BAD)"; then
        log "  ${STORAGE_DEVICE}: SMART FAILED! Drive may be failing — backup immediately."
        ERRORS=$(( ERRORS + 1 ))
    elif echo "${smart_raw}" | grep -qi "USB bridge"; then
        # USB-SATA bridge may need -d sat or -d sntasmedia
        log "  ${STORAGE_DEVICE}: USB-SATA bridge detected — try: smartctl -d sat -H ${STORAGE_DEVICE}"
        log "  (See docs/troubleshooting.md for USB-SATA bridge SMART passthrough)"
    else
        log "  ${STORAGE_DEVICE}: SMART status unknown — ${smart_raw}"
    fi

    # Save SMART attributes snapshot
    SMART_LOG_DIR="${STORAGE_ROOT}/logs/health"
    mkdir -p "${SMART_LOG_DIR}"
    smartctl "${SMARTCTL_ARGS[@]}" -A "${STORAGE_DEVICE}" > "${SMART_LOG_DIR}/smart-attrs-$(date +%Y%m%d-%H%M%S).log" 2>/dev/null || true
    log "  SMART attributes saved to ${SMART_LOG_DIR}/"
fi

# ---------------------------------------------------------------------------
echo ""
log "=== Storage health check finished — issues: ${ERRORS} ==="
if (( ERRORS > 0 )); then
    exit 1
fi
