#!/usr/bin/env bash
# Локальные ворота качества — запускать ДО выката на живую систему.
# Local quality gate — run BEFORE deploying to the live system.
#
# Каждая проверка здесь стоит за конкретным дефектом, который уже доходил до боевой
# машины. Это не список модных линтеров, а список пойманных ошибок:
#
#   3.6  → subprocess.run(capture_output=True): параметр из Python 3.7, на Jetson 3.6.
#          Упало только в бою (2026-08-22).
#   env  → незакавыченное значение с пробелом в .env: source под `set -euo pipefail`
#          падал с кодом 127 и МОЛЧА ломал бэкапы 16 дней, а systemd рапортовал success.
#   sh   → `sudo -S` вместе с heredoc: пароль уехал в файл вместо содержимого.
#   sec  → секреты в коммите.
#   img  → ${IMMICH_VERSION:-release}: `compose pull` молча поднял бы Immich через
#          мажорную версию, а он мигрирует схему БД при старте (D6/DEP-2, 2026-09-26).
#
# Правило: ворота либо проходят целиком, либо выкат не делается.
#
# Usage:  bash scripts/quality/preflight.sh [--quick] [--images-only]
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 2

FAIL=0
WARN=0
QUICK=0
# --images-only — прогнать ТОЛЬКО проверку тегов образов (раздел 7б) и выйти.
# Нужен тесту tests/unit/test_immich_pinned_version.py: тот подкладывает дерево-фикстуру
# и проверяет, что ворота различают плавающий тег Immich (bad) и :latest у прочих (warn).
IMAGES_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=1 ;;
        --images-only) IMAGES_ONLY=1 ;;
    esac
done

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; WARN=$((WARN+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }

# ── Теги образов (раздел 7б) ───────────────────────────────────────────────────
# Вынесено в функцию, потому что эту проверку гоняет ещё и тест
# tests/unit/test_immich_pinned_version.py — на дереве-фикстуре (режим --images-only).
# Пути берутся от текущего каталога, а скрипт сам делает `cd` в корень дерева,
# поэтому фикстуре достаточно положить копию скрипта в <tmp>/scripts/quality/.
#
# bad/ok/warn — общие функции ворот: FAIL и WARN считаются по всему прогону.
check_image_tags() {
    local f line lineno
    local immich_seen=0 immich_bad=0 other_latest=0
    for f in docker/compose/*.yml; do
        [ -f "$f" ] || continue
        lineno=0
        while IFS= read -r line; do
            lineno=$((lineno + 1))
            # Смотрим только строки образа, а не любое упоминание слова в комментарии.
            case "$line" in
                *[Ii]mage:*) ;;
                *) continue ;;
            esac
            case "$line" in
                *[Ii][Mm][Mm][Ii][Cc][Hh]*)
                    immich_seen=$((immich_seen + 1))
                    # `:-release}` — дефолт по умолчанию; `:release` — голый плавающий тег;
                    # `:latest` — то же самое, но названное честно. Любой из них означает,
                    # что pull уедет вперёд без нашего решения.
                    case "$line" in
                        *:-release*|*:release*|*:latest*)
                            bad "плавающий тег у образа Immich: $f:$lineno"
                            printf '      %s\n' "$(printf '%s' "$line" | sed 's/^[[:space:]]*//')"
                            immich_bad=$((immich_bad + 1))
                            ;;
                    esac
                    ;;
                *:latest*)
                    warn "не-Immich образ на :latest: $f:$lineno (DEP-2, ворота не блокирует)"
                    other_latest=$((other_latest + 1))
                    ;;
            esac
        done < "$f"
    done
    if [ "$immich_seen" -eq 0 ]; then
        warn "образов Immich в docker/compose/*.yml не найдено — проверять нечего"
    elif [ "$immich_bad" -eq 0 ]; then
        ok "Immich закреплён по версии: образов Immich — $immich_seen, плавающих тегов нет"
    fi
    [ "$other_latest" -eq 0 ] || \
        warn "прочих образов на :latest — $other_latest (netdata/portainer/samba: задача DEP-2)"
}

# Режим одной проверки: тесту нужен результат только 7б, без shellcheck, vermin
# и прогона всех тестов (иначе тест, запускающий ворота, запустил бы и сам себя).
if [ "$IMAGES_ONLY" = "1" ]; then
    head_ "7б. Теги образов Immich / Immich image tags"
    check_image_tags
    printf '\n'
    if [ "$FAIL" -eq 0 ]; then
        printf '\033[32m✓ теги образов Immich закреплены\033[0m\n'
        exit 0
    fi
    printf '\033[31m✗ плавающих тегов у Immich: %d\033[0m\n' "$FAIL"
    exit 1
fi

# ── 1. Синтаксис shell ─────────────────────────────────────────────────────────
head_ "1. Синтаксис bash / bash syntax"
sh_files=$(find scripts services tests systemd -name '*.sh' -type f 2>/dev/null)
n=0; bad_n=0
for f in $sh_files; do
    n=$((n+1))
    bash -n "$f" 2>/dev/null || { bad "синтаксис: $f"; bad_n=$((bad_n+1)); }
done
[ "$bad_n" -eq 0 ] && ok "проверено файлов: $n"

# ── 2. ShellCheck ──────────────────────────────────────────────────────────────
head_ "2. ShellCheck"
if have shellcheck; then
    # Ошибки блокируют, предупреждения — нет: иначе ворота никогда не пройдут
    # на легаси-скриптах, и их начнут обходить.
    if echo "$sh_files" | xargs -r shellcheck -S error >/dev/null 2>&1; then
        ok "ошибок уровня error нет"
    else
        bad "shellcheck нашёл ошибки — запусти: shellcheck -S error <файл>"
    fi
else
    warn "shellcheck не установлен (в CI он есть; локально: choco/apt install shellcheck)"
fi

# ── 3. Синтаксис Python ────────────────────────────────────────────────────────
head_ "3. Синтаксис Python"
py_files=$(find scripts services -name '*.py' -type f 2>/dev/null)
if have python || have python3; then
    PY=$(command -v python3 || command -v python)
    n=0; bad_n=0
    for f in $py_files; do
        n=$((n+1))
        "$PY" -c "import ast,io,sys; ast.parse(io.open(sys.argv[1],encoding='utf-8').read())" "$f" 2>/dev/null \
            || { bad "синтаксис: $f"; bad_n=$((bad_n+1)); }
    done
    [ "$bad_n" -eq 0 ] && ok "проверено файлов: $n"
else
    bad "python не найден"
fi

# ── 4. 🔴 Совместимость с Python целевой машины ────────────────────────────────
head_ "4. Python 3.6 на Jetson — совместимость / target compatibility"
if have vermin; then
    # ВАЖНО: суффикс '-' обязателен. `--target=3.6` означает «ровно 3.6»,
    # а нужно «3.6 или ниже». Короткая форма -t= в PowerShell не парсится.
    #
    # Проверяются ТОЛЬКО scripts/ — они выполняются на самом Jetson.
    # services/ живут в контейнерах со своим Python (3.9+) и под это правило не подпадают.
    if vermin --target=3.6- --violations --no-tips scripts/ >/tmp/vermin.$$ 2>&1; then
        ok "scripts/ укладываются в Python 3.6"
    else
        bad "scripts/ требуют Python новее 3.6 — на Jetson упадёт:"
        grep -E "^!2, 3\.[7-9]|requires !2, 3\.[7-9]|Minimum required" /tmp/vermin.$$ | head -8 | sed 's/^/      /'
    fi
    rm -f /tmp/vermin.$$
else
    warn "vermin не установлен — это ГЛАВНАЯ проверка проекта: pip install vermin"
fi

# ── 5. 🔴 Синтаксис .env ───────────────────────────────────────────────────────
head_ "5. Файлы .env — значения с пробелами / dotenv syntax"
#
# 🔴 Первая версия этой проверки делала `( set -euo pipefail; . "$envf" )` — и
# ПРОПУСТИЛА файл, в котором лежала ровно та строка, что сломала бэкапы на 16 дней.
# Поведение `set -e` при `source` зависит от контекста вызова: внутри условия `if`
# bash его отключает. Ровно на этих же граблях у соседнего проекта упавший линтер
# рапортовал успех и код уехал в бой.
#
# Вывод, ставший правилом: **ворота не должны зависеть от семантики shell.**
# Разбор вынесен в отдельный скрипт с явным кодом возврата.
env_checked=0
env_files=""
for envf in config/.env config/.env.example; do
    [ -f "$envf" ] && env_files="$env_files $envf" && env_checked=$((env_checked+1))
done
if [ "$env_checked" -eq 0 ]; then
    warn "файлов .env не найдено (в git их и не должно быть, кроме .example)"
elif have python || have python3; then
    PY=$(command -v python3 || command -v python)
    # Код возврата берём явно, а не через `if` — см. комментарий выше.
    # shellcheck disable=SC2086
    env_out=$("$PY" scripts/quality/check_env_syntax.py $env_files 2>&1)
    env_rc=$?
    if [ "$env_rc" -eq 0 ]; then
        ok "проверено файлов: $env_checked — значения закавычены корректно"
    else
        bad "в .env есть значения, на которых упадёт 'source' под 'set -euo pipefail':"
        printf '%s\n' "$env_out" | sed 's/^/      /'
    fi
else
    bad "python не найден — проверку .env выполнить нечем"
fi

# ── 5б. Кодировка .ps1 ─────────────────────────────────────────────────────────
head_ "5б. Кодировка PowerShell-скриптов / .ps1 encoding"
#
# 2026-08-23: скрипт туннеля был сохранён в UTF-8 без BOM. PowerShell 5.1 прочёл
# его как cp1251, кириллица развалилась, и одна искажённая последовательность
# порвала строковый литерал — скрипт не парсился целиком. Симптом был нулевой:
# запущенный скрыто, он просто ничего не делал.
if have python || have python3; then
    PY=$(command -v python3 || command -v python)
    ps_out=$("$PY" scripts/quality/check_ps1_bom.py scripts 2>&1)
    ps_rc=$?
    if [ "$ps_rc" -eq 0 ]; then
        ok "$(printf '%s' "$ps_out" | tail -1 | sed 's/^✓ //')"
    else
        bad "есть .ps1 с кириллицей без BOM — PowerShell 5.1 их не разберёт:"
        printf '%s\n' "$ps_out" | sed 's/^/      /'
    fi
else
    warn "python не найден — проверку кодировки .ps1 выполнить нечем"
fi

# ── 6. Секреты ─────────────────────────────────────────────────────────────────
head_ "6. Секреты / secrets"
if [ -x scripts/security/check_no_secrets.sh ] || [ -f scripts/security/check_no_secrets.sh ]; then
    if bash scripts/security/check_no_secrets.sh >/dev/null 2>&1; then
        ok "секретов вне разрешённых файлов нет"
    else
        bad "check_no_secrets.sh нашёл проблему — запусти его отдельно"
    fi
else
    bad "scripts/security/check_no_secrets.sh отсутствует"
fi

# ── 7. docker-compose ──────────────────────────────────────────────────────────
head_ "7. Файлы docker-compose"
if [ "$QUICK" = "1" ]; then
    warn "пропущено (--quick)"
elif have docker && docker info >/dev/null 2>&1; then
    n=0; bad_n=0
    for f in docker/compose/*.yml; do
        [ -f "$f" ] || continue
        n=$((n+1))
        docker compose -f "$f" --env-file config/.env.example config --quiet >/dev/null 2>&1 \
            || { bad "compose не валиден: $f"; bad_n=$((bad_n+1)); }
    done
    [ "$bad_n" -eq 0 ] && ok "проверено файлов: $n"
else
    warn "docker недоступен — проверка compose пропущена (в CI она есть)"
fi

# ── 7б. 🔴 Теги образов Immich ─────────────────────────────────────────────────
head_ "7б. Теги образов Immich / Immich image tags"
#
# История дефекта (2026-09-26, задача D6/DEP-2): устройство работало на Immich 2.7.5,
# а образ брался по плавающему тегу — ${IMMICH_VERSION:-release}. Обычный
# `docker compose pull` поднял бы мажорную версию МОЛЧА, а Immich мигрирует схему БД
# при старте: откатить образ, не откатив дамп БД, нельзя. Версия закреплена на v2.7.5.
#
# Прочие образы на :latest (netdata, portainer, samba) пока НЕ блокируют ворота —
# это отдельная задача DEP-2. Предупреждение видно, но ворота не краснеют на том,
# что ещё не сделано: покрасневшие ворота начинают обходить.
check_image_tags

# ── 8. Регрессионные тесты ─────────────────────────────────────────────────────
head_ "8. Регрессионные тесты / regression tests"
#
# Здесь живут проверки СЕМАНТИЧЕСКИХ дефектов — тех, которые не ловит ни один
# статический анализатор. Каждый тест обязан соответствовать реальному дефекту,
# уже доходившему до боевой машины: тест без своей истории — это балласт.
if [ -d tests/unit ] && { have python || have python3; }; then
    PY=$(command -v python3 || command -v python)
    n=0; bad_n=0
    for t in tests/unit/test_*.py; do
        [ -f "$t" ] || continue
        n=$((n+1))
        out=$("$PY" "$t" 2>&1); rc=$?
        if [ "$rc" -ne 0 ]; then
            bad "$t"
            printf '%s\n' "$out" | grep -E '\[FAIL\]|падений' | head -6 | sed 's/^/      /'
            bad_n=$((bad_n+1))
        fi
    done
    if [ "$n" -eq 0 ]; then
        warn "тестов в tests/unit не найдено"
    elif [ "$bad_n" -eq 0 ]; then
        ok "пройдено тестов: $n"
    fi
else
    warn "tests/unit отсутствует или нет python"
fi

# ── 9. Тесты сервисов (pytest) ─────────────────────────────────────────────────
head_ "9. Тесты сервисов / service tests (pytest)"
#
# История дефекта: 2026-09-19 коммит d52c11b сломал КАЖДЫЙ чат GigaChat (HTTP 500),
# а ворота были зелёными — раздел 8 гоняет только tests/unit, тесты шлюза сюда не
# попадали. Аудит NAS-REG-001 / NAS-QA-001. Теперь провал любого теста шлюза — провал ворот.
# Каталоги данных уводим во временный, чтобы тесты не писали в /data (на Windows — корень диска).
# Каждый каталог — отдельным запуском: оба сервиса называют свой пакет `app`.
PY=$(command -v python3 || command -v python)
if [ -n "$PY" ] && "$PY" -c "import pytest, fastapi, httpx, pydantic_settings" >/dev/null 2>&1; then
    for SVC_TESTS in tests/llm_gateway tests/nas_api tests/watchdog tests/backup_api tests/stt; do
        [ -d "$SVC_TESTS" ] || continue
        tmpd=$(mktemp -d)
        out=$(IMAGE_OUTPUT_ROOT="$tmpd/images" LLM_USAGE_FILE="$tmpd/usage.json" \
              "$PY" -m pytest -q -p no:cacheprovider "$SVC_TESTS" 2>&1); rc=$?
        rm -rf "$tmpd"
        summary=$(printf '%s\n' "$out" | tail -1)
        if [ "$rc" -eq 0 ]; then
            ok "$SVC_TESTS: $summary"
        else
            bad "$SVC_TESTS: $summary"
            printf '%s\n' "$out" | grep -E '^FAILED|^ERROR' | head -8 | sed 's/^/      /'
        fi
    done
else
    warn "тесты сервисов не запущены: нет pytest/fastapi/httpx/pydantic-settings"
fi

# ── Итог ───────────────────────────────────────────────────────────────────────
printf '\n'
if [ "$FAIL" -eq 0 ]; then
    printf '\033[32m✓ ВОРОТА ПРОЙДЕНЫ\033[0m  (предупреждений: %d)\n' "$WARN"
    printf 'Выкат разрешён. / Gate passed, deployment allowed.\n'
    exit 0
else
    printf '\033[31m✗ ВОРОТА НЕ ПРОЙДЕНЫ: %d ошибок\033[0m (предупреждений: %d)\n' "$FAIL" "$WARN"
    printf 'Выкат НЕ делается, пока не исправлено. / Do NOT deploy.\n'
    exit 1
fi
