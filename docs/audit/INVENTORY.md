# Инвентаризация проекта / Project inventory

**Дата замера / Measured:** 2026-08-30. **Метод / Method:** read-only, без sudo, без root-файлов и секретов (`.env`, `certs/`) / read-only, no sudo, no secret files read. Источники — Windows-репозиторий `NAS_Jetson_Nano` (`origin` → `github.com/AlexeyBorovskoy/NAS_Jetson_Nano.git`, HEAD `7707d0e`) и устройство `admin@192.168.0.50` (`~/nasa`, `origin` → `Nasa_home.git`, HEAD `0f9fd0f`).

## 1. Два состояния одного проекта / Two states of one project

🇷🇺 Windows-репозиторий и устройство **не являются одним и тем же деплоем** на момент аудита — это заранее известное и отдельно исправляемое расхождение (см. `CLAUDE.md`, «Расхождение git ↔ устройство»). Инвентаризация ниже покрывает обе стороны там, где они отличаются.

🇬🇧 The Windows repository and the live device are **not the same deployment** at audit time — a known, separately tracked divergence (see `CLAUDE.md`). The inventory below covers both sides where they differ.

| | Windows-репо / Windows repo | Устройство / Device |
|---|---|---|
| Remote | `NAS_Jetson_Nano.git` | `Nasa_home.git` |
| HEAD | `7707d0e` | `0f9fd0f` |
| Контейнеры / Containers | `nas_jetson_nano-*` (compose-имена) | `homecloud_*` (реально работают) |
| API-сервис / API service | `services/nas_jetson_nano-api/` | `services/nasa-api/` |
| systemd | `nas_jetson_nano-*` | `nasa-*` |
| `git status --short` | `?? docs/audit/` (чисто) | 33 строки: 13 modified + 20 untracked `.bak.*` |

## 2. Docker Compose (8 файлов, Windows-репо `docker/compose/`) / Docker Compose files

`docker-compose.coturn.yml`, `docker-compose.immich.yml`, `docker-compose.llm-gateway.yml`, `docker-compose.monitoring.yml`, `docker-compose.nas_jetson_nano-api.yml`, `docker-compose.nextcloud.yml`, `docker-compose.samba.yml`, `docker-compose.stage1.yml` (последний — устаревший монолитный слепок, вытеснен раздельными файлами, использование в скриптах не подтверждено — см. `UNKNOWNS.md` / the last one is a legacy monolithic snapshot superseded by the split files; whether it's still referenced anywhere was not confirmed).

## 3. Dockerfile (3)

`services/backup-api/Dockerfile`, `services/llm-gateway/Dockerfile`, `services/nas_jetson_nano-api/Dockerfile`.

## 4. Python-проекты (3, все FastAPI) / Python projects (all FastAPI)

`services/backup-api`, `services/llm-gateway`, `services/nas_jetson_nano-api` (на устройстве — `services/nasa-api`).

## 5. Shell-скрипты / Shell scripts

37 файлов под `scripts/` (backup, diagnostics, maintenance, monitoring, network, quality, security, setup, storage).

## 6. Systemd units

25 файлов под `systemd/` в Windows-репо (`nas_jetson_nano-*` + `jetson-nas-*` — последние не переименовывались, см. `docs/plans/tranquil-wandering-truffle.md`). На устройстве — 11 живых юнитов `nasa-*`, подробности в `RUNTIME.md`.

## 7. Cron

`crontab -l` для `admin` на устройстве → пусто. Все периодические задачи — через systemd timers, не cron.

## 8. Мессенджер-интеграции / Messaging integrations

- `nas_jetson_nano-daily-report-telegram` (устройство: `nasa-daily-report-telegram`) — одностороння отправка отчёта в Telegram.
- Talk-бот `@бобик`/`нас` — внутри Nextcloud Talk (OCS API), не Telegram.

## 9. Redis

Два инстанса `redis:7-alpine` — по одному на Immich и на Nextcloud (кэш/сессии, не отдельный сервис проекта). Оба защищены паролем (подтверждено `NOAUTH` при неавторизованном запросе).

## 10. nginx / reverse proxy

Живёт на **VPS**, не на Jetson — контейнер `nasa_nginx`, up 7 недель на момент замера. Проксирует туннельные порты (8080/2283/8090/8099/8091 и др.) на localhost VPS.

## 11. VPN

AmneziaVPN на VPS: `amnezia-xray` (up 3 нед) и `amnezia-awg2` (up 7 нед) активны; `amnezia-openvpn`/`amnezia-wireguard` — `Exited (143)` 3 недели назад (остановлены, не удалены). 19 пиров WireGuard.

## 12. Мониторинг / Monitoring

Netdata, Uptime Kuma, Portainer (на Jetson) + Beszel Agent (systemd-юнит, не контейнер) → Beszel Hub (контейнер на VPS).

## 13. Backup/deploy/install-скрипты / Backup, deploy, install scripts

`scripts/backup/*`, `scripts/setup/install_*`, `scripts/storage/deploy_usb_fix.sh` и др.

## 14. Документация / Documentation

`docs/00`–`docs/33`+, `docs/plans/`, `docs/quality/` — двуязычность требуется правилом №15 CLAUDE.md; фактическое покрытие — см. `AUDIT_REPORT.md` §31.

## 15. Найдено, но НЕ развёрнуто / Present in repo but NOT deployed

🇷🇺 `docker-compose.coturn.yml` и `configs/coturn/turnserver.conf` описывают план «coturn на VPS», но на VPS образ `coturn` **ни разу не скачивался** (`docker images`/`docker ps -a` — пусто). Возможное следствие: видеозвонки Nextcloud Talk снаружи LAN не проходят TURN-релей за симметричным NAT. Не проверено живым звонком — гипотеза, не подтверждённый сбой.

🇬🇧 `docker-compose.coturn.yml` and `configs/coturn/turnserver.conf` describe a "coturn on VPS" plan, but the `coturn` image has **never been pulled** on the VPS. Possible consequence: Nextcloud Talk video calls outside the LAN may fail to traverse symmetric NAT without a TURN relay. Not verified with a live call — a hypothesis, not a confirmed failure.

## 16. AI/ML-инвентарь / AI/ML inventory

Ноль моделей проекта (`.onnx`/`.engine`/`.trt`), ноль ссылок на GStreamer/DeepStream/RTSP в коде проекта. Найдены только штатные демо-файлы JetPack SDK (`/usr/src/tensorrt/data/...`), не относящиеся к проекту. Подробности и метод поиска — `AI_STACK.md`.

## 17. Тесты / Tests

17 файлов под `tests/` (Windows-репо): `network/`, `service/`, `storage/`, `backup/`, `android/`, `load/` (k6), `goss/`, плюс `tests/unit/test_talk_alert_selftest.py` — единственный настоящий unit-тест. Подробности — `AUDIT_REPORT.md` §25 (Tests).
