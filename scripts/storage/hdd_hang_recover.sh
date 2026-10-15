#!/usr/bin/env bash
# NAS_Jetson_Nano — ручное восстановление после зависания ntfs-3g на /mnt/hdd2tb.
#
# ЗАЧЕМ. Инцидент 13-14.10.2026 (CLAUDE.md «Грабли»): два параллельных обхода
# внешней библиотеки Immich повесили демон ntfs-3g — `stat -f /mnt/hdd2tb` не
# отвечал, счётчики диска в /proc/diskstats не менялись. Сторож контейнеров
# (OPS-1) увидел Nextcloud `unhealthy` и сделал `docker restart` — контейнер
# держал bind на мёртвом монтировании и не поднялся, Nextcloud лежал 10 часов.
# С OPS-2 сторож сам больше не трогает держателей /mnt/hdd2tb при зависании —
# это восстановление делает человек, вот этим скриптом. Порядок шагов — тот
# самый, что ведущий проделал руками 13-14.10: убить ntfs-3g → отмонтировать →
# остановить держателей → добить то, что ещё держит старое fuseblk → убедиться
# в пустом каталоге → примонтировать → поднять держателей через compose → сверить
# изнутри, что это снова fuseblk.
#
# По умолчанию — ТОЛЬКО проверки и план, никаких изменений (--dry-run, он же
# режим без аргументов). Действия — только с --apply. Запускать от root.
#
# 🔴 НИКОГДА не запускать ntfsfix или форматирование /mnt/hdd2tb — там единственная
# копия семейного архива 1.4 ТБ (CLAUDE.md, правило №7). «Нечистая» NTFS после
# аварийного `umount -l` — повод звать владельца, а не чинить ФС автоматически.
#
# Usage:
#   sudo bash scripts/storage/hdd_hang_recover.sh            # план, ничего не меняет
#   sudo bash scripts/storage/hdd_hang_recover.sh --dry-run   # то же самое явно
#   sudo bash scripts/storage/hdd_hang_recover.sh --apply     # реальное восстановление
set -euo pipefail

# Раскладка хоста — единая точка правды (scripts/lib/layout.sh, NAS-STO-001).
_nas_lay="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/layout.sh"
[[ -r "$_nas_lay" ]] || _nas_lay=/usr/local/lib/nas_jetson_nano/layout.sh
# shellcheck source=../lib/layout.sh
source "$_nas_lay"

MOUNT="/mnt/hdd2tb"
# Тот же путь, что PAUSE_FILE в scripts/monitoring/nas_jetson_nano-container-watchdog.py —
# не из layout.sh, он там тоже захардкожен.
PAUSE_FILE="/etc/nas-watchdog.pause"
STAT_TIMEOUT=10
DISKSTATS_WINDOW=10

APPLY=0
for arg in "$@"; do
    case "$arg" in
        --apply) APPLY=1 ;;
        --dry-run) APPLY=0 ;;
        -h|--help)
            echo "Usage: $0 [--dry-run|--apply]"
            exit 0
            ;;
        *)
            echo "неизвестный аргумент: $arg (ожидается --apply или --dry-run)" >&2
            exit 2
            ;;
    esac
done

if (( EUID != 0 )); then
    echo "ERROR: запускать от root (sudo) — нужны kill/umount/docker" >&2
    exit 1
fi

LOG_DIR="$NAS_LOG_DIR"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/hdd-recover.log"
# Скрипт запускают руками с консоли — вывод нужен и на экране, и в логе.
exec > >(tee -a "$LOG") 2>&1

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }

# ── read-only диагностика (выполняется и в dry-run, и в --apply) ────────────
diskstats_source() {
    # findmnt на неподключённой точке молча возвращает ненулевой код без вывода
    # в stderr — ловим его через if, а не глушим редиректом.
    if ! SRC=$(findmnt -n -o SOURCE "$MOUNT"); then
        DEV=""
        return
    fi
    DEV=$(basename "$SRC")
}

diskstats_snapshot() { awk -v d="$1" '$3==d{print $4,$6,$8,$10}' /proc/diskstats; }

confirm_hang() {
    log "Шаг 1: проверяю, действительно ли завис $MOUNT"
    if timeout "$STAT_TIMEOUT" stat -f "$MOUNT" >/dev/null 2>&1; then
        log "stat -f ответил за ${STAT_TIMEOUT}с — это НЕ зависание, точка монтирования жива"
        return 1
    fi
    log "stat -f не ответил за ${STAT_TIMEOUT}с — смотрю счётчики диска ${DISKSTATS_WINDOW}с"
    diskstats_source
    if [ -z "$DEV" ]; then
        log "findmnt не нашёл источник для $MOUNT — возможно, уже отмонтирован"
        return 1
    fi
    local before after
    before=$(diskstats_snapshot "$DEV")
    sleep "$DISKSTATS_WINDOW"
    after=$(diskstats_snapshot "$DEV")
    if [ -z "$before" ] || [ -z "$after" ]; then
        log "не нашёл устройство $DEV в /proc/diskstats — не могу подтвердить зависание"
        return 1
    fi
    if [ "$before" = "$after" ]; then
        log "ПОДТВЕРЖДЕНО: stat не отвечает, счётчики $DEV не меняются ${DISKSTATS_WINDOW}с — зависание ntfs-3g"
        return 0
    fi
    log "счётчики $DEV меняются — диск просто медленный, это НЕ зависание (CLAUDE.md: не рвать)"
    return 1
}

holder_bind_mounts() {
    # "Source<TAB>Destination" на строку, по одной на bind-монтирование —
    # источник правды для (а) «держатель ли это» и (б) пути внутри контейнера
    # для проверки fuseblk (пункт ревью: не хардкодить таблицу путей).
    # Пробелы и кириллица в путях переживают TAB-разделение через `read`
    # (пункт ревью), в отличие от word-splitting по пробелу.
    local out rc=0
    out=$(docker inspect "$1" \
        --format '{{range .Mounts}}{{if eq .Type "bind"}}{{.Source}}{{"\t"}}{{.Destination}}{{"\n"}}{{end}}{{end}}') || rc=$?
    if [ "$rc" -ne 0 ]; then
        die "docker inspect $1 вернул код $rc — не могу прочитать монтирования"
    fi
    printf '%s' "$out"
}

holder_destination() {
    # Печатает Destination первого bind-монтирования с Source == $MOUNT или
    # подкаталогом под ним; код возврата 1, если держателем не является.
    local src dest
    while IFS=$'\t' read -r src dest; do
        [ -n "$src" ] || continue
        case "$src" in
            "$MOUNT"|"$MOUNT"/*) printf '%s' "$dest"; return 0 ;;
        esac
    done <<< "$(holder_bind_mounts "$1")"
    return 1
}

find_holders() {
    # Docker недоступен — падаем громко (set -e): считать это "держателей нет"
    # было бы опаснее, чем остановить скрипт.
    local names name rc=0
    names=$(docker ps -a --format '{{.Names}}') || rc=$?
    if [ "$rc" -ne 0 ]; then
        die "docker ps -a вернул код $rc — не могу найти держателей"
    fi
    for name in $names; do
        if holder_destination "$name" >/dev/null; then
            printf '%s\n' "$name"
        fi
    done
}

# Нет держателей в /proc/[pid]/mounts — ОБЫЧНЫЙ исход (grep -l вернёт 1), не
# ошибка; /proc может потерять файл процесса между glob и чтением (TOCTOU) —
# единственное в скрипте намеренное подавление, не трогать без причины.
find_stale_pids() { grep -l "$MOUNT" /proc/[0-9]*/mounts 2>/dev/null | sed -E 's#/proc/([0-9]+)/mounts#\1#' || true; }

# ── шаги восстановления (только --apply) ─────────────────────────────────────
PAUSE_CREATED_BY_US=0
pause_watchdog() {
    log "Шаг 2: пауза сторожа контейнеров"
    if [ -e "$PAUSE_FILE" ]; then
        log "сторож уже на паузе ($PAUSE_FILE существовал) — не трогаю его при выходе"
        return
    fi
    touch "$PAUSE_FILE"
    PAUSE_CREATED_BY_US=1
    log "поставил паузу: $PAUSE_FILE"
}

resume_watchdog() {
    if [ "$PAUSE_CREATED_BY_US" = "1" ] && [ -e "$PAUSE_FILE" ]; then
        log "снимаю паузу сторожа: $PAUSE_FILE"
        rm -f "$PAUSE_FILE"
    fi
}

kill_ntfs3g_and_unmount() {
    # Осиротевший `stat`/`mount.ntfs-3g` может застрять в непрерываемом
    # D-state внутри ядра на мёртвом fuseblk — его не снимет ни SIGTERM, ни
    # SIGKILL, пока не освободится само монтирование. Это ожидаемо: после
    # umount -l он исчезнет сам, дожидаться здесь не нужно.
    log "Шаг 3: завершаю ntfs-3g для $MOUNT, отмонтирую"
    local pids pid
    pids=""
    # pgrep без совпадения — обычный исход (демон уже умер сам), не ошибка.
    if found=$(pgrep -f "ntfs-3g.*${MOUNT}"); then
        pids="$found"
    fi
    if [ -n "$pids" ]; then
        for pid in $pids; do
            log "kill -9 ntfs-3g (pid $pid)"
            if ! kill -9 "$pid"; then
                log "kill -9 $pid не сработал (возможно, процесс уже умер, либо застрял в D-state) — продолжаю"
            fi
        done
        sleep 1
    else
        log "процесс ntfs-3g для $MOUNT не найден (возможно, уже умер сам)"
    fi
    log "umount -l $MOUNT"
    if ! umount -l "$MOUNT"; then
        log "umount -l $MOUNT вернул ошибку — проверю состояние явно на шаге 6"
    fi
}

stop_holders() {
    log "Шаг 4: останавливаю держателей: $1"
    local h rc
    for h in $1; do
        log "docker stop $h"
        rc=0
        docker stop "$h" >/dev/null || rc=$?
        if [ "$rc" -ne 0 ]; then
            die "docker stop $h вернул код $rc"
        fi
    done
}

kill_stale_pids() {
    log "Шаг 5: добиваю процессы, которые ещё держат старое монтирование $MOUNT"
    local pid cmd
    for pid in $1; do
        cmd="(не удалось прочитать cmdline)"
        if read_cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline"); then
            cmd="$read_cmd"
        fi
        case "$cmd" in
            *dockerd*|*containerd*)
                die "процесс $pid ($cmd) держит старое монтирование — это сам Docker, разбираться руками, не убиваю"
                ;;
        esac
        log "kill -9 $pid ($cmd)"
        if ! kill -9 "$pid"; then
            log "kill -9 $pid не сработал (возможно, процесс уже умер) — продолжаю"
        fi
    done
}

check_clear_and_empty() {
    log "Шаг 6: проверяю, что держателей не осталось и $MOUNT пуст"
    local remaining leftover
    remaining=$(find_stale_pids)
    if [ -n "$remaining" ]; then
        die "после остановки держателей всё ещё заняты PID: $remaining — разбираться руками"
    fi
    leftover=$(ls -A "$MOUNT")
    if [ -n "$leftover" ]; then
        die "$MOUNT не пуст после отмонтирования — не продолжаю (похоже на незавершённый umount или оставшийся держатель)"
    fi
    log "держателей не осталось, $MOUNT пуст — можно монтировать"
}

do_mount() {
    log "Шаг 7: mount $MOUNT"
    if ! mount "$MOUNT"; then
        die "mount $MOUNT не прошёл — НЕ запускать ntfsfix/mkfs; 'нечистая' NTFS — повод звать владельца (CLAUDE.md, правило №7)"
    fi
    log "смонтировано: $(findmnt -n -o SOURCE,FSTYPE,OPTIONS "$MOUNT")"
}

start_holder() {
    local name out rc=0 project wdir files svc envf
    name="$1"
    out=$(docker inspect "$name" --format \
        '{{index .Config.Labels "com.docker.compose.project"}}{{"\t"}}{{index .Config.Labels "com.docker.compose.project.working_dir"}}{{"\t"}}{{index .Config.Labels "com.docker.compose.project.config_files"}}{{"\t"}}{{index .Config.Labels "com.docker.compose.service"}}{{"\t"}}{{index .Config.Labels "com.docker.compose.project.environment_file"}}') || rc=$?
    if [ "$rc" -ne 0 ]; then
        die "docker inspect $name вернул код $rc — не могу прочитать метки compose"
    fi
    IFS=$'\t' read -r project wdir files svc envf <<< "$out"
    if [ -z "$envf" ]; then
        envf="$NAS_ENV_FILE"
    fi
    log "пересоздаю $name: -p $project -f $files --env-file $envf (cwd $wdir) --no-deps --force-recreate --pull never $svc"
    ( cd "$wdir" && docker compose -p "$project" -f "$files" --env-file "$envf" \
        up -d --no-deps --force-recreate --pull never "$svc" )
}

start_holders() {
    log "Шаг 8: поднимаю держателей через docker compose"
    local h
    for h in $1; do
        start_holder "$h"
    done
}

verify_fuseblk_inside() {
    local name path fstype
    name="$1"; path="$2"
    fstype=""
    if out=$(docker exec "$name" sh -c "stat -f -c %T '$path'"); then
        fstype="$out"
    fi
    if [ "$fstype" != "fuseblk" ]; then
        log "WARNING: $name:$path — тип ФС '$fstype', ожидался fuseblk — проверь руками"
        return 1
    fi
    log "OK: $name:$path внутри контейнера — fuseblk"
}

verify_holders() {
    local h path
    for h in $1; do
        if path=$(holder_destination "$h"); then
            verify_fuseblk_inside "$h" "$path"
        else
            log "у $h нет bind-монтирования под $MOUNT — проверять нечего"
        fi
    done
}

# ── main ───────────────────────────────────────────────────────────────────

log "=== hdd_hang_recover: старт (apply=$APPLY) ==="

if ! confirm_hang; then
    log "НЕ зависание — делать ничего не нужно, выхожу"
    exit 0
fi

HOLDERS="$(find_holders)"
STALE_PIDS="$(find_stale_pids)"

if [ -z "$HOLDERS" ]; then
    log "держателей $MOUNT среди контейнеров не найдено"
else
    log "держатели $MOUNT: $HOLDERS"
fi
if [ -n "$STALE_PIDS" ]; then
    log "уже сейчас держат старое монтирование (PID): $STALE_PIDS"
fi

if [ "$APPLY" != "1" ]; then
    log "--dry-run (по умолчанию): план восстановления, ничего не меняю"
    log "  2) пауза сторожа: $PAUSE_FILE"
    log "  3) kill -9 mount.ntfs-3g для $MOUNT; umount -l $MOUNT"
    log "  4) docker stop для держателей: ${HOLDERS:-<нет>}"
    log "  5) kill -9 оставшихся PID со старым монтированием (если появятся)"
    log "  6) проверка: держателей нет, $MOUNT пуст"
    log "  7) mount $MOUNT (НЕ ntfsfix/mkfs при неудаче)"
    log "  8) docker compose up -d --no-deps --force-recreate --pull never для держателей"
    log "  9) проверка внутри контейнеров: тип ФС fuseblk"
    log "Повторить с --apply, чтобы выполнить это по-настоящему."
    exit 0
fi

trap resume_watchdog EXIT
pause_watchdog
kill_ntfs3g_and_unmount
if [ -n "$HOLDERS" ]; then
    stop_holders "$HOLDERS"
fi
STALE_PIDS="$(find_stale_pids)"
if [ -n "$STALE_PIDS" ]; then
    kill_stale_pids "$STALE_PIDS"
fi
check_clear_and_empty
do_mount
if [ -n "$HOLDERS" ]; then
    start_holders "$HOLDERS"
    sleep 3
    verify_holders "$HOLDERS"
fi

log "Шаг 9: восстановление завершено. Держатели: ${HOLDERS:-<нет>}."
log "=== hdd_hang_recover: конец ==="
