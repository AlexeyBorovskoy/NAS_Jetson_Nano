#!/bin/bash
set -euo pipefail

# ---------------------------------------------------------------------------
# restic_backup_example.sh — full restic backup workflow for NAS_Jetson_Nano
# ---------------------------------------------------------------------------
# Usage: ./restic_backup_example.sh
# Reads config from ../../config/.env relative to this script's location.
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../config/.env"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Load environment if available
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    log "Loaded env from ${ENV_FILE}"
fi

# ---- Required variables ----------------------------------------------------
: "${RESTIC_REPOSITORY:?Set RESTIC_REPOSITORY in config/.env}"
: "${RESTIC_PASSWORD:?Set RESTIC_PASSWORD (or RESTIC_PASSWORD_FILE) in config/.env}"
export RESTIC_REPOSITORY
export RESTIC_PASSWORD

# ---- Defaults (overridden by .env) -----------------------------------------
STORAGE_ROOT="${STORAGE_ROOT:-/mnt/storage}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/storage/backups}"
BACKUP_RETENTION_DAILY="${BACKUP_RETENTION_DAILY:-7}"
BACKUP_RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-4}"
BACKUP_RETENTION_MONTHLY="${BACKUP_RETENTION_MONTHLY:-3}"

# ---------------------------------------------------------------------------
# 1. Init restic repo if it doesn't exist yet
# ---------------------------------------------------------------------------
log "=== Restic backup started ==="
log "Repository: ${RESTIC_REPOSITORY}"

if restic snapshots --quiet > /dev/null 2>&1; then
    log "Restic repository already initialised"
else
    log "Initialising new restic repository at ${RESTIC_REPOSITORY}"
    restic init
fi

# ---------------------------------------------------------------------------
# 2. Run database dumps first
# ---------------------------------------------------------------------------
log "Running database dumps before backup..."
DB_SCRIPT="${SCRIPT_DIR}/backup_databases.sh"
if [[ -x "${DB_SCRIPT}" ]]; then
    "${DB_SCRIPT}"
else
    log "WARNING: ${DB_SCRIPT} not found or not executable — skipping DB dump"
fi

# ---------------------------------------------------------------------------
# 3. Restic backup
# ---------------------------------------------------------------------------
log "Starting restic backup of ${STORAGE_ROOT}"
restic backup "${STORAGE_ROOT}" \
    --exclude="*.sock" \
    --exclude="*/tmp/*" \
    --exclude="*/lost+found/*" \
    --exclude="*/restic-repo/*" \
    --tag "homecloud" \
    --verbose

# ---------------------------------------------------------------------------
# 4. Pruning — apply retention policy
# ---------------------------------------------------------------------------
log "Applying retention policy: daily=${BACKUP_RETENTION_DAILY} weekly=${BACKUP_RETENTION_WEEKLY} monthly=${BACKUP_RETENTION_MONTHLY}"
restic forget \
    --keep-daily  "${BACKUP_RETENTION_DAILY}" \
    --keep-weekly "${BACKUP_RETENTION_WEEKLY}" \
    --keep-monthly "${BACKUP_RETENTION_MONTHLY}" \
    --prune \
    --verbose

# ---------------------------------------------------------------------------
# 5. Integrity check
# ---------------------------------------------------------------------------
log "Verifying repository integrity (check --read-data-subset=5%)..."
restic check --read-data-subset=5%

log "=== Restic backup completed successfully ==="
