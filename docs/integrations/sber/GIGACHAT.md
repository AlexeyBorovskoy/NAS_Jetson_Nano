# GigaChat (PERS) — NAS integration  
# GigaChat (PERS) — интеграция NAS

## Target config / Целевой конфиг (ADR-0008)

```env
LLM_PROVIDER=gigachat
GIGACHAT_BASE_URL=https://api.giga.chat/v1
GIGACHAT_MODEL=GigaChat-2
GIGACHAT_IMAGE_MODEL=GigaChat-2-Max
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_CA_BUNDLE=/certs/russian_trusted_bundle.pem
GIGACHAT_VERIFY_SSL=true
LLM_PREFER_LOCAL=false
TALK_BOT_LLM_PROVIDER=gigachat
LLM_GIGA_FALLBACK_DEEPSEEK=true
```

## Live facts / Живые факты

🇬🇧 OAuth + TLS bundle OK. Freemium roughly full (Lite/Pro/Max/Ultra buckets).  
🇷🇺 OAuth + TLS bundle OK. Freemium почти полный.

🇬🇧 `GigaChat-2` stable on new host; legacy id `GigaChat` missing/flaky.  
🇷🇺 `GigaChat-2` стабилен; legacy id `GigaChat` нет/flaky.

🇬🇧 Phys persons: **1 concurrent stream** — gateway serializes.  
🇷🇺 Физлица: **1 поток** — шлюз сериализует.

🇬🇧 Jetson cutover 2026-09-08: `/health` provider=gigachat, chat 200.  
🇷🇺 Выкат 2026-09-08: provider=gigachat, chat 200.

## Code / Код

- Gateway: `services/llm-gateway/app/main.py`
- Talk: `TALK_BOT_LLM_PROVIDER` → payload `provider`
- Balance: `GET /v1/provider/gigachat/balance`
- Failover: DeepSeek on Giga 429/502/503 (`fallback_from`)
- Tests: `tests/llm_gateway/test_sber_routing.py`
- Certs: `config/certs/` (public CA, not a secret)

## Do not / Нельзя

🇬🇧 Send family photo albums for analysis (`LLM_ALLOW_IMAGE_ANALYSIS=false`).  
🇷🇺 Не отправлять семейные альбомы на analysis.

🇬🇧 Commit `GIGACHAT_AUTH_KEY`.  
🇷🇺 Не коммитить `GIGACHAT_AUTH_KEY`.
