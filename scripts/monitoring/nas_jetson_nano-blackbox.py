#!/usr/bin/env python3
"""Точка входа сборщика «чёрного ящика» (OBS-1, задача 7).

Тонкая обёртка: найти пакет `blackbox` (рядом с репозиторием —
`services/blackbox`, либо установленный в `/usr/local/lib/nas_jetson_nano`),
положить его на `sys.path` и вызвать `blackbox.collector.main()`. Вся логика
живёт в пакете и проверяется тестами без этого файла.

Python 3.6 (хост Jetson), только стандартная библиотека.
"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
#: Каталог на sys.path: в репозитории — `services/blackbox`, на устройстве —
#: установленная копия (внутри неё лежит пакет `blackbox/`).
CANDIDATES = (
    os.path.join(HERE, "..", "..", "services", "blackbox"),
    "/usr/local/lib/nas_jetson_nano",
    "/usr/local/lib/nas_jetson_nano/blackbox",
)


def find_package_dir(candidates=CANDIDATES):
    """Первый каталог, внутри которого есть `blackbox/__init__.py`, или `None`."""
    for candidate in candidates:
        path = os.path.abspath(candidate)
        if os.path.isfile(os.path.join(path, "blackbox", "__init__.py")):
            return path
        # Установленная копия может быть самим пакетом: ../blackbox на sys.path.
        if (os.path.basename(path) == "blackbox"
                and os.path.isfile(os.path.join(path, "__init__.py"))):
            return os.path.dirname(path)
    return None


def main():
    """Находит пакет и запускает сборщик; 2 — пакет не найден."""
    package_dir = find_package_dir()
    if package_dir is None:
        sys.stderr.write("blackbox: пакет blackbox не найден\n")
        return 2
    if package_dir not in sys.path:
        sys.path.insert(0, package_dir)
    from blackbox.collector import main as collector_main
    return collector_main()


if __name__ == "__main__":
    sys.exit(main())
