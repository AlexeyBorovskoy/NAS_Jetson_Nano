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

---

## Карта API Container Apps и Jobs (2026-09-20, проверено)

> 🇷🇺 Источник путей — исходный код официально рекомендованного Cloud.ru MCP-сервера
> `github.com/Nick1994209/cloudru-containerapps-mcp` (на него ссылается туториал Cloud.ru
> `container-apps__vibecode-django-photo-app-mcp-server`). Документация на сайте —
> одностраничное приложение, её тело инструментам не отдаётся; код оказался надёжнее.
> Ключевые пути **подтверждены живым запросом** с ключа владельца.

### 🔴 Jobs живут в **`/v2`**, и версии перемешаны внутри одного сервиса

Это и было причиной «503 на всех путях»: перебор шёл по `/v1`, где заданий нет вовсе.

| Ресурс | Действие | Путь | Статус |
|---|---|---|---|
| Containers | список | `GET /v1/containers?projectId=` | ✅ 200 (замер) |
| Containers | список | `GET /v2/containers?projectId=&pageSize=` | ✅ 200 (замер) |
| Containers | создать | `POST /v2/containers/` | из кода |
| Containers | пуск/стоп | `POST /v2/containers/{name}:start` / `:stop` | из кода |
| Containers | логи | `GET /v2/containers/{name}/logs` | из кода |
| **Jobs** | **список** | **`GET /v2/jobs?projectId=&pageSize=`** | ✅ **200 (замер)** |
| **Jobs** | **создать** | **`POST /v2/jobs`** | из кода |
| **Jobs** | **запустить** | **`POST /v2/jobs/{name}:execute`** | из кода |
| **Jobs** | **статус запусков** | **`GET /v2/jobs/{name}/executions?projectId=&pageSize=`** | из кода |
| Jobs | изменить / удалить | `PATCH` / `DELETE /v2/jobs/{name}?projectId=` | из кода |

Несуществующий путь в `/v2` отвечает честным **404** (`/v2/registries` — замер), в отличие
от `/v1`, где всё неизвестное превращается в `503`.

### Что важно знать до проектирования

| Вопрос | Ответ | Источник |
|---|---|---|
| **Встроенное расписание (cron)** | **НЕТ.** Ни страницы в документации, ни поля `schedule`/`cron`/`trigger` в структурах API. Задание запускается только вызовом `:execute` | оглавление `guides__container-jobs` + структуры `CreateJobRequest`/`PatchJobRequest` |
| ⚠️ Ложный след | «Cron Job» у Cloud.ru есть, но это **другой продукт** — Cloud Container Engine (управляемый Kubernetes). К Container Jobs и бесплатному тарифу отношения не имеет | `cloud.ru/docs/cce/ug/topics/guides__workload-cron-jobs-create` |
| Максимум одного запуска | **3600 с** (1 час) | `concepts__jobs` |
| Одновременных запусков одного задания | не более 5 | `guides__job-run` |
| Заданий на организацию | не более 10 | `overview__limitations` |
| Минимальные ресурсы | **0.1 vCPU / 256 Ми** (шаги: 0.1/256, 0.2/512, 0.3/768, 0.5/1024, 1/4096) | код `ParseCPU` |
| Откуда образ | Artifact Registry Cloud.ru — своего проекта или публичных реестров **внутри Cloud.ru**. Прямой Docker Hub / ghcr.io документацией не подтверждён | `concepts__container`, `guides__job-create` |
| Переменные и секреты | `template.containers[].env` = `[{"name","value","type"}]`; значение может быть ссылкой на секрет из сервиса Secret Management. Точный enum для `type` не найден | `concepts__runtime` |
| Статусы задания | `created → publishing → ready`, далее `suspended*`, `deleting/deleted`, `error` | `concepts__jobs-status` |
| Статусы запуска | `creating → running → succeeded / failed / canceled` | там же |
| Логи конкретного запуска Job | отдельного метода в клиенте нет (у Containers — есть). Основной сигнал — `executionStatus` | код `jobs.go` |
| SSH внутрь | только для Container **Service**, не для Job: свой образ с `openssh-server`, `ssh -i key <name>.<project>@ssh.containers.cloud.ru -p 2222` | `guides__ssh-access` |

### Следствие для D3 (внешний сторож)

Расписания внутри сервиса нет, поэтому задание обязан кто-то будить снаружи. Это меняет
исходный замысел D3: Cloud.ru перестаёт быть независимым наблюдателем, если будить его
будет тот же VPS, за которым он в том числе должен присматривать. Решение по схеме
запуска — за владельцем; варианты и цена каждого разобраны при постановке D3.

Минимальная конфигурация сторожа (0.1 vCPU, 256 Ми, запуск раз в 15 минут по минуте)
расходует около 0.1 vCPU·ч и 0.25 ГБ·ч в месяц — это единицы процентов бесплатного
лимита Jobs (5 vCPU·ч и 10 ГБ·ч).

---

### EN summary (API map)

Container **Jobs live under `/v2`**, not `/v1` — that alone explains the earlier "503 on every
path": the probing was done in v1, which has no jobs at all. Confirmed live with the owner's
key: `GET /v2/jobs?projectId=…` returns 200. Unknown paths under `/v2` answer a proper 404,
while `/v1` turns everything unknown into 503. Jobs are created with `POST /v2/jobs`, run with
`POST /v2/jobs/{name}:execute`, and their outcome is read from
`GET /v2/jobs/{name}/executions`. Paths come from the source of the MCP server Cloud.ru's own
tutorial recommends; the docs site is a JS application whose body tools cannot retrieve.

**There is no built-in schedule**: no cron page in the docs and no `schedule`/`cron`/`trigger`
field in the API structures. Cloud.ru's "Cron Job" belongs to a different product (managed
Kubernetes) and does not apply here. So a job must be woken from outside — which changes the
D3 design, since Cloud.ru stops being an independent observer if the waking is done by the very
VPS it is meant to watch. Limits: one execution ≤ 3600 s, 5 concurrent runs per job, 10 jobs per
organisation, smallest size 0.1 vCPU / 256 Mi. Images come from Cloud.ru's Artifact Registry;
pulling straight from Docker Hub is not documented. A watchdog at the smallest size running a
minute every 15 minutes costs a few percent of the free Jobs tier.

---

## Биллинг, Object Storage и Foundation Models (2026-09-20, проверено)

> 🇷🇺 Пути API взяты из официальных OpenAPI-файлов Cloud.ru
> (`cloud.ru/docs/api/specs/billing/ug/_specs/swagger.yaml` и `swagger2.yaml` — отдаются
> без авторизации; сам сайт документации — SPA, тело статей инструментам не даётся).
> Ключевые вызовы **подтверждены живым запросом** с ключа владельца.

### 1. Потребление: рабочий рецепт

🔴 **`agreement_id` обязателен.** Именно из-за него был `400`: с корректными датами, но без
договора запрос всё равно отвергается. Проверено обоими способами.

```
# 1. договор
GET https://organization.api.cloud.ru/v3/agreements
    -> 200 {"agreements":[{"id":"<uuid>","status":"AGREEMENT_STATUS_ACTIVE",...}]}

# 2. потребление - три обязательных параметра
GET https://organization.api.cloud.ru/v1/consumption
    ?agreement_id=<uuid>&start_date=2026-09-01T00:00:00Z&end_date=2026-09-20T23:59:59Z
    -> 200 {"consumptions":[{sku, servname, resource_id, usedate, amount, cost, unit, usefact}]}
```

Замер 2026-09-20: на аккаунте владельца видно реальное потребление GigaChat-2-Max за сентябрь.
Есть также `/v2/consumption` (дополнительно требует `page_filter.page_size`) и
`/v1/consumption/static` (у владельца пуст). Для алерта достаточно v1.

`agreement_id` в скриптах **не хардкодить** — брать из `/v3/agreements`, тогда смена договора
ничего не сломает. Значения идентификаторов в репозиторий не кладём, только путь получения.

### 2. 🔴 Остаток бесплатного тарифа API НЕ отдаёт

Ни одного поля «сколько осталось» в ответе `consumption` нет; отдельного метода баланса в
документации биллинга тоже нет — в оглавлении справочника ровно два метода, v1 и v2
consumption. «Порог баланса» в личном кабинете — про автосписание с карты у физлиц, к
бесплатному тарифу отношения не имеет.

**Следствие для алерта расходов:** лимиты надо держать у себя и вычитать из них потребление
за текущий месяц. Известные лимиты (официальные страницы, 2026-09-20):

| Сервис | Бесплатно в месяц |
|---|---|
| Container Apps Services | 25 vCPU·ч + 50 ГБ·ч |
| Container Apps Jobs | 5 vCPU·ч + 10 ГБ·ч |
| Object Storage | 15 ГБ хранения · 10 ТБ исходящего трафика · 100 000 операций записи · 1 000 000 чтений |

Всё — на организацию целиком, остаток не переносится на следующий месяц.

### 3. Object Storage — закрывает P0 проекта бесплатно

| Что | Значение |
|---|---|
| Endpoint | `https://s3.cloud.ru`, регион `ru-central-1` |
| Протокол | обычный S3 — `restic` и `aws-cli` работают штатно |
| Создание бакета | `aws s3 mb s3://<bucket> --endpoint-url https://s3.cloud.ru` |
| Классы хранения | `STANDARD`, `COLD`, `ICE`, `SINGLE` (заголовок `X-Amz-Storage-Class`) |
| Версионирование | поддерживается полностью |
| Lifecycle | `Expiration` и `NoncurrentVersionExpiration` — да; **`Transition` (автосмена класса) заявлен, но НЕ работает** |

🔴 **S3-ключи — третий, отдельный секрет**, не IAM-ключ и не ключ Foundation Models:

- `AWS Access Key ID` = **`<tenant_id>:<key_id>`**, `AWS Secret Access Key` = Key Secret;
- `tenant_id` — из личного кабинета: Хранение данных → Object Storage → Параметры работы с API;
- ключ выдаётся только через личный кабинет, API для генерации нет.

**Вероятная причина прошлой ошибки `CreateBucket AccessDenied`** (сентябрь): не хватало роли.
Полные права на операции хранилища дают `s3e.admin`, роль с действием `s3e.tenant.edit`, либо
«Администратор проекта». Документация не привязывает код ошибки к роли прямо — перед следующей
попыткой проверить роль у того аккаунта, которым выпущен ключ.

**Экономика для задачи «вторая копия фотографий Immich вне дома» (~9 ГБ):**
9 ГБ меньше 15 ГБ бесплатного хранения, разовая заливка 9 ГБ несопоставимо меньше 10 ТБ
бесплатного трафика, операций на порядки меньше бесплатных.
**Сценарий укладывается в бесплатный тариф целиком.**
⚠️ Версионирование без `NoncurrentVersionExpiration` тихо накопит платный объём — старые
версии тарифицируются как обычное хранение.

Цены сверх бесплатного (официальный тариф, договор `260619` от 29.06.2026, без НДС):
STANDARD 1.5075 ₽/ГБ·мес, SINGLE 0.93, COLD 0.8025, ICE 0.40125; исходящий трафик сверх
10 ТБ — 0.96 ₽/ГБ. У COLD и ICE объект тарифицируется не менее чем 128 КБ.

### 4. Foundation Models

- База: `https://foundation-models.api.cloud.ru/v1`, OpenAI-совместимый.
- В официальной спецификации **ровно два метода**: `GET /v1/models` и `POST /v1/chat/completions`.
  **Метода баланса или квоты нет.**
- `CLOUDRU_FM_API_KEY` — **отдельный ключ сервисного аккаунта** с областью «Foundation Models»,
  выпускается в личном кабинете. Это не IAM-ключ и не S3-ключ.
- Записанная в проекте ошибка `chat 402` объясняется, скорее всего, окончанием акционной
  бесплатной раздачи моделей, а не исчерпанием тарифной квоты: фиксированного free tier у FM
  в документации нет, бесплатные периоды были акциями без формальной даты окончания.

**Итого три независимых секрета Cloud.ru**, у каждого своя область и своё место выдачи:
IAM `keyId`/`secret` (есть, бессрочный, в Credential Manager), S3 Key ID/Secret (ещё нет),
FM API key (есть). Хранить раздельными записями, не пытаться переиспользовать один.

---

### EN summary (billing, storage, models)

Consumption needs **three** mandatory parameters, and the missing one was `agreement_id`, not the
dates: `GET https://organization.api.cloud.ru/v1/consumption?agreement_id=<uuid>&start_date=...&end_date=...`
returns 200, verified on the owner account, which already shows GigaChat-2-Max usage. The
agreement itself comes from `GET /v3/agreements`. **No API returns the remaining free-tier
allowance** — neither a field nor an endpoint exists, so an alert must hold the documented limits
itself and subtract measured consumption.

Object Storage speaks plain S3 at `https://s3.cloud.ru` (region `ru-central-1`), so `restic` works
unchanged. Its free tier — **15 GB of storage, 10 TB egress, 100k write and 1M read operations per
month, permanently** — covers the project P0 entirely: the ~9 GB Immich library fits with room to
spare, making an off-site copy of the family photos free. Storage keys are a **separate** secret
from the IAM key: Access Key ID is `<tenant_id>:<key_id>`, issued only through the console, and
bucket creation needs the `s3e.admin` / `s3e.tenant.edit` / project-admin role — the likely cause
of the earlier `CreateBucket AccessDenied`. Lifecycle `Transition` is advertised but does not work,
and versioning without `NoncurrentVersionExpiration` silently accrues billable storage.

Foundation Models exposes exactly two methods and no balance endpoint; its key is a third,
separate service-account secret.

---

## Object Storage: доступ получен и проверен (2026-09-20)

### 🔑 Отдельный S3-ключ НЕ понадобился

Проверено замером: **существующий IAM-ключ владельца работает как ключ Object Storage**,
если подставить его в документированной форме. Новый ключ в кабинете выпускать не нужно.

| Форма `AWS Access Key ID` | Результат |
|---|---|
| `<tenant_id>:<keyId>` | ✅ **работает** |
| `<tenant_id>.<keyId>` | ✅ работает (точка вместо двоеточия) |
| просто `<keyId>` | ⛔ `403 InvalidAccessKeyId` |

`AWS Secret Access Key` — тот же `secret`, что и у IAM-ключа.
Это уточняет прежнюю запись «S3-ключи — третий отдельный секрет»: **отдельный ключ можно
выпустить, но обязательным он не является**; достаточно префикса `tenant_id`.

### Параметры подключения (из консоли, Object Storage → Параметры работы с API)

| Параметр | Значение |
|---|---|
| Endpoint | `https://s3.cloud.ru` |
| Регион | `ru-central-1` |
| Имя сервиса | `s3` |
| Подпись | AWS Signature v4 |
| `tenant_id` | в консоли; в git не кладём |

### Корзина проекта

Создана владельцем 2026-09-20: **`nas-immich-offsite`**, класс **стандартный**
(бесплатные 15 ГБ действуют только для него), версионирование выключено.

### Проверка доступа — полный цикл, а не только чтение

Замер 2026-09-20 (`boto3`, подпись v4):

```
ListBuckets  : OK, корзин 1 — nas-immich-offsite
HeadBucket   : OK
PutObject    : OK (37 байт)
GetObject    : OK, содержимое совпало по sha256
ListObjects  : OK
DeleteObject : OK (тестовый объект удалён)
```

Права на запись подтверждены, тестовый объект за собой убран. Прошлая ошибка
`CreateBucket AccessDenied` не воспроизводится — роль текущей учётной записи достаточна.

⚠️ Что ещё не сделано: репозиторий `restic` в этой корзине не создан, фотографии Immich
не залиты, восстановление из облака не проверялось. До этого момента **off-site копии
фотографий по-прежнему нет** — есть только подтверждённый доступ к месту, где она будет.

---

### EN summary (storage access verified)

No separate storage key was needed: the owner's existing **IAM key works as an Object Storage
key** when the Access Key ID is given as `<tenant_id>:<keyId>` (the dotted form works too, the
bare key ID returns `403 InvalidAccessKeyId`). Endpoint `https://s3.cloud.ru`, region
`ru-central-1`, AWS Signature v4. The project bucket `nas-immich-offsite` was created in the
standard class (the free 15 GB apply to that class only) with versioning off.

Access was verified as a full round trip rather than a read: ListBuckets, HeadBucket, PutObject,
GetObject with a sha256 comparison, ListObjects and DeleteObject all succeeded, and the test
object was removed afterwards. The earlier `CreateBucket AccessDenied` does not reproduce.

Still missing: no restic repository exists in the bucket, no photos are uploaded and no restore
has been exercised — so there is still **no off-site copy**, only a verified place for one.
