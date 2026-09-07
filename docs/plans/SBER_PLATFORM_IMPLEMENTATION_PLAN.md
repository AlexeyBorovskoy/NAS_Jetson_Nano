# План внедрения платформы Сбер в NAS_Jetson_Nano

> **Дата:** 2026-09-04  
> **Статус:** план (не канон до приёмки владельцем)  
> **Область:** семейное облако на Jetson Nano + внешние сервисы экосистемы Сбера  
> **RU + EN:** ниже основной текст на русском; краткое EN-резюме в §14.
>
> Связанные решения владельца (2026-09-04):
> - рабочая станция RTX — **не узел проекта** (только разработка);
> - Vostro — **вне проекта**;
> - вторая копия Immich — **на HDD 2 ТБ Jetson** (on-site, не off-site).

---

## 1. Цель

Собрать **осознанный, минимальный и безопасный** контур использования сервисов Сбера
вокруг уже работающего Stage 1 (Nextcloud + Immich + Talk-бот + LLM Gateway), не ломая:

- правило Amnezia/VPN на VPS (~19 клиентов);
- LAN-only модель (ADR-0003) и reverse SSH (ADR-0005);
- запрет выноса семейных фото во внешние LLM без явного risk-note;
- публичный git (секреты только на устройстве / в gitignored store).

**Не цель:** перенос домашнего NAS в Cloud.ru Evolution, замена Jetson, «всё в одной
экосистеме Сбера» как у research-обзора Белгорода (там вердикт 03.09: **не канон** для АСУДД).

---

## 2. Карта экосистемы Сбера (что реально доступно физлицу)

Источники: официальная документация developers.sber.ru / cloud.ru / gitverse.ru
(снятие 2026-09-04), плюс уже реализованный код NAS и research `E:\Belgorod_platform`.

### 2.1. GigaChat API (ядро для NAS)

| Элемент | Факт на 2026-09-04 |
|---|---|
| **Аудитория** | Физлица: scope `GIGACHAT_API_PERS` |
| **OAuth** | `POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth`, токен **30 мин** |
| **Базовый URL (новый)** | `https://api.giga.chat` — **целевой с 17.07.2026** для всех |
| **Базовый URL (legacy)** | `https://gigachat.devices.sberbank.ru/` — ещё работает для старых подключений, **будет выведен** |
| **TLS** | Сертификаты **НУЦ Минцифры** → нужен bundle (у нас `config/certs/russian_trusted_bundle.pem`) |
| **Потоки (физлицо)** | **1 concurrent stream** (и freemium, и платный пакет) |
| **OpenAI-совместимость** | Частичная: chat / embeddings / models; SDK OpenAI с `base_url=https://api.giga.chat/v1` |
| **Рекомендация вендора** | GigaChain / `langchain-gigachat`; утилита `gpt2giga` |

#### Модели генерации (ID в запросе)

| Семейство | ID | Freemium (физлицо, 12 мес) |
|---|---|---|
| Lite | `GigaChat`, `GigaChat-2` | **250M** токенов |
| Pro | `GigaChat-Pro`, `GigaChat-2-Pro` | **40M** |
| Max | `GigaChat-Max`, `GigaChat-2-Max` | **25M** |
| Ultra | `GigaChat-3-Ultra` | **50M** (freemium; на платных тарифах Ultra пока **нет**) |

Суммарно freemium: **365M** токенов генерации на 12 месяцев (с 01.09.2026 условия
для *новых* клиентов могут уходить на cloud.ru — у действующих физлиц freemium
описан в [тарифах физлиц](https://developers.sber.ru/docs/ru/gigachat/tariffs/individual-tariffs)).

Платные пакеты (ориентир, с НДС, 1 месяц): Lite 20M ≈ 1300 ₽; Pro 3M ≈ 1500 ₽;
Max 3M ≈ 1950 ₽; Embeddings 50M ≈ 700 ₽.

#### Модели эмбеддингов

`Embeddings`, `Embeddings-2`, `EmbeddingsGigaR`, `Embeddings-3B-2025-09` —
тарифицируются **отдельно** от генерации.

#### REST-поверхность (справочник API)

| Группа | Методы (смысл) |
|---|---|
| Auth | OAuth token |
| Models | `GET /models`, retrieve |
| Chat | `POST /v1/chat/completions`, `POST /v2/chat/completions` |
| Embeddings | `POST /embeddings` |
| Files | upload / download / delete / list (изображения, документы, аудио) |
| Images / 3D | генерация изображений (Kandinsky path), 3D-модели |
| Functions | function calling |
| Batches | пакетная обработка |
| Utility | `POST /tokens/count`, `GET /balance`, AI-check текста, validate function |
| gRPC | отдельный контур + свои сертификаты |

**Ограничения контента:** `finish_reason: blacklist` на запрещённые темы
(политика, экстремизм, NSFW и т.д. — см. limitations docs).

**Важно для семьи (уже проверено проектом 2026-08-10):** GigaChat API
**не редактирует** пользовательские фото (ретушь/restore). Vision/анализ —
только у моделей класса Max; upload + chat. Флаг `LLM_ALLOW_IMAGE_ANALYSIS=false`
остаётся по умолчанию.

### 2.2. Cloud.ru (Sber Cloud / Evolution)

| Что | Оценка для NAS |
|---|---|
| Foundation Models (OpenAI-compatible, multi-model) | **Кандидат фазы C** — единый `base_url`, каталог Giga/Qwen/DeepSeek/Whisper/OCR |
| VM / VPC / Managed PG / Object Storage | **Не для Stage 1 семьи** — усложнение, деньги, не нужно при живом Jetson |
| «Гига-помощник» кабинета | Другой продукт, не наш Talk-бот |
| Оплата GigaChat для *новых* клиентов с 01.09.2026 | Следить; наш ключ PERS уже выдан через developers.sber.ru |

Вердикт соседнего проекта (`Belgorod_platform`, 03.09.2026): Cloud.ru / Giga
**не** вставлять в боевую очередь АСУДД; для NAS — **отдельный** план (этот
документ), без смешения с ASUDD credentials policy.

### 2.3. GitVerse (gitverse.ru)

| Элемент | Факт |
|---|---|
| Назначение для NAS | **Дополнительное зеркало кода** `Alexey_Borovskoy/NAS_HOME` (не System of Record) |
| Канон | GitHub `AlexeyBorovskoy/NAS_Jetson_Nano` (публичный) |
| API | `https://api.gitverse.ru` + `Authorization: Bearer` + `Accept: application/vnd.gitverse.object+json;version=1` |
| SSH | `git@gitverse.ru:user/repo.git`, порт 22; ключ `~/.ssh/gitverse_ed25519` уже в ssh config |
| CI/CD | Опционально позже; не блокирует Stage 1 |

Правило (из опыта Белгорода): remote имя **`gitverse`**, **не** pushurl у `origin`
(dual-push ломает другие зеркала). Сначала private/public пустышка владельцем,
потом `git remote add` + push.

### 2.4. Что сознательно вне плана

- SaluteSpeech / SmartHome / банковский API Сбер ID для платежей;
- перенос семейных фото в Object Storage Cloud.ru;
- Kubernetes / Container Apps для Nextcloud/Immich;
- использование GigaChat как единственного провайдера **без** redaction gateway;
- любые write-операции к Amnezia на VPS.

---

## 3. Что уже есть в NAS (as-is)

| Компонент | Состояние |
|---|---|
| `services/llm-gateway` | Провайдеры: **deepseek**, **gigachat**, **ollama** |
| GigaChat в коде | OAuth cache 30 мин, TLS bundle, chat, file upload/download, image generate, budget+redaction |
| Default | `LLM_PROVIDER=deepseek` |
| Talk-бот `@бобик` | Ходит в gateway **без** поля `provider` → default DeepSeek |
| CA bundle | закоммичен, воспроизводим |
| Секреты | `gigachat/` gitignored; device `~/nasa/config/.env` |
| Документация | `docs/08_LLM_GATEWAY_DEEPSEEK.md` (имя устарело — шлюз уже multi-provider) |

**Вывод:** «подключить Сбер» ≠ писать OAuth с нуля. Нужно **активировать, обновить
URL/модели, маршрутизировать семью и закрыть пробелы** (balance, embeddings,
api.giga.chat, GitVerse mirror).

---

## 4. Принципы внедрения (safety)

1. **Один вход наружу** — только LLM Gateway (redaction + budget + audit).
2. **Фото семьи** — не в GigaChat analysis; generate-by-text допустим; restore — нет.
3. **Freemium first** — Lite/Pro/Max/Ultra квоты; платные пакеты только после
   исчерпания и явного OK владельца.
4. **1 поток** — очередь на gateway, без параллельных storm от бота.
5. **Секреты** — только device `.env` / gitignored; не в GitVerse/GitHub/docs.
6. **Amnezia** — до/после любых VPS-правок: контейнеры up, peer count не упал.
7. **Станция/Vostro** — не в архитектуре; ollama-prefer выключить в проде.
8. **Вторая копия Immich** — локальный HDD; это **не** замена off-site и **не**
   часть Сбер-платформы, но идёт параллельным P0 данных.

---

## 5. Целевая архитектура (после внедрения)

```
Семья (Talk / API)
        │
        ▼
┌───────────────────┐
│  LLM Gateway      │  redaction · budget · 1-flight queue
│  Jetson :8090     │
└─────────┬─────────┘
          │
    ┌─────┼──────────────┐
    ▼     ▼              ▼
 DeepSeek  GigaChat    (future: Cloud.ru FM)
           │
           ├─ api.giga.chat  (primary)
           ├─ models: Lite default, Max vision-only, Ultra opt-in
           ├─ embeddings (optional RAG admin docs)
           └─ GET /balance → monitoring

GitHub (канон) ──mirror──► GitVerse NAS_HOME
Jetson SSD live ──copy──► Jetson HDD 2TB (Immich)   [не Сбер]
```

Маршрутизация (рекомендация):

| Класс запроса | Провайдер | Модель |
|---|---|---|
| Семейный чат `@бобик` | **gigachat** | `GigaChat-2` (Lite freemium) |
| Админ/диагностика/код | deepseek **или** gigachat Pro | по флагу |
| Генерация картинки по тексту | gigachat | `GigaChat-2-Max` |
| Анализ/upload семейного фото | **запрет** | 403 |
| Embeddings для admin RAG (логи, runbook) | gigachat | `Embeddings` / `EmbeddingsGigaR` |
| Cloud.ru FM | не в v1 | фаза C |

---

## 6. Фазы внедрения

### Фаза 0 — Инвентаризация и live-probe (1 вечер)

**Что меняется:** ничего в проде, только измерения.

| # | Действие | Verify |
|---|---|---|
| 0.1 | OAuth + `GET /models` + `GET /balance` с ключом PERS (Windows или Jetson) | token ok, список моделей, остатки freemium |
| 0.2 | Сравнить legacy URL vs `api.giga.chat` | оба 200 или зафиксировать cutover |
| 0.3 | `curl` Jetson `/health` → `providers.gigachat` | true/false |
| 0.4 | GitVerse: существует ли `NAS_HOME`, SSH `git@gitverse.ru` | 200/404, auth ok |
| 0.5 | Зафиксировать результаты в checkpoint (без секретов) | этот план §11 |

**Rollback:** n/a.

### Фаза A — GigaChat production-ready на Jetson (основной блок)

**Что меняется:** device `.env`, compose env defaults, docs; опционально код gateway.

| # | Действие | Файлы (ожидаемо) |
|---|---|---|
| A.1 | Выставить `GIGACHAT_AUTH_KEY` на Jetson, если missing | `~/nasa/config/.env` only |
| A.2 | `GIGACHAT_BASE_URL=https://api.giga.chat/v1` (cutover с legacy) | `.env`, `.env.example`, compose |
| A.3 | `GIGACHAT_MODEL=GigaChat-2` (Lite freemium); `GIGACHAT_IMAGE_MODEL=GigaChat-2-Max` | `.env*` |
| A.4 | Опционально Ultra: `GIGACHAT_MODEL_ULTRA=GigaChat-3-Ultra` для opt-in | код + env |
| A.5 | `LLM_PREFER_LOCAL=false` (станция вне проекта) | `.env` |
| A.6 | `LLM_PROVIDER=gigachat` **или** dual-route (см. A.7) | решение владельца |
| A.7 | Talk-бот: `TALK_BOT_LLM_PROVIDER=gigachat` в payload | `talk_bot.py`, config |
| A.8 | Очередь/семафор 1 in-flight на gigachat (лимит физлица) | `llm-gateway` |
| A.9 | Endpoint proxy `GET /v1/provider/gigachat/balance` → upstream `/balance` | gateway + monitoring |
| A.10 | Алерт: balance Lite < порога / HTTP 429 / blacklist spike | monitoring scripts |
| A.11 | Регрессия: chat Lite, image Max (text-only), analysis 403 | tests + manual |
| A.12 | Обновить `docs/08_…` (rename multi-provider), CHANGELOG | docs |

**Verify:**

```bash
curl -s http://127.0.0.1:8090/health   # providers.gigachat=true
curl -s http://127.0.0.1:8090/v1/chat -H 'Content-Type: application/json' \
  -d '{"prompt":"Скажи одно слово: ок","provider":"gigachat","user":"admin"}'
# @бобик в Talk — ответ с provider gigachat в usage
```

**Rollback:** `LLM_PROVIDER=deepseek`, убрать `TALK_BOT_LLM_PROVIDER`,
`GIGACHAT_BASE_URL` вернуть legacy; `docker compose up -d` gateway.

### Фаза B — GitVerse зеркало `NAS_HOME`

**Что меняется:** remote + push политики; **не** секреты.

| # | Действие |
|---|---|
| B.1 | Владелец создаёт на gitverse.ru репозиторий `Alexey_Borovskoy/NAS_HOME` (public или private — решение) |
| B.2 | Проверка токена/SSH на **существующий** репо (404 ≠ «токен плохой») |
| B.3 | `git remote add gitverse git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git` |
| B.4 | Первый push: `main` как есть **или** orphan-clean, если когда-либо в history были секреты (history NAS уже чистилась 2026-06-28 — обычный push допустим после `check_no_secrets`) |
| B.5 | README badge / docs: «Mirror: GitVerse NAS_HOME» |
| B.6 | Опционально: GitVerse Actions только lint/docs — без деплоя на Jetson |

**Не делать:** dual-pushurl на `origin`; токен в `.env` репозитория; issues GitVerse как task backend семьи.

**Verify:** `git ls-remote gitverse`; страница репо открывается; CI green optional.

**Rollback:** `git remote remove gitverse`.

### Фаза C — Расширения GigaChat (по потребности)

| # | Возможность | Зачем семье | Приоритет |
|---|---|---|---|
| C.1 | Embeddings + маленький admin-RAG (runbooks, не фото) | «Бобик, как восстановить SSD?» по своим docs | P2 |
| C.2 | Streaming token в Talk | UX | P3 |
| C.3 | Structured output / functions | стабильные команды бота | P2 |
| C.4 | Batches | ночной разбор логов | P3 |
| C.5 | `GigaChat-3-Ultra` opt-in | сложные вопросы, жрёт freemium Ultra | P2 |
| C.6 | Cloud.ru Foundation Models adapter | multi-model одним ключом | P3 / later |
| C.7 | OpenAI SDK path через `api.giga.chat` | упростить код | P2 |

Каждый пункт C — отдельный маленький PR + quality gate.

### Фаза D — Данные (параллельно, не Сбер, но блокирует «платформу дома»)

| # | Действие |
|---|---|
| D.1 | restic/rsync Immich library → `/mnt/hdd2tb/backups/immich/` |
| D.2 | timer + restore-drill одного файла |
| D.3 | preflight free space на HDD |

Это **on-site** копия. Off-site после исключения Vostro — отдельное решение
(внешний диск / другой cloud **не Сбер Object Storage с фото** без risk doc).

---

## 7. Матрица «бесплатные ресурсы клиента» → использование в NAS

| Ресурс Сбера | Как использовать | Как не использовать |
|---|---|---|
| Freemium Lite 250M/12м | Default `@бобик`, админ-FAQ | Параллельные 10 воркеров (лимит 1 поток) |
| Freemium Pro 40M | Сложные объяснения, structured | Постоянный default |
| Freemium Max 25M | Text→image, редкий vision **без** семейных фото | Анализ альбома Immich |
| Freemium Ultra 50M | Opt-in «подумай глубже» | Фоновый batch |
| Embeddings пакет | Admin RAG | Индексация 7k семейных фото в облаке |
| GitVerse storage/CI | Mirror кода | Хранение `.env`, дампов БД |
| Cloud.ru trial (если появится) | Только FM API SANITIZED | Хостинг Nextcloud |

Учёт: gateway `/v1/usage` + периодический `/balance` Сбера; не полагаться только
на внутренний счётчик.

---

## 8. Изменения кода (чеклист, не делать всё сразу)

1. `GIGACHAT_BASE_URL` default → `https://api.giga.chat/v1`
2. `talk_bot._ask_llm`: добавить `provider` из settings
3. Семафор/asyncio lock на gigachat calls
4. `GET /balance` proxy + cache 5–15 мин
5. Модель matrix в config: lite/pro/max/ultra
6. Тест: mock OAuth + models list; vermin 3.6- совместимость gateway
7. Docs rename 08 → multi-provider; ссылка на этот план
8. `docs/plans/README.md` + опционально `docs/index.md` — ссылка

---

## 9. GitVerse: операционный runbook (кратко)

```bash
# 1) После создания репо владельцем:
cd "E:/Linux mint/virtual_VM/shared/NAS_Jetson_Nano"
bash scripts/quality/preflight.sh
git remote add gitverse git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git
git push -u gitverse main

# 2) Проверка
git ls-remote gitverse
ssh -T -i ~/.ssh/gitverse_ed25519 -o IdentitiesOnly=yes git@gitverse.ru
```

Если репозиторий ещё 404 — **не** добавлять remote «на вырост».  
Если GitVerse rate-limit (429) — повторить позже; не крутить в цикле.

Имя `NAS_HOME` vs локальное `NAS_Jetson_Nano`: допустимо как product name на
GitVerse; в README явно: «канон GitHub NAS_Jetson_Nano, зеркало GitVerse NAS_HOME».

---

## 10. Риски и митигации

| Риск | Митигация |
|---|---|
| Исчерпание freemium | balance poll + soft switch на DeepSeek |
| 1 поток → таймауты бота | queue + timeout chain (уже грабля 60s vs 120s) |
| Cutover URL api.giga.chat ломает TLS/DNS | dual-try legacy fallback 1 релиз |
| Утечка ключа в mirror | preflight secrets; gitignore `gigachat/` |
| Семья шлёт фото боту | analysis 403; UX «фото не покидают дом» |
| blacklist finish_reason | дружелюбный ответ бота, счётчик |
| GitVerse 429 / пустой аккаунт | ручное создание репо, без автоматики |
| Смешение с ASUDD-секретами Белгорода | **отдельные** ключи; NAS только PERS home |
| On-site HDD ≠ disaster recovery | честно в docs; не называть off-site |

---

## 11. Результаты live-probe (фаза 0, 2026-09-04)

> Только статусы и числа. Секреты не записывались.
>
> **Источник ключа GigaChat для probe:** gitignored store NAS
> (`gigachat/`, тот же ключ уже **set** в контейнере `homecloud_llm_gateway` на Jetson).
> **В `E:\Belgorod_platform` файлов/переменных GigaChat / Cloud.ru FM / GitVerse Bearer
> не найдено** — там research + SSH-ключ GitVerse на машине владельца
> (`~/.ssh/gitverse_ed25519`), не токены API Сбера в дереве ASUDD.

| Проверка | Результат | Дата |
|---|---|---|
| OAuth PERS | **200**, token+expires present, TLS OK с bundle | 2026-09-04 |
| `api.giga.chat` GET `/models` | **200**, 10 id: GigaChat-2, -2-Max, -2-Pro, -3-Lightning, -3-Pro, -3-Ultra, Embeddings, Embeddings-2, EmbeddingsGigaR, GigaEmbeddings-3B-2025-09 | 2026-09-04 |
| legacy devices host GET `/models` | **200**, 14 id (вкл. legacy `GigaChat`, Max/Pro/Plus, previews) | 2026-09-04 |
| `/balance` (оба base) | Ultra **50M**; Pro **40M**; Max **~24.99M**; GigaChat/Lite bucket **~250.0M** | 2026-09-04 |
| chat `GigaChat-2` | **200** stop на обоих base | 2026-09-04 |
| chat legacy id `GigaChat` | на `api.giga.chat` **404**; на legacy **200/500** (flaky) | 2026-09-04 |
| embeddings | **402** Payment Required (оба base) | 2026-09-04 |
| Jetson via VPS :10022 | **up**, host nasa-jetson, 13 containers ~3d | 2026-09-04 |
| Jetson `/health` | ok; **gigachat=true**; deepseek=true; ollama=true; `provider=deepseek`; `prefer_local=true` | 2026-09-04 |
| Jetson gateway env | `GIGACHAT_KEY=set`; `BASE_URL=…devices.sberbank…/api/v1`; `MODEL=GigaChat` (legacy id) | 2026-09-04 |
| df storage/hdd2tb | SSD 6% (204G free); HDD 76% (462G free) | 2026-09-04 |
| GitVerse SSH | **OK** as `Alexey_Borovskoy` | 2026-09-04 |
| GitVerse `NAS_HOME` | **exists**; `ls-remote` HEAD/master = `809ac973…` | 2026-09-04 |

**Вывод probe для A.2/A.3:** на Jetson сменить `GIGACHAT_MODEL` → `GigaChat-2` и
предпочтительно `GIGACHAT_BASE_URL` → `https://api.giga.chat/v1` (legacy id на новом
host отсутствует). Embeddings — только после оплаты пакета. Freemium генерации
почти полный.

---

## 12. Критерии приёмки платформы Сбер (v1)

- [ ] `@бобик` отвечает через GigaChat Lite при доступном ключе
- [ ] DeepSeek остаётся fallback при 429/5xx Giga
- [ ] `/health` показывает `gigachat: true`
- [ ] Base URL — `api.giga.chat` (или dual с планом отключения legacy)
- [ ] Balance виден админу (endpoint или daily report)
- [ ] Семейные фото analysis = 403
- [ ] 1 in-flight на Giga; нет шторма
- [ ] GitVerse `NAS_HOME` содержит актуальный `main` без секретов
- [ ] Quality gate green; Amnezia peer count не изменился (если VPS не трогали — n/a)
- [ ] Документация 08 + этот план согласованы с фактом

---

## 13. Порядок работ (рекомендуемый)

```
Фаза 0  probe (Giga + Jetson + GitVerse)     ← сейчас
Фаза A  Giga default/family path             ← главный value
Фаза D  Immich → HDD                         ← параллельно данным
Фаза B  GitVerse mirror                      ← когда репо создан
Фаза C  embeddings / ultra / FM              ← по желанию
```

Жёсткие зависимости: A требует 0; B требует создание репо владельцем; C после A;
D независима от Сбера.

---

## 14. EN summary

Sber platform for this home NAS is **not** “move everything to Cloud.ru”.
It is: (1) finish GigaChat as the family default behind the existing redaction
gateway, migrating to `api.giga.chat`, freemium model matrix, single-stream
queue, balance monitoring; (2) optional GitVerse mirror `NAS_HOME`;
(3) later embeddings/admin-RAG and optional Cloud.ru Foundation Models;
(4) Immich second copy on local 2 TB HDD in parallel — on-site, not off-site.
Workstation and Vostro stay out of the architecture. Secrets never enter git
or GitVerse. Amnezia on the VPS remains untouchable.

---

## 15. Ссылки

- GigaChat docs: https://developers.sber.ru/docs/ru/gigachat/guides/main  
- Tariffs individuals: https://developers.sber.ru/docs/ru/gigachat/tariffs/individual-tariffs  
- API auth / URL cutover: https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api  
- OpenAI compatibility: https://developers.sber.ru/docs/ru/gigachat/guides/compatible-openai  
- Models: https://developers.sber.ru/docs/ru/gigachat/models/main  
- Limitations: https://developers.sber.ru/docs/ru/gigachat/limitations  
- GitVerse (target): https://gitverse.ru/Alexey_Borovskoy/NAS_HOME  
- NAS gateway code: `services/llm-gateway/app/main.py`  
- Belgorod research (non-canon for ASUDD): `E:\Belgorod_platform\docs\research\2026-09-03-cloud-ru-gitverse-verdict.md`  
- **Public probe 2026-09-04 (no secrets):** [`CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md`](CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md)  
- Cloud.ru FM api-ref: https://cloud.ru/docs/foundation-models/ug/topics/api-ref  
- Cloud.ru API registry: https://cloud.ru/docs/console_api/ug/topics/overview__reestr_api

---

## 16. Следующий безопасный шаг

1. ~~Фаза 0~~ — **сделана** (§11).  
2. ~~Default gigachat + git templates + Talk provider + gateway lock~~ — **в git** (2026-09-07).  
3. **Деплой** (когда скажете): [`DEPLOY_W1_GIGA_CUTOVER.md`](DEPLOY_W1_GIGA_CUTOVER.md).  
4. Затем W2 timer on device + GitVerse push + Cloud.ru W3.  
Канон прогресса: [`DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](DEVELOPMENT_PLAN_2026-09_SBER_ERA.md).
