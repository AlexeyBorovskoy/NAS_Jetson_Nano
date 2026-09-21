#!/usr/bin/env python3
"""E5 (план 2026-09): сбор потребления Cloud.ru для алерта расходов.

ЗАЧЕМ. Проект строит внешнего сторожа (D3, Cloud.ru Job) и вторую копию фото
(Object Storage, S3) в расчёте на бесплатный тариф. Тариф кончается молча —
платёж обнаруживается постфактум в личном кабинете. API НЕ отдаёт остаток
бесплатного тарифа (ни поля, ни метода — проверено 2026-09-20, см.
docs/integrations/sber/CLOUD_RU.md), поэтому сборщик держит лимиты у себя и
вычитает из них измеренное потребление. `agreement_id` — обязательный
параметр `/v1/consumption` (без него `400`) и не хардкодится: берётся из
`/v3/agreements` при каждом запуске.

Сеть подменяется заглушками `_post_json`/`_get_json` — живых обращений нет.
Боевой модуль импортируется целиком, копий логики нет.

Запуск (без pytest, идёт и на Jetson с Python 3.6):
    python3 tests/unit/test_cloudru_consumption_poll.py
"""
import datetime
import importlib.util
import io
import json
import os
import sys
import tempfile

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTOR = os.path.join(HERE, "..", "..", "scripts", "sber",
                         "check_cloudru_consumption.py")


def load_module():
    spec = importlib.util.spec_from_file_location("cloudru_consumption", COLLECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Подставные значения — не настоящие идентификаторы договора/проекта.
TOKEN_OK = {"access_token": "tok-fake-123", "expires_in": 3600,
            "id_token": "eyFAKE.PAYLOAD.IGNORE"}
AGREEMENTS_OK = {"agreements": [{"id": "agr-fake-abc",
                                 "status": "AGREEMENT_STATUS_ACTIVE"}]}

# Реальность боевого аккаунта (задача E5, требование 4): GigaChat-2-Max уже
# тратит квоту, и Container Apps Services сюда добавлены как второй сервис —
# ответ должен корректно сгруппироваться, а не свалиться в одну кучу.
# 🔴 2026-09-21: `amount` — это НАЧИСЛЕННЫЕ РУБЛИ (= usefact * cost), а не
# количество. Прежняя редакция фикстуры клала в `amount` штуки и часы — такая
# выгрузка от Cloud.ru прийти не может. Здесь всё в бесплатном тарифе:
# ставка 0 → начислено 0, а количество живёт в `usefact`.
CONSUMPTION_MIXED = {"consumptions": [
    {"sku": "giga-2-max", "servname": "GigaChat-2-Max", "resource_id": "r1",
     "usedate": "2026-09-01", "amount": 0, "amount_nds": 0, "cost": 0,
     "unit": "token", "usefact": 100},
    {"sku": "ca-svc-vcpu", "servname": "Container Apps Services",
     "resource_id": "r2", "usedate": "2026-09-05", "amount": 0, "amount_nds": 0,
     "cost": 0, "unit": "vCPU*hour", "usefact": 3.5},
    {"sku": "ca-svc-ram", "servname": "Container Apps Services",
     "resource_id": "r3", "usedate": "2026-09-05", "amount": 0, "amount_nds": 0,
     "cost": 0, "unit": "GB*hour", "usefact": 4.0},
]}

# 20 ГБ по ставке 12.5 ₽/ГБ → начислено 250 ₽ (305 с НДС). Величины связаны
# так же, как в живой выгрузке: amount = usefact * cost.
CONSUMPTION_WITH_COST = {"consumptions": [
    {"sku": "os-storage", "servname": "Object Storage", "resource_id": "r4",
     "usedate": "2026-09-10", "amount": 250, "amount_nds": 305, "cost": 12.5,
     "unit": "GB", "usefact": 20},
]}


def main():
    mod = load_module()
    failures = 0

    def case(name, cond, got):
        nonlocal failures
        if cond:
            print("  [ok]   %s" % name)
        else:
            print("  [FAIL] %s\n         получено: %r" % (name, got))
            failures += 1

    print("E5: сбор потребления Cloud.ru")

    # ── чистые функции, без сети ────────────────────────────────────────────
    cost, by_service, by_bucket = mod.summarize(CONSUMPTION_MIXED["consumptions"])
    case("деньги по всем строкам верны (в этой выборке ставки нулевые — 0)",
         cost == 0, cost)
    case("группировка по servname — два сервиса, не три строки",
         set(by_service) == {"GigaChat-2-Max", "Container Apps Services"},
         sorted(by_service))
    case("Container Apps Services объединяет обе строки (vCPU и RAM)",
         by_service["Container Apps Services"]["count"] == 2, by_service)
    case("GigaChat-2-Max посчитан отдельно и не смешан с Container Apps",
         by_service["GigaChat-2-Max"]["usefact"] == 100, by_service)
    case("группировка по (servname, unit) держит vCPU и ГБ·ч раздельно — "
         "иначе 3.5 vCPU·ч и 4.0 ГБ·ч сложились бы в бессмысленные 7.5",
         by_bucket[("Container Apps Services", "vCPU*hour")]["usefact"] == 3.5
         and by_bucket[("Container Apps Services", "GB*hour")]["usefact"] == 4.0,
         by_bucket)

    tiers = mod.match_free_tier(by_bucket)
    svc_vcpu = next(t for t in tiers if t["label"] == "Container Apps Services — vCPU")
    case("vCPU Container Apps Services сматчился по unit и посчитан",
         svc_vcpu["matched"] is True and svc_vcpu["used"] == 3.5, svc_vcpu)
    svc_ram = next(t for t in tiers if t["label"] == "Container Apps Services — RAM")
    case("RAM Container Apps Services взял свою строку, а не строку vCPU",
         svc_ram["matched"] is True and svc_ram["used"] == 4.0, svc_ram)
    os_tier = next(t for t in tiers if t["label"] == "Object Storage — хранение")
    case("Object Storage не встречался в этом снимке — matched=False, а НЕ 0%"
         " (нет данных ≠ ноль)",
         os_tier["matched"] is False and os_tier["percent"] is None, os_tier)

    start, end = mod.current_month_range(
        now=datetime.datetime(2026, 9, 20, 12, 0, 0))
    case("начало периода — 1-е число месяца, 00:00 UTC",
         start == "2026-09-01T00:00:00Z", start)
    case("конец периода — переданный момент (ISO, с Z)",
         end == "2026-09-20T12:00:00Z", end)

    # ── poll(): сквозной путь с заглушками сети, три вызова в правильном порядке ──
    calls = []

    def stub_post(url, payload, headers=None):
        calls.append(("POST", url, payload, headers))
        return TOKEN_OK

    def stub_get(url, headers=None):
        calls.append(("GET", url, headers))
        if "/v3/agreements" in url:
            return AGREEMENTS_OK
        return CONSUMPTION_WITH_COST

    mod._post_json = stub_post
    mod._get_json = stub_get
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "state", "consumption.json")
    state = mod.poll("kid-fake", "ksec-fake", out_path=out)

    case("шаг 1 — POST на IAM с {keyId, secret}, а не form-encoded",
         calls[0][:3] == ("POST", mod.IAM_TOKEN_URL,
                          {"keyId": "kid-fake", "secret": "ksec-fake"}), calls[0])
    case("шаг 2 — GET /v3/agreements с Bearer-токеном из шага 1",
         calls[1][0] == "GET" and "/v3/agreements" in calls[1][1]
         and calls[1][2] == {"Authorization": "Bearer tok-fake-123"}, calls[1])
    case("шаг 3 — agreement_id взят из ответа шага 2, а не захардкожен",
         "agreement_id=agr-fake-abc" in calls[2][1], calls[2][1])
    case("шаг 3 — обе даты присутствуют в запросе потребления",
         "start_date=" in calls[2][1] and "end_date=" in calls[2][1], calls[2][1])

    case("poll() записал файл", os.path.exists(out), out)
    # 2026-09-21: прежде здесь ожидалось 12.5 — то есть СТАВКА тарифа.
    # Деньги лежат готовыми в `amount`: 20 ГБ по ставке 12.5 = 250 ₽.
    # Подробности и история дефекта — tests/unit/test_cloudru_cost_is_a_rate.py.
    case("ненулевой расход виден в снимке (начислено 250)",
         state["total_cost"] == 250.0, state)

    with io.open(out, encoding="utf-8") as fh:
        raw_on_disk = fh.read()
    case("на диске нет agreement_id и id_token — не персистятся, "
         "берутся заново при каждом опросе",
         "agreement_id" not in raw_on_disk and "id_token" not in raw_on_disk
         and "agr-fake-abc" not in raw_on_disk, raw_on_disk)

    # ── обработка сбоев: «нет данных» — явная ошибка, а не тихий 0 ─────────────
    def stub_get_no_agreements(url, headers=None):
        return {"agreements": []}
    mod._get_json = stub_get_no_agreements
    try:
        mod.poll("kid-fake", "ksec-fake", out_path=out)
        case("пустой agreements — исключение, а не тихий успех", False, "не упало")
    except RuntimeError as exc:
        case("пустой agreements — понятная ошибка на русском",
             "договор" in str(exc), str(exc))

    def stub_post_no_token(url, payload, headers=None):
        return {"token_type": "Bearer"}
    mod._post_json = stub_post_no_token
    try:
        mod.get_access_token("kid-fake", "ksec-fake")
        case("ответ без access_token — исключение", False, "не упало")
    except RuntimeError as exc:
        case("ответ без access_token — понятная ошибка",
             "access_token" in str(exc), str(exc))

    print("\nпадений: %d" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
