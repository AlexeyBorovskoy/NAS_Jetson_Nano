#!/bin/bash
# aria2 on-download-complete: переносит готовое (файл или верхний каталог многофайлового
# торрента) из .incomplete в Downloads. С SSD — копированием на HDD, с HDD — переименованием.
# Аргументы aria2: GID, число файлов, путь первого файла. Имя занято — суффикс « (N)».
set -u
SSD_INC="${DL_SSD_INCOMPLETE:-/downloads/ssd/.incomplete}"
HDD_INC="${DL_HDD_INCOMPLETE:-/downloads/hdd/.incomplete}"
FINAL="${DL_FINAL:-/downloads/hdd}"
path="${3:-}"
[ -n "$path" ] || exit 0   # метаданные magnet: файла нет

src="" top=""
for root in "$SSD_INC" "$HDD_INC"; do
  case "$path" in
    "$root"/*)
      rel="${path#"$root"/}"
      top="${rel%%/*}"
      src="$root/$top"
      break ;;
  esac
done
case "$top" in ""|"."|"..") exit 0 ;; esac
[ -e "$src" ] || exit 0
[ -d "$FINAL" ] || { echo "on_complete: нет $FINAL — оставляю $src" >&2; exit 1; }

dst="$FINAL/$top"
n=2
while [ -e "$dst" ]; do
  if [ -d "$src" ]; then
    dst="$FINAL/$top ($n)"
  else
    base="${top%.*}"; ext=".${top##*.}"
    [ "$base" = "$top" ] && ext=""
    dst="$FINAL/$base ($n)$ext"
  fi
  n=$((n + 1))
done
mv -- "$src" "$dst" || { echo "on_complete: не перенёс $src" >&2; exit 1; }
