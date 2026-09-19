#!/bin/bash
# aria2 on-download-stop (отмена или ошибка; готовое обрабатывает on_complete.sh):
# удаляет недокачанное из .incomplete, чтобы отменённые 100 ГБ не остались на HDD.
# Трогает ТОЛЬКО верхний элемент внутри .incomplete; «..» и пути вне корней — игнор.
set -u
SSD_INC="${DL_SSD_INCOMPLETE:-/downloads/ssd/.incomplete}"
HDD_INC="${DL_HDD_INCOMPLETE:-/downloads/hdd/.incomplete}"
path="${3:-}"
[ -n "$path" ] || exit 0
case "$path" in *"/../"*|*"/.."|"../"*) exit 0 ;; esac

for root in "$SSD_INC" "$HDD_INC"; do
  case "$path" in
    "$root"/*)
      rel="${path#"$root"/}"
      top="${rel%%/*}"
      case "$top" in ""|"."|"..") exit 0 ;; esac
      rm -rf -- "$root/$top" "$root/$top.aria2"
      exit 0 ;;
  esac
done
exit 0
