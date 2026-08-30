# 29. Где считать и на чём думать — план развития / Where to compute and what to think on — development plan

> Составлен 2026-08-22 после того, как две записи в собственной документации
> оказались неверны. Обе меняли выводы, поэтому документ начинается с них.

🇬🇧
> Written on 2026-08-22 after two entries in our own documentation turned out
> to be wrong. Both changed conclusions, so this document starts with them.

---

## 1. Две поправки к фактам, на которых стоял прежний план / Two corrections to facts the previous plan relied on

### 1.1. «Считать не на чем» — неверно / "Nothing to compute on" — incorrect

🇷🇺 `CHECKPOINT_2026-08-11`, пункт 5, утверждал: «Windows-ноутбук с RTX 3050 Ti выведен
из проекта. У Jetson и Vostro подходящего ускорителя нет — **считать не на чем**».

🇬🇧 `CHECKPOINT_2026-08-11`, item 5, stated: "The Windows laptop with the RTX 3050 Ti
has been removed from the project. Neither Jetson nor Vostro has a suitable
accelerator — **there is nothing to compute on**."

🇷🇺 Замер 2026-08-22 на самой рабочей станции:

🇬🇧 Measurement on 2026-08-22 on the workstation itself:

```
NVIDIA GeForce RTX 3050 Ti Laptop GPU   4096 MiB VRAM, драйвер 596.36
AMD Ryzen 7 4800H                       8 ядер / 16 потоков
RAM                                     31.4 ГБ
```

🇷🇺 Это **та же машина, с которой ведётся проект**. Она никуда не выводилась. Ускоритель
скромный — 4 ГБ VRAM, — но это на порядок больше того, чем располагает Jetson, и
достаточно для всего, что проекту реально нужно.

🇬🇧 This is **the same machine the project has been run from all along**. It was never
removed. The accelerator is modest — 4 GB VRAM — but that is an order of magnitude
more than Jetson has, and enough for everything the project actually needs.

🇷🇺 Единственное настоящее ограничение: **машина включена не всегда**. Это меняет не
«можно ли», а «как проектировать»: всё тяжёлое должно быть **пакетным и
догоняющим**, а не синхронным.

🇬🇧 The only real constraint: **the machine is not always on**. This changes not
"whether it's possible" but "how to design it": everything heavy must be
**batched and catch-up**, not synchronous.

### 1.2. Приватность фотографий — решение владельца изменилось / Photo privacy — the owner's decision has changed

🇷🇺 Прежние документы (`PHOTO_PROCESSING_FEASIBILITY`, оценка Kaggle) строились на том,
что семейные фотографии не должны покидать дом ни при каких условиях. Владелец
2026-08-22 снял это ограничение: снимки и так распределены по внешним сервисам.

🇬🇧 Earlier documents (`PHOTO_PROCESSING_FEASIBILITY`, the Kaggle assessment) were
built on the premise that family photos must never leave home under any
circumstances. On 2026-08-22 the owner lifted this restriction: the photos are
already spread across external services anyway.

🇷🇺 Фиксирую как решение владельца, а не как техническую истину, и один раз называю
цену: снятие ограничения касается не только его собственных снимков, но и всех, кто
на них есть. Решение принято; дальше документ его не оспаривает.

🇬🇧 Recording this as the owner's decision, not as a technical truth, and naming the
cost once: lifting the restriction affects not only his own photos but everyone
who appears in them. The decision has been made; the rest of this document does
not contest it.

🇷🇺 **Что это меняет по факту: меньше, чем кажется.** Ниже показано, что оба варианта
с выносом фотографий наружу проигрывают локальному — не по приватности, а по
инженерии.

🇬🇧 **What this actually changes: less than it seems.** Below it is shown that both
options for moving photos off-site lose to the local option — not on privacy
grounds, but on engineering grounds.

---

## 2. Что проекту на самом деле не хватает / What the project actually lacks

🇷🇺 Не «мощности вообще», а трёх конкретных вещей:

🇬🇧 Not "compute power in general," but three specific things:

| # | Чего нет / What's missing | Чем это болит / Why it hurts | Кто просил / Who asked for it |
|---|---|---|---|
| 1 | **Распознавания лиц и умного поиска в Immich**<br>**Face recognition and smart search in Immich** | 7476 снимков, найти в них что-то можно только глазами<br>7476 photos, findable only by scrolling through them by eye | запрос №1 из комментариев к статье (dE1l, falcon4fun)<br>request #1 from the article comments (dE1l, falcon4fun) |
| 2 | **Локальной модели для семейного бота**<br>**A local model for the family bot** | `@бобик` уносит вопросы наружу — в проекте «уход от облаков» это дыра в тезисе<br>`@бобик` sends questions outside — in a project about "leaving the cloud," that is a hole in the thesis | тезис самого проекта<br>the project's own thesis |
| 3 | **Свободной памяти на Jetson**<br>**Free memory on Jetson** | 2.1 / 3.9 ГБ занято, три контейнера на 85–92 % лимитов<br>2.1 / 3.9 GB used, three containers at 85–92% of their limits | замечание tklim<br>tklim's remark |

🇷🇺 Все три решаются одним и тем же ходом: **снять тяжёлое с Jetson и отдать туда, где
есть чем считать.** Jetson остаётся тем, в чём он хорош — всегда включённым узлом
хранения и обслуживания.

🇬🇧 All three are solved by the same move: **take the heavy work off Jetson and hand
it to something that can actually compute.** Jetson stays what it's good at — an
always-on storage and serving node.

---

## 3. Immich ML — ближайший и самый ценный шаг / Immich ML — the nearest and most valuable step

🇷🇺 Immich умеет выносить машинное обучение на отдельный узел через
`IMMICH_MACHINE_LEARNING_URL`. Официальные CUDA-образы требуют CUDA 11/12, чего на
Jetson нет и не будет, — но на рабочей станции есть.

🇬🇧 Immich can offload machine learning to a separate node via
`IMMICH_MACHINE_LEARNING_URL`. The official CUDA images require CUDA 11/12, which
Jetson does not have and never will — but the workstation does.

### 3.1. Препятствие, которое надо назвать первым / The obstacle that has to be named first

🇷🇺 После перестройки домашней сети (`docs/28`) **Jetson не может сам инициировать
соединение к рабочей станции**: он в `192.168.0.0/24` за EC220, станция — в
`192.168.68.0/22` за Deco, и NAT пропускает только в одну сторону. А Immich ходит
к ML-сервису именно **со стороны сервера**.

🇬🇧 After the home network rebuild (`docs/28`), **Jetson cannot initiate a connection
to the workstation on its own**: it is on `192.168.0.0/24` behind the EC220, the
workstation is on `192.168.68.0/22` behind the Deco, and NAT only passes traffic
one way. And Immich reaches the ML service precisely **from the server side**.

🇷🇺 Три выхода, по возрастанию затрат:

🇬🇧 Three ways out, in increasing order of cost:

| Вариант / Option | Что делать / What to do | Цена / Cost |
|---|---|---|
| **A. Обратный туннель**<br>**A. Reverse tunnel** | станция сама поднимает `ssh -R 3003:localhost:3003 admin@192.168.0.50`; Jetson ходит на свой `127.0.0.1:3003`<br>the workstation itself brings up `ssh -R 3003:localhost:3003 admin@192.168.0.50`; Jetson talks to its own `127.0.0.1:3003` | ноль изменений в сети, работает сегодня; ровно та схема, которой соседний проект связывает Vostro с Ollama на Windows<br>zero network changes, works today; exactly the scheme the neighboring project uses to link Vostro with Ollama on Windows |
| B. Станцию в подсеть Jetson<br>B. Put the workstation on Jetson's subnet | воткнуть кабелем в EC220 либо задать Wi-Fi станции адрес из `192.168.0.0/24`<br>plug it into the EC220 by cable, or set the workstation's Wi-Fi address from `192.168.0.0/24` | нужно трогать сеть; станция теряет Wi-Fi-удобство<br>requires touching the network; the workstation loses Wi-Fi convenience |
| C. Довести Волну 1 до конца<br>C. Finish Wave 1 | шаги 2/3/6 регламента Deco: одна подсеть, один шлюз<br>steps 2/3/6 of the Deco rollout plan: one subnet, one gateway | правильно по существу, но это отдельная работа с простоем<br>correct in principle, but it's separate work with downtime |

🇷🇺 **Рекомендация — A.** Она ничего не ломает, проверяема за один вечер и не требует
согласований. B и C остаются как способ убрать туннель позже.

🇬🇧 **Recommendation — A.** It breaks nothing, is verifiable in one evening, and
needs no approvals. B and C remain as ways to remove the tunnel later.

### 3.2. Порядок работ / Order of work

1. На станции: `docker run` образа `immich-machine-learning` с CUDA, том под модели.
2. Проверить локально: `curl http://127.0.0.1:3003/ping`.
3. Поднять обратный туннель как службу Windows (autossh или запланированная задача).
4. На Jetson: `IMMICH_MACHINE_LEARNING_URL=http://127.0.0.1:3003`, пересоздать
   `immich_server` и `immich_microservices`.
5. Запустить фоновые задания: `Smart Search`, затем `Face Detection`.
6. **Замерить**: сколько времени занимает разбор 7476 снимков, сколько при этом
   ест Jetson (он раздаёт файлы) и сколько — станция.

🇬🇧
1. On the workstation: `docker run` the `immich-machine-learning` image with CUDA, a volume for the models.
2. Check locally: `curl http://127.0.0.1:3003/ping`.
3. Bring up the reverse tunnel as a Windows service (autossh or a scheduled task).
4. On Jetson: `IMMICH_MACHINE_LEARNING_URL=http://127.0.0.1:3003`, recreate
   `immich_server` and `immich_microservices`.
5. Run the background jobs: `Smart Search`, then `Face Detection`.
6. **Measure**: how long parsing 7476 photos takes, how much load Jetson carries
   meanwhile (it serves the files), and how much the workstation carries.

### 3.3. Чего ожидать честно / What to honestly expect

- Разбор 7476 снимков на 3050 Ti — часы, не минуты; это разовая догоняющая работа.
- Пока станция выключена, очередь Immich просто ждёт. Для семейного архива это
  нормально: новых снимков единицы в день.
- 4 ГБ VRAM хватает для CLIP и детекции лиц; это не тот случай, где нужен A100.
- **Jetson от этого разгружается**, а не нагружается: сегодня ML не работает вовсе.

🇬🇧
- Parsing 7476 photos on the 3050 Ti — hours, not minutes; this is a one-off catch-up job.
- While the workstation is off, the Immich queue simply waits. For a family archive
  that's fine: new photos arrive at a rate of a few per day.
- 4 GB VRAM is enough for CLIP and face detection; this is not a case that needs an A100.
- **Jetson is offloaded by this**, not burdened: today ML doesn't run at all.

🇷🇺 Этот шаг закрывает замечания dE1l и falcon4fun **без покупок** — ровно как и
обещала Фаза 5, только узлом оказывается не Vostro, а машина, которая всё это время
стояла рядом.

🇬🇧 This step addresses dE1l's and falcon4fun's remarks **without buying anything** —
exactly as Phase 5 promised, except the node turns out to be not Vostro but the
machine that had been sitting right there the whole time.

---

## 4. Kaggle — честная оценка / Kaggle — an honest assessment

🇷🇺 Владелец обучает там собственные модели (проект `Belgorod_platform`: Qwen2.5-1.5B,
QLoRA, Tesla P100 16 ГБ, прогон около двух часов, артефакт забирается и сливается
локально). Обвязка рабочая и хорошо документированная.

🇬🇧 The owner trains his own models there (the `Belgorod_platform` project:
Qwen2.5-1.5B, QLoRA, Tesla P100 16 GB, a run of about two hours, the artifact is
retrieved and merged locally). The tooling around it is working and well
documented.

### 4.1. Для фотографий Immich — не подходит, и не из-за приватности / For Immich photos — not a fit, and not because of privacy

🇷🇺 Даже теперь, когда ограничение по приватности снято, остаются три препятствия,
и каждого достаточно:

🇬🇧 Even now that the privacy restriction has been lifted, three obstacles remain,
and each is sufficient on its own:

1. **Kaggle — пакетный и односторонний.** Ноутбук не может достучаться до дома
   (CGNAT), а дом не может запустить ноутбук по событию. Каждый прогон запускается
   и забирается руками. Для индексации, которая должна догонять новые снимки
   ежедневно, это не механизм.
2. **Immich не принимает эмбеддинги со стороны.** Его конвейер рассчитан на
   собственный ML-сервис по `IMMICH_MACHINE_LEARNING_URL`. Посчитать векторы на
   Kaggle и «влить» их — не поддерживаемый путь; пришлось бы писать и сопровождать
   собственный импорт в схему чужой БД.
3. **Объём.** 5.8 ГБ фотографий надо было бы заливать в датасет и качать обратно
   на каждый заход. Против варианта, где всё считается дома за те же часы, это
   проигрыш по всем осям.

🇬🇧
1. **Kaggle is batch and one-directional.** The notebook cannot reach home (CGNAT),
   and home cannot trigger the notebook on an event. Every run is started and
   collected by hand. For indexing that needs to catch up with new photos daily,
   that is not a workable mechanism.
2. **Immich does not accept externally computed embeddings.** Its pipeline is
   built around its own ML service at `IMMICH_MACHINE_LEARNING_URL`. Computing
   vectors on Kaggle and "pouring them in" is not a supported path; it would
   mean writing and maintaining a custom import into someone else's DB schema.
3. **Volume.** The 5.8 GB of photos would need to be uploaded into a dataset and
   downloaded back on every run. Against an option that computes everything at
   home in the same number of hours, this loses on every axis.

🇷🇺 **Вывод: Kaggle для фотографий — нет.** Не потому что «страшно», а потому что
рабочая станция делает то же самое проще, быстрее и без ручных заходов.

🇬🇧 **Conclusion: Kaggle for photos — no.** Not because it's "scary," but because
the workstation does the same job more simply, faster, and without manual runs.

### 4.2. Для чего Kaggle действительно годится нам / What Kaggle is actually good for here

🇷🇺 Ровно для того же, для чего он у соседей: **разовое обучение маленькой модели под
узкую задачу**, где результат — небольшой артефакт, который потом живёт дома.

🇬🇧 Exactly what it's good for in the neighboring project: **a one-off training run
of a small model for a narrow task**, where the result is a small artifact that
then lives at home.

🇷🇺 Реалистичный кандидат у нас один, и он не про фотографии:

🇬🇧 We have exactly one realistic candidate, and it's not about photos:

> **Локальный классификатор намерений для семейного бота.** Сейчас любой свободный
> вопрос с позывным `@бобик` уходит наружу целиком. Маленькая модель, обученная
> отличать «на что можно ответить из домашних данных» от «это действительно вопрос
> к внешней модели», сократила бы исходящий поток и число вопросов, покидающих дом.

🇬🇧
> **A local intent classifier for the family bot.** Right now any free-form
> question addressed with the `@бобик` callsign goes outside in full. A small
> model trained to distinguish "answerable from home data" from "this really is
> a question for the external model" would cut down the outgoing traffic and
> the number of questions leaving home.

🇷🇺 Это близнец задачи соседей (у них — вопрос оператора → JSON-намерение), и их
обвязку можно переиспользовать почти целиком: сборщик ноутбука, `watch_kaggle_training.ps1`
(опрос статуса → скачивание → сверка SHA-256), локальное слияние адаптера.

🇬🇧 This is a twin of the neighboring project's task (theirs is operator question →
JSON intent), and their tooling can be reused almost wholesale: the notebook
builder, `watch_kaggle_training.ps1` (status polling → download → SHA-256
verification), local adapter merging.

🇷🇺 **Но делать это стоит не первым и не вторым шагом.** Сначала надо, чтобы локальная
модель вообще появилась (раздел 5) — иначе классифицировать не для чего.

🇬🇧 **But this should not be the first or second step.** First the local model
needs to exist at all (section 5) — otherwise there is nothing to classify for.

---

## 5. Локальная модель — закрыть дыру в тезисе проекта / Local model — closing the hole in the project's thesis

🇷🇺 Проект называется «уход от облаков», а его семейный ассистент отправляет вопросы
в DeepSeek. Это самая заметная нестыковка, и она чинится.

🇬🇧 The project is called "leaving the cloud," yet its family assistant sends
questions to DeepSeek. This is the most visible inconsistency, and it is fixable.

### 5.1. Что где помещается / What fits where

| Где / Where | Что реально запустится / What will actually run | Скорость / Speed | Всегда ли доступно / Always available |
|---|---|---|---|
| **Станция, RTX 3050 Ti 4 ГБ**<br>**Workstation, RTX 3050 Ti 4 GB** | Qwen2.5-7B-Instruct в Q4 с частичной выгрузкой; 3B в Q4 — с запасом<br>Qwen2.5-7B-Instruct in Q4 with partial offload; 3B in Q4 — comfortably | быстро<br>fast | нет, только когда включена<br>no, only while it's on |
| Jetson Nano 4 ГБ, CUDA 10.2<br>Jetson Nano 4 GB, CUDA 10.2 | 1.5B в Q4 на процессоре, ~1 ГБ<br>1.5B in Q4 on the CPU, ~1 GB | единицы токенов в секунду<br>a few tokens per second | да<br>yes |
| Vostro | ⛔ 3.7 ГБ RAM, боевой контур соседей, уже свопит<br>⛔ 3.7 GB RAM, the neighboring project's production environment, already swapping | — | — |

🇷🇺 Vostro из этого списка выбывает окончательно: владелец прямо сказал, что Belgorod
требователен к ресурсам, а квота у соседей ещё запрошена (`m0064`).

🇬🇧 Vostro drops out of this list for good: the owner said outright that Belgorod
is resource-hungry, and the quota with the neighboring project is still pending
request (`m0064`).

### 5.2. Как встроить, не ломая работающее / How to integrate it without breaking what works

🇷🇺 В шлюзе уже есть абстракция провайдера (`provider` в запросе, два провайдера,
единый бюджет и единое редактирование персональных данных). Добавляется **третий
провайдер — `ollama`**, и включается правило:

🇬🇧 The gateway already has a provider abstraction (`provider` in the request, two
providers, one shared budget, and one shared PII redaction). A **third provider
— `ollama`** — is added, along with the rule:

```
станция доступна  →  локальная модель, наружу не уходит ничего
станция выключена →  DeepSeek, как сейчас, с прежним редактированием
```

🇬🇧
```
workstation available  →  local model, nothing leaves home
workstation off        →  DeepSeek, as now, same redaction
```

🇷🇺 Редактирование, лимиты по людям и учёт токенов остаются на месте — они в шлюзе, а
не в провайдере. Связь Jetson → станция — тем же обратным туннелем, что и в п. 3.

🇬🇧 Redaction, per-person limits, and token accounting stay where they are — they
live in the gateway, not in the provider. The Jetson → workstation link uses
the same reverse tunnel as in section 3.

🇷🇺 **Выигрыш:** большая часть семейных вопросов перестаёт покидать дом, и это можно
показать цифрой — `/v1/usage` уже разбивает обращения по людям и провайдерам.

🇬🇧 **Payoff:** most family questions stop leaving home, and this can be shown as
a number — `/v1/usage` already breaks down requests by person and by provider.

---

## 6. OpenRouter — проверено в вебе, август 2026 / OpenRouter — verified on the web, August 2026

### 6.1. Факты / Facts

🇷🇺 **Подписки как таковой нет.** Это предоплаченные кредиты (pay-as-you-go). Цена
токенов передаётся **без наценки**, но комиссия берётся при пополнении:

🇬🇧 **There is no subscription as such.** It's prepaid credits (pay-as-you-go).
Token pricing is passed through **without markup**, but a fee is charged on
top-up:

| Что / What | Сколько / How much |
|---|---|
| Пополнение картой (Stripe)<br>Top-up by card (Stripe) | **5,5 %**, минимум $0,80 за платёж<br>**5.5%**, minimum $0.80 per payment |
| Пополнение криптовалютой (USDC)<br>Top-up by crypto (USDC) | 5 % / 5% |
| BYOK — свой ключ провайдера<br>BYOK — your own provider key | первый **1 млн запросов в месяц бесплатно**, дальше 5 %<br>the first **1M requests per month free**, then 5% |
| Бесплатный уровень (модели `:free`)<br>Free tier (`:free` models) | 50 запросов в сутки; после разового пополнения на $10 — 1000 в сутки. Потолок 20 запросов в минуту не снимается никогда<br>50 requests/day; after a one-off $10 top-up — 1000/day. The 20-requests-per-minute ceiling is never lifted |

🇷🇺 Что даёт: 500+ моделей от 80+ провайдеров через один API, **совместимый с форматом
OpenAI**; автоматическое переключение на другого провайдера при отказе или
rate-limit; маршрутизация по цене и скорости; мультимодальный ввод (изображения,
PDF, аудио) и структурированный вывод через `response_format: json_schema`.

🇬🇧 What it provides: 500+ models from 80+ providers through one API, **compatible
with the OpenAI format**; automatic failover to another provider on error or
rate-limit; routing by price and speed; multimodal input (images, PDF, audio)
and structured output via `response_format: json_schema`.

🇷🇺 Данные: OpenRouter по умолчанию **не логирует содержимое** запросов и заявляет, что
не использует их для обучения; но провайдеры-источники могут — по своим правилам.
Есть переключатели на уровне аккаунта: запрет маршрутизации к провайдерам,
обучающимся на данных, и режим **Zero Data Retention**.

🇬🇧 Data: by default OpenRouter **does not log the contents** of requests and
states it does not use them for training; but the upstream providers
themselves may, under their own rules. There are account-level toggles:
disallowing routing to providers that train on data, and a **Zero Data
Retention** mode.

### 6.2. Три факта, которые решают вопрос для нас / Three facts that settle the question for us

1. 🔴 **GigaChat в каталоге OpenRouter отсутствует.** Проверено поиском по
   провайдерам. То есть для половины нашей текущей связки агрегатор не даёт **ничего**;
   прямая интеграция остаётся единственным путём и никуда не денется.
2. 🔴 **Ограничение по России — не по IP, а по платёжному адресу.** С мая 2026
   аккаунтам с российским billing address закрыт доступ к моделям **OpenAI,
   Anthropic и Google** — то есть ровно к тем, ради которых агрегатор и берут.
   Пополнение российскими картами через Stripe заблокировано. **VPN эту проблему не
   решает** — решает платёжный инструмент, а не выходной IP. Остальные провайдеры
   (DeepSeek, Qwen, Mistral, Meta) остаются доступны.
3. **DeepSeek через OpenRouter не дешевле.** Цена та же, что напрямую, плюс 5,5 % на
   пополнение. BYOK со своим ключом убирает комиссию, но тогда OpenRouter — чистая
   прослойка поверх уже работающего у нас ключа, без выигрыша.

🇬🇧
1. 🔴 **GigaChat is absent from OpenRouter's catalog.** Verified by searching the
   provider list. So for half of our current setup the aggregator gives **nothing**;
   direct integration remains the only path and isn't going anywhere.
2. 🔴 **The Russia restriction is not by IP, but by billing address.** Since May
   2026, accounts with a Russian billing address have been cut off from
   **OpenAI, Anthropic, and Google** models — precisely the ones an aggregator
   is taken out for in the first place. Topping up with Russian cards via
   Stripe is blocked. **A VPN does not solve this** — the payment instrument
   is the gate, not the exit IP. The other providers (DeepSeek, Qwen, Mistral,
   Meta) remain available.
3. **DeepSeek through OpenRouter is not cheaper.** The price is the same as
   going direct, plus 5.5% on top-up. BYOK with your own key removes the fee,
   but then OpenRouter is a pure pass-through layer over a key we already
   have working, with no upside.

### 6.3. Вывод / Conclusion

🇷🇺 **Постоянную подписку брать не стоит.** Главное, ради чего берут агрегатор — единая
точка входа, абстракция провайдера и переключение между ними, — **у проекта уже
написано своими руками**, причём с редактированием персональных данных и учётом
токенов по каждому члену семьи, чего у OpenRouter нет. Пропускать уже
отредактированный семейный трафик ещё через одного внешнего посредника ради
функции, которая и так есть, — плата без покупки.

🇬🇧 **A standing subscription is not worth taking.** The main reason people use an
aggregator — a single entry point, a provider abstraction, and switching
between them — **the project has already built by hand**, complete with PII
redaction and per-family-member token accounting, which OpenRouter does not
have. Routing already-redacted family traffic through one more external
intermediary for a feature we already have would be paying without buying
anything.

🇷🇺 **Где он всё же может пригодиться — разово, а не подпиской.** Пополнить $10–20 без
автопополнения и использовать как испытательный стенд: сравнить ответы моделей,
которых у нас нет, попробовать vision-модель на фотографии, проверить
структурированный вывод. Для этого агрегатор удобен именно тем, что не требует
заводить аккаунт у каждого провайдера.

🇬🇧 **Where it could still be useful — as a one-off, not a subscription.** Top up
$10–20 with auto-recharge off and use it as a test bench: compare responses
from models we don't have, try a vision model on a photo, check structured
output. For this the aggregator is convenient precisely because it doesn't
require opening an account with every provider.

🇷🇺 Если это делать — **подключать в шлюз четвёртым провайдером** и не менять
умолчание. Наша абстракция это позволяет, и API совместим с OpenAI, так что работы
там на вечер.

🇬🇧 If this is done — **wire it into the gateway as a fourth provider** without
changing the default. Our abstraction allows this, and the API is
OpenAI-compatible, so it's an evening's work.

---

## 7. Порядок работ / Order of work

```
Шаг 1  Immich ML на станции + обратный туннель      ← наибольшая польза на единицу труда
Шаг 2  Локальная модель в шлюз третьим провайдером
Шаг 3  Классификатор намерений, обучение на Kaggle   ← только когда есть шаг 2
—      OpenRouter: постоянная подписка НЕ рекомендуется (раздел 6);
       при желании — разовые $10–20 как испытательный стенд, четвёртым провайдером
```

🇬🇧
```
Step 1  Immich ML on the workstation + reverse tunnel      ← biggest payoff per unit of effort
Step 2  Local model added to the gateway as the third provider
Step 3  Intent classifier, trained on Kaggle                ← only once step 2 exists
—       OpenRouter: a standing subscription is NOT recommended (section 6);
        if desired — a one-off $10–20 as a test bench, as a fourth provider
```

🇷🇺 **Зависимости.** Шаг 1 и шаг 2 делят один обратный туннель — поднимать его один раз.
Шаг 3 бессмыслен без шага 2.

🇬🇧 **Dependencies.** Step 1 and step 2 share one reverse tunnel — set it up once.
Step 3 is meaningless without step 2.

🇷🇺 **Чего в этом плане сознательно нет:** покупок железа, переноса вычислений на Vostro,
выгрузки фотографий во внешние сервисы. Первое — принцип проекта, второе — чужой
боевой контур, третье — проигрывает локальному варианту инженерно, а не этически.

🇬🇧 **What this plan deliberately does not include:** buying hardware, moving
compute to Vostro, uploading photos to external services. The first is a
project principle, the second is someone else's production environment, the
third loses to the local option on engineering grounds, not ethical ones.

---

## 8. Что этот план закрывает из старых обещаний / What this plan closes out of old promises

| Обещание / Promise | Где было / Where it was made | Чем закрывается / What closes it |
|---|---|---|
| ML-разгрузка на существующее железо<br>ML offload onto existing hardware | Фаза 5, ответ falcon4fun<br>Phase 5, reply to falcon4fun | шаг 1, узлом стала рабочая станция<br>step 1, the workstation became the node |
| Распознавание лиц и умный поиск<br>Face recognition and smart search | ответ dE1l<br>reply to dE1l | шаг 1 / step 1 |
| «GPU простаивает»<br>"GPU sits idle" | ответ vvzvlad<br>reply to vvzvlad | частично: GPU Jetson по-прежнему не у дел (CUDA 10.2 — структурное ограничение), но ML в проекте появляется<br>partially: Jetson's GPU is still unused (CUDA 10.2 is a structural limit), but ML now exists in the project |
| Разгрузка Jetson по памяти<br>Freeing up Jetson's memory | Фаза 2, замечание tklim<br>Phase 2, tklim's remark | шаг 1: тяжёлое уезжает с Jetson<br>step 1: the heavy work moves off Jetson |
| «Уход от облаков» для бота<br>"Leaving the cloud" for the bot | тезис проекта<br>the project's thesis | шаг 2 / step 2 |
