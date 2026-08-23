#!/usr/bin/env python3
"""Проверка: .ps1 с кириллицей обязан быть сохранён в UTF-8 С BOM.

ЗАЧЕМ ОН СУЩЕСТВУЕТ. 2026-08-23 скрипт туннеля был сохранён в UTF-8 без BOM.
Windows PowerShell 5.1 читает такой файл как ANSI (cp1251), кириллица в
комментариях разваливается, и одна искажённая последовательность порвала
строковый литерал — скрипт перестал парситься ЦЕЛИКОМ:

    В строке отсутствует завершающий символ: "
    Отсутствует закрывающий знак "}" в блоке операторов

Симптом при этом был максимально неинформативный: запущенный скрыто скрипт
просто ничего не делал. Ошибку видно, только если запустить его в открытую.

Правило: файл `.ps1`, содержащий не-ASCII, обязан начинаться с EF BB BF.
Чистый ASCII BOM не требует.

Usage:  python3 check_ps1_bom.py <файлы или каталоги>
Exit:   0 — чисто, 1 — найдены проблемы.
"""
import io
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

BOM = b"\xef\xbb\xbf"


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in names:
                    if n.lower().endswith(".ps1"):
                        files.append(os.path.join(root, n))
        elif p.lower().endswith(".ps1"):
            files.append(p)
    return sorted(files)


def check(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    has_bom = raw.startswith(BOM)
    body = raw[len(BOM):] if has_bom else raw
    try:
        body.decode("ascii")
        non_ascii = False
    except UnicodeDecodeError:
        non_ascii = True

    if non_ascii and not has_bom:
        return "содержит не-ASCII, но сохранён БЕЗ BOM — PowerShell 5.1 прочтёт как cp1251"
    return None


def main(argv):
    targets = argv[1:] or ["scripts"]
    files = collect(targets)
    if not files:
        print("файлов .ps1 не найдено")
        return 0

    failed = 0
    for f in files:
        problem = check(f)
        if problem:
            print("✗ %s" % f)
            print("    %s" % problem)
            print("    исправление: пересохранить в UTF-8 с BOM (encoding='utf-8-sig')")
            failed += 1

    if not failed:
        print("✓ проверено файлов: %d — кодировка корректна" % len(files))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
