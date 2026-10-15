"""Порция журнала systemd по курсору (OBS-1, задача 5, спецификация §4.1, цикл journal).

`journal_since` зовёт `journalctl` через параметр `run` (сигнатура как
`subprocess.run`) — ни один настоящий процесс не запускается внутри модуля,
подмена целиком в руках вызывающей стороны (тесты, сборщик).

Курсор — непрозрачная строка из `journalctl --show-cursor`; хранится и
передаётся вызывающей стороной (каталог `catalog.db`), сюда приходит и уходит
как есть, без разбора содержимого.

Хост — systemd 237 (CLAUDE.md, факты 13.10): `--after-cursor` и `--show-cursor`
есть, `--cursor-file` НЕТ — поэтому курсор читается из последней строки вывода,
а не из отдельного файла.

Python 3.6: только стандартная библиотека, без f-строк с `=`, без
`dataclasses`, без `:=`.
"""
import subprocess

#: Префикс строки курсора в выводе `journalctl --show-cursor` (последняя строка).
_CURSOR_PREFIX = "-- cursor: "

#: Окно первого запроса, когда курсора ещё нет (нет смысла тянуть весь журнал).
_INITIAL_WINDOW = "--since=-5min"


def _journal_command(cursor):
    """Команда `journalctl` для одной порции: с курсором или с окном `-5min`."""
    cmd = ["journalctl", "--no-pager", "-o", "short-iso-precise", "--show-cursor"]
    if cursor:
        cmd.append("--after-cursor=" + cursor)
    else:
        cmd.append(_INITIAL_WINDOW)
    return cmd


def _split_cursor(stdout, prev_cursor):
    """(lines, new_cursor) — отделяет строку курсора от содержимого журнала.

    Если в выводе курсора не нашлось (пустой ответ, ошибка `journalctl`) —
    курсор не продвигается, а строки отдаются как есть.
    """
    lines = stdout.splitlines()
    if lines and lines[-1].startswith(_CURSOR_PREFIX):
        new_cursor = lines[-1][len(_CURSOR_PREFIX):].strip()
        return lines[:-1], new_cursor
    return lines, prev_cursor


def journal_since(cursor, run=subprocess.run):
    """(lines, new_cursor) — новые строки журнала после `cursor`.

    Без курсора (`None`/пустая строка) берётся окно последних 5 минут
    (`--since=-5min`) — так начинается первая порция после старта сборщика.
    С курсором — только то, что появилось после него (`--after-cursor`).
    `run` подменяется в тестах; сигнатура и поля ответа — как у
    `subprocess.run`/`subprocess.CompletedProcess` (`stdout`, `returncode`).
    """
    cmd = _journal_command(cursor)
    completed = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     universal_newlines=True)
    return _split_cursor(completed.stdout, cursor)
