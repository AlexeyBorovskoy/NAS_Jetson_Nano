# План развития NAS_Jetson_Nano — эра Сбер / Cloud.ru (2026-09)

> **Статус:** канон развития (замена операционной части `docs/31_MASTER_PLAN.md` 2026-08-22).  
> **Дата:** 2026-09-04 · **Обновлено:** 2026-09-19 — **сводная редакция**: решения Сбер-эры +
> Hardening Sprint GigaCode (`audit_new`, H01–H16) + полный аудит 2026-09-19 (`docs/audit/2026-09-19_full_audit/`).  
> **Входы владельца:** станция RTX и Vostro **вне архитектуры**; Immich 2-я копия на HDD Jetson;
> Сбер/Cloud.ru/GitVerse усиливают проект; деплой Jetson — только по «деплой».  
> **Доказательная база:** audit 2026-08-30; probes 2026-09-04…08; device cutover 2026-09-08;
> `audit_new` 2026-09-18; live-аудит 2026-09-19 (замеры Jetson/VPS, исполнение кода).
>
> 🇬🇧 Project canon for development. EN summary §12.

---

## 0. Что изменилось в этой редакции (2026-09-19)

1. **Три входа слиты в одну очередь.** Волна 0.5 (H01–H16) и находки аудита 2026-09-19 (NAS-*,
   R*-*) больше не живут отдельными списками — дубли сведены, у каждой задачи один ID (§4).
2. **Приоритет «данные раньше удобства».** Аудит нашёл на живой системе то, чего не было в
   `audit_new` (сломанное авто-восстановление SSD, обесточивание, незащищённые копии) — эти задачи
   встали рядом с P0 безопасности.
3. **Сбер-решения привязаны к дырам, которые они закрывают**: Cloud.ru S3 → off-site (NAS-BAK-001),
   Container Apps-сторож → детекция отказа и обесточивания (NAS-REL-001), GigaChat → «что сломалось?»
   для владельца (ADR-0011), FM → админский RAG по runbook'ам.
4. **Отозваны статусы «✅», не подтверждённые тестами** (§1.1). Введено определение готовности (§3).
5. **Photo AI Orchestrator** (Kaggle/Modal/Colab для семейных фото) — **исследовательский трек, не
   план** (§8): противоречит `AGENTS.md` п. 4 и требует решения по ADR-0010.

---

## 1. Журнал выполнения / Progress log

| Когда | Шаг | Статус | Артефакты |
|---|---|---|---|
| 2026-09-04 | ADR-0007 / 0008 / 0009, banners 29–31, `docs/integrations/sber/` | ✅ git | ADR, docs |
| 2026-09-04 | Шаблоны W1 (`.env.example`, compose, Talk provider) | ✅ git | |
| 2026-09-07 | Gateway: cloudru, balance, Giga→DS failover, 1-flight lock + tests | ✅ git | `main.py`, `test_sber_routing.py` |
| 2026-09-07 | Offline Sber pack; auth probe Cloud.ru + GitVerse; SA `home-nas-api` | ✅ | `OFFLINE_SBER_READY_PACK.md`, `AUTH_PROBE_*` |
| 2026-09-07 | FM chat (после пополнения) | ✅ 200 | `AUTH_PROBE_FM_KEY_SMOKE_2026-09-07.md` |
| 2026-09-07 | GitVerse mirror `NAS_HOME` (HTTPS) | ✅ | |
| 2026-09-08 | **Device:** Giga-2 cutover, `prefer_local=false`, Immich→HDD timer, giga-balance timer | ✅ device | |
| 2026-09-08 | S3 + restic L2 | ❌ blocked | tenant_id / CreateBucket AccessDenied |
| 2026-09-09 | F-01 fail-closed dumps на устройстве | ✅ device | `backup_databases.sh` |
| 2026-09-18 | `audit_new` → Hardening Sprint H01–H16 | план | `docs/research/audit_new.md` |
| 2026-09-19 | `d52c11b` W0.1 save_path + smart routing + presets | ⚠️ git, с P0-дефектом → **исправлено в A2** | см. §1.1 |
| 2026-09-19 | W0.2 service token | ⚠️ WIP с регрессией → **доведено в A3** | `36c4ced` |
| 2026-09-19 | Полный аудит + разбор работы GigaCode | ✅ git | `docs/audit/2026-09-19_full_audit/` |
| 2026-09-19 | **A1** ворота/CI гоняют тесты сервисов; heredoc-баги | ✅ git + **CI зелёный** впервые с 08-30 | `36c4ced`, `b8f50c9` |
| 2026-09-19 | **A2** шлюз: чат/картинки восстановлены, smart routing за флагом | ✅ git (37/37) | `36c4ced` |
| 2026-09-19 | **A3** токен шлюза: код + бот шлёт заголовок | ✅ git; выкат — `DEPLOY_STAGE_A_2026-09.md` | `36c4ced` |
| 2026-09-19 | **A4** единая раскладка хоста; recovery SSD; compose API через переменные; H10 | ✅ git; проверено на Jetson (stdin) | `9ec1b15`, этот коммит |
| 2026-09-19 | **A5** runbook выката этапа A | ✅ git | `DEPLOY_STAGE_A_2026-09.md` |
| 2026-09-19 | **A6** честные статусы | ✅ git | `0f209bb` |
| 2026-09-19 | **Выкат этапа A на Jetson** (04:37–04:45 UTC) | ✅ **device** | репо `bdba26b`; recovery `Result=success`; чат Giga 200; токен включён (401 без него, бот 🐕 ок); failed units 0; правило №13 до/после идентично |
| 2026-09-19 | **B1** бэкап конфигурации/`.env`/`config.php`/файлов NC/Samba/дампов — restic шифр. на HDD, 7д/4н/6м, fail-closed | ✅ git; тест с настоящим restic | `config_backup.sh`, `install_restic.sh` (0.19.1, SHA-256), `setup_config_backup.sh` |
| 2026-09-19 | **B2** `backups/` только чтение в Samba и Nextcloud (вложенный ro-bind) | ✅ git | compose nextcloud/samba, `test_backup_isolation.py` |
| 2026-09-19 | **B6** учения по восстановлению (ежемесячно; ловят неполный снапшот) | ✅ git | `restore_drill.sh`, таймер |
| 2026-09-19 | **B3** S3 — тот же скрипт, цель `s3.env` | готово в коде; ждёт tenant_id | `DEPLOY_STAGE_B_2026-09.md` |
| 2026-09-19 | **Выкат этапа B на Jetson** (05:00–05:06 UTC) | ✅ **device** | restic 0.19.1 (SHA-256 OK); репо `3bdd878a61` на HDD; снапшот `291b0be5` 532 файла / 415 МиБ (196 МиБ в репо) за 12 с; учения **DRILL OK** за 5 с; `backups/` ro в Samba и Nextcloud — запись отклонена (`Read-only file system`); пароль репо — Windows Credential Manager; простой ~1.5 мин; правило №13 до/после идентично |
| 2026-09-19 | **C1/C2** NAS API: JWT на всех маршрутах кроме `/healthcheck`/входа; роли семья/владелец; без `CORS *` | ✅ git (тест по всем 21 маршруту) | `ecdb63f` |
| 2026-09-19 | **C3** `save_path` ограничен | ✅ (A2) | `36c4ced` |
| 2026-09-19 | **C4/C5** бюджет fail-closed + атомарная запись; откат на DeepSeek только 429/5xx/транспорт | ✅ git | `ecdb63f` |
| 2026-09-19 | **C6** gate до фото, лимит вложения 10 МБ | ✅ git | `ecdb63f` |
| 2026-09-19 | **C7** токены комнат и MAC из публичного HEAD; guard по хэшам | ✅ git (история не переписана) | `3266241` |
| 2026-09-19 | **C8** шлюз не от root (API — осознанно root: docker.sock) | ✅ git | этот коммит |
| 2026-09-19 | **C10** Portainer только 127.0.0.1; rpcbind — в runbook. Netdata в LAN — до D5 (монитор Kuma) | ✅ git | этот коммит, `DEPLOY_STAGE_C_2026-09.md` |
| 2026-09-19 | **C9** SSH по паролю / общий пароль | ⏸ решение владельца (runbook §8) | — |
| 2026-09-19 | **Выкат этапа C на Jetson** | ✅ **device** | репо `339db92`; без токена 401 на всех проверенных маршрутах, `/healthcheck` 200, CORS нет; admin (владелец) — логи 200; алерт success; бот 🐕 ок; шлюз UID 10001, `/data` пишется; Portainer 127.0.0.1; rpcbind выкл. (NFS нет); 13 контейнеров, failed 0; правило №13 идентично. Сборка шлюза падала из-за испорченного `RUN` — старый контейнер работал, исправлено `339db92`. `API_OWNERS` пуст: владелец работает как `admin` |
| 2026-09-19 | долг: `tests/unit/test_bobik_gate.py` не запускается на Python 3.6 хоста (`from __future__ import annotations`) | ⏳ | в CI проходит |
| 2026-09-19 | **C11** имя API-контейнера | ✅ (A4) | `a12c5bd` |
| 2026-09-19 | **E2** алерт квоты GigaChat (порог по моделям, устаревший опрос) | ✅ git; выкат по «деплой» | `6bd36bf` |
| 2026-09-19 | **D3** внешний сторож Cloud.ru: VPS-скрипт, задача, установщик, 39 тестов | ✅ git; спайк + выкат — `DEPLOY_D3_WATCHDOG_2026-09.md` | спецификация `126e06b` |
| 2026-09-19 | Спецификации: Telegram-бот + домашняя качалка на Jetson (ред. 1–5), **приоритет владельца** (запрос сына) — обращение по имени «@бобик», размер закачки без предела (SSD ≤20 ГБ / HDD больше), вопросы к GigaChat в первом срезе бота, SOCKS на `172.17.0.1:1080` (Jetson не достаёт Telegram напрямую) | ✅ git (спецификации); реализация — следующий шаг | `telegram-family-bot-design.md`, `home-downloader-design.md` |

### 1.1. Отозванные статусы (как найдено)

| Было записано | Где | Факт (2026-09-19) | Как найдено |
|---|---|---|---|
| «W0.5 ✅ git: gateway auth guard, save_path, smart routing, presets» | прошлая редакция, журнал | auth guard не было в коде; smart routing ломает чат | исполнение `TestClient` на трёх версиях `main.py` |
| «H15 Smart routing ✅ done» | §9 прошлой редакции | каждый чат GigaChat → **500** (`full` до присваивания); русские паттерны не срабатывают; Max — **отдельная** квота ≈25 млн, а не «общее ведро» | тест + прогон фраз + журнал баланса |
| «8 новых тестов — все 16 прошли ✅» | `CHECKPOINT_2026-09-19.md:29` | на `d52c11b` падают 2 старых теста; на W0.2 — 5 | `pytest tests/llm_gateway` |
| «`nasa-ssd-recovery` ✅ active» | `CLAUDE.md` | `failed` (127) с 2026-09-18; сломан с 2026-09-08 | `systemctl --failed` на Jetson |
| «Vostro исключён» (как факт работы) | §1 п. 2 | Vostro — **единственный работающий off-site** (забор 2026-09-19 01:05 UTC) | штамп `offsite-pull-last.stamp` |

Системная причина: pre-commit (`preflight.sh:183-202`) гоняет только `tests/unit`; CI красный с
2026-08-30 — «зелёные ворота» не видели тестов шлюза. Закрывается задачей **A1** (§4).

---

## 2. Решения владельца и архитектура

### 2.1. Зафиксировано (в силе)

1. Рабочая станция (RTX) — только разработка, не узел платформы (ADR-0007).
2. Vostro — вне целевой архитектуры. **Уточнение 2026-09-19:** до работающего S3 его pull-забор
   дампов **не выключать** — это действующий L2 (legacy, не развивается).
3. Вторая копия Immich — HDD Jetson (L1, не off-site).
4. Платформа Сбера усиливает проект: GigaChat PERS (семья), Cloud.ru FM + Object Storage, GitVerse.
5. Без выноса семейных фото в LLM и без открытия NAS в интернет мимо VPN.

### 2.2. Ждут решения владельца

| # | Вопрос | Рекомендация | Решение владельца (2026-09-19) | Влияет на |
|---|---|---|---|---|
| D1 | Покупка ИБП для Jetson + USB-дисков | **да** — два подтверждённых обесточивания (17.08, 18.09) | **отложено**. Тем важнее D2 (алерт после аварийной загрузки) и D3 (внешний сторож) | D1-задачи §4 |
| D2 | Что в S3: только дампы/конфиг или и фото Immich (≈13 ГБ, растёт) | сначала дампы + конфиг + файлы NC; фото — после оценки цены | **B3 отложен**, off-site остаётся на Vostro | B3 |
| D3 | Есть ли копия 1.4 ТБ архива вне HDD | если нет — внешний диск (не облако) | **копии нет и не будет — риск принят**. Защита только SMART-алерт и еженедельный самотест HDD; отказ диска = потеря архива | B5 закрыт |
| D4 | Immich ML: Cloud.ru (ADR-0010, превью уходят из дома) **или** станция батчем по туннелю | станция батчем; Cloud.ru — только с принятием риска ПДн | **Cloud.ru, если укладывается в free tier** (риск ПДн принят при этом условии). Сначала спайк: E6 после E5 | E6 |
| D5 | Smart routing: чинить или убрать | убрать до нормального классификатора и учёта квоты Max | A2 |
| D6 | Окно для Part B (переезд устройства на новое именование) | после A/B-этапов | F1 |

### 2.3. Целевая архитектура

```
Семья (LAN / VPN→VPS) ──► Jetson = System of Record + control plane
                              NC · Immich · Samba · @бобик · Gateway · таймеры
                              SSD: БД+фото (live)   HDD: копия фото + restic-репо (L1)
                              SD: только ОС (Docker root → SSD, цель)
        │ reverse SSH                    │ HTTPS (исходящий)
        ▼                                ▼
VPS (edge): nginx, Amnezia, Beszel   Cloud.ru: S3 (restic L2, шифрование) · FM (админ) ·
                                     Container Apps-сторож (внешняя проверка живости)
                                     GigaChat PERS: семейный LLM через шлюз (redaction, бюджет)
GitHub (канон) ◄──► GitVerse NAS_HOME (зеркало)
```

| Узел | Роль | Запрещено |
|---|---|---|
| Jetson | SoR, on-site backup, шлюз, бот | локальная LLM, Immich ML, секреты в git |
| VPS | туннель, nginx, Amnezia (~19 пиров), Beszel hub | семейные данные; трогать Amnezia без чек-листа |
| Cloud.ru | S3 off-site (шифр.), FM, сторож | сырые семейные фото в FM/RAG без ADR |
| GigaChat PERS | семейный LLM | анализ альбома; >1 потока |
| GitVerse | зеркало | секреты |
| Станция / Vostro | вне архитектуры (Vostro — legacy L2 до S3) | обязательные таймеры |
| Kaggle (с 2026-09-20) | бесплатный GPU для **подготовительных** работ: сравнение моделей распознавания речи, проверка моделей Immich ML, квантование, тяжёлые бенчмарки. Домой приезжает артефакт (файл модели / таблица замеров) | семейные фото, видео, документы, дампы, секреты; любой рабочий контур — дом не зависит от внешнего сервиса (`docs/integrations/kaggle/README.md`) |

### 2.4. Жёсткие правила (не пересматриваются)
Amnezia и порты 22·443·40568; Jetson `192.168.0.50` и профиль LAN; redaction + бюджет на всех
облачных провайдерах; `LLM_ALLOW_IMAGE_ANALYSIS=false`; секретов нет в git/GitVerse; деструктивные
операции с дисками — только с явного OK; деплой — только по «деплой».

---

## 3. Определение готовности (DoD) — обязательно для любого «✅»

Статус «✅ git» ставится только если **все** пункты выполнены и вывод команд записан в точку/коммит:

1. `python -m pytest tests/ -q` — **0 failed** (весь набор, не только новый файл).
2. Для HTTP-изменений — проверка эндпоинта через `TestClient` (статус-код в записи).
3. `bash scripts/quality/preflight.sh` зелёный **и** CI зелёный на этом коммите.
4. Числа и утверждения о внешнем мире (квоты, цены, лимиты) — с источником и датой.

«✅ device» дополнительно: сверка `ActiveEnterTimestamp`/`StartedAt` против времени выката, живой
smoke, правило №13 до и после.

5. **Материал для статьи на Хабр** (решение владельца 2026-09-20): после каждого значимого шага —
   строка в `docs/articles/HABR_PART2_MATERIALS.md` с датой замера, доказательством (команда/коммит/файл)
   и ссылкой на подробности. Без доказательства пункт в статью не идёт; отозванные гипотезы записываются
   наравне с успехами.

---

## 4. Сводная очередь работ

ID: **A** — блокеры · **B** — данные · **C** — безопасность · **D** — надёжность и наблюдаемость ·
**E** — Сбер-edge и ИИ · **F** — платформа · **G** — инженерный стандарт и чистка репозитория. В скобках — исходные ID (H* — GigaCode/`audit_new`,
NAS-*/R* — аудит 2026-09-19).
Колонка «Где»: **git** — без устройства; **dev** — деплой по «деплой»; **owner** — действие владельца.

### Этап A — Блокеры (1–2 дня)

| ID | Задача | Источник | Где | Готово, когда |
|---|---|---|---|---|
| A1 | Ворота видят все тесты: `tests/llm_gateway` в `preflight.sh`; исправить 2 битых heredoc в `scripts/sber/`; CI зелёный | NAS-QA-001, R1-05 | git | 10 зелёных CI подряд; pre-commit падает на сломанном тесте шлюза |
| A2 | Починить шлюз в `main`: `full` до выбора модели, вернуть `_IMG_TAG_RE`, ленивый `mkdir`, тесты без записи в `/data`. Smart routing — убрать или переписать (D5) с учётом отдельной квоты Max | NAS-REG-001, H15 | git | `POST /v1/chat` (gigachat, мок) → 200 в тесте; весь `tests/` зелёный |
| A3 | W0.2 доделать: эндпоинты синхронные (или `run_in_threadpool`); Talk-бот, daily report, скрипт баланса шлют `X-Service-Token`; затем fail-closed; `hmac.compare_digest`; `/v1/usage` за токеном | H02, NAS-SEC-003 | git → dev | тест «`/health` < 1 с во время медленного чата»; без токена 401; `@бобик` отвечает с токеном |
| A4 | Авто-восстановление SSD: путь проекта из env юнита, поиск других абсолютных путей | NAS-STO-001, R0-02 | git → dev | `systemctl start nasa-ssd-recovery` → success |
| A5 | До Part B — никаких `git pull` на устройстве вне runbook'а деплоя | R0-03 | runbook | запись в `DEPLOY_*` |
| A6 | Честные статусы: поправка в `CHECKPOINT_2026-09-19.md`, `CLAUDE.md` (recovery, HEAD устройства) | H13, NAS-DOC-001 | git | нет «✅» без DoD |

### Этап B — Данные (неделя; P1)

| ID | Задача | Источник | Где | Готово, когда |
|---|---|---|---|---|
| B1 | Локальный restic-репозиторий на HDD: `.env`, `config.php` + том `nextcloud_app`, `nextcloud/data`, пользователи Samba, дампы | NAS-BAK-001, R4-01 | git → dev | restore на чистой машине поднимает NC |
| B2 | Изолировать `backups/` от шар `hdd2tb` и `/HDD-2TB` (read-only или вне шары) | NAS-BAK-002, R4-02 | dev | запись через SMB в `backups/` → отказ |
| B3 | **Cloud.ru S3 = L2** (Сбер): owner — tenant_id + bucket + ключи; restic с шифрованием, набор B1; фото — по D2 | ADR-0009, W3.3, R4-03 | owner → dev | restore одного файла и одного дампа из S3 |
| B4 | Vostro pull оставить до B3; после 2 недель зелёного S3 — отключить отдельным решением | §2.1 п. 2 | — | запись решения |
| B5 | Архив 1.4 ТБ — ответ по D3; при отсутствии копии — внешний диск | NAS-BAK-003 | owner | ✅ закрыт 2026-09-19: копии нет и не будет, риск принят владельцем |
| B6 | Restore-drill раз в месяц (дамп + файл фото + конфиг) | R4-04 | git → dev | журнал drill |

### Этап C — Безопасность (неделя; P0/P1 из `audit_new` + аудит)

| ID | Задача | Источник | Готово, когда |
|---|---|---|---|
| C1 | NAS API: auth на `/v1/status,/metrics,/containers,/logs,/talk/*`, `/v1/report/now`; CORS — allowlist или выкл. | H04, NAS-SEC-001 | без токена 401, кроме `/healthcheck` |
| C2 | NAS API RBAC owner/family; действия — только owner; docker-действия через allowlist | H03, NAS-SEC-002 | family-JWT на restart → 403 |
| C3 | Шлюз: `save_path` — только имя в фиксированном каталоге (логика `_sanitize_save_path` из `d52c11b` верна) | H01 | тест traversal |
| C4 | Бюджет fail-closed + атомарная запись; `user` из токена | H06, NAS-SEC-003 | битый файл → 503 |
| C5 | Fallback в DeepSeek только на 429/5xx/транспорт, не на 401/403 | H07, NAS-SEC-004 | матрица тестов |
| C6 | `@бобик`: safety gate до ветки картинок; лимит размера вложения до скачивания | H08, H09 | тесты |
| C7 | Приватность HEAD: токены комнат, логины, MAC — в `docs/local/` | H05, H14, NAS-SEC-008 | сканер чист |
| C8 | Контейнеры шлюза/API не от root; safety-флаги в compose NAS API | H12, H11 | `USER` в Dockerfile |
| C9 | SSH без пароля; sudo ≠ пароль Nextcloud-админа (осторожно: единственный путь входа) | NAS-SEC-005 | `sshd -T` → no, вход по ключу проверен |
| C10 | Portainer — по требованию или `127.0.0.1`; Netdata — `127.0.0.1` или удалить (см. D5); rpcbind выкл. | NAS-SEC-006/007 | `ss -tln` |
| C11 | Имя контейнера `homecloud_nasa_api` в ожиданиях мониторинга | H10 | нет ложных алертов |

### Этап D — Надёжность и наблюдаемость

| ID | Задача | Источник | Готово, когда |
|---|---|---|---|
| D1 | **ИБП** (D1) + корректное выключение — ⏸ отложено владельцем 2026-09-19 | NAS-REL-001 | Jetson жив при выдернутой сети ИБП |
| D2 | Алерт при загрузке после `TEGRA_POWER_ON_RESET` без штатного выключения | NAS-REL-001 | алерт в Talk |
| D3 | **Внешний сторож на Cloud.ru Container Apps** (Сбер, W3.4): проверка живости через VPS → алерт, если Jetson молчит | ADR-0007, NAS-REL-001 | выключенный туннель → алерт ≤ 15 мин |
| D4 | Алерт на `systemctl --failed`; возраст бэкапов по слоям (дамп / HDD / off-site) в ежедневном отчёте | NAS-OBS-001, R2-01/02 | тестовый упавший юнит → алерт |
| D5 | Запись на SD ≈8 → <1 ГБ/сутки: `log-opts` Docker, Netdata RAM-mode/удаление, Docker root → SSD | NAS-PERF-001, R5-01 | счётчик `mmcblk0` в отчёте |
| D6 | Закрепить теги образов (`IMMICH_VERSION=v2.7.5` и др.) | NAS-OPS-001, R1-06 | нет `latest`/`release` |

### Этап E — Сбер-edge и ИИ (после A–C)

| ID | Задача | Сбер-решение | Условие |
|---|---|---|---|
| E1 | Маршрутизация GigaChat с учётом раздельных квот (Lite ≈250 млн / Max ≈25 млн): классификатор, работающий на русском, + бюджет по модели | GigaChat PERS | после A2; тесты на русских фразах |
| E2 | Порог баланса Giga → алерт (таймер уже есть) | GigaChat balance API | — |
| E3 | `@бобик` structured tools (ADR-0011): «что сломалось?» — правила собирают факты (failed units, возраст бэкапов, SMART, USB, питание), GigaChat объясняет, человек решает. **Без действий от LLM** | GigaChat | после C1–C2, D4 |
| E4 | Админский RAG по runbook'ам (`docs/`) через FM embeddings | Cloud.ru FM | только документация, не семейные данные |
| E5 | Cloud.ru billing/balance алерт, мягкий месячный лимит | Cloud.ru API | до B3 |
| E6 | Immich ML в Cloud.ru Container Apps — только если укладывается в free tier (решение D4 2026-09-19). Спайк: RAM/CPU первичной индексации 7 тыс. фото, холодный старт поиска, закрытие эндпоинта (у Immich ML нет авторизации), потолок `max instances=1`. Бесплатной VM в Evolution free tier нет (проверено 2026-09-19) | Cloud.ru Container Apps | после E5 (алерт расходов) |
| E7 | GitVerse: зеркало после каждого push, без секретов | GitVerse | — |
| E8 | Пресеты картинок (8 шт., `d52c11b`) — оставить; проверить эндпоинт после A2 | GigaChat-2-Max | тест `/v1/image/presets` |
| E9 | **Telegram-бот, первый срез** (приоритет владельца — запрос сына): SOCKS-транспорт, whitelist, качалка aria2 (SSD ≤20 ГБ / HDD больше, качает домашний интернет Jetson — не VPS, правило №13), вопросы GigaChat («@бобик», путь Talk). Фото — следующим срезом | GigaChat PERS (путь Talk) | спецификации утверждены 2026-09-19 (ред. 1–5); план реализации → код с тестами → выкат по «деплой» |

### Этап F — Платформа (месяц+)

| ID | Задача | Источник |
|---|---|---|
| F1 | Part B: переезд устройства на новое именование, одним окном | W5.1, R3-01 |
| F2 | `deploy.sh`: сверка SHA git ↔ контейнер, тесты, откат | R3-02 |
| F3 | План выхода с EOL (Ubuntu 18.04 / JetPack 4.6), проверенный restore-drill'ом на другой машине | NAS-LIFE-001, R6-01 |
| F4 | Immich v3 — после D6, B1, B3 и проверенного restore фото | R6-02 |
| F5 | coturn или Talk-видео LAN-only | W5.3 |
| F6 | Статья Habr ч. 2: «SoR дома, мозги в РФ-облаке» + «полупереезд» + «8 ГБ/сутки на SD». Материалы копятся по ходу — `docs/articles/HABR_PART2_MATERIALS.md` (DoD §3 п. 5) | W5.7 |

### Этап G — инженерный стандарт и чистка репозитория (после D–F; исходник — мастер-промт)

Источник: `docs/research/NAS_CODE_QUALITY_AND_REPOSITORY_CLEANUP_MASTER_PROMPT.md` (поправки — в преамбуле того же файла).
**Когда:** когда проект реализован «в полноте» — бот со всеми срезами, D2/D4/D5/D6 закрыты, выкатов в очереди нет.
Исключение — G0: четыре дешёвых сторожа ставятся раньше, они ловят то, что иначе накапливается.

| ID | Задача | Замер/цель | Когда |
|---|---|---|---|
| G0 | Дешёвые сторожа заранее: Gitleaks (история + рабочее дерево), Dependabot (Python, Actions, Docker), CodeQL, `scripts/quality/check_repository_hygiene.py` + `config/repository-policy.yml` | сейчас: `check_no_secrets.sh` смотрит только рабочее дерево; обновления зависимостей не отслеживаются | **можно сразу** |
| G1 | Базовая линия: размер репо, tracked-файлы, дубли, прогон всех тестов, отчёт в `docs/local/` (не в git) | 2026-09-20: 545 файлов, 20,2 МБ, docs+assets = 96 % дерева | начало этапа |
| G2 | Чистка репозитория: 62 картинки, один файл в 6 копиях, ещё 4 — в 4 копиях; `git rm --cached` + `.gitignore`, **локальные файлы остаются** | цель: убрать дубли и сырые артефакты, историю **не** переписывать | G1 |
| G3 | Инструменты по одному: Ruff (сначала новые сервисы), затем mypy на `services/*`; `pyproject.toml` | 30 python-файлов; legacy-зона `scripts/` остаётся на 3.6 (vermin уже в воротах) | G1 |
| G4 | Ворота FAST/FULL поверх существующего `preflight.sh` (9 разделов) + `pre-push`; одна точка входа (`make quality` или скрипт) | второй gate не заводить | G3 |
| G5 | Docker и CI: Hadolint, `docker compose config`, yamllint, Trivy (в CI); actionlint уже есть | 4 workflow — свести без дублей | G3 |
| G6 | Производительность и память: py-spy и Memray **на рабочей станции/в контейнере**, не на Jetson (4 ГБ, боевой); baseline в `tests/performance/baseline.json` только агрегаты | оптимизировать только измеренное узкое место | после G4 |
| G7 | Документация для новичка: README остаётся **одним двуязычным** (правило №15), но beginner-first; разделение `docs/` на user/admin/development — по фактическим ссылкам, не механически | 253 markdown-файла | после G2 |
| G8 | Знания проекта: не заводить `skills/` — стандартом остаются `CLAUDE.md`, `AGENTS.md`, `docs/32_QUALITY_GATE.md`; в `AGENTS.md` — правило «задача не закрыта, пока не прошли ворота» | промт сам запрещает второй фреймворк | после G4 |
| G9 | Итоговый отчёт `docs/development/CODE_QUALITY_AND_REPOSITORY_CLEANUP_REPORT.md` + таблица «было/стало» | честно указать, что история git не переписывалась | конец этапа |

**Поправки к промту (наш проект):** README — один двуязычный файл, не пара RU/EN; локальная зона — существующий `docs/local/` и `.git/info/exclude`, а не новый `_local/`; Project Skill — существующие `CLAUDE.md`/`AGENTS.md`, отдельный каталог `skills/` не создавать; ворота — расширение `scripts/quality/preflight.sh`, второй gate запрещён; профилирование — вне Jetson.

### Порядок и зависимости

```text
A1 → A2 → A3 ─┐
A4 (окно) ────┼→ B1 → B2 → B3(owner tenant_id) → B6
A6            │   C1 → C2 → C4/C5 → C3,C6..C11
              └→ D4, D6 → D5(окно) ; D1/D2 (owner ИБП) ; D3 после B3/E5
E1..E8 — после A–C ; F — после B и D
```

Параллельно без устройства: A1, A2, A3 (код), A6, B1/B2 (код), C1–C8 (код), D4, D6, E1.
Требуют «деплой»: A3, A4, B1–B2, B3, C*, D2–D6. Требуют владельца: B3 (tenant_id), B5, D1, D4-решения §2.2.

---

## 5. Матрица провайдеров LLM (целевая)

| Priority | Provider | Model | Use | Failover |
|---|---|---|---|---|
| 1 | `gigachat` | `GigaChat-2` (Max — только по E1 с учётом квоты) | семья, Talk | → 2 на 429/5xx |
| 2 | `deepseek` | `deepseek-chat` | fallback | — |
| 3 | `cloudru` | FM internal (Giga/Qwen) | админ, RAG по докам | → error |
| — | `ollama` | — | dev only | off in prod |
| — | внешние FM (GPT/Claude) | — | явный admin opt-in + SANITIZED | off |

Картинки: GigaChat-2-Max text→image. Vision семейных фото: **запрещено**.

## 6. Backup topology (целевая, с фактом на 2026-09-19)

| Layer | What | Where | Факт 2026-09-19 |
|---|---|---|---|
| L0 | Immich + NC данные, БД | SSD | ✅ |
| L1 | копия Immich | HDD `backups/immich` | ✅ ежедневно; с 2026-09-19 только чтение через шары (B2) |
| L1b | дампы БД (7 шт.) | SSD | ✅ fail-closed |
| L1c | конфиг, `.env`, файлы NC, Samba users, дампы | HDD restic (шифр.) | ✅ с 2026-09-19, ежедневно 03:40, учения ежемесячно |
| L2 | restic шифрованный | Cloud.ru S3 | ❌ blocked (B3); **legacy L2 = Vostro pull дампов** ✅ |
| L3 | код | GitHub + GitVerse | ✅ |

## 7. Риски

| Risk | Mitigation |
|---|---|
| Выкат `main` с P0 шлюза | A1–A2 до любого деплоя |
| Полупереезд устройства ломает юниты | A4, A5, F1 |
| Обесточивание | D1–D3 |
| Потеря конфигурации/секретов с SD | B1, B3 |
| Cloud.ru расходы | E5 до B3; free tier — **NOT VERIFIED**, проверить в консоли |
| Квота GigaChat-Max (≈25 млн) | E1; не включать smart routing без учёта |
| S3 хранит семейно-смежные данные | только restic с шифрованием; ключ шифрования не в облаке |
| Amnezia | не трогать; правило №13 |
| Статусы без проверки | DoD §3 |

## 8. Исследовательский трек (не план)

`research/…Multi-Provider Photo AI Orchestrator.md` и `research/…Photo RAG на Jetson Nano.md` —
**промпты** для внешних моделей, не результаты. В план развития не входят, пока нет:
1. решения владельца по D4 и классу приватности семейных фото (по умолчанию — `LOCAL_ONLY`);
2. соответствия `AGENTS.md` п. 4 и ADR-0010 (новый ADR, если идём дальше);
3. результата на **несемейных** данных (пилот на станции / Kaggle — только публичные наборы).

## 9. Что сознательно не делаем
Nextcloud/Immich в Cloud.ru как primary; K8s; Managed RAG по альбому; Immich ML на Jetson; прод-
зависимость от станции/Vostro; порты VPS мимо VPN; секреты в git; in-place апгрейд Jetson;
автоматический деплой; мутации АСУДД в `@бобик`; семейные фото во внешние LLM/GPU; апгрейд Immich
«заодно»; покупка нового сервера без доказанного узкого места (аудит: CPU/RAM/I/O не упираются).

## 10. Критерии приёмки «эры Сбер» (MVP)

- [x] ADR-0007/8/9; 29–31 superseded
- [x] Device: GigaChat-2 на `api.giga.chat`, `prefer_local=false` (2026-09-08)
- [x] Immich L1 на HDD, timer
- [x] Баланс Giga виден + таймер
- [x] GitVerse `NAS_HOME` актуален
- [x] Cloud.ru FM: adapter + live chat 200
- [x] Amnezia peer count не уменьшался (19 на 2026-09-19)
- [x] Этап A закрыт по DoD в git и **на устройстве** (2026-09-19, `DEPLOY_STAGE_A_2026-09.md`)
- [x] L1c конфиг/NC + изоляция L1 (B1–B2) — на устройстве 2026-09-19
- [ ] S3 off-site (B3) — ⏸ отложено владельцем 2026-09-19, off-site на Vostro
- [x] Этап C в git и **на устройстве** (2026-09-19), кроме C9
- [ ] ИБП (D1) — ⏸ отложен владельцем 2026-09-19
- [ ] Внешний сторож (D3) — ✅ git 2026-09-19 (44 теста), выкат по `DEPLOY_D3_WATCHDOG_2026-09.md`

## 11. Следующий шаг

1. ~~Этап A~~ — ✅ git + device 2026-09-19.
2. **Этап B** — ✅ git + **device** 2026-09-19 (B1, B2, B6). B3 (S3) — код готов, **отложен владельцем**; B4 Vostro pull остаётся; B5 закрыт (копии архива нет, риск принят).
3. **Этап C** — ✅ git + **device** 2026-09-19 (кроме C9 — оставлен как есть по решению владельца).
3a. **Telegram-бот + качалка (E9), первый срез — приоритет владельца** (запрос сына): обе спецификации
    утверждены — `docs/superpowers/specs/2026-09-19-telegram-family-bot-design.md`,
    `docs/superpowers/specs/2026-09-19-home-downloader-design.md` (ред. 1–5: обращение «@бобик» по имени,
    размер закачки без предела, SOCKS на `172.17.0.1:1080`, вопросы к GigaChat — в этом же срезе; фото —
    следующим срезом). **✅ Реализовано в git 2026-09-19** (`90b52bc`, 90 тестов API, финальное ревью Opus);
    выкат — по «деплой», runbook `DEPLOY_DOWNLOADER_2026-09.md`.
3b. **E2** ✅ git; **D3** ✅ git — оба ждут «деплой» (D3: сначала спайк в Cloud.ru, runbook §0).
3c. Дальше без владельца: E5 (алерт расходов Cloud.ru — **до** выката D3 и E6), E1 (маршрутизация с учётом квоты Max, закрывает D5), E3 (`@бобик` «что сломалось?»), D2 (алерт после аварийной загрузки — важнее без ИБП), затем спайк E6.
4. **Owner:** D5 (smart routing) и D6 (окно Part B); `/start` в @bobik_borovskoy_bot для chat_id (D3).

## 12. EN summary

Consolidated edition (2026-09-19). The Sber-era architecture stays: Jetson is the system of record,
the VPS is the network edge, and Cloud.ru plus GigaChat form the RU AI/storage edge. GigaCode's Hardening
Sprint (H01–H16) and the 2026-09-19 live audit are merged into one queue with unique IDs.
Stage A contains blockers: the gateway P0 in `main`, gates that skip gateway tests, the unfinished service
token and the broken SSD recovery. Stage B covers data: config and Nextcloud backups, isolation of the
HDD copy, and Cloud.ru S3 as L2, with the Vostro pull kept until S3 works. Stage C is auth and RBAC.
Stage D covers the UPS, power-loss alerts, a Cloud.ru Container Apps watchdog and SD write reduction.
Stage E covers GigaChat routing that respects the separate Max quota, `@бобик` diagnostics with no LLM
actions, and admin RAG over docs via FM. Stage F covers device migration, deploy tooling and the EOL exit.
Unverified "✅" statuses were withdrawn, and a Definition of Done is mandatory. The Photo AI Orchestrator
is research only.

Status 2026-09-19 (evening): stages A–C are on the device. E2 (GigaChat quota alert) and D3 (Cloud.ru
watchdog through the VPS, 44 tests) are in git and wait for an owner-triggered deploy. Owner decisions:
S3 postponed (off-site stays on the Vostro), UPS postponed, no second copy of the 1.4 TB archive (risk
accepted), Immich ML on Cloud.ru only within the free tier.

Later that night, the owner's son asked for a home downloader on the Jetson, and the owner gave it priority
(E9). Two specs were approved through five revisions: the Telegram bot's main interface is chat with
`@bobik_borovskoy_bot` in the family group, addressed by name ("@бобик ...") exactly like `@бобик` in Talk —
so the bot's group privacy mode is turned off, and every message without the name is dropped at once,
unstored and unlogged. aria2 downloads through the Jetson's home internet, never the VPS (rule #13: the VPS
carries ~25 VPN peers, and a rights-holder complaint could get its IP blocked). There is no size cap:
downloads up to 20 GB go through the SSD, larger ones straight to the HDD; the Telegram 20 MB limit applies
only to a `.torrent` file sent in chat. GigaChat questions ("@бобик <question>", reusing the Talk path) are
part of this same first slice; photos come later. The Jetson cannot reach Telegram directly (3 of 3 timeouts
measured 2026-09-19), so an SSH SOCKS tunnel listens on the docker0 address 172.17.0.1. E9 is
implemented in git (`90b52bc`) and awaits an owner-triggered deploy. Next: E5, E1, E3, D2, voice messages.

## 13. Changelog

| Date | Change |
|---|---|
| 2026-09-04 | Initial plan from owner directives + probes + audits |
| 2026-09-08 | W1/W2 device done; giga-balance timer; S3 blocker |
| 2026-09-18 | Hardening Sprint W0.5 from `audit_new` (H01–H16) |
| 2026-09-19 | Owner decisions D1/D2/D3/D4; E2 + D3 in git (spec, plan, runbook) |
| 2026-09-19 | **Consolidated edition**: H* + audit 2026-09-19 + Sber decisions in one queue (A–F); withdrawn statuses §1.1; DoD §3; owner decisions §2.2; research track §8 |
| 2026-09-19 | **E9** added — Telegram bot + home downloader, owner priority (son's request); specs approved through revisions 1–5 |
| 2026-09-19 | **E9** implemented in git (`90b52bc`): aria2 downloader + first Telegram bot slice; awaiting deploy |
| 2026-09-19 | **E9 deployed** on Jetson 17:03 UTC: end-to-end download + GigaChat checked, announcement sent to the family group; rule #13 identical |
