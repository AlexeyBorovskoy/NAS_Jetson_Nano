# Cloud.ru Evolution — NAS notes

## Auth (docs)

```text
POST https://auth.iam.cloud.ru/auth/system/openid/token
grant_type=access_key&client_id=<Key ID>&client_secret=<Key Secret>
→ Authorization: Bearer <token>
```

FM chat/list: `https://foundation-models.api.cloud.ru/v1` + Bearer (SA API key scoped to Foundation Models).  
S3: `https://s3.cloud.ru`, SigV4, Access Key ID format `tenant_id:key_id`.

## Inventory

See [`../../plans/CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md`](../../plans/CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md).

- `GET /v1/models` **public** catalog (~98 models) ≠ free inference.
- VM/PG/CA/AR/RAG: auth required; do not probe API roots `/`.

## NAS use (plan waves)

| Wave | Use |
|---|---|
| W3 | FM adapter behind gateway — **`provider=cloudru`** in code (2026-09-07); needs `CLOUDRU_FM_API_KEY` on device |
| W3 | S3 restic encrypted dumps (L2 off-site, ADR-0009) |
| later | optional Container Apps watchdog / free_tier VM |

### Gateway env

```env
CLOUDRU_FM_API_KEY=          # FM static SA key (Bearer), not IAM pair alone
CLOUDRU_FM_BASE_URL=https://foundation-models.api.cloud.ru/v1
CLOUDRU_FM_MODEL=ai-sage/GigaChat3-10B-A1.8B
```

```bash
curl -s http://127.0.0.1:8090/v1/chat -H 'Content-Type: application/json' \
  -d '{"prompt":"ping","provider":"cloudru","user":"admin"}'
```

## Live status (2026-09-08)

| Item | State |
|---|---|
| Org / customer | `d7322872-213e-4331-a522-8ac88ae15282` |
| Project | `10dd738e-6389-4b75-9570-852df04c0165` («Новый Проект» / home-nas) |
| SA | `home-nas-api` (`8f07c1f7-202a-4bfa-a66d-2550f2b2fa11`) |
| SA role on project | `platform.project.admin` (bound) |
| IAM access_key → token | OK |
| FM API key | issued; **`Authorization: Bearer`** (not `Api-Key`) |
| FM chat | **OK** (200) — Bearer key; `ai-sage/GigaChat3-10B-A1.8B` + `GigaChat/GigaChat-2-Max` after balance top-up |
| S3 buckets | **0** — 2026-09-08 re-probe: Bearer ListBuckets empty; CreateBucket `nas-home-restic` → `AccessDenied`; SigV4 tenant prefixes → `NoSuchTenant`. **Blocker:** console **tenant_id** + Object Storage service + S3 keys `tenant_id:key_id`. restic L2 **not** run. See `S3_AND_BUDGET_CHECKLIST.md` |

Probe notes: `docs/plans/AUTH_PROBE_*.md`, `AUTH_PROBE_FM_KEY_SMOKE_2026-09-07.md`.

## Access keys (2026-09-20)

IAM access key pair for SA `home-nas-api` received from the owner: **no expiry** (владелец сделал бессрочными).
Verified 2026-09-20: `grant_type=access_key` → HTTP 200, `token_len=1295`, `expires_in=3600`.
Stored **only** in Windows Credential Manager (`nas-cloudru-iam`, user = Key ID) and in the owner's local file
outside git (`kaggle/` is git-ignored). Never in the repository, never in argv, never printed.
Unblocks: D3 watchdog job in Container Apps, E5 spend alert, E6 Immich ML spike.

## Do not

- Primary host Nextcloud/Immich in Cloud.ru.
- Managed RAG over family photos.
- Put Key ID/Secret / FM key in git.

---

## Проверенный доступ к платформе (2026-09-20) / Verified platform access

> 🇷🇺 Всё ниже — **замер**, а не документация: каждая строка получена реальным запросом
> 2026-09-20 с бессрочного ключа владельца. EN summary в конце раздела.

### 1. Авторизация (работает)

```
POST https://iam.api.cloud.ru/api/v1/auth/token
Content-Type: application/json
{"keyId": "<KeyID>", "secret": "<Secret>"}
→ 200, access_token (~1287 симв.), expires_in=3600
```

Ключи владельца **бессрочные**, лежат в Windows Credential Manager, ресурс `nas-cloudru-iam`
(username = KeyID, password = Secret). В репозиторий и на устройство не попадают.

🔴 **Ответ авторизации содержит `id_token`, а в нём — почта и телефон владельца.**
Печатать тело ответа целиком нельзя никогда; выводить только длину токена и `expires_in`.
Фильтровать все поля, оканчивающиеся на `_token`, а не только `access_token`.

### 2. Container Apps

| Что | Значение |
|---|---|
| Базовый URL | `https://containers.api.cloud.ru` |
| ⛔ Неверно (имени не существует) | `containerapps.api.cloud.ru` — `curl` rc=6, not resolved |
| Обязательный параметр | **`projectId=<uuid>` в query у каждого запроса** |
| Рабочий путь | `GET /v1/containers?projectId=<uuid>` → **200**, `{"data": [], "total": "0"}` |
| Где взять `projectId` | адресная строка `console.cloud.ru` (идентификаторы — вне git) |

🔴 **Главная ловушка платформы: этот API отвечает `503` вместо `404` и вместо `400`.**
Проверено перебором: без `projectId` рабочий путь `/v1/containers` даёт `503`; с `projectId`
двенадцать путей (`jobs`, `container-jobs`, `tasks`, `executions`, `registries`, `secrets`,
`volumes`, `domains` и др.) дают `503`, и только `containers` — `200`. Без токена те же пути
дают `403 RBAC: access denied`, то есть авторизация проходит раньше маршрутизации.
**Вывод: `503` от Cloud.ru НЕ означает «сервис недоступен». Он означает «я не понял запрос».**
Повтор с задержками 0/5/15/30/60/90 с ничего не меняет — проверено, 12 попыток подряд.

### 3. Биллинг и потребление

| Что | Значение |
|---|---|
| Базовый URL | `https://organization.api.cloud.ru` |
| ⛔ Неверно | `billing.api.cloud.ru` — хост живой, но это не API потребления |
| Путь | `GET /v1/consumption` — без токена `403`, с токеном **`400`** (не хватает обязательных параметров) |
| Документация | https://cloud.ru/docs/billing/ug/topics/api-ref_start, v2 — `api_consumptionv2` |

### 4. Бесплатный тариф Container Apps (подтверждён официальной страницей 2026-09-20)

Источник: https://cloud.ru/docs/container-apps-evolution/ug/topics/overview__free-tier

- **Container Services:** 50 ГБ·ч RAM + 25 vCPU·ч в месяц.
- **Container Jobs:** 10 ГБ·ч RAM + 5 vCPU·ч в месяц.
- Лимиты — **на всю организацию**, не на контейнер; остаток **не переносится** на следующий месяц.
- Container Jobs — не более **10 штук** на организацию.

Практическое следствие: постоянно работающий контейнер съедает 25 vCPU·ч примерно за сутки.
Для сторожа (D3) годится только задание, просыпающееся по расписанию, а не сервис.

### 5. Отзыв собственного диагноза (как найдено)

**Было записано** (`docs/research/IMMICH_ML_CLOUDRU_TRIAL_2026-09-20.md`, утро 2026-09-20):
«Container Apps API систематически возвращает 503 на всех путях `/v1/`, сервис недоступен,
пробный прогон невозможен». На этом основании были заморожены D3 и E6.

**Факт:** диагноз неверен. Во-первых, запросы шли на **несуществующее имя хоста**
`containerapps.api.cloud.ru`. Во-вторых, `503` у этой платформы — ответ по умолчанию на
непонятный запрос, а не признак аварии. С правильным хостом и обязательным `projectId`
API отвечает `200`.

**Как найдено:** владелец спросил, во что упираются D3 и E6, раз все допуски выданы.
Перепроверка заняла один запрос: `curl` к `containerapps.api.cloud.ru` вернул rc=6
(имя не резолвится) — то есть утренний «503» физически не мог прийти оттуда.

**Урок — повторение уже записанного в `CLAUDE.md`:** отрицательный результат не называет
причину, он называет только себя. Симптом «сервис отвечает 503» был объяснён поломкой
на стороне провайдера прежде, чем была проверена входная величина — существует ли вообще
адрес, по которому стучались. В том же разборе было зафиксировано наблюдение, которое
прямо указывало на ошибку: **«503 даёт даже заведомо неверный путь»**. Наблюдение верное,
вывод из него сделан противоположный правильному.

---

### EN summary (verified access, 2026-09-20)

Auth works: `POST https://iam.api.cloud.ru/api/v1/auth/token` with `{"keyId","secret"}` returns
an hour-long `access_token`; the owner's keys never expire and live in Windows Credential Manager
(`nas-cloudru-iam`). The auth response also carries an `id_token` holding the owner's e-mail and
phone — never print that body.

Container Apps live at `https://containers.api.cloud.ru` (the name `containerapps.api.cloud.ru`
does not exist at all) and **require `projectId` as a query parameter on every call**:
`GET /v1/containers?projectId=<uuid>` returns 200. The platform's key trap is that it answers
**503 instead of 404 or 400** — a missing `projectId` or an unknown route both yield 503, so a
503 here means "I did not understand the request", not "the service is down". Retrying with
backoff changes nothing. Consumption/billing lives at `https://organization.api.cloud.ru`
(`GET /v1/consumption`, 400 until the required parameters are supplied), not at
`billing.api.cloud.ru`. Free tier, confirmed on the official page: Services 50 GB·h + 25 vCPU·h
per month, Jobs 10 GB·h + 5 vCPU·h, org-wide, non-transferable, max 10 jobs.

An earlier diagnosis in this repository — "the Container Apps API returns 503 everywhere, the
service is unavailable" — is **withdrawn**: it was measured against a hostname that does not
resolve, and it misread the platform's default error code. The evidence that would have caught
it was already in that same document: even a deliberately wrong path returned 503.
