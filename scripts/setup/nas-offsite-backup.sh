#!/usr/bin/env bash
# Runs ON VOSTRO (off-site node), not on Jetson. Pulls DB dumps from
# NAS_Jetson_Nano via VPS jump, stores them in the restic repository at
# /srv/nas-offsite. Phase 1: dumps only, no photos (docs/plans/WAVE_0_OFFSITE_BACKUP.md).
set -euo pipefail

export RESTIC_REPOSITORY=/srv/nas-offsite
export RESTIC_PASSWORD_FILE=/root/.nas-offsite-restic-password

WORKDIR=$(mktemp -d /tmp/nas-offsite-pull.XXXXXX)
trap 'rm -rf "$WORKDIR"' EXIT

ssh -o ProxyCommand="ssh -i /root/.ssh/id_nas_offsite -o StrictHostKeyChecking=accept-new -W %h:%p root@95.163.176.103" \
    -p 10022 -i /root/.ssh/id_nas_offsite \
    -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    admin@127.0.0.1 'ignored — forced command on Jetson overrides this' \
    | tar -xf - -C "$WORKDIR"

restic backup "$WORKDIR" --tag nas-jetson-dumps --host nas-jetson-nano
restic forget --keep-daily 14 --keep-weekly 8 --prune
