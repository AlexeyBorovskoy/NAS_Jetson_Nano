# Глубокое инженерное исследование домашней интеллектуальной фотобиблиотеки на Jetson Nano

## 0. Роль исследователя

Ты выполняешь глубокое инженерное исследование для реального домашнего контура.

Не ограничивайся обзором официальных сайтов. Необходимо исследовать:

- официальную документацию;
- GitHub repositories;
- GitHub Issues;
- GitHub Discussions;
- release notes;
- документацию Docker;
- документацию используемых ML-фреймворков;
- Reddit и другие практические обсуждения;
- реальные отчёты пользователей;
- технические статьи;
- benchmarks;
- ограничения ARM64;
- ограничения NVIDIA Jetson Nano;
- совместимость версий CUDA/cuDNN/TensorRT/PyTorch/ONNX Runtime;
- практику эксплуатации больших фотоархивов.

Главная цель исследования — определить, какую архитектуру разумнее всего построить на уже имеющемся оборудовании, **без превращения ноутбука в постоянно работающий сервер**.

---

# 1. Исходный контур

Имеется домашняя система:

## 1.1. Jetson Nano

Jetson Nano является постоянным домашним сервером и NAS.

Он должен оставаться постоянно включённым.

На Jetson уже подключены два накопителя:

### HDD

- ёмкость около 2 ТБ;
- используется как основное хранилище;
- на нём находятся оригинальные фотографии и другие пользовательские данные.

### Быстрый NVMe

- ёмкость около 256 ГБ;
- физически подключён к Jetson Nano;
- должен использоваться как быстрый рабочий накопитель.

Необходимо исследовать оптимальное распределение данных между HDD и NVMe.

Предварительная гипотеза:

```text
HDD
└── оригинальные фотографии / видео

NVMe
├── PostgreSQL
├── LibrePhotos application data
├── thumbnails
├── embeddings
├── face recognition data
├── search indexes
├── cache
├── temporary processing data
└── AI models
```

Эта схема является гипотезой и должна быть проверена, а не принята как факт.

---

# 2. Ноутбук

Ноутбук пользователя НЕ должен превращаться в постоянно работающий сервер фотобиблиотеки.

Ноутбук должен оставаться:

- рабочей машиной разработки;
- VS Code;
- Codex;
- Claude;
- локальные LLM;
- экспериментальная разработка;
- исследовательские задачи;
- временные вычисления.

На ноутбуке имеется NVIDIA RTX 3050 Ti 4 GB VRAM.

Необходимо рассмотреть возможность использования ноутбука как:

- временного AI worker;
- benchmark machine;
- экспериментального ML worker;

но не как постоянного сервера.

Если архитектура требует постоянного включённого ноутбука — считать это существенным недостатком.

---

# 3. Главный исследовательский вопрос

Определить, насколько рационально построить на существующем Jetson Nano:

**домашнюю интеллектуальную фотобиблиотеку с semantic search, распознаванием лиц, объектов, сцен, событий и возможностью последующего подключения собственного RAG/LLM.**

Основные кандидаты:

1. LibrePhotos
2. Immich
3. PhotoPrism
4. Nextcloud + Memories + Recognize
5. другие зрелые open-source решения, если они реально подходят под требования.

Необходимо также найти альтернативы, которые исследователь считает более подходящими.

---

# 4. Особое внимание LibrePhotos

Провести глубокий технический разбор LibrePhotos.

Исследовать текущую актуальную версию проекта.

Определить:

- архитектуру;
- Docker containers;
- используемую БД;
- storage architecture;
- thumbnail architecture;
- metadata processing;
- face recognition;
- object recognition;
- scene recognition;
- image captioning;
- CLIP;
- semantic search;
- similarity search;
- embeddings;
- FAISS или используемый актуальный механизм индексации;
- background workers;
- очереди;
- multiprocessing;
- resource limits;
- ARM64 support;
- NVIDIA support;
- GPU Docker image;
- CPU mode;
- возможность custom builds;
- возможность вынесения ML processing на другой компьютер;
- возможность использования external library;
- backup/restore;
- database backup;
- миграции;
- обновления.

Для каждого утверждения желательно дать ссылку на первоисточник.

---

# 5. Jetson Nano: критический технический анализ

Исследовать реальную совместимость LibrePhotos и других кандидатов с Jetson Nano.

Нельзя писать просто:

> ARM64 supported.

Это недостаточно.

Необходимо установить:

- поддерживаемую архитектуру;
- поддерживаемую ОС;
- поддерживаемый JetPack;
- CUDA version;
- cuDNN;
- TensorRT;
- PyTorch;
- ONNX Runtime;
- Python;
- Docker;
- Docker Compose;
- наличие ARM64 Docker images;
- наличие NVIDIA CUDA ARM64 images;
- необходимость самостоятельной сборки;
- какие современные ML-модели реально работают;
- какие модели не работают;
- какие версии являются legacy;
- какие проблемы возникают из-за старого JetPack.

Отдельно проверить:

### NVIDIA Jetson Nano

- Maxwell GPU;
- 128 CUDA cores;
- compute capability;
- доступность современных CUDA runtime;
- совместимость с текущими ML frameworks.

---

# 6. GPU LibrePhotos на Jetson

Это критический раздел.

Необходимо установить:

1. Может ли LibrePhotos использовать GPU Jetson Nano штатно?
2. Если нет — почему?
3. Есть ли ARM64 CUDA image?
4. Можно ли собрать собственный image?
5. Какие компоненты потребуется собрать?
6. Возможно ли использовать TensorRT?
7. Возможно ли использовать ONNX Runtime GPU?
8. Возможно ли использовать PyTorch CUDA?
9. Какие версии совместимы с JetPack Nano?
10. Какова практическая производительность?

Особенно внимательно исследовать GitHub Issues и Discussions.

Не считать единичный успешный эксперимент полноценной официальной поддержкой.

Разделить:

```text
Officially supported
Community supported
Possible with custom build
Theoretically possible
Practically unreasonable
```

---

# 7. CPU-only режим

Если GPU Jetson использовать не получится, исследовать CPU-only режим.

Нужно получить реальные оценки:

- скорость индексации;
- скорость thumbnail generation;
- скорость CLIP embedding;
- скорость face recognition;
- скорость caption generation;
- примерная обработка 1 000 фотографий;
- 10 000;
- 50 000;
- 100 000;
- 500 000.

Если точных benchmark нет — не придумывать числа.

Вместо этого:

```text
нет достоверного benchmark
```

и привести реальные косвенные данные.

---

# 8. NVMe 256 GB

Исследовать оптимальное использование NVMe.

Нужно определить примерный расход места на:

- PostgreSQL;
- thumbnails;
- embeddings;
- face data;
- indexes;
- application data;
- Docker layers;
- AI models;
- cache;
- temporary files.

Рассмотреть сценарии:

### 10 000 фото

### 50 000 фото

### 100 000 фото

### 500 000 фото

### 1 000 000 фото

Сделать оценку:

```text
originals → HDD

derived data → NVMe
```

Определить, при каком размере библиотеки NVMe 256 GB становится узким местом.

---

# 9. HDD

Исследовать работу LibrePhotos с оригиналами на HDD.

Особенно важно:

- external library;
- read-only mount;
- symbolic links;
- SMB;
- NFS;
- local filesystem;
- Docker bind mounts.

Определить, какой вариант наиболее надёжен:

```text
Jetson local mount → HDD
```

или

```text
NAS share
```

Поскольку HDD физически подключён к тому же Jetson, предпочтителен локальный filesystem, если это действительно лучший вариант.

---

# 10. Сохранность оригиналов

Оригинальные фотографии являются главным активом.

Необходимо проверить:

- может ли LibrePhotos работать без копирования оригиналов;
- что произойдёт при удалении LibrePhotos;
- что произойдёт при повреждении БД;
- что произойдёт при переустановке Docker;
- можно ли восстановить каталог;
- можно ли повторно просканировать фотографии;
- какие данные теряются при уничтожении базы;
- какие данные необходимо отдельно резервировать.

Создать модель:

```text
ORIGINAL DATA
DERIVED DATA
APPLICATION DATA
DATABASE
AI INDEX
```

и определить требования к backup для каждой категории.

---

# 11. Semantic Search

Провести отдельное исследование semantic search.

Разобрать:

```text
photo
 ↓
CLIP/image embedding
 ↓
vector index
 ↓
text query
 ↓
text embedding
 ↓
similarity
 ↓
results
```

Определить:

- какая модель используется;
- какая версия;
- размер embedding;
- где хранится embedding;
- какой vector index используется;
- можно ли экспортировать embeddings;
- можно ли получить их через API;
- можно ли использовать их вне LibrePhotos;
- можно ли построить собственный RAG поверх них.

---

# 12. Face Recognition

Исследовать:

- face detection;
- face embeddings;
- clustering;
- identity assignment;
- false positives;
- false negatives;
- качество на старых фотографиях;
- качество на групповых фотографиях;
- качество при плохом освещении;
- качество при низком разрешении.

Отдельно исследовать:

> насколько хорошо система работает именно с семейным архивом старых фотографий.

---

# 13. Object / Scene Recognition

Исследовать способность распознавать:

- автомобиль;
- автобус;
- поезд;
- самолёт;
- море;
- лес;
- горы;
- город;
- дом;
- людей;
- животных;
- документы;
- здания;
- дорожную инфраструктуру;
- светофоры;
- транспорт.

Отдельно определить, можно ли расширять taxonomy.

---

# 14. Captioning

Исследовать:

- какие модели используются;
- насколько они тяжёлые;
- CPU requirements;
- GPU requirements;
- ARM64 compatibility;
- возможность отключения;
- реальная полезность captions для поиска.

Определить, нужен ли вообще captioning для будущего Photo RAG.

---

# 15. Photo RAG

Это отдельный ключевой раздел.

Разработать архитектуру:

```text
                PHOTO ARCHIVE
                      │
                      ▼
                 LibrePhotos
                      │
       ┌──────────────┼──────────────┐
       │              │              │
      EXIF           Faces          CLIP
       │              │              │
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                  PostgreSQL
                      │
                      ▼
                 Photo RAG
                      │
                      ▼
                     LLM
```

Определить:

- какие данные можно получать из LibrePhotos;
- API;
- database;
- export;
- embeddings;
- metadata;
- captions;
- face identities;
- locations;
- dates;
- events.

Показать, как реализовать запросы типа:

> "Найди фотографии с родителями на море в 1990-е."

> "Найди фотографии автомобилей зимой."

> "Покажи похожие фотографии этого места."

> "Найди поездки, где были фотографии моря и самолётов."

---

# 16. LibrePhotos vs Immich

Сделать техническое сравнение.

Не рекламное.

Таблица:

| Критерий | LibrePhotos | Immich |
|---|---|---|
| ARM64 | | |
| Jetson Nano | | |
| CPU mode | | |
| GPU | | |
| CUDA | | |
| Semantic Search | | |
| CLIP | | |
| Face recognition | | |
| Object recognition | | |
| Scene recognition | | |
| Captioning | | |
| Similar photos | | |
| API | | |
| DB access | | |
| External library | | |
| Read-only originals | | |
| Docker | | |
| Backup | | |
| Stability | | |
| Community | | |
| Development activity | | |
| Future prospects | | |
| Photo RAG integration | | |

Для каждого спорного пункта дать источник.

---

# 17. PhotoPrism

Исследовать отдельно.

Определить:

- ARM64;
- Jetson;
- AI;
- semantic search;
- face recognition;
- object recognition;
- GPU;
- API;
- database;
- external storage.

Не тратить много места, если решение очевидно хуже, но причины должны быть доказаны.

---

# 18. Nextcloud + Memories + Recognize

Исследовать как альтернативу.

Особенно:

- object recognition;
- face recognition;
- semantic search;
- ARM64;
- Jetson;
- storage;
- complexity;
- resource consumption.

Определить, не является ли это избыточным решением.

---

# 19. Другие open-source проекты

Найти современные альтернативы.

Искать проекты по следующим направлениям:

- self-hosted photo management;
- semantic photo search;
- AI photo management;
- CLIP photo search;
- face recognition photo library;
- local AI photo search;
- ARM64 photo server;
- Jetson photo AI.

Добавлять проект в сравнение только если он действительно жизнеспособен.

---

# 20. Возможность remote ML worker

Исследовать архитектуру:

```text
Jetson Nano
│
├── NAS
├── HDD
├── LibrePhotos
├── DB
└── Web UI
       │
       │ LAN
       ▼
temporary AI worker
│
└── RTX 3050 Ti
```

Нужно установить:

- поддерживает ли LibrePhotos remote ML;
- если нет — можно ли реализовать такой режим;
- какие данные передаются;
- передаются ли оригиналы;
- можно ли передавать только previews;
- насколько это безопасно;
- можно ли выключать worker после обработки;
- как избежать копирования всей библиотеки.

---

# 21. Энергопотребление

Исследовать практическую модель:

Jetson постоянно включён.

Ноутбук выключен.

AI worker включается только периодически.

Сравнить с постоянной работой x86-сервера.

Если нет достоверных данных по потреблению — не придумывать.

---

# 22. Безопасность

Исследовать:

- LAN-only deployment;
- authentication;
- HTTPS;
- reverse proxy;
- external access;
- VPN;
- backup;
- database security;
- sensitive face data;
- privacy.

Особенно важно:

> семейный фотоархив не должен автоматически отправляться во внешние облачные AI API.

Определить, какие компоненты полностью локальные.

---

# 23. Надёжность

Исследовать отказоустойчивость:

### Потеря HDD

Что происходит?

### Потеря NVMe

Что происходит?

### Потеря PostgreSQL

Что происходит?

### Удаление LibrePhotos

Что происходит?

### Обновление LibrePhotos

Что происходит?

### Повреждение Docker

Что происходит?

### Восстановление Jetson

Что происходит?

Создать таблицу:

| Отказ | Потеря оригиналов | Потеря метаданных | Восстановление |
|---|---:|---:|---|
| HDD | | | |
| NVMe | | | |
| DB | | | |
| Docker | | | |
| Jetson | | | |

---

# 24. Производительность

Если возможно, найти реальные benchmark.

Особенно нужны данные:

- Jetson Nano;
- ARM64;
- 4 GB RAM;
- CPU-only;
- CUDA;
- CLIP;
- face recognition.

Если benchmark отсутствует — явно написать:

> достоверные данные не найдены.

Не подменять предположение benchmark.

---

# 25. Практический пилот

Разработать конкретный план тестирования.

## Stage 1

Установить LibrePhotos на Jetson.

## Stage 2

Подключить:

```text
HDD → originals
NVMe → application/DB/cache
```

## Stage 3

Создать тестовую библиотеку:

```text
1 000 фото
5 000 фото
10 000 фото
```

## Stage 4

Измерить:

- indexing time;
- RAM;
- CPU;
- disk I/O;
- NVMe usage;
- HDD usage;
- search latency;
- face processing;
- CLIP processing.

## Stage 5

Проверить:

- semantic search;
- face search;
- similar photos;
- dates;
- locations;
- events.

## Stage 6

После успешного теста увеличить библиотеку.

---

# 26. Необходимо разработать benchmark protocol

Создать воспроизводимый benchmark.

Например:

```text
TEST-LIBRARY-001
1000 images

TEST-LIBRARY-002
5000 images

TEST-LIBRARY-003
10000 images
```

Каждый тест должен фиксировать:

```text
JetPack
Docker
LibrePhotos version
CPU
RAM
storage
filesystem
model versions
worker count
start time
finish time
errors
```

---

# 27. Финальная архитектура

После исследования предложить:

## Architecture A

LibrePhotos полностью на Jetson.

## Architecture B

LibrePhotos на Jetson + temporary AI worker.

## Architecture C

Immich на Jetson + temporary AI worker.

## Architecture D

Другой вариант, если он объективно лучше.

Для каждого:

- плюсы;
- минусы;
- стоимость;
- сложность;
- надёжность;
- производительность;
- расширяемость;
- пригодность для Photo RAG.

---

# 28. Финальная рекомендация

Необходимо дать чёткий вывод:

### Что выбрать сейчас?

### Что НЕ покупать?

### Что установить первым?

### Что проверить экспериментально?

### Какие ограничения являются критическими?

### Где возможен технический тупик?

---

# 29. Очень важное требование к исследованию

Не путать:

```text
официально поддерживается
```

с

```text
работает у пользователя
```

и:

```text
теоретически возможно
```

с:

```text
практически целесообразно
```

Для каждого важного утверждения использовать один из статусов:

- VERIFIED — подтверждено первоисточником;
- COMMUNITY — подтверждено практикой сообщества;
- EXPERIMENTAL — экспериментально;
- INFERENCE — вывод исследователя;
- UNKNOWN — достоверных данных нет.

---

# 30. Источники

Приоритет:

1. Official documentation
2. GitHub repository
3. GitHub Issues
4. GitHub Discussions
5. официальные release notes
6. NVIDIA documentation
7. Docker documentation
8. technical papers
9. Reddit
10. blogs/forums

Для каждого критического технического вывода дать ссылку.

Не использовать SEO-статьи в качестве единственного источника.

---

# 31. Финальный результат

Подготовить итоговый Markdown-документ:

```text
PHOTO_AI_HOME_SERVER_RESEARCH.md
```

Структура:

```text
1. Executive Summary

2. Existing Hardware

3. Requirements

4. LibrePhotos Architecture

5. LibrePhotos + Jetson Nano

6. ARM64 / CUDA / TensorRT

7. Storage Architecture

8. HDD vs NVMe

9. CPU-only Processing

10. GPU Processing

11. Remote AI Worker

12. Semantic Search

13. Face Recognition

14. Object / Scene Recognition

15. Captioning

16. Photo RAG

17. LibrePhotos vs Immich

18. PhotoPrism

19. Nextcloud

20. Other Alternatives

21. Backup

22. Failure Scenarios

23. Security

24. Performance

25. Benchmark Plan

26. Pilot Deployment

27. Architecture Options

28. Cost

29. Risks

30. Final Recommendation

31. Sources
```

Дополнительно подготовить:

```text
PHOTO_AI_ARCHITECTURE.md
PHOTO_AI_BENCHMARK_PLAN.md
PHOTO_AI_DECISION_MATRIX.md
PHOTO_AI_PILOT_PLAN.md
PHOTO_AI_RAG_ARCHITECTURE.md
```

---

# 32. Главный критерий успеха

Исследование должно ответить не на вопрос:

> "Какой photo manager самый популярный?"

а на вопрос:

> **"Как на имеющемся Jetson Nano с HDD 2 TB + NVMe 256 GB построить автономную локальную интеллектуальную фотобиблиотеку, которая сохраняет оригиналы, предоставляет semantic search и в будущем может стать источником данных для собственного Photo RAG/LLM, при этом ноутбук остаётся исключительно машиной разработки?"**

Исследование должно закончиться конкретной инженерной рекомендацией и планом пилотного развёртывания.

Не принимать решение заранее в пользу LibrePhotos или Immich.

Если факты говорят, что выбранная технология для Jetson Nano непрактична — прямо указать это.

Не придумывать benchmark, совместимость, API или возможности, которых нет в источниках.