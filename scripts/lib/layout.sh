# shellcheck shell=bash
# NAS_Jetson_Nano — единая раскладка хоста / single source of truth for host paths.
#
# Подключать через `source`, не исполнять. Python-двойник: scripts/lib/nas_layout.py —
# правила обязаны совпадать (tests/unit/test_layout.py сверяет их между собой).
#
# Зачем: 2026-09-08 на устройство пришёл код с новыми именами (`nas_jetson_nano-*`),
# а устройство жило по старым (`nasa-*`). Захардкоженный путь сломал авто-восстановление
# SSD на 11 дней. Раскладка — конфигурация хоста, а не код: скрипт спрашивает её здесь.
#
# Порядок разрешения каждой переменной:
#   1. явная переменная окружения (например, из systemd `Environment=`);
#   2. файл раскладки `/etc/nas-layout.env` (строки KEY=VALUE, не исполняется);
#   3. автоопределение: есть только старые каталоги `nasa-monitor` → префикс `nasa`;
#   4. целевые имена `nas_jetson_nano`.
#
# Переезд устройства (Part B) = поправить `/etc/nas-layout.env` и перенести каталоги;
# менять скрипты не нужно.
#
# NAS_LAYOUT_ROOT — корень для автоопределения и поиска файла (только для тестов).

_nas_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_nas_root="${NAS_LAYOUT_ROOT:-}"
_nas_file="${NAS_LAYOUT_FILE:-${_nas_root}/etc/nas-layout.env}"

if [[ -r "$_nas_file" ]]; then
    while IFS='=' read -r _nas_k _nas_v || [[ -n "$_nas_k" ]]; do
        [[ "$_nas_k" =~ ^NAS_[A-Z_]+$ ]] || continue
        [[ -n "${!_nas_k:-}" ]] && continue          # явное окружение сильнее файла
        _nas_v="${_nas_v%$'\r'}"
        _nas_v="${_nas_v%\"}"; _nas_v="${_nas_v#\"}"
        printf -v "$_nas_k" '%s' "$_nas_v"
    done < "$_nas_file"
fi

if [[ -z "${NAS_PREFIX:-}" ]]; then
    if [[ ! -d "${_nas_root}/etc/nas_jetson_nano-monitor" ]] \
       && [[ -d "${_nas_root}/etc/nasa-monitor" || -d "${_nas_root}/var/log/nasa-monitor" ]]; then
        NAS_PREFIX="nasa"
    else
        NAS_PREFIX="nas_jetson_nano"
    fi
fi

: "${NAS_PROJECT_DIR:=$(cd "${_nas_lib_dir}/../.." && pwd)}"
: "${NAS_ENV_FILE:=${NAS_PROJECT_DIR}/config/.env}"
: "${NAS_CONF_DIR:=/etc/${NAS_PREFIX}-monitor}"
: "${NAS_LOG_DIR:=/var/log/${NAS_PREFIX}-monitor}"
: "${NAS_STATE_DIR:=/var/lib/${NAS_PREFIX}-monitor}"
: "${NAS_SBIN_PREFIX:=/usr/local/sbin/${NAS_PREFIX}}"
: "${NAS_UNIT_PREFIX:=${NAS_PREFIX}}"
: "${NAS_OPT_DIR:=/opt/${NAS_PREFIX}}"
# Решение 2026-08-30: API-контейнер не переименовывается (конфликт порта 8099).
: "${NAS_API_CONTAINER:=homecloud_nasa_api}"

export NAS_PREFIX NAS_PROJECT_DIR NAS_ENV_FILE NAS_CONF_DIR NAS_LOG_DIR NAS_STATE_DIR \
       NAS_SBIN_PREFIX NAS_UNIT_PREFIX NAS_OPT_DIR NAS_API_CONTAINER

unset _nas_lib_dir _nas_root _nas_file _nas_k _nas_v
