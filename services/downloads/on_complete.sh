#!/bin/bash
# aria2 on-download-complete: переносит готовое (файл или верхний каталог многофайлового
# торрента) из .incomplete в Downloads. С SSD — копированием на HDD, с HDD — переименованием.
# Аргументы aria2: GID, число файлов, путь первого файла. Имя занято (в том числе
# параллельной закачкой) — суффикс « (N)»; занятое имя не перезаписывается никогда.
set -u
SSD_INC="${DL_SSD_INCOMPLETE:-/downloads/ssd/.incomplete}"
HDD_INC="${DL_HDD_INCOMPLETE:-/downloads/hdd/.incomplete}"
FINAL="${DL_FINAL:-/downloads/hdd}"
path="${3:-}"
[ -n "$path" ] || exit 0   # метаданные magnet: файла нет

src="" top="" dest="$FINAL"
for root in "$SSD_INC" "$HDD_INC"; do
  case "$path" in
    "$root"/*)
      rel="${path#"$root"/}"
      # 2026-09-26: у каждого члена семьи своя папка — .incomplete/.u/<логин>/… → Downloads/<логин>/
      case "$rel" in
        .u/*/*)
          user="${rel#.u/}"; user="${user%%/*}"
          case "$user" in ""|*[!A-Za-z0-9_-]*) exit 0 ;; esac
          root="$root/.u/$user"; rel="${rel#.u/"$user"/}"; dest="$FINAL/$user" ;;
      esac
      top="${rel%%/*}"
      src="$root/$top"
      break ;;
  esac
done
case "$top" in ""|"."|"..") exit 0 ;; esac
[ -e "$src" ] || exit 0
is_dir=0
[ -d "$src" ] && is_dir=1
[ -d "$FINAL" ] || { echo "on_complete: нет $FINAL — оставляю $src" >&2; exit 1; }
if [ "$dest" != "$FINAL" ]; then
  mkdir -p -- "$dest" || { echo "on_complete: не создал $dest — оставляю $src" >&2; exit 1; }
fi
FINAL="$dest"

# Имя для попытки № $1: 1 — как есть, дальше — « (N)» (у файла суффикс перед расширением).
name_at() {
  local base ext
  if [ "$1" = 1 ]; then
    printf '%s/%s\n' "$FINAL" "$top"
  elif [ "$is_dir" = 1 ]; then
    printf '%s/%s (%s)\n' "$FINAL" "$top" "$1"
  else
    base="${top%.*}"; ext=".${top##*.}"
    [ "$base" = "$top" ] && ext=""
    printf '%s/%s (%s)%s\n' "$FINAL" "$base" "$1" "$ext"
  fi
}

MV="${DL_MV:-mv}"
tmp="$FINAL/.incoming.$$.$top"
if ! $MV -- "$src" "$tmp"; then
  rm -rf -- "$tmp"
  echo "on_complete: не перенёс $src — оставлен на месте" >&2
  exit 1
fi

# HK-1 (аудит 2026-09-26): выбрать свободное имя ЗАРАНЕЕ нельзя — между проверкой и mv
# имя может занять параллельная закачка (aria2 качает две разом), и тогда mv молча затрёт
# её файл. Поэтому переносим с -n (не перезаписывать), а о судьбе судим по факту: $tmp
# исчез — перенеслось, остался — имя заняли, берём следующий суффикс.
moved=0
try=1
while [ "$try" -le 100 ]; do
  dst="$(name_at "$try")"
  if [ ! -e "$dst" ]; then
    $MV -n -- "$tmp" "$dst" 2>/dev/null
    if [ ! -e "$tmp" ]; then
      # Каталог с таким именем mv не перезаписывает, а ПРИНИМАЕТ внутрь себя — наш
      # объект оказался бы спрятан в чужой папке. Возвращаем себе и берём суффикс.
      if [ -e "$dst/${tmp##*/}" ]; then
        $MV -n -- "$dst/${tmp##*/}" "$tmp" 2>/dev/null
        [ -e "$tmp" ] || { echo "on_complete: не вернул $top из чужого каталога $dst" >&2; exit 1; }
      else
        moved=1
        break
      fi
    elif [ ! -e "$dst" ]; then
      # Не перенеслось, а имя свободно — это не гонка, а отказ mv: говорим прямо.
      echo "on_complete: не перенёс $tmp в $dst — готовое оставлено в $tmp" >&2
      exit 1
    fi
  fi
  try=$((try + 1))
done
if [ "$moved" != 1 ]; then
  echo "on_complete: 100 имён занято для «$top» — готовое оставлено в $tmp" >&2
  exit 1
fi
