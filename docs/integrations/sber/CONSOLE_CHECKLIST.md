# Чеклист кабинетов Сбер / Cloud.ru / GitVerse (offline prep)

> Делает **владелец** в браузере. Агент не логинится и не хранит секреты в git.  
> После выдачи ключей — только device `config/.env` / password manager.

## A. GigaChat (developers.sber.ru) — PERS

- [ ] Аккаунт физлица, проект API
- [ ] Scope **GIGACHAT_API_PERS**
- [ ] Client ID + Secret → `GIGACHAT_AUTH_KEY = base64(id:secret)`
- [ ] Freemium: Lite/Pro/Max/Ultra — зафиксировать остаток после cutover (`/balance`)
- [ ] Модель чата: **GigaChat-2**; картинки: **GigaChat-2-Max**
- [ ] Base URL: **https://api.giga.chat** (не legacy devices host)
- [ ] TLS: на Jetson уже `config/certs/russian_trusted_bundle.pem`

## B. Cloud.ru Evolution

### B1. IAM access key (Key ID + Key Secret)

- [ ] Сервисный аккаунт в нужном **проекте**
- [ ] Роль не ниже нужной для FM/S3 (не раздавать лишнее)
- [ ] Ключ доступа (Key ID / Key Secret), TTL по политике
- [ ] Проверка token exchange (скрипт `scripts/sber/cloudru_iam_token_example.sh`)

### B2. Foundation Models static API key

- [ ] В SA → API-ключ с сервисом **Foundation Models**
- [ ] Сохранить **Key Secret** один раз → `CLOUDRU_FM_API_KEY` на Jetson
- [ ] Модель по умолчанию: `ai-sage/GigaChat3-10B-A1.8B` (internal) или из каталога
- [ ] Не слать семейные фото в FM

### B3. Object Storage (L2 off-site)

- [ ] Object Storage visible under **Хранение данных** for this Evolution project  
- [ ] **tenant_id** copied from Object Storage → Параметры работы с API (≠ customer/project id)  
- [ ] Bucket name recorded (e.g. `nas-home-restic`) — API create blocked until tenant_id  
- [ ] S3 ключ: Access Key ID = `tenant_id:key_id`  
- [ ] Endpoint `https://s3.cloud.ru`, region `ru-central-1`
- [ ] restic password file **вне git**
- [ ] Скрипт-пример: `scripts/backup/restic_s3_cloudru_example.sh` — сначала только DB dumps

### B4. Не делать сейчас

- [ ] Managed K8s / PG для Nextcloud
- [ ] Managed RAG над Immich
- [ ] Публичный 0.0.0.0 на VM без SG

## C. GitVerse

- [x] Репо `Alexey_Borovskoy/NAS_HOME` существует (HTTPS mirror OK)
- [ ] **UI:** https://gitverse.ru/settings/keys — add `gitverse_ed25519.pub` (API cannot register SSH)
- [ ] SSH: `ssh -T -i ~/.ssh/gitverse_ed25519 -o IdentitiesOnly=yes git@gitverse.ru`
- [ ] `bash scripts/sber/gitverse_mirror_push.sh` после preflight
- [x] Remote name **`gitverse`**, не pushurl на origin

## D. После «деплой» на Jetson

См. [`../../plans/DEPLOY_FULL_SBER_CUTOVER.md`](../../plans/DEPLOY_FULL_SBER_CUTOVER.md).
