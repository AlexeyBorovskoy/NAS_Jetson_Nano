#!/usr/bin/env python3
"""E5: деньги в биллинге Cloud.ru лежат в `amount`. Ни складывать ставки, ни умножать.

ИСТОРИЯ ДЕФЕКТА (без неё проверка — балласт). Одну выгрузку прочли неверно
дважды подряд, обе версии успели побывать в коде или в рекомендации:

    сумма `cost`            953.34 ₽   — сложение СТАВОК тарифа. Неверно.
    сумма `amount * cost`     7.7222 ₽ — умножение денег на ставку второй раз.
                                         Неверно, и эта версия была выкачена
                                         и закреплена тестом.
    сумма `amount`            0.0263 ₽ — ВЕРНО (0.0321 с НДС).

За полтора месяца на счету израсходовано две с половиной копейки, а не 953 ₽
и не 7.72 ₽.

СЕМАНТИКА ПОЛЕЙ, доказанная замером 2026-09-21 на 13 строках из 13:
    usefact    — количество в единице из `unit` (млн шт, ГБ, тыс. шт);
    cost       — ставка тарифа, рублей за единицу;
    amount     — НАЧИСЛЕНО, рублей без НДС, ровно = usefact * cost;
    amount_nds — начислено с НДС, ровно = amount * 1.22.

Решающий довод — НДС: он лежит на `amount`. На количество НДС не начисляют,
значит `amount` — денежная величина, а не «тарифицируемое количество», как
здесь было записано в первой редакции этого файла.

ПРИЗНАК, КОТОРЫЙ БЫЛ ПЕРЕД ГЛАЗАМИ И НЕ БЫЛ ИСПОЛЬЗОВАН: отношение
`amount / usefact` у токенов даёт ровно 466.67 — то есть ставку. Значит
`amount` уже произведение. Число стояло в собственной выгрузке, и его хватило
бы, чтобы не выкатывать вторую неверную версию. Родня правилу проекта:
объяснение появилось раньше, чем была проверена входная величина.

⚠️ ЧЕГО ЭТОТ ТЕСТ НЕ ДОКАЗЫВАЕТ. Для Object Storage равенство
`amount = usefact * cost` не проверено ничем: там `amount = 0`, и ноль
умножается на что угодно. Что значит `usefact` для хранения — мгновенные ГБ,
среднесуточные или ГБ·сутки — **неизвестно**: в день, когда в корзине лежало
7.5 ГБ, биллинг показал 0.0656 и 0.1250. Расхождение в 60 раз не объяснено
(указано соседним проектом, доска m0142). Поэтому сопоставление
FREE_TIER_LIMITS по хранилищу остаётся НЕПРОВЕРЕННЫМ.

Найдено соседним проектом (m0138), им же отозвано и исправлено (m0141),
подтверждено здесь независимым замером с Jetson. Данные ниже — та самая
выгрузка, не выдуманная.

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

# Живая выгрузка GET /v1/consumption, аккаунт владельца, замер 2026-09-21.
LIVE_ROWS = [
    {"servname": "БЯМ GigaChat-2-Max входные токены", "unit": "млн шт",
     "amount": 0.01446677, "amount_nds": 0.01764946, "usefact": 0.00003100, "cost": 466.67},
    {"servname": "БЯМ GigaChat-2-Max генерируемые токены", "unit": "млн шт",
     "amount": 0.00186668, "amount_nds": 0.00227735, "usefact": 0.00000400, "cost": 466.67},
    {"servname": "БЯМ GigaChat3-10B-A1.8B входные токены", "unit": "млн шт",
     "amount": 0.00997000, "amount_nds": 0.01216340, "usefact": 0.00099700, "cost": 10.0},
    {"servname": "БЯМ GigaChat3-10B-A1.8B генерируемые токены", "unit": "млн шт",
     "amount": 0.00002000, "amount_nds": 0.00002440, "usefact": 0.00000200, "cost": 10.0},
    {"servname": "Объектное хранилище Стандартное", "unit": "ГБ",
     "amount": 0.0, "amount_nds": 0.0, "usefact": 0.19066740, "cost": 0.0},
    {"servname": "Объектное хранилище Исходящий трафик", "unit": "ГБ",
     "amount": 0.0, "amount_nds": 0.0, "usefact": 0.01042504, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции L", "unit": "тыс. шт",
     "amount": 0.0, "amount_nds": 0.0, "usefact": 0.124, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции H", "unit": "тыс. шт",
     "amount": 0.0, "amount_nds": 0.0, "usefact": 0.030, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции G", "unit": "тыс. шт",
     "amount": 0.0, "amount_nds": 0.0, "usefact": 0.074, "cost": 0.0},
    {"servname": "Объектное хранилище Стандартное операции P", "unit": "тыс. шт",
     "amount": 0.0, "amount_nds": 0.0, "usefact": 0.494, "cost": 0.0},
]

REAL_TOTAL = 0.02632345       # сумма amount — деньги, взятые готовыми
REAL_TOTAL_NDS = 0.03211461   # сумма amount_nds = amount * 1.22
BUGGY_SUM_COST = 953.34       # сложение ставок — первая неверная версия
BUGGY_AMOUNT_X_COST = 7.7222  # деньги * ставка — вторая неверная версия


def load_module():
    spec = importlib.util.spec_from_file_location("cloudru_consumption", COLLECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load_module()
    failed = [0]

    def case(title, ok, detail=""):
        failed[0] += 0 if ok else 1
        print("%s %s%s" % ("OK  " if ok else "ПАДЕНИЕ", title,
                           ("  — %s" % detail) if detail else ""))

    # Сами данные — тоже проверка: если выгрузка перестанет сходиться,
    # толкование полей придётся пересматривать, а не подгонять код.
    prod_ok = sum(1 for r in LIVE_ROWS
                  if abs(r["usefact"] * r["cost"] - r["amount"]) <= max(1e-9, abs(r["amount"]) * 1e-6))
    case("на живых данных amount == usefact * cost",
         prod_ok == len(LIVE_ROWS), "сошлось %d из %d" % (prod_ok, len(LIVE_ROWS)))

    nds_ok = sum(1 for r in LIVE_ROWS
                 if (abs(r["amount_nds"] - r["amount"] * 1.22) < 1e-6
                     if r["amount"] else r["amount_nds"] == 0))
    case("на живых данных amount_nds == amount * 1.22 (НДС на деньгах)",
         nds_ok == len(LIVE_ROWS), "сошлось %d из %d" % (nds_ok, len(LIVE_ROWS)))

    total, by_service, by_bucket = mod.summarize(LIVE_ROWS)

    case("деньги берутся из amount готовыми",
         abs(total - REAL_TOTAL) < 1e-6,
         "получено %.8f, ожидалось %.8f" % (total, REAL_TOTAL))

    case("сложение ставок (953.34) не воспроизводится",
         abs(total - BUGGY_SUM_COST) > 900,
         "получено %.6f" % total)

    case("умножение денег на ставку (7.7222) не воспроизводится",
         abs(total - BUGGY_AMOUNT_X_COST) > 7,
         "получено %.6f" % total)

    free_only = [r for r in LIVE_ROWS if r["amount"] == 0]
    total_free, _, bucket_free = mod.summarize(free_only)
    case("строки бесплатного тарифа (amount=0) не поднимают денежную тревогу",
         total_free == 0.0,
         "total_cost=%.8f по %d строкам" % (total_free, len(free_only)))

    storage = bucket_free.get(("Объектное хранилище Стандартное", "ГБ"))
    case("usefact сохранён для учёта бесплатного тарифа",
         storage is not None and abs(storage["usefact"] - 0.1906674) < 1e-9,
         "хранилище: %s" % (storage["usefact"] if storage else "строки нет"))

    gmax = by_service.get("БЯМ GigaChat-2-Max входные токены")
    case("разбивка по услуге — деньги, а не ставка и не произведение",
         gmax is not None and abs(gmax["cost"] - 0.01446677) < 1e-8,
         "получено %.8f, ставка была бы 466.67" % (gmax["cost"] if gmax else -1))

    case("НДС считается отдельным полем, а не домножением на лету",
         gmax is not None and abs(gmax["cost_nds"] - 0.01764946) < 1e-8,
         "получено %.8f" % (gmax["cost_nds"] if gmax else -1))

    nds_total = sum(r["cost_nds"] for r in by_service.values())
    case("сумма с НДС совпадает с выгрузкой",
         abs(nds_total - REAL_TOTAL_NDS) < 1e-6,
         "получено %.8f, ожидалось %.8f" % (nds_total, REAL_TOTAL_NDS))

    case("vCPU·ч и ГБ·ч не смешиваются: ключ by_bucket — (услуга, единица)",
         all(isinstance(k, tuple) and len(k) == 2 for k in by_bucket),
         "ключей: %d" % len(by_bucket))

    no_usefact = [{"servname": "Без usefact", "unit": "ГБ", "amount": 5.0,
                   "amount_nds": 6.1, "cost": 2.5}]
    t2, s2, _ = mod.summarize(no_usefact)
    case("строка без usefact: деньги верны, количество не подменяется деньгами",
         t2 == 5.0 and s2["Без usefact"]["usefact"] == 0.0,
         "деньги=%.2f, usefact=%.2f" % (t2, s2["Без usefact"]["usefact"]))

    print("\nпадений: %d" % failed[0])
    return 1 if failed[0] else 0


if __name__ == "__main__":
    sys.exit(main())
