#!/usr/bin/env bash
# Deployed on Jetson as /usr/local/sbin/nasa-offsite-export.sh (device naming,
# see "Расхождение git ↔ устройство" in CLAUDE.md — this file was created
# directly on-device 2026-08-22, not previously tracked in git).
#
# Forced command behind admin's authorized_keys entry for the Vostro pull key
# (docs/plans/WAVE_0_OFFSITE_BACKUP.md): the client's request line is
# deliberately ignored, only *.sql.gz dumps ever leave this way.
set -euo pipefail
DIR=/mnt/storage/backups/database-dumps
cd "$DIR" 2>/dev/null || { echo "offsite-export: no dump directory" >&2; exit 1; }
shopt -s nullglob
files=( *.sql.gz )
(( ${#files[@]} )) || { echo "offsite-export: no dumps present" >&2; exit 1; }
date -u +%s > /mnt/storage/backups/offsite-pull-last.stamp
exec tar -cf - -- "${files[@]}"
