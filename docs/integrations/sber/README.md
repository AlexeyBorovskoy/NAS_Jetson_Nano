# Интеграции экосистемы Сбер / Sber ecosystem integrations

> Указатель. Канон: [`../../plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](../../plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md).  
> **Offline pack:** [`../../plans/OFFLINE_SBER_READY_PACK.md`](../../plans/OFFLINE_SBER_READY_PACK.md).

| Тема | Документ | ADR / scripts |
|---|---|---|
| Узлы (Jetson SoR) | plan §2 | [ADR-0007](../../decisions/ADR-0007-node-model-jetson-sor-cloud-edge.md) |
| LLM Giga first | [GIGACHAT.md](GIGACHAT.md) | [ADR-0008](../../decisions/ADR-0008-llm-routing-giga-first.md) |
| Backup SSD/HDD/S3 | plan §7 | [ADR-0009](../../decisions/ADR-0009-backup-ssd-hdd-s3.md) |
| Cloud.ru FM / S3 / IAM | [CLOUD_RU.md](CLOUD_RU.md) | `scripts/sber/cloudru_*`, `restic_s3_cloudru_example.sh` |
| GitVerse mirror | [GITVERSE.md](GITVERSE.md) | `scripts/sber/gitverse_mirror_push.sh` |
| Кабинеты (ручной) | [CONSOLE_CHECKLIST.md](CONSOLE_CHECKLIST.md) | owner only |
| Cutover on device | [DEPLOY_FULL_SBER_CUTOVER.md](../../plans/DEPLOY_FULL_SBER_CUTOVER.md) | after «деплой» |
| Env snippet | `config/sber.env.snippet` | `scripts/sber/merge_sber_snippet.sh` |
| API inventory | [CLOUD_RU_GITVERSE_PUBLIC_PROBE](../../plans/CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md) | — |

## Status 2026-09-07

| | |
|---|---|
| Offline pack + gateway code | ✅ in repo |
| GitVerse mirror | ✅ HTTPS; main=master aligned |
| Cloud.ru SA + FM key | ✅ auth; inference ⏳ balance/grant |
| Jetson cutover | ⏳ after «деплой» |

## Quick offline check

```bash
bash scripts/sber/preflight_sber_pack.sh
python -m pytest tests/llm_gateway/test_sber_routing.py -q
```

**Secrets:** never in git. Device `config/.env` + password manager only.
