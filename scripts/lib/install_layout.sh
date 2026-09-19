#!/usr/bin/env bash
# Установить библиотеку раскладки на хост / install the host-layout library.
#
# Что делает:
#   1. копирует layout.sh и nas_layout.py в /usr/local/lib/nas_jetson_nano/ —
#      их ищут копии скриптов, живущие в /usr/local/sbin;
#   2. создаёт /etc/nas-layout.env с ТЕКУЩЕЙ раскладкой (префикс + каталог проекта),
#      если файла ещё нет. Существующий файл не трогает — показывает расхождение.
#
# Запуск на Jetson из каталога проекта, только в окне деплоя:
#   sudo bash scripts/lib/install_layout.sh
# Проверка:   bash -c 'source /usr/local/lib/nas_jetson_nano/layout.sh; env | grep ^NAS_'
# Откат:      sudo rm -r /usr/local/lib/nas_jetson_nano /etc/nas-layout.env
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST=/usr/local/lib/nas_jetson_nano
LAYOUT_FILE=/etc/nas-layout.env

[[ $EUID -eq 0 ]] || { echo "нужен root (sudo)" >&2; exit 1; }

# shellcheck source=layout.sh
source "$SRC/layout.sh"

install -d -m 755 "$DEST"
install -m 644 "$SRC/layout.sh" "$SRC/nas_layout.py" "$DEST/"
echo "библиотека: $DEST"

wanted="NAS_PREFIX=${NAS_PREFIX}
NAS_PROJECT_DIR=${NAS_PROJECT_DIR}"

if [[ -f "$LAYOUT_FILE" ]]; then
    echo "$LAYOUT_FILE уже есть — не перезаписываю. Сверка:"
    diff <(grep -E '^NAS_(PREFIX|PROJECT_DIR)=' "$LAYOUT_FILE" | sort) <(sort <<<"$wanted") \
        && echo "  совпадает" || echo "  ⚠ расходится — проверить вручную"
else
    {
        echo "# Раскладка хоста NAS_Jetson_Nano (scripts/lib/layout.sh). KEY=VALUE, не исполняется."
        echo "# Создано $(date -Iseconds) установщиком install_layout.sh."
        echo "$wanted"
    } > "$LAYOUT_FILE"
    chmod 644 "$LAYOUT_FILE"
    echo "создан $LAYOUT_FILE:"; sed 's/^/  /' "$LAYOUT_FILE"
fi
