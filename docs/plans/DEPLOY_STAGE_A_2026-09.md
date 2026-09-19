# Выкат этапа A на Jetson / Stage A device rollout (2026-09)

> 🇷🇺 Только по команде владельца «деплой». Каждый шаг — проверка результата; при расхождении — стоп.
> 🇬🇧 Owner-triggered only ("деплой"). Verify every step; stop on any mismatch. EN summary at the end.
>
> План: `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` §4, задачи A3, A4, A5. Раскладка: `docs/35_HOST_LAYOUT.md`.

## 0. Что приедет на устройство

`git pull` на Jetson принесёт **всё** начиная с `0206261` (HEAD устройства на 2026-09-19), не только этап A:

| Коммит | Что | Эффект на устройстве |
|---|---|---|
| `65b7229` | compose Immich ML для ROG | ничего не запускается само |
| `8ce58e2` | **ADR-0011: safety gate + structured tools `@бобик`** | новое поведение бота — проверить в Talk |
| `d52c11b` + `36c4ced` | шлюз: `save_path`, пресеты, smart routing (**выкл.**), токен, починка чата | пересборка шлюза |
| `9ec1b15` + этот | раскладка хоста; recovery SSD; compose API через переменные | восстановление SSD снова работает |
| `b8f50c9` | CI | — |

Предусловия: CI зелёный на выкатываемом коммите; окно, когда семья может 10–15 мин без `@бобик`.

## 1. Правило №13 — ДО (VPS, только чтение)

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 '
  docker inspect -f "{{.Name}} {{.State.StartedAt}}" amnezia-awg2 amnezia-xray
  docker exec amnezia-awg2 wg show | grep -c "^peer"
  ss -tlnH | awk "{print \$4}" | grep -vE "^(127\.|\[::1\]|172\.)" | sort -u'
```
Записать: StartedAt обоих, число пиров (19 на 2026-09-19), публичные порты.

## 2. Базовая линия Jetson

```bash
ssh admin@192.168.0.50 '
  docker ps --format "{{.Names}} {{.Status}}" | sort
  curl -s http://127.0.0.1:8090/health; echo
  systemctl --failed --no-legend
  ls -lt /mnt/storage/backups/database-dumps | head -3
  cd ~/nasa && git rev-parse --short HEAD && git status --short | grep -v "\.bak"'
```
Ожидается: 13 контейнеров, HEAD `0206261`, изменён только `docker-compose.nas_jetson_nano-api.yml`.

## 3. Страховка

```bash
cd ~/nasa
TS=$(date +%s)
git rev-parse HEAD > /tmp/stageA-prev-head.$TS
git diff > /tmp/stageA-device-local.$TS.patch
cp -p config/.env config/.env.bak.stageA.$TS
chmod 600 config/.env config/.env.bak.stageA.$TS     # было 664 (замер 2026-09-19)
```

## 4. Раскладка в `.env` (заменяет ручную правку compose)

Дописать в `~/nasa/config/.env` (значения без пробелов — правило №8):
```env
NAS_LOG_DIR=/var/log/nasa-monitor
NAS_CONF_DIR=/etc/nasa-monitor
NAS_SBIN_PREFIX=/usr/local/sbin/nasa
LLM_SMART_ROUTING=false
LLM_GATEWAY_SERVICE_TOKEN=
```
Проверка синтаксиса: `( set -euo pipefail; source config/.env >/dev/null ) && echo OK`.

## 5. Обновить код

```bash
git checkout -- docker/compose/docker-compose.nas_jetson_nano-api.yml   # правка теперь в .env
git pull --ff-only
git rev-parse --short HEAD
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env config \
  | grep -A1 "source: /var/log\|source: /etc\|send-report"
```
Ожидается: источники томов — `/var/log/nasa-monitor`, `/etc/nasa-monitor`, `/usr/local/sbin/nasa-send-report-telegram.sh`.

## 6. Библиотека раскладки и восстановление SSD

```bash
sudo bash scripts/lib/install_layout.sh          # /etc/nas-layout.env: NAS_PREFIX=nasa, NAS_PROJECT_DIR=/home/admin/nasa
sudo systemctl start nasa-ssd-recovery.service   # SSD смонтирован, Docker работает → «nothing to do»
systemctl show -p Result nasa-ssd-recovery.service   # Result=success
tail -5 /var/log/nasa-monitor/ssd-recovery.log       # "Preflight OK" … "Recovery complete"
```

## 7. Пересборка шлюза и API (код запекается в образ — нужен `--build`)

```bash
docker compose -f docker/compose/docker-compose.llm-gateway.yml     --env-file config/.env up -d --build
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d --build
docker ps --format "{{.Names}} {{.Status}}" | grep -E "gateway|nasa_api"
docker inspect -f "{{.Name}} {{.State.StartedAt}}" homecloud_llm_gateway homecloud_nasa_api   # время = сейчас
curl -s http://127.0.0.1:8090/health   # smart_routing_enabled:false, service_token_enforced:false
```
Smoke в Talk: `@бобик скажи одним словом: ок` → ответ; `нас статус` → ответ Phase A.

## 8. Включить сервисный токен (отдельно, после успеха п. 7)

```bash
T=$(openssl rand -hex 32)
sed -i "s/^LLM_GATEWAY_SERVICE_TOKEN=.*/LLM_GATEWAY_SERVICE_TOKEN=$T/" config/.env; unset T
# сначала вызывающий, потом шлюз; docker restart .env НЕ перечитывает — только up -d
docker compose -f docker/compose/docker-compose.nas_jetson_nano-api.yml --env-file config/.env up -d
docker compose -f docker/compose/docker-compose.llm-gateway.yml     --env-file config/.env up -d
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8090/v1/chat \
  -H "Content-Type: application/json" -d '{"prompt":"x"}'          # 401
curl -s http://127.0.0.1:8090/health | grep -o '"service_token_enforced":[a-z]*'   # true
```
Smoke в Talk ещё раз: `@бобик` отвечает.

## 9. Правило №13 — ПОСЛЕ

Повторить п. 1: StartedAt `amnezia-*` не изменились, пиров не меньше, публичные порты те же.

## 10. Откат

| Что откатить | Команда |
|---|---|
| только токен | `LLM_GATEWAY_SERVICE_TOKEN=` в `.env` → `up -d` шлюза, затем API |
| весь этап | `git checkout $(cat /tmp/stageA-prev-head.*)` → `git apply /tmp/stageA-device-local.*.patch` → `cp config/.env.bak.stageA.* config/.env` → `up -d --build` обоих → `sudo rm -r /etc/nas-layout.env /usr/local/lib/nas_jetson_nano` |

После отката recovery SSD снова сломан — это состояние «до», не новое.

## EN summary
Owner-triggered rollout of Stage A. First check the VPS: Amnezia untouched and peer count recorded.
Take a Jetson baseline and back up the HEAD, the local diff and `.env` (tighten `.env` to 600). Move
the device-specific compose paths into `.env` (`NAS_LOG_DIR`, `NAS_CONF_DIR`, `NAS_SBIN_PREFIX`).
Discard the local compose edit and `git pull`. Install the layout library, verify SSD recovery
(`Result=success`), then rebuild the gateway and API with `--build`. Smoke-test `@бобик`. Enable the
service token separately: API first, then the gateway, using `up -d` rather than `restart`. Finish with
the VPS check again. The rollback table covers the token only or the whole stage.
