#!/usr/bin/env bash
# Runs ON VOSTRO (off-site node), not on Jetson. Pulls DB dumps from
# NAS_Jetson_Nano via VPS jump, stores them in the restic repository at
# /srv/nas-offsite. Phase 1: dumps only, no photos (docs/plans/WAVE_0_OFFSITE_BACKUP.md).
set -euo pipefail

export RESTIC_REPOSITORY=/srv/nas-offsite
export RESTIC_PASSWORD_FILE=/root/.nas-offsite-restic-password

# OPS-2: one source of truth shared with the Jetson tunnel configuration.
VPS_ENV="${NAS_TUNNEL_ENV:-/opt/nasa/config/.env}"
if [ -z "${VPS_HOST:-}" ]; then
    if [ ! -r "$VPS_ENV" ]; then
        echo "ERROR: VPS config is not readable: $VPS_ENV" >&2
        exit 1
    fi
    VPS_HOST="$(sed -n 's/^[[:space:]]*VPS_HOST[[:space:]]*=[[:space:]]*//p' \
        "$VPS_ENV" | tail -1 | tr -d '\r')"
    VPS_HOST="${VPS_HOST#\"}"
    VPS_HOST="${VPS_HOST%\"}"
fi
case "$VPS_HOST" in
    ""|*[!A-Za-z0-9._:-]*)
        echo "ERROR: VPS_HOST is missing or invalid in $VPS_ENV" >&2
        exit 1
        ;;
esac
VPS_USER="${VPS_USER:-root}"
OFFSITE_SSH_KEY="${OFFSITE_SSH_KEY:-/root/.ssh/id_nas_offsite}"

WORKDIR=$(mktemp -d /tmp/nas-offsite-pull.XXXXXX)
trap 'rm -rf "$WORKDIR"' EXIT

ssh -o ProxyCommand="ssh -i ${OFFSITE_SSH_KEY} -o StrictHostKeyChecking=accept-new -W %h:%p ${VPS_USER}@${VPS_HOST}" \
    -p 10022 -i "$OFFSITE_SSH_KEY" \
    -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    admin@127.0.0.1 'ignored — forced command on Jetson overrides this' \
    | tar -xf - -C "$WORKDIR"

restic backup "$WORKDIR" --tag nas-jetson-dumps --host nas-jetson-nano
restic forget --keep-daily 14 --keep-weekly 8 --prune
