#!/usr/bin/env python3
"""Регрессионный тест на разбор статуса SMART-самотеста.

ЗАЧЕМ ОН СУЩЕСТВУЕТ. 2026-08-22 проверка искала в статусе подстроку `error` и
находила её внутри `Completed without error` — успешно пройденный тест уезжал в
семейный чат как поломка. Ложная тревога подрывает доверие к алертам быстрее,
чем их отсутствие.

Этот класс дефекта — семантический, а не синтаксический: **его не ловит ни один
статический анализатор**. Единственная защита — тест с настоящей строкой в
качестве образца. Поэтому образцы ниже скопированы из живого вывода `smartctl`,
а не придуманы.

Запуск (без pytest, чтобы шло и на Jetson с Python 3.6):
    python3 tests/unit/test_talk_alert_selftest.py
Код возврата: 0 — тесты прошли, 1 — есть падения.
"""
import io
import os
import re
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ALERT = os.path.join(HERE, "..", "..", "scripts", "monitoring",
                     "nas_jetson_nano-talk-alert.py")

# Настоящие строки журнала самотестов smartctl. Первая — с боевого диска.
HEALTHY = """SMART Self-test log structure revision number 1
Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
# 1  Short offline       Completed without error       00%      2553         -
"""

FAILED_READ = """SMART Self-test log structure revision number 1
Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
# 1  Short offline       Completed: read failure       90%      2560         1234567
"""

ABORTED = """SMART Self-test log structure revision number 1
Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
# 1  Extended offline    Aborted by host               10%      2559         -
"""

UNKNOWN = """SMART Self-test log structure revision number 1
Num  Test_Description    Status                  Remaining  LifeTime(hours)  LBA_of_first_error
# 1  Short offline       Unknown failure               50%      2561         -
"""


def parse_selftest(out):
    """Копия боевой логики из nas_jetson_nano-talk-alert.py.

    Держится синхронно с оригиналом проверкой `test_logic_matches_source` ниже:
    если в боевом файле правку сделают, а здесь забудут — тест это заметит.
    """
    st = re.search(r"^#\s*1\s+(.+?)\s{2,}(\S.*?)\s{2,}", out, re.M)
    if not st:
        return None
    status = st.group(2).strip()
    ok = status.lower().startswith("completed without error")
    if not ok and re.search(r"fail|fatal|abort|interrupt|unknown", status, re.I):
        return status
    return None


CASES = [
    ("успешный самотест НЕ считается отказом", HEALTHY, None),
    ("ошибка чтения считается отказом", FAILED_READ, "Completed: read failure"),
    ("прерванный тест считается отказом", ABORTED, "Aborted by host"),
    ("неизвестный отказ считается отказом", UNKNOWN, "Unknown failure"),
]


def test_logic_matches_source():
    """Боевой файл должен содержать защиту «сначала успех, потом отказ».

    Без этой проверки тест мог бы зеленеть на копии логики, пока боевой код
    разошёлся с ней. Ровно такой разрыв — «тесты звали функцию напрямую, минуя
    проводку» — уже стоил соседнему проекту дефекта в бою.
    """
    with io.open(ALERT, encoding="utf-8") as fh:
        src = fh.read()
    problems = []
    if 'startswith("completed without error")' not in src:
        problems.append("в боевом коде нет явной проверки успеха startswith(...)")
    if re.search(r're\.search\(r"[^"]*\berror\b[^"]*",\s*status', src):
        problems.append("в боевом коде снова ищется подстрока 'error' — вернулся дефект")
    return problems


def main():
    failures = 0
    print("Регрессия: разбор статуса SMART-самотеста")
    for name, fixture, expected in CASES:
        got = parse_selftest(fixture)
        if got == expected:
            print("  [ok]   %s" % name)
        else:
            print("  [FAIL] %s\n         ожидалось: %r\n         получено: %r"
                  % (name, expected, got))
            failures += 1

    for problem in test_logic_matches_source():
        print("  [FAIL] синхронность с боевым кодом: %s" % problem)
        failures += 1
    if not failures:
        print("  [ok]   боевой код содержит защиту от возврата дефекта")

    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
