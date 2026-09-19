#!/usr/bin/env bash
# Бэкап конфигурации и файлов Nextcloud (restic, шифрованно) — этап B, задачи B1/B3.
#
# Зачем: аудит 2026-09-19 (NAS-BAK-001) — `.env` с секретами, `config.php` Nextcloud,
# файлы Nextcloud и пользователи Samba не копировались никуда. Дампы БД копировались,
# и это создавало иллюзию, что бэкап есть.
#
# Цели (targets) — файлы `$NAS_BACKUP_TARGETS_DIR/<имя>.env` (root, 600):
#   RESTIC_REPOSITORY=/mnt/hdd2tb/backups/restic-config    # или s3:https://... (B3)
#   RESTIC_PASSWORD_FILE=/root/.config/nas-backup/hdd.pass
#   REQUIRES_MOUNT=/mnt/hdd2tb                              # необязательно
#   AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...         # только для S3
# Каталог целей НЕ в $NAS_CONF_DIR: тот смонтирован в контейнер API.
#
# Режимы:  (без аргументов) бэкап во все цели  |  --plan  список источников
#          --init  создать репозитории (явно, один раз)
# Код возврата: 0 — все цели успешно; 1 — отказ/ошибка; 2 — частичный (ALLOW_PARTIAL).
# Штамп успеха: $NAS_STATE_DIR/config-backup-<цель>.stamp (эпоха) — для алерта возраста.
#
# Ограничение: файлы Nextcloud копируются без maintenance mode — снимок на уровне
# файлов, дамп БД сделан в 03:00 отдельно. Для семейного объёма (~260 МБ) принято.
set -uo pipefail

_nas_lay="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/layout.sh"
[[ -r "$_nas_lay" ]] || _nas_lay=/usr/local/lib/nas_jetson_nano/layout.sh
# shellcheck source=../lib/layout.sh
source "$_nas_lay"

STORAGE="${NAS_STORAGE_ROOT:-/mnt/storage}"
TARGETS_DIR="${NAS_BACKUP_TARGETS_DIR:-/root/.config/nas-backup/targets}"
LAYOUT_FILE="${NAS_LAYOUT_FILE:-/etc/nas-layout.env}"
TAG="nas-config"
HOST_TAG="nas-jetson-nano"
KEEP=(--keep-daily 7 --keep-weekly 4 --keep-monthly 6)

log() { echo "[$(date -Iseconds)] config-backup: $*"; }

vol_path() { docker volume inspect -f '{{.Mountpoint}}' "$1" 2>/dev/null; }

# Строки «req|путь» или «opt|путь». Порядок — от важного к объёмному.
plan() {
    local nc sb
    nc="$(vol_path homecloud-nextcloud_nextcloud_app)"
    sb="$(vol_path homecloud-samba_samba_data)"
    echo "req|${NAS_ENV_FILE}"
    echo "opt|${NAS_OPT_DIR}/config/.env"
    echo "opt|${NAS_CONF_DIR}"
    echo "opt|${LAYOUT_FILE}"
    echo "req|${nc:-<volume homecloud-nextcloud_nextcloud_app>}/config"
    echo "opt|${sb:-<volume homecloud-samba_samba_data>}"
    echo "req|${STORAGE}/nextcloud/data"
    echo "req|${STORAGE}/backups/database-dumps"
}

MODE="${1:-backup}"
if [[ "$MODE" == "--plan" ]]; then
    plan
    exit 0
fi

# ── источники ────────────────────────────────────────────────────────────────
if ! mountpoint -q "$STORAGE"; then
    log "ERROR: $STORAGE не смонтирован — отказ"
    exit 1
fi

sources=()
missing=0
while IFS='|' read -r kind path; do
    if [[ -e "$path" ]]; then
        sources+=("$path")
    elif [[ "$kind" == "req" ]]; then
        log "ERROR: нет обязательного источника: $path"
        missing=$((missing + 1))
    else
        log "skip (нет необязательного): $path"
    fi
done < <(plan)

if (( missing > 0 )) && [[ "${NAS_BACKUP_ALLOW_PARTIAL:-0}" != "1" ]]; then
    log "ERROR: пропущено обязательных источников: $missing — бэкап не делается"
    exit 1
fi

# ── цели ─────────────────────────────────────────────────────────────────────
shopt -s nullglob
targets=("$TARGETS_DIR"/*.env)
if (( ${#targets[@]} == 0 )); then
    log "ERROR: нет ни одной цели (target) в $TARGETS_DIR"
    exit 1
fi

rc=0
for t in "${targets[@]}"; do
    name="$(basename "$t" .env)"
    (
        set -a
        # shellcheck source=/dev/null
        source "$t"
        set +a
        if [[ -n "${REQUIRES_MOUNT:-}" ]] && ! mountpoint -q "$REQUIRES_MOUNT"; then
            log "ERROR[$name]: $REQUIRES_MOUNT не смонтирован"
            exit 1
        fi
        if [[ "$MODE" == "--init" ]]; then
            if restic cat config >/dev/null 2>&1; then
                log "[$name] репозиторий уже есть"
                exit 0
            fi
            restic init
            exit $?
        fi
        restic backup --tag "$TAG" --host "$HOST_TAG" "${sources[@]}" || exit 1
        restic forget --tag "$TAG" --host "$HOST_TAG" "${KEEP[@]}" --prune || exit 1
    )
    r=$?
    if (( r == 0 )); then
        if [[ "$MODE" != "--init" ]]; then
            mkdir -p "$NAS_STATE_DIR"
            date +%s > "$NAS_STATE_DIR/config-backup-$name.stamp"
        fi
        log "[$name] OK"
    else
        log "ERROR[$name]: rc=$r"
        rc=1
    fi
done

if (( rc == 0 && missing > 0 )); then
    log "ЧАСТИЧНЫЙ бэкап: не хватало обязательных источников ($missing)"
    exit 2
fi
exit "$rc"
