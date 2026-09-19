#!/usr/bin/env bash
# Учения по восстановлению (этап B, задача B6): распаковать последний снапшот
# конфигурации во временный каталог и проверить, что из него можно подняться.
#
# Зачем: «бэкап есть» ≠ «из бэкапа можно восстановиться». Проверяется не наличие
# снапшота, а содержимое: каждый обязательный источник на месте, `.env` читается
# под `set -euo pipefail` (урок 16 дней простоя бэкапов из-за одной пары кавычек),
# `config.php` содержит instanceid, свежий дамп проходит `gzip -t`.
#
# Использование:  restore_drill.sh [цель]   (по умолчанию hdd)
# Код возврата 0 — «DRILL OK» + штамп $NAS_STATE_DIR/restore-drill-<цель>.stamp.
# Ничего не меняет в живой системе: пишет только во временный каталог и штамп.
set -uo pipefail

HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
_nas_lay="$HERE/../lib/layout.sh"
[[ -r "$_nas_lay" ]] || _nas_lay=/usr/local/lib/nas_jetson_nano/layout.sh
# shellcheck source=../lib/layout.sh
source "$_nas_lay"

TARGET="${1:-hdd}"
TARGETS_DIR="${NAS_BACKUP_TARGETS_DIR:-/root/.config/nas-backup/targets}"
# Распаковка — на SSD (ext4): ntfs-3g на HDD может отказать в chown, и restore упадёт.
TMP_BASE="${NAS_DRILL_TMP:-${NAS_STORAGE_ROOT:-/mnt/storage}/.restore-drill}"
TAG="nas-config"
HOST_TAG="nas-jetson-nano"

log() { echo "[$(date -Iseconds)] restore-drill: $*"; }
fail=0
bad() { log "FAIL: $*"; fail=$((fail + 1)); }

tfile="$TARGETS_DIR/$TARGET.env"
[[ -r "$tfile" ]] || { log "ERROR: нет цели $tfile"; exit 1; }
set -a
# shellcheck source=/dev/null
source "$tfile"
set +a

mkdir -p "$TMP_BASE"
tmp="$(mktemp -d "$TMP_BASE/drill.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

log "restore latest ($TARGET) → $tmp"
if ! restic restore latest --tag "$TAG" --host "$HOST_TAG" --target "$tmp" >/dev/null; then
    log "ERROR: restic restore не удался"
    exit 1
fi

# Путь внутри распакованного дерева: /mnt/x → mnt/x; C:/x (Windows-тесты) → C/x.
restored() { local p="${1#/}"; echo "$tmp/${p/:/}"; }

env_file=""; ncconf=""; dumps=""; ncdata=""
while IFS='|' read -r kind path; do
    rp="$(restored "$path")"
    if [[ -e "$rp" ]]; then
        case "$path" in
            "$NAS_ENV_FILE") env_file="$rp" ;;
            */config) ncconf="$rp/config.php" ;;
            */database-dumps) dumps="$rp" ;;
            */nextcloud/data) ncdata="$rp" ;;
        esac
    elif [[ "$kind" == "req" ]]; then
        bad "в снапшоте нет обязательного: $path"
    fi
done < <(bash "$HERE/config_backup.sh" --plan)

if [[ -n "$env_file" ]]; then
    ( set -euo pipefail; source "$env_file" >/dev/null 2>&1 ) || bad ".env из снапшота не читается под set -e"
fi
if [[ -z "$ncconf" || ! -f "$ncconf" ]]; then
    bad "нет config.php Nextcloud"
elif ! grep -q "'instanceid'" "$ncconf"; then
    bad "config.php без instanceid"
fi
if [[ -n "$dumps" ]]; then
    newest="$(ls -t "$dumps"/*.sql.gz 2>/dev/null | head -1)"
    if [[ -z "$newest" ]]; then bad "в снапшоте нет дампов"
    elif ! gzip -t "$newest"; then bad "дамп не проходит gzip -t: $(basename "$newest")"
    fi
fi
if [[ -n "$ncdata" ]] && [[ -z "$(find "$ncdata" -type f -print -quit)" ]]; then
    bad "файлы Nextcloud пусты"
fi

if (( fail > 0 )); then
    log "DRILL FAILED: $fail"
    exit 1
fi
mkdir -p "$NAS_STATE_DIR"
date +%s > "$NAS_STATE_DIR/restore-drill-$TARGET.stamp"
log "DRILL OK ($TARGET)"
