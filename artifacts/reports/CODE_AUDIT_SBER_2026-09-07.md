# Code audit + Sber implementation status — 2026-09-07

> Jetson **offline** — audit and code only; **no device deploy**.

## Scope

| Area | Path | Verdict |
|---|---|---|
| LLM Gateway | `services/llm-gateway/app/main.py` | Extended for Sber-era |
| Talk bot | `services/nas_jetson_nano-api/.../talk_bot.py` | Provider field OK |
| Compose / env | `docker/compose/*`, `config/.env.example` | Aligned |
| Backup Immich HDD | `scripts/backup/immich_hdd_second_copy.sh` + systemd | Git ready, not installed |
| Cloud.ru live | keys on owner PC | Not wired on Jetson (off) |
| Tests | `tests/llm_gateway/test_sber_routing.py` | Added |

## Gaps found (before this change)

1. Default provider still partially deepseek in old docs paths — fixed in code defaults.
2. No Giga→DeepSeek failover on 429/5xx.
3. No `/balance` proxy.
4. No Cloud.ru FM provider.
5. No unit tests for routing.
6. Device `.env` not cut over (Jetson off / deploy gate).

## Implemented in this session (git)

| Feature | Detail |
|---|---|
| `provider=cloudru` | OpenAI-compatible FM chat via `CLOUDRU_FM_*` |
| `GET /v1/provider/gigachat/balance` | Upstream balance proxy |
| `LLM_GIGA_FALLBACK_DEEPSEEK` | default true; ChatResponse.fallback_from |
| Health | cloudru flag, base URL, model, fallback flag |
| Env/compose | Cloud.ru + fallback vars |
| Tests | mock routing / failover / balance 503 |

## Still needs device (when Jetson on + «деплой»)

1. W1 cutover runbook `DEPLOY_W1_GIGA_CUTOVER.md`
2. W2 enable immich-hdd-copy timer
3. Optional: set `CLOUDRU_FM_API_KEY` from FM static key (not IAM Key Secret alone unless exchanged)
4. GitVerse push
5. Live balance cron/alert

## Risk notes

- Cloud.ru spend: keep key empty until owner OK.
- Failover burns DeepSeek quota — intended.
- Image analysis still gated false.
- Amnezia untouched.
