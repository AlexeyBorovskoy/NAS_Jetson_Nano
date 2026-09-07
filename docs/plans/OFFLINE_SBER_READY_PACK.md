# Offline Sber-ready pack — всё подготовлено без Jetson

> **Дата:** 2026-09-07  
> **Статус:** committed + mirrored (GitHub + GitVerse); device install = после «деплой» + Jetson online  
> Канон: [`DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](DEVELOPMENT_PLAN_2026-09_SBER_ERA.md)  
>
> Cloud.ru FM key exists but chat returns **402** until balance/grant. GigaChat PERS path does not need Cloud.ru money.

## 1. Что уже в репозитории (код + docs)

| Блок | Артефакты |
|---|---|
| ADR | 0007 nodes, 0008 LLM Giga-first, 0009 backup |
| Gateway | Giga-2, api.giga.chat, flight lock, failover→DeepSeek, balance, **cloudru** |
| Talk | `TALK_BOT_LLM_PROVIDER` |
| Env | `.env.example`, `config/sber.env.snippet` |
| Immich→HDD | script + systemd + install helper |
| S3 L2 example | `scripts/backup/restic_s3_cloudru_example.sh` |
| Verify / balance | `scripts/sber/verify_gateway.sh`, `check_gigachat_balance.sh` |
| Merge env | `scripts/sber/merge_sber_snippet.sh` |
| GitVerse | `scripts/sber/gitverse_mirror_push.sh` |
| IAM example | `scripts/sber/cloudru_iam_token_example.sh` |
| Console steps | `docs/integrations/sber/CONSOLE_CHECKLIST.md` |
| Deploy | `DEPLOY_W1_GIGA_CUTOVER.md` + **`DEPLOY_FULL_SBER_CUTOVER.md`** |
| Tests | `tests/llm_gateway/test_sber_routing.py` (5 pass) |
| Audit | `artifacts/reports/CODE_AUDIT_SBER_2026-09-07.md` |

## 2. Кабинеты — факт на 2026-09-07

| Шаг | Статус |
|---|---|
| Проект + SA `home-nas-api` + роль | ✅ |
| FM API key | ✅ (Bearer); 402 without money |
| Грант/баланс Cloud.ru | ⏳ owner |
| S3 bucket | ⏳ later |
| GitVerse NAS_HOME | ✅ mirror |
| Keys → password manager (leave Downloads) | ⏳ recommended |

See [`../integrations/sber/CONSOLE_CHECKLIST.md`](../integrations/sber/CONSOLE_CHECKLIST.md), [`../integrations/sber/CLOUD_RU.md`](../integrations/sber/CLOUD_RU.md).

## 3. Проверка pack на workstation

```bash
bash scripts/sber/preflight_sber_pack.sh
python -m pytest tests/llm_gateway/test_sber_routing.py -q
```

## 4. Когда Jetson снова online + «деплой»

Один документ: [`DEPLOY_FULL_SBER_CUTOVER.md`](DEPLOY_FULL_SBER_CUTOVER.md)

Порядок: git pull → merge snippet → rebuild gateway/api → verify → Immich HDD timer → (optional) S3 → balance timer → mark plan.

## 5. Сознательно не сделано offline

- Запись в device `.env`  
- `docker compose` на Jetson  
- Создание bucket/VM в Cloud.ru  
- Push с секретами  
- Amnezia / VPS firewall  
