#!/usr/bin/env bash
# Настроить/откатить machineLearning.urls в Immich через REST API (D4, вариант Б).
#
# ЗАЧЕМ ЧЕРЕЗ API, А НЕ ЧЕРЕЗ .env: с версии, где появился Administration Settings
# UI, machineLearning.urls хранится в самом Immich (таблица system_metadata) и
# переопределяет то, что задано переменной окружения IMMICH_MACHINE_LEARNING_URL
# при первом старте. Значит менять .env и перезапускать контейнер — не тот путь;
# нужен PUT /api/system-config, как это делает сам Admin UI.
#
# Поле подтверждено в OpenAPI-спеке Immich, закреплённой на тег v2.7.5 (та же
# версия, что на Jetson, IMMICH_VERSION=v2.7.5, D6/DEP-2):
#   https://raw.githubusercontent.com/immich-app/immich/v2.7.5/open-api/immich-openapi-specs.json
#   schemas.SystemConfigMachineLearningDto: { enabled: bool, urls: string[] (uri, minItems 1), ... }
#   paths./system-config: { get, put }; auth — заголовок `x-api-key`.
# PUT заменяет ВЕСЬ объект конфигурации (все поля required) — поэтому сначала
# читаем текущий конфиг целиком, правим только машинное обучение, и отправляем
# обратно целиком. GET тоже используется как бэкап перед заменой.
#
# Приватность: сам вызов идёт по домашней сети (Jetson localhost или LAN),
# наружу ничего не уходит; API-ключ читается из переменной окружения и никогда
# не печатается и не попадает в бэкап-файл (бэкап — это ответ /system-config,
# в котором ключей нет).
#
# Usage:
#   export IMMICH_API_KEY='...'                # обязателен, не коммитить
#   # опционально: IMMICH_BASE_URL (по умолчанию http://127.0.0.1:2283 — запуск на Jetson;
#   #              с другой машины в LAN — http://192.168.0.50:2283)
#   # опционально: IMMICH_CONFIG_BACKUP_DIR (по умолчанию /mnt/storage/backups/immich-system-config)
#
#   bash scripts/immich/set_ml_url.sh set http://172.17.0.1:3003 [ещё URL...]
#   bash scripts/immich/set_ml_url.sh restore /mnt/storage/backups/immich-system-config/system-config.<ts>.json
#   bash scripts/immich/set_ml_url.sh show
#
# Откат (см. docs/plans/IMMICH_ML_STATION_RUNBOOK.ru.md, раздел «Откат»):
#   найти последний файл бэкапа в IMMICH_CONFIG_BACKUP_DIR и вызвать `restore` с ним.
set -euo pipefail

: "${IMMICH_API_KEY:?export IMMICH_API_KEY=... (Administration -> API Keys в Immich)}"
BASE="${IMMICH_BASE_URL:-http://127.0.0.1:2283}"
BASE="${BASE%/}"

MODE="${1:-}"
shift || true

PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "python3 не найден — нечем разобрать JSON" >&2; exit 2; }

# Бэкап-каталог: предпочитаем постоянное хранилище на Jetson, но если скрипт
# запущен не на устройстве (например, с рабочей станции) и каталога нет —
# не падаем, а тихо уходим в локальный каталог рядом с текущей директорией.
BACKUP_DIR="${IMMICH_CONFIG_BACKUP_DIR:-/mnt/storage/backups/immich-system-config}"
if ! mkdir -p "$BACKUP_DIR" 2>/dev/null; then
    BACKUP_DIR="./immich-system-config-backups"
    mkdir -p "$BACKUP_DIR"
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
CUR_FILE="$(mktemp)"
BACKUP_FILE="${BACKUP_DIR}/system-config.${TS}.json"
trap 'rm -f "$CUR_FILE"' EXIT

fetch_current() {
    local code
    code=$(curl -sS -H "x-api-key: ${IMMICH_API_KEY}" \
        -o "$CUR_FILE" -w "%{http_code}" \
        "${BASE}/api/system-config")
    if [ "$code" != "200" ]; then
        echo "GET /api/system-config -> HTTP $code" >&2
        head -c 400 "$CUR_FILE" >&2 2>/dev/null || true
        echo >&2
        exit 1
    fi
}

put_config() {
    local file="$1"
    local out code
    out="$(mktemp)"
    code=$(curl -sS -X PUT \
        -H "x-api-key: ${IMMICH_API_KEY}" \
        -H "Content-Type: application/json" \
        --data-binary "@${file}" \
        -o "$out" -w "%{http_code}" \
        "${BASE}/api/system-config")
    if [ "$code" != "200" ]; then
        echo "PUT /api/system-config -> HTTP $code" >&2
        head -c 800 "$out" >&2 2>/dev/null || true
        echo >&2
        rm -f "$out"
        exit 1
    fi
    echo "PUT /api/system-config -> HTTP 200"
    "$PY" - "$out" <<'PYEOF'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
print("machineLearning:", json.dumps(data.get("machineLearning"), ensure_ascii=False))
PYEOF
    rm -f "$out"
}

case "$MODE" in
    show)
        fetch_current
        "$PY" - "$CUR_FILE" <<'PYEOF'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
print(json.dumps(data.get("machineLearning"), ensure_ascii=False, indent=2))
PYEOF
        ;;

    set)
        [ "$#" -ge 1 ] || { echo "usage: $0 set <url> [url2 ...]" >&2; exit 2; }
        fetch_current
        cp "$CUR_FILE" "$BACKUP_FILE"
        echo "Бэкап текущего system-config: $BACKUP_FILE"

        NEW_FILE="$(mktemp)"
        "$PY" - "$CUR_FILE" "$NEW_FILE" "$@" <<'PYEOF'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
urls = sys.argv[3:]
with open(src, encoding="utf-8") as fh:
    data = json.load(fh)
data.setdefault("machineLearning", {})
data["machineLearning"]["enabled"] = True
data["machineLearning"]["urls"] = urls
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False)
PYEOF
        put_config "$NEW_FILE"
        rm -f "$NEW_FILE"
        ;;

    restore)
        [ "$#" -ge 1 ] || { echo "usage: $0 restore <backup-file.json>" >&2; exit 2; }
        RESTORE_FILE="$1"
        [ -f "$RESTORE_FILE" ] || { echo "не найден файл бэкапа: $RESTORE_FILE" >&2; exit 2; }
        echo "Восстанавливаю system-config из $RESTORE_FILE (полная замена, как при set)"
        put_config "$RESTORE_FILE"
        ;;

    *)
        echo "usage: $0 {set <url> [url2...] | restore <backup.json> | show}" >&2
        exit 2
        ;;
esac
