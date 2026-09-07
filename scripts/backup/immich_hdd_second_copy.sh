#!/usr/bin/env bash
# Immich on-site second copy → HDD (ADR-0009 / DEVELOPMENT_PLAN W2).
# Run on Jetson only. Does NOT delete source. Does NOT touch Cloud.ru.
#
# Usage:
#   sudo bash scripts/backup/immich_hdd_second_copy.sh
#   DRY_RUN=1 sudo bash scripts/backup/immich_hdd_second_copy.sh
#
# Env overrides:
#   IMMICH_SRC   default /mnt/storage/immich
#   IMMICH_DST   default /mnt/hdd2tb/backups/immich
#   MIN_FREE_GB  default 20

set -euo pipefail

IMMICH_SRC="${IMMICH_SRC:-/mnt/storage/immich}"
IMMICH_DST="${IMMICH_DST:-/mnt/hdd2tb/backups/immich}"
MIN_FREE_GB="${MIN_FREE_GB:-20}"
DRY_RUN="${DRY_RUN:-0}"
LOG_TAG="immich-hdd-copy"

log() { echo "[$(date -Iseconds)] $LOG_TAG: $*"; }

if [[ ! -d "$IMMICH_SRC" ]]; then
  log "ERROR: source missing: $IMMICH_SRC"
  exit 1
fi

if [[ ! -d /mnt/hdd2tb ]]; then
  log "ERROR: HDD mount missing: /mnt/hdd2tb"
  exit 1
fi

# Free space on destination filesystem (GB)
free_gb=$(df -BG --output=avail /mnt/hdd2tb | tail -1 | tr -dc '0-9')
if [[ -z "$free_gb" ]] || (( free_gb < MIN_FREE_GB )); then
  log "ERROR: free space ${free_gb:-?}GB < MIN_FREE_GB ${MIN_FREE_GB}GB on /mnt/hdd2tb"
  exit 1
fi

mkdir -p "$IMMICH_DST"

RSYNC_OPTS=(-a --info=stats2)
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_OPTS+=(--dry-run)
  log "DRY_RUN=1"
fi

log "rsync $IMMICH_SRC/ → $IMMICH_DST/"
# Trailing slashes: copy contents into destination tree
rsync "${RSYNC_OPTS[@]}" "$IMMICH_SRC/" "$IMMICH_DST/"
log "done"
