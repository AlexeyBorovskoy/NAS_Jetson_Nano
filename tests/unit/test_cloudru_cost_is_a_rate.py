#!/usr/bin/env python3
"""E5: поле `cost` у Cloud.ru — СТАВКА тарифа, а не начисленная сумма.

ИСТОРИЯ ДЕФЕКТА (без неё проверка — балласт). До 2026-09-21 сборщик складывал
столбец `cost` и считал это деньгами. На живой выгрузке за сентябрь 2026 это
давало 953.34 ₽ при реально начисленных 7.72 ₽ — завышение в ~123 раза,
потому что у токенов единица «млн шт»: 466.67 ₽ за МИЛЛИОН токенов, а
израсходовано 0.014 миллиона.

Второй дефект был опаснее завышения: тревога `total_cost > 0` срабатывала от
самого НАЛИЧИЯ тарифной строки. В выгрузке шесть строк Object Storage с
`amount = 0` (всё в бесплатном тарифе) — они подняли бы тревогу на пустом
месте, и её быстро научились бы не читать.

Найдено соседним проектом (доска, m0138), подтверждено независимым замером с
Jetson 2026-09-21. Данные ниже — та самая выгрузка, не выдуманная.

Разделение полей, проверенное на живых данных:
  * `amount`  — тарифицируемое количество → ДЕНЬГИ = amount * cost;
  * `usefact` — фактическое потребление → БЕСПЛАТНЫЙ ТАРИФ.
У Object Storage `amount = 0`, а `usefact` показывает реальные 0.19 ГБ и
операции: сложи их как деньги — получишь ноль, сложи как потребление —
увидишь, сколько бесплатного тарифа съедено.

Запуск (идёт и на Jetson с Python 3.6):
    python3 tests/unit/test_cloudru_cost_is_a_rate.py
"""
import importlib.util
import io
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTOR = os.path.join(HERE, "..", "..", "scripts", "sber",
                         "check_cloudru_consumption.py")

# Живая выгрузка GET /v1/consumption за 2026-09-01…21, аккаунт владельца.
LIVE_ROWS = [
    {"servname": "БЯМ GigaChat-2-Max входные токены", "unit": "млн шт",
     "amount": 0.01446677, "usefact": 0.00003100, "cost": 466.67},
    {"servname": "БЯМ GigaChat-2-Max генерируемые токены", "unit": "млн шт",
     "amount": 0.00186668, "usefact": 0.00000400, "cost": 466.67},
    {"servname": "БЯМ GigaChat3-10B-A1.8B входные токены", "unit": "млн шт",
     "amount": 0.00997000, "usefact": 0.00099700, "cost": 10.0},
    {"servname": "БЯМ GigaChat3-10B-A1.8B генерируемые токены", "unit": "млн шт",
     "amount": 0.00002000, "usefact": 0.00000200, "cost": 10.0},
    {"servname": "Объектное хранилище Стандартное", "unit": "ГБ",
     "amount": 0.0, "usefact": 0.19066740, "cost": 0.0},
    {"servname": "Объектное хранилище Исходящий трафик", "unit": "ГБ",
     "amount": 0.0, "usefact": 0.01042504, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции L", "unit": "тыс. шт",
     "amount": 0.0, "usefact": 0.124, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции H", "unit": "тыс. шт",
     "amount": 0.0, "usefact": 0.030, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции G", "unit": "тыс. шт",
     "amount": 0.0, "usefact": 0.074, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции P", "unit": "тыс. шт",
     "amount": 0.0, "usefact": 0.494, "cost": 0.0},
]

REAL_TOTAL = 7.7222        # amount * ставка, сверено с соседним проектом
BUGGY_TOTAL = 953.34       # сумма столбца cost — то, что считалось раньше


def load_module():
    spec = importlib.util.spec_from_file_location("cloudru_consumption", COLLECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load_module()
    failures = 0

    def case(title, ok, detail=""):
        nonlocal_failures[0] += 0 if ok else 1
        print("%s %s%s" % ("OK  " if ok else "ПАДЕНИЕ", title,
                           ("  — %s" % detail) if detail else ""))

    nonlocal_failures = [0]

    total, by_service, by_bucket = mod.summarize(LIVE_ROWS)

    case("деньги считаются как amount * ставка, а не суммой ставок",
         abs(total - REAL_TOTAL) < 0.01, "получено %.4f, ожидалось %.4f" % (total, REAL_TOTAL))

    case("прежнее завышение в ~123 раза не воспроизводится",
         abs(total - BUGGY_TOTAL) > 900, "получено %.2f, дефектное было %.2f" % (total, BUGGY_TOTAL))

    free_only = [r for r in LIVE_ROWS if r["amount"] == 0]
    total_free, _, bucket_free = mod.summarize(free_only)
    case("строки бесплатного тарифа (amount=0) не поднимают денежную тревогу",
         total_free == 0.0, "total_cost=%.6f по %d строкам" % (total_free, len(free_only)))

    storage = bucket_free.get(("Объектное хранилище Стандартное", "ГБ"))
    case("usefact сохранён для учёта бесплатного тарифа",
         storage is not None and abs(storage["usefact"] - 0.1906674) < 1e-9,
         "хранилище: %s" % (storage["usefact"] if storage else "строки нет"))

    gmax = by_service.get("БЯМ GigaChat-2-Max входные токены")
    case("разбивка по услуге тоже в деньгах, а не в ставках",
         gmax is not None and abs(gmax["cost"] - 6.7512) < 0.01,
         "получено %.4f, ставка была бы 466.67" % (gmax["cost"] if gmax else -1))

    case("vCPU·ч и ГБ·ч не смешиваются: ключ by_bucket — (услуга, единица)",
         all(isinstance(k, tuple) and len(k) == 2 for k in by_bucket),
         "ключей: %d" % len(by_bucket))

    failures = nonlocal_failures[0]
    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
