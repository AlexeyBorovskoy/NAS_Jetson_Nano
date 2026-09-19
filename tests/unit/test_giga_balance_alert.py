#!/usr/bin/env python3
"""E2 (план 2026-09): алерт о заканчивающейся квоте GigaChat.

ЗАЧЕМ. Квоты freemium у GigaChat раздельные по моделям: Max — отдельные ≈25 млн
токенов, а не «общее ведро» (так было ошибочно записано 2026-09-19, см. план §1.1).
Ежедневная проверка баланса с 2026-09-08 только печатала ответ в журнал —
кончившуюся квоту владелец узнал бы по замолчавшему `@бобик`.

Проверка читает файл, который пишет ежедневный опрос баланса, а не ходит в сеть:
алерты крутятся каждые 15 мин, дёргать GigaChat 96 раз в сутки незачем.
Устаревший файл — тоже тревога: тишина ≠ успех.

Боевой модуль импортируется целиком — никаких копий логики.
Запуск (без pytest, идёт и на Jetson с Python 3.6):
    python3 tests/unit/test_giga_balance_alert.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import time

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ALERT = os.path.join(HERE, "..", "..", "scripts", "monitoring",
                     "nas_jetson_nano-talk-alert.py")

# Живой ответ шлюза, снят с Jetson 2026-09-19 06:57 UTC.
LIVE = {"provider": "gigachat", "base": "https://api.giga.chat/v1",
        "balance": {"balance": [
            {"usage": "GigaChat", "value": 249995568},
            {"usage": "GigaChat-Ultra", "value": 50000000},
            {"usage": "GigaChat-Pro", "value": 40000000},
            {"usage": "GigaChat-Max", "value": 24991737}]}}


def load_module():
    spec = importlib.util.spec_from_file_location("talk_alert", ALERT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, data, age_h=0):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data))
    t = time.time() - age_h * 3600
    os.utime(path, (t, t))


def low_max():
    d = json.loads(json.dumps(LIVE))
    d["balance"]["balance"][3]["value"] = 900000
    return d


def main():
    mod = load_module()
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "balance.json")
    failures = 0

    def case(name, cond, got):
        nonlocal failures
        if cond:
            print("  [ok]   %s" % name)
        else:
            print("  [FAIL] %s\n         получено: %r" % (name, got))
            failures += 1

    print("E2: алерт о квоте GigaChat")
    write(path, LIVE)
    key, msg = mod.check_giga_balance(path=path, warn_tokens=2000000)
    case("живой баланс — тишина", key == "giga_balance" and msg is None, msg)

    write(path, low_max())
    key, msg = mod.check_giga_balance(path=path, warn_tokens=2000000)
    case("Max ниже порога — алерт называет модель и остаток",
         msg is not None and "GigaChat-Max" in msg and "900" in msg, msg)
    case("…и не упоминает модели выше порога",
         msg is not None and "GigaChat-Pro" not in msg, msg)

    write(path, LIVE, age_h=51)
    key, msg = mod.check_giga_balance(path=path, warn_tokens=2000000)
    case("файл старше 50 ч — алерт о сломанной проверке",
         msg is not None and "не обновлялся" in msg, msg)

    key, msg = mod.check_giga_balance(path=os.path.join(tmp, "нет.json"),
                                      warn_tokens=2000000)
    case("файла нет — алерт", msg is not None, msg)

    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write("{битый")
    key, msg = mod.check_giga_balance(path=path, warn_tokens=2000000)
    case("битый файл — алерт, а не падение всего скрипта", msg is not None, msg)

    write(path, {"provider": "gigachat", "balance": {"balance": []}})
    key, msg = mod.check_giga_balance(path=path, warn_tokens=2000000)
    case("пустой список моделей — алерт", msg is not None, msg)

    case("проверка включена в CHECKS",
         mod.check_giga_balance in mod.CHECKS, [c.__name__ for c in mod.CHECKS])

    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
