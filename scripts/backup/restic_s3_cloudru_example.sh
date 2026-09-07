#!/usr/bin/env bash
# EXAMPLE — Cloud.ru Object Storage off-site (ADR-0009 L2). Does nothing destructive by default.
# Fill secrets via env or root-only files. Never commit real keys.
#
# Prerequisites (console):
#   - Object Storage bucket created (or free-tier)
#   - S3 access key: Access Key ID = <tenant_id>:<key_id>, Secret = Key Secret
#   - endpoint https://s3.cloud.ru  region ru-central-1
#
# Usage:
#   export AWS_ACCESS_KEY_ID='tenant:keyid'
#   export AWS_SECRET_ACCESS_KEY='...'
#   export RESTIC_PASSWORD_FILE=/root/.config/homecloud/restic-s3-password
#   export RESTIC_REPOSITORY='s3:https://s3.cloud.ru/your-bucket/nas-restic'
#   DRY_RUN=1 bash scripts/backup/restic_s3_cloudru_example.sh
set -euo pipefail

: "${RESTIC_REPOSITORY:?set RESTIC_REPOSITORY}"
: "${RESTIC_PASSWORD_FILE:?set RESTIC_PASSWORD_FILE}"
: "${AWS_ACCESS_KEY_ID:?set AWS_ACCESS_KEY_ID}"
: "${AWS_SECRET_ACCESS_KEY:?set AWS_SECRET_ACCESS_KEY}"

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-ru-central-1}"

# Prefer DB dumps first — small, high value. Photos only after explicit OK.
SRC_DUMPS="${SRC_DUMPS:-/mnt/storage/backups/database-dumps}"
SRC_EXTRA="${SRC_EXTRA:-}"  # e.g. empty; do not default to full Immich

if [[ ! -d "$SRC_DUMPS" ]]; then
  echo "WARN: $SRC_DUMPS missing — create dumps first"
fi

if [[ "${INIT:-0}" == "1" ]]; then
  restic -r "$RESTIC_REPOSITORY" init
fi

ARGS=(backup --verbose)
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  ARGS+=(--dry-run)
fi

ARGS+=("$SRC_DUMPS")
if [[ -n "$SRC_EXTRA" ]]; then
  ARGS+=("$SRC_EXTRA")
fi

echo "restic ${ARGS[*]}"
restic -r "$RESTIC_REPOSITORY" "${ARGS[@]}"

if [[ "${PRUNE:-0}" == "1" ]]; then
  restic -r "$RESTIC_REPOSITORY" forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
fi

echo "snapshots:"
restic -r "$RESTIC_REPOSITORY" snapshots
