# Технический аудит проекта NAS_Jetson_Nano

**Дата анализа:** 2026-09-18
**Репозиторий:** `AlexeyBorovskoy/NAS_Jetson_Nano`
**Объект анализа:** публичная ветка `main`
**Статус:** статический аудит Git + документации, без deployment и без изменений production

---

# 1. Executive summary

1. `NAS_Jetson_Nano` фактически уже не просто NAS, а **домашняя семейная edge-платформа**: Nextcloud + Immich + Samba + резервирование + LLM Gateway + Talk-бот `@бобик` + мониторинг + защищённый удалённый доступ. Это соответствует принятой архитектуре Jetson как SoR.
2. Архитектурное разделение в целом правильное: **Jetson = домашние данные и сервисы; VPS = network edge; Vostro/ROG = не production NAS**.
3. Reverse SSH выбран обоснованно для CGNAT и позволяет не вмешиваться в Amnezia. Профиль `nas_jetson_nano-lan / 192.168.0.50` является защищённым архитектурным инвариантом.
4. Главный текущий технический риск находится не в Jetson Nano как старом железе, а в **LAN attack surface управляющих сервисов**: `llm-gateway:8090` и NAS API `:8099`.
5. В LLM Gateway отсутствует собственная аутентификация, порт публикуется на host, а image API принимает произвольный `save_path`. При включённой генерации изображений это позволяет писать в произвольные доступные пути контейнера, включая persistent `/data`. Это **P0 до следующего deployment**.
6. NAS API аутентифицирует пользователя через Nextcloud, но практически не выполняет авторизацию по роли: любой валидный пользователь получает JWT и затем может попасть к операциям restart/backup. Часть диагностических endpoints вообще не требует JWT. Это второй **P0**.
7. Backup L1 для Immich уже работает и подтверждён checkpoint от 12.09.2026, однако L2 Cloud.ru S3 остаётся `BLOCKED`, а DB dumps находятся на том же SSD. Поэтому защита от отказа диска/пожара/кражи ещё не замкнута.
8. ADR-0011 уже реализован в коде как safety gate + structured read-only tools, что является сильной стороной проекта. Однако обработка изображения выполняется раньше gate, поэтому policy enforcement пока не единообразен.
9. Документация стала отставать от реализации: `README`, `CLAUDE.md`, backup docs, CHANGELOG и network inventory содержат несколько разных временных состояний проекта, включая уже запрещённые исторические операции. Это создаёт риск прежде всего для IDE/LLM-агентов.
10. Рекомендуемый следующий этап — **не добавлять новые функции**, а провести короткий hardening sprint: gateway auth/path confinement, API RBAC, fail-closed budget, backup guards, тест restore, repo privacy cleanup и синхронизацию канона. После этого можно безопасно развивать Immich ML, семейный UX и материал для второй статьи на Habr.

---

# 2. Что это за проект

## 2.1. Назначение

Проект представляет собой локальную домашнюю информационную платформу для семьи с централизованным хранением данных и минимальной зависимостью от внешних облачных сервисов.

Основные функции:

* семейное файловое облако — Nextcloud;
* фотоархив — Immich;
* файловый доступ LAN — Samba;
* резервирование данных;
* LLM Gateway для контролируемого доступа к GigaChat/DeepSeek/Cloud.ru;
* семейный Talk-бот `@бобик`;
* мониторинг состояния NAS;
* административный FastAPI API;
* reverse SSH через VPS для доступа за CGNAT;
* экспериментальные возможности Immich ML вне Jetson.

README прямо описывает Jetson как домашний сервер с Nextcloud, Immich, Samba, LLM Gateway, Talk bot, alerts и management API.

## 2.2. Пользователи

Фактически имеются четыре класса субъектов:

| Субъект           | Назначение                                 | Уровень доверия                              |
| ----------------- | ------------------------------------------ | -------------------------------------------- |
| Владелец          | эксплуатация, backup, recovery, deployment | максимальный                                 |
| Члены семьи       | Nextcloud, Immich, Talk/@бобик             | доверенный пользователь, но не администратор |
| Системные сервисы | Docker, timers, API, gateway               | machine trust                                |
| Внешние LLM/cloud | GigaChat, DeepSeek, Cloud.ru               | внешняя недоверенная граница                 |

Критическая проблема текущей реализации: для NAS API граница между **«член семьи прошёл Nextcloud authentication»** и **«оператор имеет административные полномочия»** практически отсутствует.

---

# 3. Архитектура as-is

```text
                             INTERNET
                                 |
                  +--------------+---------------+
                  |                              |
            GigaChat / DeepSeek             VPS / AEZA
            Cloud.ru FM / S3             network edge
                  ^                       nginx/reverse SSH
                  |                       Amnezia — НЕ ТРОГАТЬ
                  |                              ^
          redaction / budgets                     |
                  |                         reverse SSH
                  |                              |
+-----------------+---------- HOME LAN ----------+----------------+
|                           192.168.0.0/24                         |
|                                                                  |
|                  Jetson Nano 4 GB                                |
|                  192.168.0.50                                    |
|                  System of Record                                |
|                                                                  |
|  +------------+  +---------+  +--------+  +----------------+     |
|  | Nextcloud  |  | Immich  |  | Samba  |  | LLM Gateway   |     |
|  +------------+  +---------+  +--------+  | :8090          |     |
|         |              |                   +----------------+     |
|         |              |                          ^               |
|         |              |                          |               |
|         |       family photos                     |               |
|         |              |                    Talk @бобик           |
|         |              v                          |               |
|         |       SSD ext4 live              NAS API :8099          |
|         |              |                          |               |
|         |              +---- L1 ----> HDD NTFS   |               |
|         |                             Immich copy  |               |
|         |                                          v               |
|         +------------------------------------ Docker socket        |
|                                                                  |
+------------------------------------------------------------------+

ROG/workstation       -> development / optional Immich ML pilot
Vostro 192.168.75.153 -> corporate bastion via VPS:10222,
                         NOT NAS production node
```

Архитектура соответствует ADR-0007: Jetson отвечает за SoR, VPS — за network edge, рабочие станции и Vostro исключены из production-контура.

## 3.1. Данные

### Live data

Основное рабочее хранилище — отдельный SSD `/mnt/storage`, ext4. HDD `/mnt/hdd2tb` остаётся NTFS-носителем с существующими данными и не должен форматироваться или превращаться в новый основной storage. Это явно зафиксировано storage design.

### Backup

Текущая модель:

```text
Immich live / SSD
        |
        +---- L1 ---> HDD Jetson
        |
        +---- L2 ---> Cloud.ru S3     [BLOCKED]

PostgreSQL dumps
        |
        +---------> SSD Jetson
        |
        +---------> legacy Vostro     [не целевая архитектура]
```

ADR-0009 корректно фиксирует важное ограничение: L1 на HDD в том же доме не является защитой от потери всего помещения/устройства.

Checkpoint от 12.09.2026 подтверждает свежую вторую копию Immich объёмом около 12.8 GB и работающие backup jobs.

## 3.2. Сетевая модель

Зафиксированы:

* CGNAT;
* LAN `192.168.0.0/24`;
* Jetson `192.168.0.50`;
* reverse SSH Jetson → VPS;
* сервисные порты не должны публиковаться непосредственно наружу;
* Amnezia является отдельным критичным production-сервисом примерно для 25 клиентов и не должна модифицироваться в рамках NAS.

По inventory LAN остаётся практически не сегментированной. Следовательно, host-published `8090` и `8099` следует считать не Internet exposure, а **дополнительной доверенной поверхностью внутри домашней сети**.

---

# 4. Фактическое состояние vs заявленное

| Область                  | Заявлено                                                         | Фактически обнаружено                                                                                                    | Оценка                             |
| ------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| Состояние проекта        | README — состояние на 08.09                                      | checkpoint имеется от 12.09                                                                                              | README устарел                     |
| Backup Immich            | `docs/12_BACKUP_RESTORE.md` ещё говорит, что HDD job не deployed | checkpoint подтверждает рабочий L1 backup                                                                                | документация устарела              |
| Secrets                  | README: secrets не находятся в git                               | в публичных `CLAUDE.md`/историческом CHANGELOG присутствуют реальные Talk room identifiers и персональные идентификаторы | нарушение собственной политики     |
| Bilingual docs           | README утверждает двуязычность документации                      | аудит 08.09 обнаружил порядка 33 пар из ~188 файлов                                                                      | фактически требование не выполнено |
| VPS                      | README использует Frankfurt                                      | актуальный network inventory указывает Vienna/AEZA                                                                       | doc drift                          |
| Storage                  | начало storage design создаёт впечатление HDD-primary            | раздел as-built определяет SSD как working storage, HDD как существующий NTFS archive                                    | опасная неоднозначность            |
| Backup target            | старые документы сохраняют Vostro в цепочке                      | ADR-0007/0009 выводят Vostro из target architecture                                                                      | legacy                             |
| LLM                      | старые CLAUDE sections содержат local-model сценарии             | ADR-0007/0008: GigaChat-first, DeepSeek fallback, local LLM Jetson не Stage 1                                            | legacy instructions                |
| Gateway fallback         | ADR-0008: fallback при 429/5xx                                   | реализация преобразует ряд upstream errors в 502, после чего они становятся основанием для fallback                      | policy/code mismatch               |
| ADR-0011                 | safety gate должен предшествовать опасным действиям              | текстовый Talk path проходит gate, image path вызывается раньше                                                          | неполное enforcement               |
| API container monitoring | ожидается `homecloud_nasa_api`                                   | compose задаёт другое имя, при этом expected-list содержит ещё третий вариант                                            | вероятный ложный alert             |
| Gate switches            | `.env.example` содержит safety flags                             | compose NAS API их явно не передаёт                                                                                      | config contract mismatch           |
| CHANGELOG                | верхняя запись 08.09                                             | существенные изменения сделаны 11–12.09                                                                                  | CHANGELOG отстаёт                  |
| Network current state    | верх inventory показывает EC220 + Jetson 1 Gb/s                  | ниже остаётся пункт, будто Deco уже заменил router и Jetson упал до 100 Mb/s                                             | внутреннее противоречие            |

Подтверждение расхождений: README и актуальный канон.
Backup status.
Bilingual audit.
Gateway routing.
Compose/API configuration.

---

# 5. Gaps / risks register

Приоритеты:

* **P0** — исправить до следующего deployment;
* **P1** — ближайший hardening sprint;
* **P2** — план 1–2 месяца;
* **P3** — документационный/эксплуатационный hygiene.

| ID  | Категория  | Gap / improvement                                                                                      | Evidence                                                                           | Зачем                                                                  | Effort      | Risk сейчас      | Priority  | Owner                 |
| --- | ---------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ----------- | ---------------- | --------- | --------------------- |
| G01 | Security   | Убрать либо жёстко ограничить `save_path` image API                                                    | `services/llm-gateway/app/main.py`, image finish path                              | исключить arbitrary write внутри контейнера/persistent volume          | M           | High             | **P0**    | deploy — да           |
| G02 | Security   | Ввести service authentication для LLM Gateway                                                          | `docker/compose/docker-compose.llm-gateway.yml:8090:8090`; chat/image API без auth | LAN-клиент сейчас способен потреблять LLM quota                        | M           | High             | **P0**    | deploy — да           |
| G03 | Security   | Реализовать authorization/RBAC NAS API отдельно от Nextcloud authentication                            | `services/nas_jetson_nano-api` auth/actions                                        | член семьи не должен автоматически становиться NAS operator            | M           | High             | **P0**    | policy — да           |
| G04 | Security   | Закрыть auth'ом `/logs`, `/metrics`, `/containers`, `/report/now`, Talk status                         | API routers                                                                        | исключить information disclosure и unauth actions                      | S/M         | High             | **P0**    | deploy — да           |
| G05 | Secrets    | Удалить реальные room identifiers, family identifiers, device IDs из текущего HEAD; проверить rotation | `CLAUDE.md`, CHANGELOG, network inventory                                          | соблюсти AGENTS и policy «no secrets/personal data in git»             | S           | High             | **P0**    | rotation/history — да |
| G06 | LLM        | Budget accounting сделать действительно fail-closed и атомарным                                        | `_load_usage`, `_save_usage`, `_check_budget`                                      | ошибка файла сейчас способна фактически сбросить учёт                  | M           | Med/High         | **P1**    | нет                   |
| G07 | LLM        | Не fallback'ить GigaChat 401/403/4xx в DeepSeek                                                        | Giga client error mapping + fallback handler                                       | не передавать prompt другому external provider из-за auth/config error | S/M         | High             | **P1**    | нет                   |
| G08 | @бобик     | Safety gate должен охватывать image path до любого обращения к gateway                                 | `talk_bot.py` image branch раньше gate                                             | единая ADR-0011 policy boundary                                        | S           | Medium           | **P1**    | нет                   |
| G09 | @бобик     | Ограничить размер Talk attachments до загрузки в память                                                | `r.content`, API memory limit                                                      | предотвратить OOM/DoS контейнера                                       | S           | Medium           | **P1**    | нет                   |
| G10 | Backup     | Завершить L2 offsite backup                                                                            | ADR-0009 / canon: S3 `BLOCKED tenant_id`                                           | L1 не защищает от полной утраты площадки                               | M           | High impact      | **P1**    | **да**                |
| G11 | Backup     | Провести текущий restore drill в disposable environment                                                | `docs/12_BACKUP_RESTORE.md` последний зафиксированный DB restore 09.08             | backup без регулярно проверенного restore недостаточен                 | M           | High impact      | **P1**    | prod cleanup — да     |
| G12 | Backup     | Добавить mountpoint/UUID guard непосредственно в Immich backup script                                  | script проверяет каталог, systemd — настоящий mount                                | ручной запуск должен быть так же безопасен, как timer                  | S           | Medium           | **P1**    | нет                   |
| G13 | Backup     | Согласовать `BACKUP_KEEP_LAST` и `BACKUP_RETENTION_*`; убрать fragile sourcing всего `.env`            | backup script + `.env.example`                                                     | уже имеется история отказа из-за значения `.env` с пробелом            | S/M         | Medium           | **P1**    | нет                   |
| G14 | Compose    | Исправить container-name mismatch в мониторинге                                                        | `homecloud_nasa_api` vs expected name                                              | устранить ложные alarms                                                | S           | Medium           | **P1**    | deploy — да           |
| G15 | Compose    | Явно прокинуть safety gate switches из env                                                             | compose NAS API vs `.env.example`                                                  | documented rollback/config должен реально работать                     | S           | Medium           | **P1**    | deploy — да           |
| G16 | Containers | Запускать gateway/API не от root, где возможно read-only filesystem                                    | оба Dockerfile не содержат `USER`                                                  | уменьшить blast radius уязвимости приложения                           | M           | Medium           | **P1**    | deploy — да           |
| G17 | Host OS    | Зафиксировать реальное состояние JetPack/L4T/Ubuntu/ESM                                                | bootstrap указывает JetPack 4.6.1 generation                                       | Ubuntu 18.04 вышел из standard support                                 | S read-only | Medium           | **P1/P2** | проверка — да         |
| G18 | API        | Зафиксировать зависимости NAS API                                                                      | `requirements.txt` использует `>=`                                                 | воспроизводимость build и снижение dependency drift                    | S           | Medium           | **P2**    | нет                   |
| G19 | Immich ML  | Не делать ML обязательным для семейного UX; Cloud.ru — только после privacy risk acceptance            | ADR-0010                                                                           | thumbnail/frame покидают дом                                           | M           | Privacy          | **P2**    | **да**                |
| G20 | CI         | Добавить policy/security tests и branch protection                                                     | audit 08.09: branch protection отсутствовал                                        | запретить regression hard rules                                        | M           | Medium           | **P2**    | GitHub setting — да   |
| G21 | Docs       | Разделить CURRENT/RUNBOOK и HISTORICAL в CLAUDE/docs                                                   | CLAUDE содержит устаревший `wg set`/local LLM material                             | агент не должен выполнить историческую инструкцию как текущую          | S/M         | High operational | **P1**    | нет                   |
| G22 | Docs       | Обновить README/CHANGELOG/checkpoint index                                                             | изменения после 08.09 не отражены в верхних документах                             | единый source of truth                                                 | S           | Low              | **P2**    | нет                   |
| G23 | Network    | Не считать host ports LAN-trusted только потому, что они закрыты с Internet                            | inventory: LAN не сегментирован                                                    | zero-trust-lite внутри дома                                            | M           | Medium           | **P2**    | router changes — да   |
| G24 | Docs       | Убрать реальные MAC/service tag из public inventory                                                    | `docs/19_NETWORK_INVENTORY.md`                                                     | документ сам классифицирует такие идентификаторы как private           | S           | Low/Med          | **P1**    | нет                   |

### G01 — arbitrary `save_path`

В image API клиент передаёт `save_path`; далее gateway создаёт родительские каталоги и записывает туда результат. Ограничения на заранее определённый output root не обнаружено.

Это не означает произвольную запись на весь host Jetson: запись происходит в файловой системе контейнера и доступных ему volumes. Но контейнер работает без `USER`, имеет persistent `/data`, поэтому дефект достаточно серьёзный для P0.

Рекомендуемая модель:

```text
API client
   |
   +-- binary/base64 result returned to caller

или

requested file name
   |
   +--> sanitize
   +--> resolve()
   +--> verify relative_to(IMAGE_OUTPUT_ROOT)
   +--> fixed non-root writable directory
```

Наиболее безопасный вариант — вообще исключить клиентский абсолютный `save_path` из публичного HTTP contract.

### G02 — gateway authentication

Compose публикует:

```yaml
ports:
  - "8090:8090"
```

т.е. без привязки к `127.0.0.1` или отдельному internal network.

Одновременно `/v1/chat` и image endpoints не имеют собственного authentication middleware.

Важно: доказательств, что `8090` открыт непосредственно в Internet, нет. Network inventory, наоборот, говорит о закрытом внешнем perimeter. Проблема относится прежде всего к **неразделённому LAN**.

### G03/G04 — authentication ≠ authorization

Nextcloud credentials используются для выпуска JWT. Но JWT фактически идентифицирует пользователя, а не административную роль.

После этого administrative action endpoints допускают restart/backup на основании наличия JWT.

Отдельно `/metrics`, `/containers`, `/logs` и другие диагностические данные доступны без аналогичной проверки.

Целевая модель:

```text
Nextcloud authentication
        |
        v
    identity
        |
        +--------- family-user -----> read-only family functions
        |
        +--------- NAS-operator ----> status / backup request
        |
        +--------- owner -----------> restart / privileged actions
```

Не следует автоматически считать Nextcloud admin-password или Talk room membership RBAC-механизмом.

---

# 6. Backup / restore

## 6.1. Сильные стороны

Backup implementation уже содержит полезный fail-safe:

* проверка `/mnt/storage`;
* защита от записи DB backup на microSD;
* temporary dump + validation;
* проверка gzip;
* отдельная systemd protection для Immich HDD mount.

Immich timer имеет `RequiresMountsFor`, `ConditionPathIsMountPoint` и дополнительную mount check перед запуском. Это правильная инженерная защита.

## 6.2. Gap: standalone script слабее systemd

Сам `backup_immich_to_hdd.sh` проверяет наличие каталога HDD, но защита от ситуации «mount исчез, каталог остался на root filesystem» в основном обеспечивается unit-файлом.

Нужно перенести invariant внутрь script:

```text
destination exists
AND destination is actual mountpoint
AND expected device/filesystem identity matches
ELSE abort
```

Без удаления файлов и без автоматического форматирования.

## 6.3. Restore drill

Документация определяет RPO порядка суток, RTO порядка 2–4 часов и предусматривает регулярный test restore. Публично обнаруженный подтверждённый DB restore датирован 09.08.2026.

Следовательно, на 18.09.2026 новый restore verification уже целесообразен.

При этом старый runbook содержит создание и последующее удаление temporary DB. В рамках заданных правил **запускать такой сценарий без владельца нельзя**.

Лучший следующий вариант:

1. отдельный disposable PostgreSQL container/network;
2. restore последнего dump;
3. `pg_dump --schema-only`/контроль основных таблиц;
4. count/checksum fixtures;
5. container teardown только после разрешённого сценария CI/local dev.

Production DB при этом вообще не затрагивается.

---

# 7. LLM Gateway / @бобик

## 7.1. Что сделано правильно

ADR-0008 задаёт разумную модель:

* GigaChat first;
* DeepSeek только fallback;
* Cloud.ru optional;
* image analysis семейных фотографий запрещён по умолчанию;
* redaction;
* budget limits.

В ADR-0011 implementation имеется явный allowlist read-only home tools:

* `home.status`;
* disk;
* backup age;
* photos;
* help;
* whoami,

и deny rules для destructive/network/secrets/ASUDD-подобных команд.

Это правильное направление: LLM формирует намерение, но реальные действия проходят через детерминированный policy layer.

## 7.2. Budget fail-open

В gateway:

* `_load_usage()` при ошибке возвращает пустую структуру;
* `_save_usage()` подавляет ошибку;
* следующий `_current_usage()` снова читает файл.

Поэтому комментарий, что при ошибке записи «in-memory state still applies», не соответствует фактическому поведению.

Требуемая семантика:

```text
Cannot reliably load/save quota state
            |
            v
        FAIL CLOSED
            |
            +--> 503 / budget-state-unavailable
```

Для внешней платной LLM это предпочтительнее silent overspend.

Кроме того, check → external request → record должны быть защищены от concurrency race.

## 7.3. Fallback semantics

ADR-0008 говорит о fallback при `429/5xx`.

В текущем Giga client ряд upstream errors нормализуется в `502`; верхний routing layer воспринимает `502` как разрешение использовать DeepSeek.

Следствие: ошибка credentials/configuration потенциально превращается из:

```text
GigaChat rejected request
```

в:

```text
Send same prompt to another external LLM provider
```

Это необходимо исправить.

Минимальный regression matrix:

| Giga result             |            DeepSeek fallback |
| ----------------------- | ---------------------------: |
| 400                     |                           NO |
| 401                     |                           NO |
| 403                     |                           NO |
| 404 configuration/model |                           NO |
| 422                     |                           NO |
| 429                     |                          YES |
| real 500                |                          YES |
| 502 upstream gateway    | YES, по явно заданной policy |
| network timeout         |              policy-explicit |

## 7.4. @бобик и image path

В Talk bot обработка image выполняется до полного safety-gate path.

Сейчас второй защитный слой существует — `LLM_ALLOW_IMAGE_ANALYSIS=false` по умолчанию. Но ADR-0011 должен быть самостоятельной гарантией, а не зависеть от другого toggle.

Целевой pipeline:

```text
Talk message
    |
normalize / identify sender
    |
Safety Gate
    |
+---DENY------------------------> deterministic refusal
|
+---ALLOW
    |
structured tool ?
 |          |
yes        no
 |          |
local RO    redaction
tool        |
            v
        LLM gateway
```

---

# 8. Immich ML / семейный UX

ADR-0010 находится в состоянии `Proposed`; выбранный вариант предполагает Cloud.ru CPU VM, причём thumbnails/frames могут покидать домашнюю сеть. ADR прямо требует privacy/risk acceptance и пилот на одном альбоме.

Checkpoint 11–12 сентября показывает, что отдельно был подготовлен бесплатный ROG pilot, но он не стал production node и на тот момент упирался в hypervisor/network constraints. Это не противоречит ADR-0007, пока ROG остаётся экспериментальным вычислителем.

Рекомендация:

```text
Stage 1:
Immich works fully without ML
        |
Stage 2:
ROG/local pilot where convenient
        |
Stage 3:
Cloud.ru ML only after owner privacy decision
        |
one album -> metrics -> decision
```

Не следует:

* переносить Immich ML на Jetson;
* делать распознавание лиц условием нормальной работы фотоархива;
* отправлять весь фотоархив в Cloud.ru «для теста»;
* смешивать GigaChat vision и official Immich ML в одну архитектурную функцию.

---

# 9. Network / VPS / bastion

Текущая схема в целом корректна.

## Jetson

`nas_jetson_nano-lan / 192.168.0.50` сохраняется неизменным.

## VPS

VPS выполняет network-edge функции:

* reverse SSH;
* nginx;
* Amnezia;
* ограниченный внешний perimeter.

Никакой причины переводить NAS на прямой port-forwarding нет.

## Vostro

Checkpoint подтверждает bastion path через VPS `:10222`, при этом Amnezia не изменялась.

Vostro следует и далее рассматривать:

```text
corporate access bastion
        ≠
NAS production node
        ≠
permanent backup SoR
```

## Следующий hardening сети

Не начинать с переделки роутера.

Сначала:

1. application authentication;
2. authorization;
3. минимизация опубликованных host ports;
4. Docker internal networks;
5. только затем, если действительно понадобится, LAN segmentation.

Это снижает риск без вмешательства в семейную сеть.

---

# 10. Технический долг платформы

## 10.1. JetPack / Ubuntu

В bootstrap документации используется JetPack 4.6.1 generation.

JetPack 4.6.1 основан на L4T 32.7.x/Ubuntu 18.04; NVIDIA относит R32.7.x к финальной ветке JetPack 4. Ubuntu 18.04 завершил стандартную поддержку 31.05.2023.

Это не означает «срочно обновить Jetson».

Правильный порядок:

```text
READ-ONLY inventory
    |
    +-- /etc/os-release
    +-- /etc/nv_tegra_release
    +-- python3 --version
    +-- Ubuntu Pro/ESM state
    |
risk assessment
    |
+-- retain + ESM
|
+-- plan hardware migration
```

In-place upgrade основного Jetson без отдельной migration design не рекомендуется.

Важно: application containers NAS API и gateway уже построены на Python 3.12, поэтому host Python 3.6 не означает, что FastAPI-приложения работают на Python 3.6.

## 10.2. Dependencies

LLM Gateway использует pinning конкретных версий библиотек.

NAS API использует `>=`, что делает повторную сборку через несколько месяцев потенциально иной.

Рекомендация:

* requirements lock;
* dependency update PR отдельно;
* vulnerability scan;
* SBOM;
* rollback по previous image digest/tag.

## 10.3. CI

Минимальный quality gate:

```text
PR
 |
 +-- pytest
 +-- compose config
 +-- shellcheck
 +-- secret scan
 +-- policy tests
 +-- dependency scan
 +-- documentation consistency test
 |
 merge
```

Критически полезны policy tests:

```text
assert no direct public gateway without auth
assert image save path cannot escape allowed root
assert Giga 401 never routes to DeepSeek
assert safety gate precedes external LLM call
assert production compose keeps image analysis disabled
assert no destructive home tools
assert no ASUDD/corporate mutation tool
```

---

# 11. Documentation / onboarding / Habr

## 11.1. Главная проблема

Документация очень развитая, но стала многослойной:

```text
README
AGENTS
CLAUDE
ADR
CHECKPOINT
STATUS
audit
CHANGELOG
old runbooks
```

При этом LLM/IDE agent может не отличить historical instructions от действующего operational canon.

Особенно опасны старые фрагменты `CLAUDE.md`, где ещё присутствуют ранее использовавшиеся network/local-LLM процедуры, хотя текущие AGENTS/ADR их уже запрещают.

## 11.2. Предлагаемая иерархия документации

```text
AGENTS.md
   |
ADR accepted
   |
docs/CURRENT_STATE.md
   |
current DEVELOPMENT_PLAN
   |
RUNBOOKS
   |
CHECKPOINTS
   |
HISTORY / audit / archived procedures
```

В начале каждого operational document:

```yaml
status: current | historical | superseded | proposed
effective_date: YYYY-MM-DD
supersedes:
superseded_by:
safe_for_agent_execution: true|false
```

Это особенно важно в проекте, который активно обслуживается несколькими AI coding agents.

## 11.3. Материал для Habr

После hardening sprint проект уже имеет сильную основу для второй статьи:

**не «я установил ещё несколько контейнеров», а переход от NAS к управляемой домашней edge-платформе.**

Технически интересные темы:

* Jetson как SoR, но не AI-compute node;
* CGNAT без публичного NAS;
* reverse SSH вместо вмешательства в рабочий VPN;
* домашний LLM Gateway с multi-provider routing;
* deterministic safety gate перед LLM;
* privacy boundary для семейных фотографий;
* layered backup и restore drill;
* incident-driven architecture;
* почему старый Jetson всё ещё полезен, если правильно разделить роли.

Перед публикацией необходимо удалить из материалов все family identifiers, реальные room IDs, MAC/service tags и сетевые эксплуатационные детали, не нужные читателю.

---

# 12. Roadmap: следующие 2 недели

Цель этапа:

> **Hardening без расширения функциональности и без deployment до команды владельца «деплой».**

## W1. Security and policy

### T1. Gateway arbitrary-path regression test — P0

Сначала написать тест, который пытается:

```text
save_path = ../../...
save_path = /data/llm_usage.json
save_path = /etc/...
```

**Expected:** request rejected.

После этого убрать/ограничить API.

**Rollback:** обычный revert commit.
**Production impact:** отсутствует до deployment.

### T2. Gateway authentication — P0

Добавить внутренний service credential/API token между NAS API/Talk и gateway.

Не использовать family/user token как service credential.

**Verification:**

* health — по выбранной policy;
* chat without token → 401;
* chat valid service token → success;
* wrong token → 401;
* token не логируется.

### T3. NAS API RBAC — P0

Отделить:

```text
authenticated user
operator
owner
```

Restart/backup требуют отдельной роли.

### T4. Protect diagnostic endpoints — P0

Закрыть или минимизировать:

* `/logs`;
* `/metrics`;
* `/containers`;
* `/report/now`;
* Talk status.

### T5. Current HEAD privacy scrub — P0

Не переписывая историю автоматически:

* room IDs → placeholders;
* family names → generic examples;
* MAC/service tag → masked/example;
* добавить проверку в CI.

Вопрос rotation/recreation уже должен решать владелец отдельно.

## W2. Reliability

### T6. Fix LLM fail-closed budget — P1

Добавить tests:

* unreadable budget;
* unwritable budget;
* corrupt JSON;
* concurrent calls;
* daily rollover.

### T7. Fix fallback semantics — P1

Regression tests `401/403/422 != DeepSeek`.

### T8. Backup guards — P1

Кодово, без запуска на Jetson:

* actual mountpoint guard;
* expected FS/device guard;
* retention variables alignment;
* безопасное чтение нужных `.env` keys вместо shell-source всего файла.

### T9. Compose contract — P1

Исправить:

* expected NAS API container name;
* safety gate env propagation;
* explicit restart policies;
* `docker compose config` validation.

### T10. Documentation re-baseline — P1/P2

Синхронизировать:

* README;
* current checkpoint index;
* CLAUDE;
* CHANGELOG;
* BACKUP_RESTORE;
* NETWORK_INVENTORY.

Historical procedures отметить `DO NOT EXECUTE / SUPERSEDED`.

---

# 13. Top-10 следующих безопасных шагов

Все десять действий можно выполнить **без изменения Jetson production**.

|  № | Действие                                                                  | Проверка результата                    | Rollback                            |
| -: | ------------------------------------------------------------------------- | -------------------------------------- | ----------------------------------- |
|  1 | Добавить regression tests для `save_path`                                 | test до fix красный, после fix зелёный | revert test/fix commits             |
|  2 | Ограничить/удалить arbitrary `save_path`                                  | path traversal невозможен              | revert commit                       |
|  3 | Добавить gateway service authentication                                   | 401/200 integration tests              | revert commit                       |
|  4 | Добавить NAS API RBAC                                                     | family user не может restart           | revert commit                       |
|  5 | Закрыть diagnostic/Talk status endpoints auth'ом                          | unauth tests → 401/403                 | revert commit                       |
|  6 | Исправить Giga→DeepSeek fallback                                          | 401/403 не вызывают fallback           | revert commit                       |
|  7 | Исправить budget fail-closed                                              | disk-state failure → 503               | revert commit                       |
|  8 | Усилить backup scripts mount guards и env parsing                         | shellcheck + fixture tests             | revert commit                       |
|  9 | Очистить current HEAD от family/private identifiers и усилить secret scan | repository scanner clean               | revert commit; rotation отдельно    |
| 10 | Подготовить disposable restore drill + обновить current docs              | restore test не касается prod          | удалить disposable test environment |

После выполнения этих шагов должен существовать отдельный owner gate:

```text
CODE READY
   |
tests pass
   |
static review
   |
owner says: "деплой"
   |
canary deployment
   |
read-only checks
   |
decision continue / rollback
```

До слова **«деплой»** эта стадия не начинается.

---

# 14. Roadmap: следующие 2 месяца

## Phase 1 — закрыть durability gap

Главная задача — довести ADR-0009 до целевой схемы:

```text
L0 live SSD
L1 local HDD
L2 encrypted/off-site Cloud.ru S3
```

Требуется решение владельца по `tenant_id`/Cloud.ru.

После появления L2:

* initial upload;
* integrity verification;
* restore sample;
* RPO/RTO measurement;
* cost measurement;
* регулярный restore drill.

## Phase 2 — platform hardening

* non-root containers;
* read-only rootfs где возможно;
* internal Docker networks;
* locked dependencies;
* SBOM;
* vulnerability scan;
* CI branch protection;
* explicit release process.

## Phase 3 — host lifecycle

После read-only inventory:

* оценить Ubuntu Pro/ESM;
* определить срок безопасной эксплуатации Jetson;
* подготовить migration target без срочной покупки hardware;
* задокументировать восстановление на новом ARM/x86 host.

## Phase 4 — Immich ML

Только после принятия owner privacy decision:

1. ROG/local experiment — если остаётся практически бесплатным;
2. либо Cloud.ru official Immich ML согласно ADR-0010;
3. один тестовый album;
4. измерить:

   * latency;
   * upload volume;
   * CPU/RAM;
   * accuracy;
   * стоимость;
   * family UX benefit;
5. после данных принять архитектурное решение.

Jetson Nano не становится ML worker.

## Phase 5 — @бобик

После security foundation можно расширять не LLM-возможности, а **structured read-only home tools**:

```text
home.status
storage.health
backup.age
backup.last_result
immich.status
nextcloud.status
network.reverse_tunnel_status
alerts.summary
```

Любые mutation-tools должны проходить отдельную ADR и explicit owner policy.

ASUDD/корпоративный контур в семейный `@бобик` не переносится.

---

# 15. Чего НЕ делать

## A01. Не трогать Amnezia

Не выполнять:

```text
wg set ...
systemctl restart amnezia...
firewall experiments affecting VPN
```

ADR-0003 зафиксировал реальный инцидент, затронувший около 25 клиентов; reverse SSH выбран именно для исключения таких вмешательств.

## A02. Не удалять и не переделывать профиль Jetson

`nas_jetson_nano-lan / 192.168.0.50` является инвариантом.

## A03. Не публиковать сервисы напрямую в Internet

Не открывать наружу:

* Nextcloud;
* Immich;
* LLM Gateway;
* NAS API;
* SSH Jetson,

мимо принятой VPN/reverse-tunnel/risk model.

## A04. Не форматировать HDD

Текущий HDD содержит существующие данные и имеет NTFS. Старые generic storage recipes с `mkfs`/partition operations не относятся к текущему устройству без отдельного решения владельца.

## A05. Не выполнять automatic backup cleanup вне утверждённой retention policy

В backup script уже имеется rotation/delete logic. Любое изменение retention должно рассматриваться как изменение data-loss policy, а не как «уборка диска».

## A06. Не переносить local LLM на Jetson как Stage 1

ADR-0007 однозначно выносит тяжёлый inference с Jetson.

## A07. Не возвращать Vostro в production NAS architecture

Vostro — bastion/legacy/emergency resource, но не SoR.

## A08. Не переписывать проект на Kubernetes

Для одного Jetson и текущего числа сервисов это увеличит operational complexity без устранения выявленных P0/P1.

## A09. Не подключать семейные фото к внешним LLM «для удобства»

AGENTS запрещает передачу private photos/backup manifests наружу; ADR-0010 требует отдельного privacy acceptance даже для Immich ML.

## A10. Не переносить ASUDD/корпоративные mutation tools в @бобик

Safety gate уже содержит концептуальные запреты на опасные/чужие domain actions. `@бобик` должен оставаться семейным home assistant с минимальным набором структурированных capabilities.

## A11. Не выполнять deployment автоматически

Канон явно фиксирует:

> deployment на Jetson выполняется только после решения владельца.

---

# 16. Сильные стороны проекта

Аудит не сводится к перечню недостатков. В проекте уже присутствуют инженерные решения, которые имеет смысл сохранить.

### 16.1. ADR-driven architecture

Решения по network edge, LLM routing, backup, Immich ML и распределению ролей фиксируются ADR, а не только в compose-файлах.

### 16.2. Incident-driven hardening

После реальных проблем появились явные запреты:

* не трогать Amnezia;
* не менять `.50`;
* не хранить secrets в git;
* не делать destructive operations автоматически;
* не использовать Jetson как LLM compute node.

### 16.3. Правильное разделение data plane / compute plane

Jetson хранит данные, но тяжёлое ML предполагается выполнять снаружи. Это существенно продлевает практическую жизнь Nano.

### 16.4. Defense-in-depth в backup

Systemd mount guards уже показывают правильный подход к защите данных.

### 16.5. LLM не получает shell непосредственно

Направление ADR-0011 с allowlisted structured tools существенно безопаснее «LLM → ssh/bash».

Именно этот подход следует развивать.

---

# 17. Итоговая оценка архитектуры

Текущее состояние проекта можно определить так:

> **Функционально зрелая домашняя edge-платформа с хорошей архитектурной дисциплиной, но с накопившимся разрывом между policy/ADR и enforcement в коде управляющих API.**

Основной дальнейший прирост качества даст не увеличение числа сервисов.

Очередность:

```text
1. Policy enforcement
        ↓
2. Authentication + authorization
        ↓
3. Backup + proven restore
        ↓
4. Reproducible build / CI
        ↓
5. Documentation as executable source of truth
        ↓
6. Immich ML / новые UX-функции
```

После выполнения P0/P1 проект будет заметно ближе не к «домашнему NAS из Docker Compose», а к небольшой управляемой production-платформе.

---

# 18. Appendix A — ключевые пути

```text
/
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── CHANGELOG.md
│
├── docs/
│   ├── 04_STORAGE_DESIGN.md
│   ├── 12_BACKUP_RESTORE.md
│   ├── 19_NETWORK_INVENTORY.md
│   │
│   ├── plans/
│   │   ├── DEVELOPMENT_PLAN_2026-09_SBER_ERA.md
│   │   ├── CHECKPOINT_2026-09-11.md
│   │   └── CHECKPOINT_2026-09-12.md
│   │
│   ├── decisions/
│   │   ├── ADR-0003-...
│   │   ├── ADR-0007-...
│   │   ├── ADR-0008-...
│   │   ├── ADR-0009-...
│   │   └── ADR-0010-immich-ml-cloudru.md
│   │
│   └── audit/
│       └── AUDIT_GITHUB_SBER_BILINGUAL_2026-09-08.md
│
├── docker/
│   └── compose/
│       ├── docker-compose.llm-gateway.yml
│       └── docker-compose.nas_jetson_nano-api.yml
│
├── config/
│   └── .env.example
│
├── services/
│   ├── llm-gateway/
│   │   ├── Dockerfile
│   │   └── app/main.py
│   │
│   └── nas_jetson_nano-api/
│       ├── Dockerfile
│       └── app/
│           ├── main.py
│           ├── auth.py
│           ├── actions.py
│           ├── talk_bot.py
│           └── bobik_gate.py
│
├── scripts/
│   └── backup/
│       ├── backup_databases.sh
│       └── backup_immich_to_hdd.sh
│
└── systemd/
    └── Immich HDD backup unit/timer
```

---

# 19. Appendix B — ограничения данного аудита

1. Путь `E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano` не был доступен из среды анализа.
2. Поэтому незакоммиченные изменения локальной копии не проверены.
3. `E:\agent_coordination\` также не был доступен; содержание coordination state `nas` не проверялось.
4. `shared/work/OPEN_ACCESS_FOR_NEIGHBORS.md` подтверждается checkpoint как существующий coordination artifact, но его локальная актуальная редакция не анализировалась.
5. Самый свежий публично обнаруженный checkpoint — `CHECKPOINT_2026-09-12.md`.
6. Полный текст отдельного ADR-0011 через публичную индексацию получить не удалось; фактическая реализация ADR-0011 проверена по `bobik_gate.py` и `talk_bot.py`.
7. Live state Jetson, Docker, systemd, дисков, Cloud.ru и VPS не опрашивался.
8. Ни одна команда deployment/restart/network/storage не выполнялась.

Следовательно, все утверждения о live-состоянии выше основаны только на repository checkpoints/audits, а не на предположении, что состояние устройства 18.09.2026 неизменно совпадает с состоянием 12.09.2026.
