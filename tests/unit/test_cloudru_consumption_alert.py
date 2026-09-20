#!/usr/bin/env python3
"""E5 (план 2026-09): алерт расходов Cloud.ru.

ЗАЧЕМ. Бесплатный тариф Cloud.ru кончается молча — счёт обнаруживается
постфактум. Проверка читает снимок, который пишет отдельный сборщик
(scripts/sber/check_cloudru_consumption.py), а не ходит в сеть сама — родня
уже принятой схеме E2 (баланс GigaChat).

Два независимых пути тревоги (задача E5, требование 2):
  а) любой ненулевой денежный расход — тревога БЕЗУСЛОВНО, для этого проекта
     это уже событие, сопоставление категорий тут ни при чём;
  б) приближение к границе бесплатного тарифа — порог в конфигурации.
Устаревший или разбитый снимок — тоже тревога: тишина ≠ успех (родня уже
записанному в CLAUDE.md правилу).

Боевой модуль импортируется целиком — никаких копий логики.
Запуск (без pytest, идёт и на Jetson с Python 3.6):
    python3 tests/unit/test_cloudru_consumption_alert.py
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


def load_module():
    spec = importlib.util.spec_from_file_location("talk_alert", ALERT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, data, age_h=0):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data))
    t = time.time() - age_h * 3600
    os.utime(path, (t, t))


# Реальность боевого аккаунта (E5, требование 4): GigaChat-2-Max уже тратит
# квоту (cost=0, в пределах free tier). Container Apps ещё не разворачивался —
# его лимиты в снимке присутствуют, но matched=False (нет данных, не ноль).
HEALTHY = {
    "period_start": "2026-09-01T00:00:00Z", "period_end": "2026-09-20T12:00:00Z",
    "total_cost": 0,
    "by_service": [{"servname": "GigaChat-2-Max", "cost": 0, "usefact": 100,
                    "unit": "token", "count": 1}],
    "free_tier": [
        {"label": "Container Apps Services — vCPU", "matched": False, "used": 0.0,
         "limit": 25.0, "unit_label": "vCPU·ч", "percent": None},
        {"label": "Container Apps Jobs — vCPU", "matched": False, "used": 0.0,
         "limit": 5.0, "unit_label": "vCPU·ч", "percent": None},
        {"label": "Object Storage — хранение", "matched": False, "used": 0.0,
         "limit": 15.0, "unit_label": "ГБ", "percent": None},
    ],
}


def near_limit():
    d = json.loads(json.dumps(HEALTHY))
    d["free_tier"][1] = {"label": "Container Apps Jobs — vCPU", "matched": True,
                         "used": 4.6, "limit": 5.0, "unit_label": "vCPU·ч",
                         "percent": 92.0}
    return d


def with_cost():
    d = json.loads(json.dumps(HEALTHY))
    d["total_cost"] = 37.4
    d["by_service"] = [
        {"servname": "Object Storage", "cost": 37.4, "usefact": 20,
         "unit": "GB", "count": 1},
        {"servname": "GigaChat-2-Max", "cost": 0, "usefact": 100,
         "unit": "token", "count": 1},
    ]
    # Даже если по совпадению какая-то категория тоже "у порога" — денежный
    # путь обязан сработать первым и не зависеть от сопоставления категорий.
    d["free_tier"][2] = {"label": "Object Storage — хранение", "matched": True,
                         "used": 14.9, "limit": 15.0, "unit_label": "ГБ",
                         "percent": 99.3}
    return d


def main():
    mod = load_module()
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "consumption.json")
    failures = 0

    def case(name, cond, got):
        nonlocal failures
        if cond:
            print("  [ok]   %s" % name)
        else:
            print("  [FAIL] %s\n         получено: %r" % (name, got))
            failures += 1

    print("E5: алерт расходов Cloud.ru")

    write(path, HEALTHY)
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=80)
    case("нулевой расход, ни одна категория не у порога — тишина",
         key == "cloudru_consumption" and msg is None, msg)

    write(path, near_limit())
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=80)
    case("категория у порога (92% >= 80%) — алерт называет её и процент",
         msg is not None and "Container Apps Jobs" in msg and "92" in msg, msg)
    case("расход по-прежнему 0 — это НЕ денежный алерт (нет 🔴)",
         msg is not None and "🔴" not in msg, msg)

    write(path, near_limit())
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=95)
    case("порог поднят до 95% — 92% уже не тревога",
         msg is None, msg)

    write(path, with_cost())
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=80)
    case("любой ненулевой расход — тревога безусловно (требование 2б)",
         msg is not None and "🔴" in msg, msg)
    case("сумма расхода видна в тексте", msg is not None and "37.4" in msg, msg)
    case("разбивка по сервисам называет главный источник расхода",
         msg is not None and "Object Storage" in msg, msg)

    write(path, HEALTHY, age_h=31)
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=80)
    case("снимок старше 30 ч — алерт о сломанном опросе, а не тишина",
         msg is not None and "не опрашивал" in msg, msg)

    key, msg = mod.check_cloudru_consumption(
        path=os.path.join(tmp, "нет-такого.json"), warn_percent=80)
    case("файла нет — «ни разу не опрошены», не падение и не тишина",
         msg is not None and "ни разу" in msg, msg)

    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write("{битый json")
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=80)
    case("битый файл — алерт, а не падение всего скрипта", msg is not None, msg)

    write(path, {"total_cost": 0, "by_service": [], "free_tier": []})
    key, msg = mod.check_cloudru_consumption(path=path, warn_percent=80)
    case("пустой снимок (ни одной категории) — тишина, а не ложная тревога",
         msg is None, msg)

    case("проверка включена в CHECKS",
         mod.check_cloudru_consumption in mod.CHECKS,
         [c.__name__ for c in mod.CHECKS])

    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
