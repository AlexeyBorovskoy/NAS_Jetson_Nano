#!/usr/bin/env python3
"""Проверка файлов .env на значения, которые уронят `source` под `set -euo pipefail`.

Почему отдельный скрипт, а не одна строка на bash: первая версия этой проверки
делала `( set -euo pipefail; . file )` и **пропустила** файл, в котором лежала
ровно та строка, что однажды сломала бэкапы на 16 дней. Поведение `set -e` при
`source` зависит от контекста вызова, и ворота, построенные на нём, дают ложный
пропуск — то есть хуже, чем их отсутствие.

Здесь семантика разбирается явно и одинаково везде.

Ловит:
    KEY=значение с пробелом      → bash выполнит `с` как команду, exit 127
    KEY=знач"ение                → незакрытая кавычка

Не считает ошибкой:
    KEY="значение с пробелом"    KEY='значение'    KEY=значение   # комментарий
    KEY=                         # пустое значение

Usage:  python3 check_env_syntax.py config/.env config/.env.example
Exit:   0 — чисто, 1 — найдены проблемы, 2 — файл не открылся.
"""
import io
import re
import sys

# Консоль Windows работает в cp1251, и печать кириллицы — или даже знака '✗' —
# роняет скрипт с UnicodeEncodeError. Это записанные грабли проекта, и первая
# версия этого файла в них угодила. `sys.stdout.reconfigure` появился в 3.7,
# а на Jetson 3.6 — поэтому оборачиваем буфер вручную.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

ASSIGN = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def strip_comment(value):
    """Убрать хвостовой комментарий, не трогая '#' внутри кавычек."""
    out = []
    quote = None
    for i, ch in enumerate(value):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or value[i - 1].isspace()):
            break
        out.append(ch)
    return "".join(out).rstrip(), quote


def check(path):
    problems = []
    try:
        with io.open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print("НЕ ОТКРЫЛСЯ %s: %s" % (path, exc))
        return None

    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = ASSIGN.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)

        cleaned, unclosed = strip_comment(value)
        if unclosed:
            problems.append((n, key, "незакрытая кавычка %s" % unclosed))
            continue
        if not cleaned:
            continue

        quoted = (len(cleaned) >= 2 and cleaned[0] == cleaned[-1]
                  and cleaned[0] in ('"', "'"))
        if not quoted and re.search(r"\s", cleaned):
            problems.append((n, key, "значение с пробелом без кавычек: %s" % cleaned[:60]))

    return problems


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2

    failed = False
    for path in argv[1:]:
        problems = check(path)
        if problems is None:
            return 2
        if problems:
            failed = True
            print("✗ %s — %d проблем(ы):" % (path, len(problems)))
            for n, key, why in problems:
                print("    строка %d: %s — %s" % (n, key, why))
                print("      исправление: %s=\"...\"" % key)
        else:
            print("✓ %s — чисто" % path)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
