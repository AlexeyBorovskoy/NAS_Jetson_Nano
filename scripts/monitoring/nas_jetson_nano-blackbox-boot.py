#!/usr/bin/env python3
"""Точка входа снимка загрузки OBS-1 (`nas_jetson_nano-blackbox-boot.service`).

Тонкая обёртка (план, «Структура файлов»): найти пакет `blackbox` рядом с
репозиторием (`NAS_PROJECT_DIR` из `/etc/nas-layout.env`), в `services/blackbox`
или в установленном каталоге — и вызвать `blackbox.bootsnap.main()`. Вся
логика — в пакете; здесь нет ни команд, ни путей `boots/`.
"""
import os
import sys

#: Куда ставится пакет на хосте (план задачи 8/13).
INSTALLED_LIB = "/usr/local/lib/nas_jetson_nano/blackbox"


def _candidate_parents():
    """Каталоги, которые можно положить в `sys.path`, чтобы импортировать `blackbox`."""
    here = os.path.dirname(os.path.abspath(__file__))
    parents = [os.path.normpath(os.path.join(here, "..", "..",
                                             "services", "blackbox"))]
    project = os.environ.get("NAS_PROJECT_DIR")
    if project:
        parents.append(os.path.join(project, "services", "blackbox"))
    parents.append(INSTALLED_LIB)
    parents.append(os.path.dirname(INSTALLED_LIB))
    return parents


def _load_package():
    """True — `blackbox` импортируется (сначала пробуем уже настроенный путь)."""
    try:
        import blackbox  # noqa: F401
    except ImportError:
        pass
    else:
        return True
    for parent in _candidate_parents():
        if os.path.isfile(os.path.join(parent, "blackbox", "__init__.py")):
            sys.path.insert(0, parent)
            return True
    return False


def main():
    """Находит пакет и передаёт управление снимку; код возврата — код пакета."""
    if not _load_package():
        sys.stderr.write("boot: пакет blackbox не найден\n")
        return 1
    from blackbox.bootsnap import main as boot_main
    return boot_main()


if __name__ == "__main__":
    sys.exit(main())
