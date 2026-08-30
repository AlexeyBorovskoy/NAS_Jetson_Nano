# Зависимости и версии / Dependencies and versions

**Дата / Date:** 2026-08-30, устройство `admin@192.168.0.50` + Windows-репозиторий.

## 1. Платформа / Platform

| Компонент | Версия | Статус |
|---|---|---|
| Модель | NVIDIA Jetson Nano Developer Kit | потолок платформы / platform ceiling |
| L4T | R32.7.1 | последняя для Nano / last for Nano |
| JetPack | 4.6.1 | последняя для Nano (JetPack 5+/6 требуют Xavier/Orin) |
| Ubuntu | 18.04.6 LTS (bionic) | **EOL стандартной поддержки апрель 2023**, ESM не подтверждён |
| Ядро / Kernel | 4.9.253-tegra | привязано к L4T |
| Python (системный / system) | 3.6.9 | **EOL декабрь 2021** |
| CUDA | 10.2.460 | не используется проектом, см. `AI_STACK.md` |
| cuDNN | 8.2.1.32 (csv-манифест) | не используется |
| TensorRT | 8.2.1.8 | не используется |
| Docker Engine | 20.10.7-0ubuntu5~18.04.3 | устарела относительно mainline (27.x), но функционально достаточна |

## 2. Python-зависимости сервисов / Service Python dependencies

| Сервис | Пиннинг | Версии |
|---|---|---|
| `services/backup-api` | **pinned (`==`)** | fastapi 0.115.12, uvicorn 0.34.2, pydantic 2.11.5, python-multipart 0.0.20 |
| `services/llm-gateway` | **pinned (`==`)** | fastapi 0.115.12, uvicorn 0.34.2, openai 1.82.1, pydantic 2.11.5, httpx 0.28.1 |
| `services/nas_jetson_nano-api` (устройство: `nasa-api`) | **НЕ pinned (`>=`)** | fastapi≥0.111, uvicorn[standard]≥0.29, pydantic-settings≥2, httpx≥0.27, python-jose[cryptography]≥3.3, passlib[bcrypt]≥1.7 |

🟠 **Находка**: три сервиса одного проекта, две разные политики закрепления версий без видимой причины. `nasa-api` — единственный непиннингованный, причём включает библиотеки аутентификации (`python-jose`, `passlib`). При пересборке (`--build`, обязательной после правки кода по CLAUDE.md) версии могут «уехать» без предупреждения.

Идентично на устройстве и в Windows-репо (сверено дословно).

## 3. Docker images — теги / image tags

| Образ | Тег | Риск |
|---|---|---|
| `netdata/netdata` | `latest` | плавающий — breaking change без контроля версии |
| `portainer/portainer-ce` | `latest` | плавающий |
| `crazymax/samba` | `latest` | плавающий |
| `homecloud-llm-gateway-*`, `homecloud-nasa-api-*` | `latest` (локальная сборка) | пересборка меняет содержимое без версионирования |
| `IMMICH_VERSION` | default `release` (плавающий, если не задан явно в `.env`) | не проверено, задан ли явно на устройстве |
| `postgres` | `16-alpine` | pinned по мажорной версии — приемлемо |
| `redis` | `7-alpine` | pinned по мажорной версии — приемлемо |
| `nextcloud` | `apache` (без версии) | плавающий |
| `tensorchord/pgvecto-rs` | `pg16-v0.3.0` | точный пин — хорошо |

## 4. Мёртвый/устаревший конфиг / Dead or stale configuration

`.env.example` содержит переменные `DUCKDNS_DOMAIN`/`DUCKDNS_TOKEN` (строки 165-166), но по факту актуальный DNS — **dynv6** (`borovskoy.dynv6.net`), не DuckDNS. Не риск сам по себе — источник путаницы при онбординге.

## 5. Docker-образы — объём / image footprint

99 образов всего, из них большинство `<none>:<none>` (dangling) — накопились от практики `--build` при каждой правке `llm-gateway`/`nasa-api`. Порядка 13 dangling-образов по 193–218 МБ каждый (~2.5–3 ГБ неиспользуемого места). Крупнейшие активные образы: `nextcloud:apache` 1.46GB, `ghcr.io/immich-app/immich-server:release` 1.3GB, `netdata/netdata:latest` 852MB, `tensorchord/pgvecto-rs` 708MB.

Точный объём `/var/lib/docker` **не измерен** — каталог принадлежит root, `admin` не может читать подкаталоги без sudo (см. `UNKNOWNS.md`).

## 6. Reproducibility по компонентам / Reproducibility by component

См. `AUDIT_REPORT.md` §23 — итоговая оценка **C (существенные неизвестные)**, главные причины: непиннингованный `nasa-api`, плавающие теги мониторинга/Samba/Nextcloud, реальные значения `.env` существуют только на устройстве без redacted-снапшота.
