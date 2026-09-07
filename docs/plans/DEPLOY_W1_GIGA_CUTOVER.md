# Deploy runbook — W1 Giga cutover (device)

> **Do not run until owner says «деплой».**  
> Amnezia: do not touch. Only Jetson containers + `.env`.  
> **Full pack (W1+W2+optional W3):** [`DEPLOY_FULL_SBER_CUTOVER.md`](DEPLOY_FULL_SBER_CUTOVER.md)  
> **Offline readiness:** [`OFFLINE_SBER_READY_PACK.md`](OFFLINE_SBER_READY_PACK.md)

## 1. What changes on device

In `~/nasa/config/.env` (or current path):

```env
LLM_PROVIDER=gigachat
GIGACHAT_BASE_URL=https://api.giga.chat/v1
GIGACHAT_MODEL=GigaChat-2
GIGACHAT_IMAGE_MODEL=GigaChat-2-Max
LLM_PREFER_LOCAL=false
TALK_BOT_LLM_PROVIDER=gigachat
TALK_BOT_LLM_TIMEOUT=150
```

Keep existing `GIGACHAT_AUTH_KEY` if already set.

## 2. Pull code (after git push from workstation)

```bash
cd ~/nasa   # or nas_jetson_nano path
git pull
```

## 3. Recreate gateway + API (code baked in image)

```bash
cd ~/nasa
docker compose -f docker/compose/docker-compose.llm-gateway.yml --env-file config/.env up -d --build
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
```

Note: container name stays `homecloud_nasa_api` / `homecloud_llm_gateway`.

## 4. Verify

```bash
curl -s http://127.0.0.1:8090/health
# expect provider gigachat or providers.gigachat true, prefer_local false

curl -s http://127.0.0.1:8090/v1/chat -H 'Content-Type: application/json' \
  -d '{"prompt":"Ответь одним словом: ок","provider":"gigachat","user":"admin"}'
```

Talk: `@бобик` ping in family room.

## 5. Rollback

```env
LLM_PROVIDER=deepseek
# optional restore GIGACHAT_BASE_URL legacy
```

```bash
docker compose ... up -d --force-recreate
```

## 6. After deploy — mark plan

Update `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` progress: W1.1–1.3 ✅.
