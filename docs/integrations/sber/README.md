# Sber ecosystem integrations / Интеграции экосистемы Сбер

> 🇬🇧 Index. Canon: [`../../plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](../../plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md).  
> 🇷🇺 Указатель. Канон: тот же план.  
> 🇬🇧 Offline pack: [`../../plans/OFFLINE_SBER_READY_PACK.md`](../../plans/OFFLINE_SBER_READY_PACK.md).

| Topic / Тема | Document / Документ | ADR / scripts |
|---|---|---|
| Nodes / Узлы | plan §2 | [ADR-0007](../../decisions/ADR-0007-node-model-jetson-sor-cloud-edge.md) |
| LLM Giga first | [GIGACHAT.md](GIGACHAT.md) | [ADR-0008](../../decisions/ADR-0008-llm-routing-giga-first.md) |
| Backup SSD/HDD/S3 | plan §7 | [ADR-0009](../../decisions/ADR-0009-backup-ssd-hdd-s3.md) |
| Cloud.ru FM / S3 / IAM | [CLOUD_RU.md](CLOUD_RU.md) | `scripts/sber/*` |
| GitVerse mirror | [GITVERSE.md](GITVERSE.md) | SSH + HTTPS |
| Console checklist | [CONSOLE_CHECKLIST.md](CONSOLE_CHECKLIST.md) | owner |
| Device cutover | [DEPLOY_FULL](../../plans/DEPLOY_FULL_SBER_CUTOVER.md) | after deploy |
| Env snippet | `config/sber.env.snippet` | `merge_sber_snippet.sh` |
| Device env checklist | [DEVICE_ENV_CHECKLIST](../../plans/DEVICE_ENV_CHECKLIST.md) | no secrets |
| S3 + budget | [S3_AND_BUDGET_CHECKLIST](S3_AND_BUDGET_CHECKLIST.md) | console |
| API inventory | [PUBLIC_PROBE](../../plans/CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md) | — |

## Status 2026-09-08 / Статус

| | 🇬🇧 | 🇷🇺 |
|---|---|---|
| Offline pack + gateway | ✅ in git | ✅ в git |
| Jetson Giga-first cutover | ✅ live | ✅ в бою |
| Immich → HDD | ✅ 13G = 13G | ✅ |
| GitVerse mirror | ✅ SSH | ✅ |
| Cloud.ru FM chat | ✅ 200 | ✅ |
| S3 restic L2 | ⏳ tenant_id | ⏳ |
| giga-balance timer | ✅ | ✅ |

## Quick check / Быстрая проверка

```bash
bash scripts/sber/preflight_sber_pack.sh
python -m pytest tests/llm_gateway/test_sber_routing.py -q
```

🇬🇧 **Secrets:** never in git. Device `config/.env` + password manager only.  
🇷🇺 **Секреты:** никогда в git. Только device `.env` и password manager.
