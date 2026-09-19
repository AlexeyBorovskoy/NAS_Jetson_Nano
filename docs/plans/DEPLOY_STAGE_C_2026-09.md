# Выкат этапа C на Jetson / Stage C device rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка; при расхождении — стоп.
> 🇬🇧 Owner-triggered only. EN summary at the end.
>
> Что едет: C1/C2 (авторизация и роли NAS API, без `CORS *`), C4/C5 (бюджет fail-closed,
> откат на DeepSeek только на временных сбоях), C6 (gate до фото, лимит 10 МБ),
> C7 (без токенов комнат в коде), C8 (шлюз не от root), C10 (Portainer — только localhost; rpcbind).
> **Не едет:** C9 (SSH/пароли) — решение владельца, §8. Netdata в LAN — до D5 (записано в тесте).

**Простой:** шлюз и API ~10 с каждый; Portainer ~5 с. Nextcloud/Immich/Samba не трогаются.

## 1. Правило №13 — ДО
Как в `DEPLOY_STAGE_A_2026-09.md` §1.

## 2. Базовая линия
```bash
cd ~/nasa && git rev-parse --short HEAD && git status --short | grep -v "\.bak"
docker ps --format "{{.Names}} {{.Status}}" | sort
curl -s -o /dev/null -w "status без токена: %{http_code}\n" http://127.0.0.1:8099/v1/status   # 200 (до)
ss -tlnH | grep -E ":(9000|9443|111) "
```

## 3. Код и тесты на устройстве
```bash
git pull --ff-only && git rev-parse --short HEAD
for t in tests/unit/test_*.py; do python3 "$t" >/dev/null 2>&1 && echo "ok $t" || echo "FAIL $t"; done
```
(`tests/nas_api`, `tests/llm_gateway` требуют FastAPI — гоняются в CI.)

## 4. Роли владельца
```bash
docker exec -u www-data homecloud_nextcloud php occ user:list     # логины
```
В `config/.env`: `API_OWNERS=<логин владельца>` (администратор Nextcloud — владелец всегда,
от него ходят алерты). `API_CORS_ORIGINS=` оставить пустым.

## 5. Том шлюза → UID 10001 (C8), пересборка шлюза и API
```bash
docker run --rm -v homecloud-llm-gateway_llm_usage:/data alpine:3.19 chown -R 10001:10001 /data
docker compose -f docker/compose/docker-compose.llm-gateway.yml     --env-file config/.env up -d --build
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
docker exec homecloud_llm_gateway id -u                               # 10001
docker exec homecloud_llm_gateway sh -c 'touch /data/.w && rm /data/.w && echo writable'
```

## 6. Проверки
```bash
# C1: без токена — 401; живость — 200; CORS не отдаётся
for p in /v1/status /v1/logs /v1/talk/rooms /v1/talk/bot/status; do
  curl -s -o /dev/null -w "$p %{http_code}\n" http://127.0.0.1:8099$p; done
curl -s -o /dev/null -w "healthcheck %{http_code}\n" http://127.0.0.1:8099/healthcheck
curl -sI -H "Origin: http://evil.example" http://127.0.0.1:8099/healthcheck | grep -ci access-control   # 0
# C2: алерты входят как администратор Nextcloud (владелец) — прогнать и проверить Result
sudo systemctl start nasa-talk-alert.service; systemctl show -p Result nasa-talk-alert.service
# шлюз под новым пользователем пишет учёт
docker exec homecloud_nasa_api python -c "import asyncio; from app.routers import talk_bot; print(asyncio.run(talk_bot._ask_llm('Ответь одним словом: ок','admin')))"
curl -s http://127.0.0.1:8090/v1/usage | head -c 200
```

## 7. Portainer и rpcbind (C10)
```bash
docker compose -f docker/compose/docker-compose.monitoring.yml --env-file config/.env up -d portainer
ss -tlnH | grep -E ":(9000|9443) "                  # только 127.0.0.1
findmnt -t nfs,nfs4 || echo "NFS не используется"   # пусто → rpcbind не нужен
sudo systemctl disable --now rpcbind.service rpcbind.socket
ss -tlnH | grep -c ":111 "                           # 0
```
Portainer теперь: `ssh -L 9443:127.0.0.1:9443 admin@192.168.0.50` → `https://127.0.0.1:9443`.

## 8. C9 — не выполняется без решения владельца
SSH пускает по паролю (`PasswordAuthentication yes`), sudo-пароль совпадает с паролем
администратора Nextcloud. Компрометация Nextcloud-админа = root на Jetson из LAN.
Порядок, если владелец решит: (1) убедиться, что вход по ключу работает с двух машин;
(2) сменить пароль `admin` в Linux на отдельный (менеджер паролей); (3) `PasswordAuthentication no`
в `sshd_config` → `sudo sshd -t` → `sudo systemctl reload ssh` при открытой второй сессии;
(4) скрипты, берущие sudo-пароль из `.env`, перевести на `sudoers` с конкретными командами.

## 9. Правило №13 — ПОСЛЕ, затем откат при необходимости
| Что | Команда |
|---|---|
| код | `git checkout <prev>` → `up -d --build` шлюза и API |
| роли | `API_OWNERS` не мешает откату; CORS вернётся со старым кодом |
| Portainer | `git checkout <prev> -- docker/compose/docker-compose.monitoring.yml` → `up -d portainer` |
| rpcbind | `sudo systemctl enable --now rpcbind.socket rpcbind.service` |

## EN summary
Stage C rollout. Pull the code and run the on-device unit tests. Set `API_OWNERS` (the Nextcloud
admin is always an owner). Chown the gateway volume to UID 10001 and rebuild the gateway and API.
Verify 401 without a token, a public `/healthcheck`, no CORS header, a working alert timer and a
working bot. Rebind Portainer to localhost and disable rpcbind after confirming no NFS mounts.
SSH password login and the shared password (C9) need an owner decision and are not changed here.
