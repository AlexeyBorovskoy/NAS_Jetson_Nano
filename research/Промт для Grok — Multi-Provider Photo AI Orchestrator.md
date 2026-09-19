# Глубокое исследование Multi-Provider Photo AI Orchestrator для домашнего фотоархива

## 1. Роль

Выступи как senior solution architect, ML infrastructure engineer и исследователь open-source решений.

Необходимо провести глубокое актуальное исследование архитектуры домашней интеллектуальной фотобиблиотеки, использующей локальный Jetson Nano как постоянный узел и бесплатные/freemium внешние GPU-платформы как временные вычислительные workers.

Это исследование должно привести к **реализуемой инженерной архитектуре**, а не к общему обзору облачных сервисов.

Используй актуальные данные на дату исследования.

Основные источники:

1. официальная документация;
2. GitHub repositories;
3. GitHub Issues;
4. GitHub Discussions;
5. release notes;
6. API documentation;
7. pricing/limits;
8. реальные примеры интеграции;
9. Reddit и форумы — только как дополнительный источник практического опыта.

Все изменяемые данные — free tiers, GPU, лимиты, API, поддерживаемые модели — перепроверять.

Для важных утверждений приводить URL источника.

---

# 2. Реальный локальный контур

Имеется:

```text
Jetson Nano
├── ARM64
├── 4 GB RAM
├── JetPack 4.x / legacy NVIDIA stack
│
├── HDD ~2 TB
│   └── оригинальный фото/видеоархив
│
└── быстрый NVMe/SSD ~256 GB
    ├── application data
    ├── database
    ├── thumbnails
    ├── embeddings
    ├── indexes
    └── cache
```

Jetson уже используется как домашний NAS и работает постоянно.

Ноутбук пользователя должен оставаться машиной разработки и **не должен быть обязательным постоянно работающим элементом системы**.

На ноутбуке имеется RTX 3050 Ti 4 GB, поэтому его можно рассматривать только как:

- временный ML worker;
- средство разработки;
- benchmark node;
- аварийный/локальный worker.

---

# 3. Основная концепция

Исследовать архитектуру:

```text
                        Jetson Nano
                  NAS + Photo Platform
                         │
              Photo AI Orchestrator
                         │
          ┌──────────────┼───────────────┐
          │              │               │
          ▼              ▼               ▼
       Kaggle           Modal         Lightning
          │              │               │
          ├──────────────┼───────────────┤
          │              │               │
          ▼              ▼               ▼
        Colab       Other Free GPU    Local Worker
                                          │
                                          ▼
                                      RTX 3050 Ti
```

External workers не являются постоянными серверами.

Они запускаются только при наличии задач.

---

# 4. Главный вопрос

Определить:

> Можно ли построить надёжный Multi-Provider Photo AI Orchestrator, который автоматически выбирает доступный бесплатный/дешёвый вычислительный ресурс, отправляет туда задания обработки фотографий и возвращает результаты на Jetson?

При этом система должна продолжать работать, даже если:

- Kaggle недоступен;
- закончилась квота Kaggle;
- закончились credits Modal;
- Lightning недоступен;
- Colab изменил лимиты;
- конкретный GPU отсутствует;
- внешний worker оборвался во время обработки.

---

# 5. Не принимать Immich как заранее выбранное решение

Исследовать минимум:

- Immich;
- LibrePhotos;
- PhotoPrism;
- собственный Photo RAG;
- гибридное решение.

Однако особое внимание уделить:

```text
Jetson
+
Immich
+
External Library
+
Multi-Provider AI Orchestrator
+
Photo RAG
```

Проверить, действительно ли эта архитектура рациональнее LibrePhotos на Jetson Nano.

---

# 6. Разделить систему на Control Plane и Compute Plane

Исследовать следующую модель.

## Control Plane

Работает постоянно на Jetson:

```text
Photo AI Orchestrator
Job Queue
Scheduler
Provider Router
Provider Health
Quota Manager
Result Collector
Metadata DB
Vector DB
Audit Log
```

## Compute Plane

Временные workers:

```text
Kaggle
Modal
Lightning
Colab
Local RTX
Other providers
```

Проверить целесообразность такого разделения.

---

# 7. Исследовать кандидатов на внешний compute

Обязательно проверить актуальное состояние:

## Kaggle

Проверить:

- актуальные GPU;
- количество GPU;
- VRAM;
- недельные лимиты;
- Notebook API;
- Kaggle CLI/API;
- автоматический запуск notebook;
- Dataset API;
- загрузку batch;
- скачивание результатов;
- Internet access;
- ограничения automation;
- session timeout;
- возможность unattended processing;
- ToS.

Особенно важно определить:

> можно ли использовать Kaggle как автоматический batch worker, а не вручную запускать Notebook.

---

## Modal

Проверить:

- актуальный free/freemium tier;
- monthly credits;
- требуется ли payment method;
- доступные GPU;
- serverless GPU;
- functions;
- containers;
- volumes;
- queues;
- secrets;
- API;
- Python SDK;
- CLI;
- web endpoints;
- timeout;
- concurrency;
- cold start;
- cost controls.

Modal рассматривается как потенциально основной **on-demand worker**.

Исследовать возможность:

```text
Jetson
   ↓
Modal API
   ↓
GPU function
   ↓
result
   ↓
Jetson
```

---

## Lightning AI

Проверить:

- бесплатные credits;
- необходимость карты;
- GPU;
- Studio;
- Jobs;
- API;
- CLI;
- SSH;
- automation;
- persistent storage;
- interruptible GPU.

Определить, насколько Lightning подходит как автоматический worker.

---

## Google Colab

Проверить:

- Free GPU;
- динамические ограничения;
- automation;
- API;
- unattended execution;
- ToS.

Если Colab плохо подходит для автоматического orchestration — прямо указать.

---

## Hugging Face

Проверить:

- ZeroGPU;
- Spaces;
- Jobs;
- Inference Providers;
- quotas;
- API;
- automation.

---

## Oracle Cloud Always Free

Рассматривать прежде всего как CPU/VPS, а не GPU.

Проверить:

- текущий Always Free;
- ARM;
- RAM;
- storage;
- availability;
- reclaim policy;
- возможность Docker;
- возможность orchestration.

Отдельно ответить:

> Нужен ли Oracle вообще, если Jetson уже работает 24/7?

---

## Cloudflare

Исследовать:

- Workers;
- Workers AI;
- Queues;
- R2;
- D1;
- Vectorize;
- free limits.

Определить, есть ли смысл использовать Cloudflare как часть orchestration/control plane.

---

## Дополнительные платформы

Найти актуальные бесплатные/freemium решения:

- AMD Developer Cloud;
- Intel Developer Cloud;
- NVIDIA developer resources;
- Paperspace;
- RunPod promotions/free credits;
- Vast.ai credits;
- ModelScope;
- Hugging Face;
- Replicate credits;
- Scaleway;
- Nebius;
- другие реальные предложения.

Не включать платформу только потому, что она когда-то имела free tier.

---

# 8. Provider Adapter Architecture

Исследовать архитектуру адаптеров:

```text
                 Orchestrator
                      │
              Provider Interface
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
 KaggleAdapter    ModalAdapter   LightningAdapter
       │              │              │
       ▼              ▼              ▼
    Kaggle          Modal         Lightning
```

Предложить общий интерфейс, например:

```text
submit(job)
status(job)
cancel(job)
download_result(job)
quota()
health()
capabilities()
estimated_cost()
```

Определить, какие функции реально возможно реализовать для каждого provider.

---

# 9. Capability Registry

Каждый worker должен сообщать:

```text
provider
GPU
VRAM
CUDA
available_runtime
remaining_quota
cost
max_batch
internet
persistent_storage
supported_models
privacy_level
```

Оркестратор выбирает provider не только по наличию GPU.

---

# 10. Routing

Разработать алгоритм маршрутизации.

Пример:

```text
JOB
 │
 ├── CLIP?
 ├── Faces?
 ├── OCR?
 ├── Caption?
 ├── VLM?
 └── Duplicate detection?
        │
        ▼
Provider Router
        │
        ├── FREE available?
        │       ↓
        │     use free
        │
        ├── cheap provider?
        │       ↓
        │     ask policy
        │
        └── local CPU fallback
```

Приоритет пользователя:

1. бесплатно;
2. уже имеющиеся credits;
3. минимальная стоимость;
4. производительность.

---

# 11. Никакого неожиданного расходования денег

Это обязательное требование.

Архитектура должна иметь:

```text
MAX_COST_PER_JOB
MAX_COST_PER_DAY
MAX_COST_PER_MONTH
```

По умолчанию:

```text
ALLOW_PAID = false
```

Если бесплатная квота закончилась:

```text
QUEUE
```

а не автоматический переход на платный GPU.

Исследовать возможности budget limits каждого provider.

---

# 12. Job Queue

Предложить технологию очереди, подходящую для Jetson Nano.

Сравнить:

- Redis;
- PostgreSQL queue;
- Celery;
- RQ;
- RabbitMQ;
- NATS;
- SQLite;
- собственную простую очередь.

Учитывать:

**Jetson имеет только 4 GB RAM.**

Не создавать тяжёлую инфраструктуру без необходимости.

---

# 13. Job Manifest

Каждая задача должна иметь manifest.

Например:

```json
{
  "job_id": "...",
  "asset_id": "...",
  "operation": "clip_embedding",
  "model": "...",
  "model_version": "...",
  "input_hash": "...",
  "preview": "...",
  "provider": "...",
  "created": "...",
  "attempt": 1
}
```

Определить необходимую схему.

---

# 14. Idempotency

Если worker умер после обработки:

```text
Jetson
 ↓
Modal
 ↓
GPU
 ↓
RESULT
 ↓
connection lost
```

повторный запуск не должен создавать дубли.

Исследовать:

- deterministic job IDs;
- SHA-256;
- idempotency keys;
- result cache.

---

# 15. Batch processing

Это особенно важно для Kaggle.

Исследовать:

```text
1 photo
10 photos
100
1 000
10 000
```

Определить оптимальный batch size.

Не отправлять по одному фото, если provider предназначен для Notebook/batch workloads.

---

# 16. Privacy-first preprocessing

Исследовать вариант:

```text
ORIGINAL
6000 × 4000
EXIF
GPS
filename

       ↓ Jetson

PREVIEW
512/768/1024 px
EXIF removed
random job ID

       ↓ external GPU

AI results
```

Проверить влияние уменьшения изображения на:

- CLIP;
- face detection;
- OCR;
- captioning;
- object recognition.

Не утверждать без источников, что один размер подходит для всех задач.

---

# 17. Разделить privacy levels

Предложить классификацию:

```text
LOCAL_ONLY
PREVIEW_ALLOWED
CLOUD_ALLOWED
PUBLIC_DATA
```

Например:

```text
family/private → LOCAL_ONLY

обычные фотографии → PREVIEW_ALLOWED
```

Router обязан учитывать privacy level.

---

# 18. Photo AI Pipeline

Исследовать pipeline:

```text
Original Photo
      │
      ▼
Metadata
      │
      ├── EXIF
      ├── GPS
      ├── date
      └── camera
      │
      ▼
Preview
      │
      ▼
AI pipeline
      │
      ├── CLIP
      ├── Face detection
      ├── Face embedding
      ├── OCR
      ├── Caption
      ├── Objects
      ├── Scene
      ├── Quality
      └── pHash
```

Определить современные open-source модели для каждого этапа.

Приоритет:

- небольшие;
- качественные;
- хорошо поддерживаемые;
- CUDA;
- batch-friendly;
- permissive license.

---

# 19. CLIP

Сравнить актуальные модели:

- OpenAI CLIP;
- OpenCLIP;
- SigLIP;
- SigLIP2;
- EVA-CLIP;
- MobileCLIP;
- другие актуальные варианты.

Оценить:

- качество;
- VRAM;
- скорость;
- embedding dimension;
- multilingual search;
- русский язык.

Русскоязычный поиск является важным требованием.

---

# 20. Face Recognition

Исследовать современные open-source варианты.

Нужно:

```text
face detection
face embedding
clustering
identity
```

Особенно важен семейный архив:

- старые фотографии;
- изменение возраста;
- дети → взрослые;
- групповые фотографии;
- плохое качество;
- сканы бумажных фотографий.

---

# 21. OCR

Нужен локальный/внешний OCR для:

- документов;
- вывесок;
- дорожных знаков;
- фотографий экранов;
- надписей.

Особенно проверить русский язык.

---

# 22. Captioning/VLM

Исследовать небольшие VLM:

- Florence;
- BLIP;
- Moondream;
- Qwen-VL;
- Gemma vision;
- другие актуальные модели.

Не использовать огромную VLM, если CLIP + metadata дают достаточный результат.

---

# 23. Критический вопрос: интеграция с Immich

Это один из главных разделов исследования.

Необходимо выяснить:

### Как именно Immich хранит:

- CLIP embeddings;
- face embeddings;
- face identities;
- search vectors;
- metadata.

### Какие официальные API существуют?

### Можно ли:

```text
external worker
       ↓
embedding
       ↓
Immich API
```

?

### Или Immich принимает только изображения через свой ML API?

### Можно ли реализовать compatible remote ML endpoint?

### Как устроен протокол `immich-machine-learning`?

### Можно ли сделать adapter:

```text
Immich
   ↓
Photo AI Orchestrator
   ↓
Modal/Kaggle/etc.
   ↓
Orchestrator
   ↓
Immich
```

?

---

# 24. НЕ писать напрямую в Immich PostgreSQL без крайней необходимости

Это принципиальное требование.

Если официального API для загрузки внешних embeddings нет:

не предлагать сразу:

```text
INSERT INTO immich_database...
```

Исследовать более безопасную архитектуру:

```text
Immich DB
     +
Photo AI DB
     +
Photo RAG
```

---

# 25. Sidecar Photo AI Database

Исследовать вариант:

```text
Immich
  │
  │ asset ID
  ▼
Photo AI DB
  │
  ├── custom CLIP
  ├── OCR
  ├── captions
  ├── objects
  ├── quality
  └── additional embeddings
```

Это позволит обновлять Immich независимо от нашего AI.

Определить, насколько эта архитектура лучше прямой модификации Immich.

---

# 26. Vector database

Учитывая Jetson Nano + NVMe 256 GB, сравнить:

- PostgreSQL + pgvector;
- VectorChord;
- Qdrant;
- FAISS;
- SQLite vector extensions;
- LanceDB;
- другие лёгкие варианты.

Критерии:

- RAM;
- ARM64;
- Docker;
- storage;
- backup;
- search speed;
- 100k / 500k / 1M images.

---

# 27. Photo RAG

Будущая система должна поддерживать запросы на русском:

> Найди фотографии, где мы были на море примерно в 1998 году.

> Найди старые фотографии родителей рядом с автомобилем.

> Где фотографии поездки, в которой мы были в горах и ездили на поезде?

> Найди фотографии похожие на эту.

> Покажи все фотографии этого человека примерно за 20 лет.

Архитектура:

```text
User
 ↓
LLM
 ↓
Query Planner
 ↓
┌───────────────┐
│ date          │
│ GPS           │
│ faces         │
│ CLIP          │
│ OCR           │
│ captions      │
│ metadata      │
└───────────────┘
 ↓
ranking
 ↓
Immich assets
```

---

# 28. Нужен ли LLM вообще?

Отдельно определить, где LLM действительно нужен.

Не использовать LLM там, где достаточно:

- SQL;
- vector search;
- metadata filters;
- deterministic rules.

LLM использовать прежде всего как:

```text
natural language
      ↓
structured query plan
```

---

# 29. Оркестратор должен быть маленьким

Jetson Nano имеет 4 GB RAM.

Предпочтительна архитектура примерно:

```text
Python/FastAPI
PostgreSQL
small scheduler
provider adapters
```

или ещё легче.

Не предлагать Kubernetes.

Не предлагать тяжёлую enterprise-инфраструктуру без доказанной необходимости.

---

# 30. Возможность MCP

Исследовать возможность предоставить оркестратор через MCP.

Например:

```text
Photo MCP
│
├── search_photos
├── find_person
├── find_similar
├── submit_ai_job
├── ai_queue
├── provider_status
├── quota_status
└── reprocess_asset
```

Это позволит использовать Photo AI из:

- Codex;
- Claude;
- Grok;
- локального LLM;
- собственного чат-бота.

---

# 31. Provider selection

Предложить scoring.

Например:

```text
score =
free_available
+ model_supported
+ enough_vram
+ privacy_allowed
+ reliability
- estimated_cost
- queue_time
```

Но формулу необходимо обосновать.

---

# 32. Fallback

Пример:

```text
Modal unavailable
       ↓
Kaggle available?
       ↓
Lightning?
       ↓
Local RTX?
       ↓
Jetson CPU?
       ↓
QUEUE
```

Определить разумный порядок не заранее, а по результатам исследования.

---

# 33. Observability

Нужны:

```text
/jobs
/providers
/quotas
/errors
/cost
```

Dashboard должен показывать:

```text
Kaggle       18/30 h remaining
Modal        $27.42 free credit
Lightning    ...
Local RTX    offline

Queue        1,428 photos
Processed    83,512
Failed       17
```

Проверить, какие provider APIs реально позволяют получать quota автоматически.

Если quota API отсутствует — указать это.

---

# 34. Security

API keys хранить только:

- environment variables;
- Docker secrets;
- encrypted local secret store.

Не хранить в Git.

Исследовать:

- Modal API token/service user;
- Kaggle token;
- Lightning credentials;
- Hugging Face token.

Предложить минимально необходимые права.

---

# 35. Cost simulation

Сделать расчёты для:

```text
10 000 photos
50 000
100 000
500 000
1 000 000
```

Для:

- CLIP;
- faces;
- OCR;
- captioning.

Использовать реальные benchmarks, если они существуют.

Если данных нет — построить диапазон и явно обозначить его как оценку.

Никогда не выдавать оценку за измеренный benchmark.

---

# 36. Initial indexing vs incremental processing

Разделить:

## INITIAL

```text
100 000 existing photos
```

и:

## DAILY

например:

```text
20–200 new photos
```

Для этих режимов могут использоваться разные providers.

---

# 37. Исследовать предварительную гипотезу

Возможно:

```text
INITIAL INDEX
      ↓
Kaggle

NEW PHOTOS
      ↓
Modal

EXPERIMENTS
      ↓
Lightning

FALLBACK
      ↓
Local RTX

PRIVATE
      ↓
Local only
```

Но не принимать это как заранее правильный результат.

Проверить фактически.

---

# 38. Failure model

Проанализировать:

- provider timeout;
- notebook terminated;
- API failure;
- upload interrupted;
- result lost;
- corrupted result;
- duplicate job;
- model changed;
- embedding model upgraded;
- provider discontinued;
- free tier removed.

Особенно важно:

> смена provider не должна менять смысл embedding.

Одинаковая задача должна использовать одинаковую модель и версию независимо от provider.

---

# 39. Model Registry

Предложить:

```text
model_id
model_version
weights_hash
runtime
embedding_dimension
preprocessing_version
```

Это позволит избежать смешивания несовместимых embeddings.

---

# 40. Reindexing

Исследовать стратегию:

```text
CLIP v1
   ↓
100k vectors

появился CLIP v2

не уничтожаем v1

создаём
embedding_set_v2
```

После проверки качества можно удалить старый индекс.

---

# 41. Backup

Оригиналы:

```text
HDD
```

Производные AI-данные:

```text
NVMe
```

Определить, что обязательно backup:

- DB;
- identities;
- manually assigned faces;
- captions corrections;
- custom tags;
- configuration;
- model registry.

Что можно пересчитать:

- thumbnails;
- embeddings;
- OCR;
- autogenerated captions.

---

# 42. Pilot

Разработать практический pilot.

## Pilot 1

1000 фотографий.

## Pilot 2

5000.

## Pilot 3

10000.

Сравнить минимум:

```text
Jetson CPU
Kaggle
Modal
Lightning
```

Фиксировать:

- runtime;
- GPU;
- VRAM;
- transfer;
- cost;
- failures;
- result quality.

---

# 43. Финальная decision matrix

Подготовить таблицу:

| Provider | Free quota | GPU | Automation | Batch | API | Privacy | Reliability | Cost | Role |
|---|---:|---|---|---|---|---|---|---|---|

---

# 44. Необходимо проверить саму идею

Исследователь не должен доказывать, что Multi-Provider Orchestrator хорош.

Нужно попытаться **опровергнуть** архитектуру.

Ответить:

> Не создаём ли мы чрезмерно сложную систему ради экономии нескольких долларов?

Сравнить с:

- одним Modal;
- только Kaggle;
- локальным CPU;
- дешёвым GPU VPS;
- покупкой бывшего в употреблении GPU/mini-PC;
- штатным Immich Remote ML.

Оценить TCO и сложность сопровождения.

---

# 45. Итоговый вердикт

Дать один из результатов:

```text
GO
```

```text
GO WITH CHANGES
```

```text
NO-GO
```

и объяснить почему.

---

# 46. Артефакты

Создать:

```text
docs/research/PHOTO_AI_ORCHESTRATOR_RESEARCH.md
docs/architecture/PHOTO_AI_ARCHITECTURE.md
docs/architecture/PROVIDER_ADAPTERS.md
docs/architecture/PHOTO_RAG.md
docs/architecture/SECURITY_PRIVACY.md
docs/benchmarks/BENCHMARK_PLAN.md
docs/operations/COST_QUOTA_POLICY.md
docs/decisions/PHOTO_AI_DECISION_MATRIX.md
```

Главный документ должен содержать ссылки на первоисточники.

---

# 47. Что пока НЕ делать

На этапе исследования:

- не менять существующий NAS;
- не удалять данные;
- не изменять Immich DB;
- не переносить фотоархив;
- не устанавливать production-сервисы;
- не запускать платные GPU;
- не добавлять банковские карты;
- не публиковать семейные фотографии;
- не создавать публичные endpoints;
- не менять Jetson.

Исследование выполняется READ-ONLY.

Допускаются только безопасные проверки документации, API и публичных репозиториев.

---

# 48. Основной критерий успеха

В результате должно стать понятно, можно ли построить систему:

```text
                 HOME
                  │
             Jetson Nano
        HDD 2 TB + NVMe 256 GB
                  │
          Photo Orchestrator
                  │
       ┌──────────┼──────────┐
       │          │          │
     Modal      Kaggle    Lightning
       │          │          │
       └──────────┼──────────┘
                  │
             AI RESULTS
                  │
                  ▼
           Local Photo DB
                  │
             Immich/RAG
                  │
                  ▼
        Natural-language search
```

при которой:

1. оригиналы остаются дома;
2. ноутбук не является сервером;
3. Jetson не выполняет тяжёлый ML постоянно;
4. бесплатные ресурсы используются первыми;
5. платные ресурсы никогда не запускаются без разрешения;
6. исчезновение одного provider не ломает систему;
7. Photo AI не зависит жёстко от Immich;
8. архитектура допускает собственный Photo RAG;
9. система остаётся достаточно простой для домашней эксплуатации;
10. полученный проект реально можно реализовать и сопровождать.