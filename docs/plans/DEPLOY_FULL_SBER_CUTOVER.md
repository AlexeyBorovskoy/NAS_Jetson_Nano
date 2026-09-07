# Полный cutover Сбер-эры на Jetson (когда online + «деплой»)

> Amnezia **не трогать**. Только Jetson git + compose + timers.  
> Offline pack: [`OFFLINE_SBER_READY_PACK.md`](OFFLINE_SBER_READY_PACK.md).

## 0. Preconditions

- [ ] Jetson powered, tunnel or LAN SSH works  
- [ ] `git` on device can pull (or scp pack)  
- [ ] `GIGACHAT_AUTH_KEY` known / already in `.env`  
- [ ] DeepSeek key still valid (fallback)  
- [ ] HDD `/mnt/hdd2tb` mounted if doing W2  

## 1. Code

```bash
cd ~/nasa   # adjust path
git pull
bash scripts/quality/preflight.sh --quick || true
```

## 2. Env merge

```bash
# dry-run first
DRY_RUN=1 bash scripts/sber/merge_sber_snippet.sh ~/nasa/config/.env
bash scripts/sber/merge_sber_snippet.sh ~/nasa/config/.env

# ensure secrets present (manual edit if empty):
#   GIGACHAT_AUTH_KEY=...
#   DEEPSEEK_API_KEY=...
# optional: CLOUDRU_FM_API_KEY=...
```

Validate source:

```bash
( set -euo pipefail; set -a; source ~/nasa/config/.env; set +a; echo OK )
```

## 3. Rebuild gateway + Talk API

```bash
cd ~/nasa
docker compose -f docker/compose/docker-compose.llm-gateway.yml --env-file config/.env up -d --build
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
```

## 4. Verify LLM

```bash
bash scripts/sber/verify_gateway.sh http://127.0.0.1:8090
```

Expect: `provider=gigachat`, `prefer_local=false`, chat 200, balance JSON if key set.

Talk: `@бобик` one word answer.

## 5. Immich → HDD (W2)

```bash
sudo bash scripts/sber/install_immich_hdd_timer.sh
DRY_RUN=1 bash scripts/backup/immich_hdd_second_copy.sh
# then real run once off-peak:
# bash scripts/backup/immich_hdd_second_copy.sh
```

## 6. Giga balance timer (optional)

```bash
sudo cp systemd/nas_jetson_nano-giga-balance.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nas_jetson_nano-giga-balance.timer
```

## 7. Cloud.ru S3 (optional L2)

Only after console bucket + keys:

```bash
# see scripts/backup/restic_s3_cloudru_example.sh
# INIT=1 first time; DRY_RUN=1; then dumps only
```

## 8. Rollback

```env
LLM_PROVIDER=deepseek
TALK_BOT_LLM_PROVIDER=deepseek
```

```bash
docker compose -f docker/compose/docker-compose.llm-gateway.yml --env-file config/.env up -d --force-recreate
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --force-recreate
```

## 9. Close the loop

- [ ] Update `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` progress W1/W2 ✅  
- [ ] `coord.py` fact to `work` if useful  
- [ ] Amnezia peer count unchanged (if VPS was not touched — n/a)  
