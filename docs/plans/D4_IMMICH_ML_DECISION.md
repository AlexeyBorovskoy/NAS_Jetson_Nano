# D4 — решение по Immich ML: где считать распознавание лиц и смысловой поиск / D4 — Immich ML decision: where to run face recognition and semantic search

> 🇷🇺 Дата: 2026-09-20. Статус: **развилка для владельца**, не выполнение. На устройстве и
> станции ничего не менялось — только чтение (Immich Postgres, `uptime`, `free -h`,
> статус гипервизора на станции). Опирается на `docs/research/IMMICH_ML_E6_ANALYSIS_2026-09-20.md`
> (не переписывается заново) и добавляет: 1) свежие живые числа с Jetson, 2) проверенные
> сегодня требования Immich к железу, 3) свежую проверку блокера станции. EN summary — в конце.

## 1. В чём выбор

Immich умеет искать фото по смыслу («покажи море 2015 года») и группировать по лицам —
но только если рядом работает `immich-machine-learning`. На Jetson он никогда не был
поднят (`ADR-0010`). Владелец должен выбрать **где физически считать эту нагрузку**:
на самом Jetson, разовым батчем на домашней станции (ROG, RTX) через существующий
обратный туннель, или в Cloud.ru — и принять, что вариант «не делать вовсе» тоже
закрывает вопрос, просто без семантического поиска. Жёсткая рамка одна и та же для
всех вариантов: **семейные фото не покидают дом** (`AGENTS.md` п.4, ADR-0010) — вариант,
где это нарушается, не вариант, даже если он дешевле или быстрее.

## 2. Живые числа с Jetson (замер 2026-09-20, ~15:00–15:01 UTC, только чтение)

Проверено `ssh admin@192.168.0.50` → `docker exec homecloud_immich_db psql`:

| Показатель | Значение | Как замерено |
|---|---|---|
| Всего ассетов | **7623** (7014 IMAGE + 609 VIDEO) | `select type, count(*) from asset group by type` |
| Метаданные (EXIF, не ML) обработаны | **7621 / 7623** | `count("metadataExtractedAt")` в `asset_job_status` |
| Лица распознаны (`facesRecognizedAt`) | **0** | тот же запрос — `count("facesRecognizedAt") = 0` |
| Строк в `smart_search` (CLIP-эмбеддинги) | **0** | `select count(*) from smart_search` |
| Строк в `asset_face` | **0** | `select count(*) from asset_face` |
| Контейнер `immich-machine-learning` | **не существует** ни в одном состоянии | `docker ps -a \| grep machine-learning` — пусто |
| RAM Jetson в момент замера | 3.9 ГБ всего, **208 МБ free**, 1.5 ГБ available, swap 574 МБ / 1.9 ГБ занято | `free -h` |
| Load average в момент замера | 2.74–3.0 (порог паузы из задания — 4.0, замер лёгкий, проведён) | `uptime` |

**Вывод из чисел:** это не «частично обработанная библиотека», а **ровно 0 % ML-обработки**
для всех 7623 ассетов — предыдущая оценка объёма работ (`E6_ANALYSIS`, ориентир «7098 фото»)
подтверждается и уточняется: индексировать придётся всю библиотеку целиком, с нуля.

## 3. Что именно считает Immich 2.7.5 (проверено в вебе 2026-09-20, `docs.immich.app`)

| Факт | Источник |
|---|---|
| Смысловой поиск — модель `ViT-B-32__openai` (CLIP) по умолчанию; собственный ориентир Immich: память **1004 МиБ**, **2.26 мс** на операцию (эталонное железо в таблице не указано — не наш замер) | `docs.immich.app/features/searching`, 20.09.2026 |
| Распознавание лиц — семейство ArcFace (`buffalo_l`, InsightFace/ONNX) | подтверждено ранее в `E6_ANALYSIS` §2, `huggingface.co/immich-app/buffalo_l` |
| Ускорение поддерживает **5 бэкендов**: ARM NN (GPU Mali), **CUDA** (NVIDIA), ROCm (AMD), OpenVINO (Intel), RKNN (Rockchip) | `docs.immich.app/features/ml-hardware-acceleration`, 20.09.2026 |
| Требование к CUDA: **драйвер ≥ 545** (нужна поддержка **CUDA 12.3**) и **compute capability ≥ 5.2** | тот же источник |
| Точные минимумы VRAM/ОЗУ для лиц/CLIP в этой странице **не указаны** — есть только качественные пометки («OpenVINO ест больше RAM», «ROCm — 35 ГиБ на диске») | тот же источник, НЕ ПРОВЕРЕНО количественно |
| 🔴 **Ни один из 5 поддерживаемых бэкендов не покрывает Tegra/Maxwell-GPU Jetson Nano.** ARM NN — это Mali (Arm GPU), не Tegra. У Jetson нет штатного пути ускорения в Immich вообще — только CPU | вывод из перечня выше, проверено 20.09.2026 |
| Из ранее сделанного разбора (`E6_ANALYSIS`, проверено 20.09.2026): системный минимум Immich — **6 ГБ ОЗУ**, рекомендовано **8 ГБ**; у ML-воркера зафиксирован скачок памяти **до ~7 ГБ** при распознавании лиц на «взрослых» библиотеках | `docs.immich.app`, GitHub issue #22717 |

## 4. Три варианта с числами

| | **Jetson Nano (дома, in-place)** | **Станция ROG батчем (обратный туннель)** | **Cloud.ru Container Apps** |
|---|---|---|---|
| **Даёт** | ML работал бы без сети наружу вообще | Полный backfill + новые фото по расписанию/по готовности станции; превью не покидают дом (только внутри SSH-туннеля) | Постоянно доступный ML-эндпоинт, не зависящий от станции |
| **Память** | 🔴 Система **уже** занимает почти всё: 3.9 ГБ всего, **208 МБ free** сейчас (§2). Immich сам требует 6–8 ГБ **только на систему**, отдельно у ML — скачки до ~7 ГБ. **Физически не влезает, разница не в разы, а на порядок** | ROG: подробностей RAM станции не снимали в этой сессии (не требовалось — GPU делает основную работу), Docker Desktop штатно резервирует память по своим настройкам | Бесплатно: 25 vCPU·ч + 50 ГБ·ч/мес. Вычисление (0.6–3.0 vCPU·ч по оценке `E6_ANALYSIS`) укладывается с запасом; ГБ-часовая часть (тарификация по времени жизни контейнера, а не по загрузке CPU) **не подтверждена практическим замером** — попытка теста 20.09 провалилась на недоступности API, не на числах |
| **GPU/ускорение** | 🔴 Ни один из 5 поддерживаемых Immich бэкендов не покрывает Tegra — CPU-only на Cortex-A57, уже занятом 13 контейнерами | ✅ Проверено сегодня: **NVIDIA RTX 3050 Ti Laptop, 4096 МиБ VRAM, драйвер 596.36** (`nvidia-smi`, 20.09.2026) — с запасом выше минимума CUDA (≥545/CC≥5.2, Ampere CC 8.6). Образ `-cuda` подходит без вопросов, если Docker поднимется | Free tier не упоминает GPU — CPU-only контейнер |
| **Время на всю библиотеку (7623 ассета)** | Оценка по CPU-only ориентиру 0.3–1.5 с/фото (§3 `E6_ANALYSIS`) на x86 — Cortex-A57 заведомо медленнее x86-ядра сопоставимого класса в разы; **вопрос спорный лишь академически: RAM уже не позволяет запустить контейнер вовсе**, поэтому оценка времени — гипотетическая и не имеет практического значения | При GPU-инференсе такого масштаба (модели <1 ГБ каждая) порядок — **минуты на всю библиотеку** по общей практике CLIP/ArcFace на дискретной GPU этого класса; **не измерено на нашей связке** (Docker не запускался с 12.09) | CPU-only: по оценке §3 `E6_ANALYSIS` вычислительная часть 0.6–3.0 vCPU·ч ≈ **десятки минут — пара часов** суммарного счётного времени; реальная стеночная длительность зависит от темпа отправки заданий и холодных стартов |
| **Что придётся сделать владельцу** | Ничего технически осмысленного — вариант закрыт числами, не мнением | Снять блокер: **Hyper-V выключен и сегодня** (`HyperVisorPresent: False`, проверено 20.09.2026 15:0x, PowerShell на станции; тот же результат, что 12.09 — **блокер не снят 8 дней**), `com.docker.service` остановлен. Нужны админ-права + перезагрузка (`dism … VirtualMachinePlatform`, `bcdedit /set hypervisorlaunchtype auto`), затем поднять Docker Desktop, поднять `immich-machine-learning:release-cuda`, прописать URL в Machine Learning Settings через туннель на `172.17.0.1`, включить станцию на время прогона | Дождаться E5 (алерт расходов — уже в git), сделать пробный прогон одного альбома с открытой биллинг-консолью **до** переноса всей библиотеки (условие уже сформулировано в `E6_ANALYSIS` §7), решить вопрос защиты эндпоинта (штатного механизма, совместимого с Immich, не нашлось — только секретный URL) |
| **Новые фото после первого батча** | — | Не считаются, пока станция выключена; встают в очередь и досчитываются при следующем включении (поведение Immich по issue-трекеру, `E6_ANALYSIS` §5) — семья не теряет доступ к фото, теряет только поиск/лица на время простоя | Считаются сразу — сервис постоянный (в рамках free tier) |
| **Риски** | — | Зависимость от готовности владельца включать станцию; неизвестное точное время на нашей реальной связке туннель+Docker | Превью **уходят из дома** — тот самый риск ADR-0010, принят владельцем **условно** («если укладывается в free tier»); условие по ГБ-часам **не подтверждено**; у ML-эндпоинта Immich нет своей авторизации — практическая защита слабее, чем «доступно только Jetson» |

## 5. Рекомендация

**Вариант Б (станция батчем) — основной, Cloud.ru — условный резерв после отдельного
теста, Jetson — закрыт.**

1. **Jetson закрывается числами, а не осторожностью.** 208 МБ свободной памяти сейчас
   против требуемых Immich 6–8 ГБ на одну лишь систему — это не «тесно», это «не
   помещается на порядок». Дополнительно ни один из 5 поддерживаемых бэкендов ускорения
   не покрывает GPU Jetson, то есть даже без учёта памяти это был бы CPU-only режим на
   и так занятом ядре. Подтверждает уже принятое `ADR-0010`, ничего не меняет.
2. **Вариант Б — единственный, где превью гарантированно не покидают дом** (SSH-туннель
   внутри домашнего контура), и при этом у него самая быстрая ожидаемая обработка —
   на GPU-класса RTX 3050 Ti индексация 7623 ассетов по общей практике займёт минуты,
   а не часы. Технически он готов процентов на 80 (образ, переменные, туннель — по
   `CLAUDE.md`); единственный блокер — административный (Hyper-V + перезагрузка), а не
   архитектурный.
3. **Блокер станции не снят 8 дней подряд.** Отложено владельцем 12.09 на «13.09» —
   сегодняшняя проверка (20.09) показывает тот же `HyperVisorPresent: False`. Это не
   довод против варианта Б, это довод **назвать это владельцу явно**: вариант готов,
   ждёт одного конкретного административного шага.
4. **Cloud.ru остаётся резервом, не основным путём**, по той же логике, что и в
   `E6_ANALYSIS`: даже если он влезет в free tier по деньгам, превью всё равно уедут
   из дома — это структурно хуже варианта Б независимо от цены. Держать его на случай,
   если станция окажется постоянно недоступна как ресурс для батчей.

## 6. Что произойдёт, если не делать ничего

Честно и без «на самом деле всё плохо»:

- **Теряется:** смысловой поиск по содержимому фото («покажи море», «Уля на площадке»)
  и автоматическая группировка лиц. Для библиотеки 7623 ассетов за несколько лет это
  ощутимая потеря удобства для того, кто ищет момент, а не листает ленту вручную.
- **Не теряется ничего из сохранности данных:** загрузка, просмотр, альбомы, шаринг,
  видео, резервные копии — всё это не зависит от ML (§3 `E6_ANALYSIS`, подтверждено
  и здесь: `metadataExtractedAt` уже выполнено для 7621/7623 без всякого ML-контейнера).
- Это **дешёвый и полностью приватный** вариант — не «нерешённая проблема», а
  корректное временное (или постоянное) состояние, если владелец предпочтёт удобство
  поиска не приоритетным сейчас.

## 7. Чего не знаем

- **Точное время индексации на реальной связке станция+туннель+наша библиотека** —
  только оценка по общей практике GPU-инференса CLIP/ArcFace, не замер. Замерить можно
  только после снятия блокера Hyper-V.
- **Модель тарификации ГБ-часов Cloud.ru** (по времени жизни контейнера или по загрузке
  CPU) — попытка проверить 20.09 не состоялась (API отдавал 503 в момент прогона),
  вопрос открыт с `E6_ANALYSIS`.
- **Способ закрыть Cloud.ru-эндпоинт именно под Immich** — штатного механизма не найдено;
  не проверено, работает ли `https://user:pass@host` с HTTP-клиентом Immich ML.
- **Точная стоимость по памяти для Immich ML на нашей реальной библиотеке** (не общий
  ориентир 6–8 ГБ из документации, а наш конкретный пик при 609 видео + 7014 фото) —
  не измерено нигде, измерять можно только там, где ML физически запускается (то есть
  не на Jetson).
- **Причина, по которой Hyper-V выключен на станции именно сейчас** (настройка BIOS,
  ручное отключение, конфликт с другим ПО) — не диагностировалась в этом заходе, только
  констатирован факт «выключен».
- **Время обработки 609 видео** отдельно от фото — Immich берёт кадр из видео, но это
  не бенчмаркалось отдельно ни в одном источнике.

---

## 8. EN summary

**The choice:** where to run Immich's ML workload (CLIP semantic search + ArcFace face
recognition) for the family photo library — on the Jetson itself, as a one-off batch on
the owner's RTX-equipped workstation over the existing reverse tunnel, or in Cloud.ru —
while family photos must never leave the house (`AGENTS.md` §4, ADR-0010); "do nothing"
is also an acceptable answer if the owner says so.

**Fresh Jetson numbers (2026-09-20, read-only, via `docker exec homecloud_immich_db
psql`):** 7623 assets (7014 images + 609 videos); EXIF metadata done for 7621/7623;
**faces recognized = 0**, **smart_search (CLIP embedding) rows = 0** for every asset — ML
has processed literally 0% of the library, not "partially." No `immich-machine-learning`
container exists on the Jetson at all. At measurement time: 3.9 GB RAM total, only **208
MB free**, 1.5 GB available, load average 2.7–3.0 (below the 4.0 pause threshold, so the
light query was safe to run).

**What Immich 2.7.5 actually needs (verified today at docs.immich.app):** default CLIP
model `ViT-B-32__openai` (~1 GiB footprint, no reference hardware given for the 2.26 ms
figure — not our measurement); face model is the ArcFace `buffalo_l` family. Immich
supports exactly **5** acceleration backends (ARM NN/Mali, CUDA, ROCm, OpenVINO, RKNN) and
**none of them covers the Jetson's Tegra/Maxwell GPU** — it would run CPU-only regardless
of memory. Immich's own docs put system RAM at 6 GB minimum / 8 GB recommended, with ML
face-recognition spikes to ~7 GB on larger libraries (GitHub #22717, cited via the earlier
E6 spike). Against 208 MB free on a 3.9 GB device, **Jetson is ruled out by an order of
magnitude, not a close call** — this closes the option numerically, not by caution.

**Workstation (ROG) checked live today:** `HyperVisorPresent: False`, same as on
2026-09-12 — the blocker has **not been lifted in 8 days**. GPU is confirmed present and
working: **NVIDIA RTX 3050 Ti Laptop, 4096 MiB VRAM, driver 596.36** (`nvidia-smi`),
comfortably clearing Immich's CUDA requirement (driver ≥545/CUDA 12.3, compute
capability ≥5.2; Ampere is CC 8.6). Once Docker Desktop starts, the `-cuda` image tag is
fully qualified, and GPU-class indexing of 7623 assets should take minutes rather than
hours by general practice — not measured on our actual setup yet.

**Cloud.ru** free tier (25 vCPU·h + 50 GB·h/month for Container Services) comfortably
covers the compute estimate (0.6–3.0 vCPU·h), but the GB-hour question — billed by
container uptime vs. CPU load — remains unverified; today's attempt to test it failed on
API unavailability, not on the numbers. Structurally weaker than the workstation option
regardless of cost: family photo previews would leave the house, which is the exact risk
ADR-0010 requires accepting explicitly, and Immich's ML endpoint has no built-in
authentication compatible with a hosted deployment.

**Recommendation:** workstation batch (Option B) as primary — it's the only option that
keeps previews inside the home network and has the fastest expected turnaround; it's
blocked by one concrete administrative step (Hyper-V + reboot), not an architectural
unknown. Cloud.ru stays a conditional fallback pending a single-album billing test.
Jetson is closed by the numbers above.

**Cost of doing nothing:** loses semantic search and automatic face grouping — a real
convenience loss for a 7623-asset, multi-year library — but nothing about data safety:
upload, browsing, albums, sharing, video and backups are all independent of ML (confirmed
today: metadata extraction is already 100% done with zero ML container ever deployed).
This is a legitimate, cheap, fully private parked state, not a hidden problem.

**What we don't know:** actual indexing time on the real workstation+tunnel setup (only
general GPU-inference practice, not measured); Cloud.ru's GB-hour billing model;
whether a working access restriction exists for Immich's ML endpoint on Cloud.ru; our
library's actual peak ML memory footprint (only Immich's generic 6–8 GB guidance is
known); why Hyper-V is off on the workstation right now; per-video processing cost
separate from photos.
