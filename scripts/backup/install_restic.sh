#!/usr/bin/env bash
# Установить restic закреплённой версии с проверкой SHA-256 (этап B).
#
# Зачем своя сборка: в Ubuntu 18.04 (Jetson) пакет restic — 0.8.x (2018), без
# сжатия и с устаревшим форматом; закреплённая версия + хэш = воспроизводимо и
# защищено от подмены при скачивании.
#
# Хэш — из подписанного SHA256SUMS релиза, сверен 2026-09-19.
# Использование (root, в окне деплоя):
#   sudo bash scripts/backup/install_restic.sh                 # скачать с GitHub
#   sudo bash scripts/backup/install_restic.sh /tmp/restic.bz2  # локальный файл (Jetson без GitHub)
set -euo pipefail

VERSION="0.19.1"
declare -A SHA256=(
    [arm64]="a5f64aaab53d51e311fa3829124c5b703f2d14cf187d8640b6be3b2b49376465"
)
DEST=/usr/local/bin/restic

case "$(uname -m)" in
    aarch64|arm64) ARCH=arm64 ;;
    *) echo "архитектура $(uname -m) не закреплена в скрипте" >&2; exit 1 ;;
esac

if [[ -x "$DEST" ]] && "$DEST" version 2>/dev/null | grep -q "restic ${VERSION} "; then
    echo "restic ${VERSION} уже установлен: $DEST"
    exit 0
fi

[[ $EUID -eq 0 ]] || { echo "нужен root (sudo)" >&2; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
file="$work/restic_${VERSION}_linux_${ARCH}.bz2"

if [[ -n "${1:-}" ]]; then
    cp "$1" "$file"
else
    curl -fsSL -o "$file" \
        "https://github.com/restic/restic/releases/download/v${VERSION}/restic_${VERSION}_linux_${ARCH}.bz2"
fi

echo "${SHA256[$ARCH]}  $file" | sha256sum -c - || { echo "SHA-256 НЕ совпал — не устанавливаю" >&2; exit 1; }

bunzip2 "$file"
install -m 0755 "${file%.bz2}" "$DEST"
"$DEST" version
