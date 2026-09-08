# Device `.env` checklist — Jetson cutover (no secrets)  
# Чеклист device `.env` — cutover Jetson (без секретов)

> 🇬🇧 Fill values **on the device only**. Never commit real keys.  
> 🇷🇺 Значения только на устройстве. Реальные ключи в git не коммитить.  
> Runbook: [`DEPLOY_FULL_SBER_CUTOVER.md`](DEPLOY_FULL_SBER_CUTOVER.md)  
> Snippet: `config/sber.env.snippet` + `scripts/sber/merge_sber_snippet.sh`

## Sources (owner password manager)

| Variable | Source | Notes |
|---|---|---|
| `GIGACHAT_AUTH_KEY` | developers.sber.ru PERS **or** local gitignored `gigachat/` store | base64(client_id:client_secret) |
| `DEEPSEEK_API_KEY` | DeepSeek console | fallback |
| `CLOUDRU_FM_API_KEY` | Cloud.ru SA API key «Foundation Models» | Bearer; from console / local store |
| `CLOUDRU` IAM Key ID/Secret | optional admin scripts only | **not** required for FM chat if FM key set |
| GitVerse token | gitverse settings | workstation push only, not Jetson |

## Must set on Jetson for W1

```env
LLM_PROVIDER=gigachat
LLM_PREFER_LOCAL=false
LLM_GIGA_FALLBACK_DEEPSEEK=true

GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_BASE_URL=https://api.giga.chat/v1
GIGACHAT_MODEL=GigaChat-2
GIGACHAT_IMAGE_MODEL=GigaChat-2-Max
GIGACHAT_CA_BUNDLE=/certs/russian_trusted_bundle.pem
GIGACHAT_VERIFY_SSL=true
GIGACHAT_AUTH_KEY=<from manager>

TALK_BOT_LLM_PROVIDER=gigachat
TALK_BOT_LLM_TIMEOUT=150

DEEPSEEK_API_KEY=<from manager>
DEEPSEEK_MODEL=deepseek-chat
```

## Optional W3 (after FM money OK — already verified 2026-09-07)

```env
CLOUDRU_FM_API_KEY=<from manager>
CLOUDRU_FM_BASE_URL=https://foundation-models.api.cloud.ru/v1
CLOUDRU_FM_MODEL=GigaChat/GigaChat-2-Max
CLOUDRU_FM_MAX_TOKENS=2048
```

Do **not** set family default to `cloudru` (cost). Keep `LLM_PROVIDER=gigachat`.

## After merge — validate

```bash
( set -euo pipefail; set -a; source config/.env; set +a; echo OK )
bash scripts/sber/verify_gateway.sh
```

## W2 Immich HDD (no cloud keys)

```bash
sudo bash scripts/sber/install_immich_hdd_timer.sh
DRY_RUN=1 bash scripts/backup/immich_hdd_second_copy.sh
```
