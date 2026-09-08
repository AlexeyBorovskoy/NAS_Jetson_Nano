#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# backup_databases.sh — dump PostgreSQL databases from running Docker containers
# ---------------------------------------------------------------------------
# Usage: ./backup_databases.sh
# Reads config from ../../config/.env relative to this script's location.
#
# F-01: fail-closed — wait for pg_isready, write to .partial, gzip -t,
# min size (reject ~20-byte empty gzip from cold postgres).
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"
NAS_BACKUP_LIB_ONLY="${NAS_BACKUP_LIB_ONLY:-0}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ---- Defaults (overridden by .env when run as script) ---------------------
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/storage/backups}"
STORAGE_ROOT="${STORAGE_ROOT:-/mnt/storage}"
BACKUP_KEEP_LAST="${BACKUP_KEEP_LAST:-7}"
MIN_DUMP_BYTES="${MIN_DUMP_BYTES:-1024}"
PG_READY_RETRIES="${PG_READY_RETRIES:-30}"
PG_READY_SLEEP="${PG_READY_SLEEP:-2}"

NEXTCLOUD_DB_CONTAINER="homecloud_nextcloud_db"
IMMICH_DB_CONTAINER="homecloud_immich_db"

NEXTCLOUD_DB_USER="${NEXTCLOUD_DB_USER:-nextcloud}"
NEXTCLOUD_DB_NAME="${NEXTCLOUD_DB_NAME:-nextcloud}"
IMMICH_DB_USER="${IMMICH_DB_USER:-immich}"
IMMICH_DB_NAME="${IMMICH_DB_NAME:-immich}"

DUMP_DIR="${BACKUP_ROOT}/database-dumps"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

container_running() {
    local name="$1"
    docker inspect --format '{{.State.Running}}' "${name}" 2>/dev/null | grep -q '^true$'
}

storage_ready() {
    if ! mountpoint -q "${STORAGE_ROOT}" 2>/dev/null; then
        log "CRITICAL: ${STORAGE_ROOT} is not a mount point; refusing to write backups"
        return 1
    fi

    local storage_source
    storage_source="$(findmnt -n -T "${STORAGE_ROOT}" -o SOURCE 2>/dev/null || true)"
    if [[ -z "${storage_source}" ]]; then
        log "CRITICAL: cannot resolve backing device for ${STORAGE_ROOT}"
        return 1
    fi

    if [[ "${storage_source}" == /dev/mmcblk* ]]; then
        log "CRITICAL: ${STORAGE_ROOT} is backed by ${storage_source}; refusing to write backups to microSD"
        return 1
    fi

    local writable_target="${STORAGE_ROOT}"
    if [[ -d "${BACKUP_ROOT}" ]]; then
        writable_target="${BACKUP_ROOT}"
    fi

    if [[ ! -w "${writable_target}" ]]; then
        log "CRITICAL: ${writable_target} is not writable"
        return 1
    fi

    return 0
}

wait_pg_ready() {
    local container="$1"
    local db_user="$2"
    local i
    for i in $(seq 1 "${PG_READY_RETRIES}"); do
        if docker exec "${container}" pg_isready -U "${db_user}" >/dev/null 2>&1; then
            log "postgres ready in ${container}"
            return 0
        fi
        log "waiting for postgres in ${container} (${i}/${PG_READY_RETRIES})"
        sleep "${PG_READY_SLEEP}"
    done
    log "ERROR: postgres not ready in ${container} after ${PG_READY_RETRIES} tries"
    return 1
}

# Reject empty (~20 B) or corrupt gzip. Fail-closed (F-01).
validate_dump_gz() {
    local gz="$1"
    local size

    if [[ ! -f "${gz}" ]]; then
        log "ERROR: dump missing: ${gz}"
        return 1
    fi
    if ! gzip -t "${gz}" 2>/dev/null; then
        log "ERROR: gzip -t failed: ${gz}"
        return 1
    fi
    size="$(wc -c < "${gz}" | tr -d ' ')"
    if [[ -z "${size}" ]] || (( size < MIN_DUMP_BYTES )); then
        log "ERROR: dump too small (${size:-0} < ${MIN_DUMP_BYTES} bytes): ${gz}"
        return 1
    fi
    return 0
}

dump_postgres() {
    local container="$1"
    local db_user="$2"
    local db_name="$3"
    local out_file="$4"
    local tmp="${out_file}.gz.partial"

    if ! wait_pg_ready "${container}" "${db_user}"; then
        return 1
    fi

    log "Dumping ${db_name} from ${container} → ${out_file}.gz"
    rm -f "${tmp}" "${out_file}.gz"
    if ! docker exec "${container}" \
        pg_dump -U "${db_user}" "${db_name}" \
        | gzip > "${tmp}"; then
        log "ERROR: pg_dump pipeline failed for ${db_name}"
        rm -f "${tmp}"
        return 1
    fi
    if ! validate_dump_gz "${tmp}"; then
        rm -f "${tmp}"
        return 1
    fi
    mv "${tmp}" "${out_file}.gz"
    log "Done: $(du -sh "${out_file}.gz" | cut -f1)"
}

rotate_old_dumps() {
    local prefix="$1"
    local keep="${BACKUP_KEEP_LAST}"
    log "Rotating old dumps for pattern '${prefix}' — keeping last ${keep}"
    local files
    mapfile -t files < <(ls -t "${DUMP_DIR}"/${prefix}_*.sql.gz 2>/dev/null)
    local total="${#files[@]}"
    if (( total > keep )); then
        local to_delete=$(( total - keep ))
        log "Deleting ${to_delete} old dump(s)"
        for f in "${files[@]:${keep}}"; do
            rm -f "${f}"
            log "Removed: ${f}"
        done
    fi
}

run_backup() {
    log "=== Database backup started ==="
    storage_ready
    mkdir -p "${DUMP_DIR}"

    ERRORS=0

    if container_running "${NEXTCLOUD_DB_CONTAINER}"; then
        NC_FILE="${DUMP_DIR}/nextcloud_${TIMESTAMP}.sql"
        if dump_postgres "${NEXTCLOUD_DB_CONTAINER}" \
                         "${NEXTCLOUD_DB_USER}" \
                         "${NEXTCLOUD_DB_NAME}" \
                         "${NC_FILE}"; then
            rotate_old_dumps "nextcloud"
        else
            log "ERROR: Nextcloud dump failed"
            ERRORS=$(( ERRORS + 1 ))
        fi
    else
        log "WARNING: Container ${NEXTCLOUD_DB_CONTAINER} is not running — skipping"
        ERRORS=$(( ERRORS + 1 ))
    fi

    if container_running "${IMMICH_DB_CONTAINER}"; then
        IM_FILE="${DUMP_DIR}/immich_${TIMESTAMP}.sql"
        if dump_postgres "${IMMICH_DB_CONTAINER}" \
                         "${IMMICH_DB_USER}" \
                         "${IMMICH_DB_NAME}" \
                         "${IM_FILE}"; then
            rotate_old_dumps "immich"
        else
            log "ERROR: Immich dump failed"
            ERRORS=$(( ERRORS + 1 ))
        fi
    else
        log "WARNING: Container ${IMMICH_DB_CONTAINER} is not running — skipping"
        ERRORS=$(( ERRORS + 1 ))
    fi

    log "=== Database backup finished — errors: ${ERRORS} ==="
    if (( ERRORS > 0 )); then
        exit 1
    fi
}

if [[ "${NAS_BACKUP_LIB_ONLY}" != "1" && "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [[ -f "${ENV_FILE}" ]]; then
        # shellcheck source=/dev/null
        source "${ENV_FILE}"
        log "Loaded env from ${ENV_FILE}"
        DUMP_DIR="${BACKUP_ROOT}/database-dumps"
    fi
    run_backup
fi
