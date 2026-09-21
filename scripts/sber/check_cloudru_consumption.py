#!/usr/bin/env python3
"""E5: алерт расходов Cloud.ru — сбор (собирает, не тревожит).

Разделение сбор/тревога — как уже сделано для квоты GigaChat (E2): этот
скрипт опрашивает API и кладёт снимок в файл; тревога (talk-alert.py,
check_cloudru_consumption) читает файл без сети.

ЗАЧЕМ. Проект разворачивает в Cloud.ru внешнего сторожа (D3) и вторую копию
семейных фото (Object Storage, S3) в расчёте на бесплатный тариф. Тариф
кончается молча — счёт обнаруживается постфактум в личном кабинете.

Рецепт API (проверен живыми запросами 2026-09-20, см.
docs/integrations/sber/CLOUD_RU.md, раздел «Биллинг, Object Storage и
Foundation Models»):
  1. POST https://iam.api.cloud.ru/api/v1/auth/token {"keyId","secret"}
     -> access_token (час жизни)
  2. GET  https://organization.api.cloud.ru/v3/agreements -> agreements[0].id
     🔴 agreement_id НЕ хардкодить — берётся заново при каждом запуске, чтобы
     смена договора ничего не сломала. Он же не персистится в снимок: заново
     не жалко получить, а хранить чужой для алерта идентификатор незачем.
  3. GET  https://organization.api.cloud.ru/v1/consumption
          ?agreement_id=...&start_date=...&end_date=...  (обе даты обязательны,
          ISO с суффиксом Z; без agreement_id — 400 даже с верными датами)

🔴 Ответ шага 1 несёт `id_token`, а внутри него в base64 — email и телефон
владельца (см. CLAUDE.md, урок 2026-09-20 о персональных данных в
OpenID-claim'ах). Здесь и далее в снимок и в стандартный вывод уходит только
факт наличия токена/длина, не тело ответа целиком.

🔴 API НЕ отдаёт остаток бесплатного тарифа — ни поля, ни отдельного метода
(проверено и по документации, и запросами, 2026-09-20). Значит лимиты — в
FREE_TIER_LIMITS ниже, а не в ответе сервера; алерт умеет только вычитать.

⚠️ Сопоставление ниже (FREE_TIER_LIMITS → servname/unit) НЕ проверено на
живых данных: на 2026-09-20 Container Apps и Object Storage ещё не
разворачивались (D3/S3 в очереди), а значит настоящих строк потребления с их
`servname`/`unit` никто не видел — только потребление GigaChat-2-Max через
Foundation Models. Названия взяты из официальных страниц Cloud.ru и могут не
совпасть с тем, что реально вернёт API. Денежный алерт (total_cost > 0) на
это сопоставление НЕ полагается и остаётся рабочим, даже если ни одна
категория ниже ни разу не сматчится — это осознанный страховочный контур,
а не то же самое, что точный учёт по категориям.

🔴 ИСПРАВЛЕНО 2026-09-21: поле `cost` — это СТАВКА тарифа за единицу, а не
начисленная сумма. Прежняя версия складывала столбец `cost` и завышала расход
в ~123 раза: на живой выгрузке за сентябрь сумма `cost` = 953.34 ₽ при реально
начисленных 7.72 ₽ (`amount` × ставка). Хуже завышения был второй дефект:
условие тревоги `total_cost > 0` срабатывало от самого НАЛИЧИЯ тарифной
строки — в выгрузке шесть строк Object Storage с `amount = 0` (бесплатный
тариф) дали бы тревогу на пустом месте. Признак, по которому видно без
разбора: у входных и генерируемых токенов GigaChat-2-Max стоит одинаковое
466.67 — реальное потребление не совпадает до копейки, совпадают ставки.
Найдено соседним проектом (доска, m0138), подтверждено здесь независимым
замером с устройства 2026-09-21. Разделение полей: деньги считать по
`amount`, бесплатный тариф — по `usefact` (у Object Storage `amount = 0`,
а `usefact` показывает реальные ГБ и операции).

Источник ключа на устройстве — открытый вопрос, решённый в задаче E5: ключи
владельца лежат в Windows Credential Manager на ноутбуке (`nas-cloudru-iam`),
это НЕ Jetson. Решение по умолчанию: отдельная пара ключей IAM для устройства
в CLOUDRU_KEY_ID / CLOUDRU_KEY_SECRET в `config/.env` (root-owned, тот же
файл и тот же режим, что и остальные секреты проекта) — НЕ тот же ключ, что
хранится у владельца на ноутбуке. Такой ключ имеет смысл выпустить с ролью
только на чтение биллинга, если Cloud.ru такую роль предоставляет; на
2026-09-20 это не проверялось (см. отчёт E5, риски).

Пишет снимок в CLOUDRU_CONSUMPTION_FILE (по умолчанию
/var/lib/nas-cloudru-consumption/consumption.json) атомарно и только при
полном успехе — как и check_gigachat_balance.sh: при сбое прежний файл
остаётся и стареет, а алерт узнаёт о сломанном опросе по возрасту файла,
а не по угадыванию (тишина ≠ успех).

Запуск: python3 scripts/sber/check_cloudru_consumption.py
Требует переменные окружения: CLOUDRU_KEY_ID, CLOUDRU_KEY_SECRET.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

IAM_TOKEN_URL = "https://iam.api.cloud.ru/api/v1/auth/token"
AGREEMENTS_URL = "https://organization.api.cloud.ru/v3/agreements"
CONSUMPTION_URL = "https://organization.api.cloud.ru/v1/consumption"

OUT_FILE = os.environ.get("CLOUDRU_CONSUMPTION_FILE",
                          "/var/lib/nas-cloudru-consumption/consumption.json")
TIMEOUT = 25

# Бесплатный тариф (подтверждено официальными страницами Cloud.ru,
# 2026-09-20) — на всю организацию целиком, остаток не переносится на
# следующий месяц. См. предупреждение о непроверенности сопоставления выше.
FREE_TIER_LIMITS = (
    {"label": "Container Apps Services — vCPU",
     "servname_has": ("container", "service"), "unit_has": ("vcpu",),
     "limit": 25.0, "unit_label": "vCPU·ч"},
    {"label": "Container Apps Services — RAM",
     "servname_has": ("container", "service"), "unit_has": ("gb",),
     "limit": 50.0, "unit_label": "ГБ·ч"},
    {"label": "Container Apps Jobs — vCPU",
     "servname_has": ("container", "job"), "unit_has": ("vcpu",),
     "limit": 5.0, "unit_label": "vCPU·ч"},
    {"label": "Container Apps Jobs — RAM",
     "servname_has": ("container", "job"), "unit_has": ("gb",),
     "limit": 10.0, "unit_label": "ГБ·ч"},
    {"label": "Object Storage — хранение",
     "servname_has": ("storage",), "unit_has": ("gb",),
     "limit": 15.0, "unit_label": "ГБ"},
)


def _post_json(url, payload, headers=None):
    hdr = {"Content-Type": "application/json"}
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=hdr, method="POST")
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    try:
        return json.loads(resp.read().decode("utf-8"))
    finally:
        resp.close()


def _get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    try:
        return json.loads(resp.read().decode("utf-8"))
    finally:
        resp.close()


def get_access_token(key_id, key_secret):
    """Шаг 1. Не логировать тело ответа целиком — там id_token с email/телефоном
    владельца (см. предупреждение в шапке файла)."""
    data = _post_json(IAM_TOKEN_URL, {"keyId": key_id, "secret": key_secret})
    token = data.get("access_token")
    if not token:
        raise RuntimeError("ответ авторизации Cloud.ru без access_token")
    return token


def get_agreement_id(token):
    """Шаг 2. agreement_id берётся заново каждый раз — не хардкодить."""
    data = _get_json(AGREEMENTS_URL, {"Authorization": "Bearer " + token})
    agreements = data.get("agreements") or []
    if not agreements:
        raise RuntimeError("у организации нет ни одного договора (agreements пуст)")
    return agreements[0]["id"]


def current_month_range(now=None):
    """Начало текущего месяца (00:00 UTC 1-го числа) — до текущего момента."""
    now = now or datetime.datetime.utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start.strftime(fmt), now.strftime(fmt)


def get_consumption(token, agreement_id, start_date, end_date):
    """Шаг 3. Три обязательных параметра: agreement_id и обе даты."""
    url = ("%s?agreement_id=%s&start_date=%s&end_date=%s"
           % (CONSUMPTION_URL, agreement_id, start_date, end_date))
    data = _get_json(url, {"Authorization": "Bearer " + token})
    return data.get("consumptions") or []


def summarize(consumptions):
    """Группировка по servname — генерическая, работает для любого сервиса,
    включая уже идущее в бою потребление GigaChat-2-Max (задача E5, п.4):
    ответ не пустой, и его нужно корректно разложить, а не свалить в кучу.

    Возвращает ДВЕ группировки:
      * by_service  — по имени сервиса, для денежной разбивки в алерте
        (деньги суммируются нормально независимо от единицы измерения);
      * by_bucket   — по (имя сервиса, единица измерения). Один и тот же
        servname может нести разнородные строки (у Container Apps Services
        отдельно vCPU·ч и ГБ·ч) — 🔴 если сложить usefact этих строк
        вместе, vCPU-часы смешаются с ГБ-часами и оба числа станут
        бессмысленными. match_free_tier() обязан сравнивать с лимитом
        именно by_bucket, а не by_service."""
    by_service = {}
    by_bucket = {}
    total_cost = 0.0
    for item in consumptions:
        name = str(item.get("servname") or item.get("sku") or "?")
        # 🔴 `cost` — СТАВКА тарифа за единицу, а не начисленная сумма.
        # Деньги = amount * cost; `amount` — тарифицируемое количество,
        # `usefact` — фактическое потребление (для бесплатного тарифа).
        rate = float(item.get("cost") or 0)
        amount = float(item.get("amount") or 0)
        money = amount * rate
        usefact_raw = item.get("usefact")
        usefact = float(usefact_raw if usefact_raw is not None
                        else (item.get("amount") or 0))
        unit = item.get("unit") or ""

        srow = by_service.setdefault(name, {"cost": 0.0, "usefact": 0.0,
                                            "unit": unit, "count": 0})
        srow["cost"] += money
        srow["usefact"] += usefact
        if unit:
            srow["unit"] = unit
        srow["count"] += 1

        brow = by_bucket.setdefault((name, unit), {"servname": name, "unit": unit,
                                                    "usefact": 0.0, "count": 0})
        brow["usefact"] += usefact
        brow["count"] += 1

        total_cost += money
    return total_cost, by_service, by_bucket


def match_free_tier(by_bucket, limits=FREE_TIER_LIMITS):
    """Для каждого лимита — «сматчилось» или нет, отдельно от «использовано 0».

    Принимает группировку (servname, unit) — см. summarize() — иначе разные
    единицы измерения под одним servname складывались бы друг с другом.

    Несматченная категория НЕ значит «потребления нет» — см. предупреждение о
    непроверенности сопоставления в шапке файла. Алерт обязан читать именно
    `matched`, а не считать отсутствие строки нулём (задача E5, требование 3:
    отличать «нет данных» от «ноль»)."""
    results = []
    for rule in limits:
        used = 0.0
        matched = False
        for (name, unit), row in by_bucket.items():
            lname = name.lower()
            lunit = (unit or "").lower()
            if (all(k in lname for k in rule["servname_has"])
                    and all(k in lunit for k in rule["unit_has"])):
                used += row["usefact"]
                matched = True
        percent = (used / rule["limit"] * 100.0) if (matched and rule["limit"]) else None
        results.append({"label": rule["label"], "matched": matched, "used": used,
                        "limit": rule["limit"], "unit_label": rule["unit_label"],
                        "percent": percent})
    return results


def poll(key_id, key_secret, out_path=None):
    out_path = out_path or OUT_FILE
    token = get_access_token(key_id, key_secret)
    agreement_id = get_agreement_id(token)
    start, end = current_month_range()
    consumptions = get_consumption(token, agreement_id, start, end)
    total_cost, by_service, by_bucket = summarize(consumptions)
    tiers = match_free_tier(by_bucket)

    state = {
        "period_start": start,
        "period_end": end,
        "total_cost": round(total_cost, 2),
        "by_service": [
            {"servname": name, "cost": round(row["cost"], 2),
             "usefact": row["usefact"], "unit": row["unit"], "count": row["count"]}
            for name, row in sorted(by_service.items())
        ],
        "free_tier": tiers,
    }

    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False)
    os.replace(tmp, out_path)
    return state


def main():
    key_id = os.environ.get("CLOUDRU_KEY_ID")
    key_secret = os.environ.get("CLOUDRU_KEY_SECRET")
    if not key_id or not key_secret:
        sys.stderr.write("нет CLOUDRU_KEY_ID/CLOUDRU_KEY_SECRET в окружении\n")
        return 1
    try:
        state = poll(key_id, key_secret)
    except (RuntimeError, ValueError, OSError, urllib.error.URLError) as exc:
        sys.stderr.write("сбор расходов Cloud.ru не удался: %s\n" % exc)
        return 1
    print("потрачено в этом месяце: %.2f; услуг в разбивке: %d"
          % (state["total_cost"], len(state["by_service"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
