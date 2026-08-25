# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.6.0] — 2026-08-22 · Сеть перестроена, алерты заговорили, один диагноз отозван

> 🇷🇺 День начался с жалобы «телефоны не синхронизируются» и трёх ❌ в отчёте.
> Закончился тем, что отчёт научился говорить правду, система — жаловаться в чат,
> а автор — отзывать собственные ошибочные выводы.
>
> 🇬🇧 The day started with "phones don't sync" and three ❌ in the report. It ended
> with the report telling the truth, the system able to complain in chat, and the
> author retracting his own wrong conclusion.

### Исправлено / Fixed

- **Nextcloud перестал навязывать всем клиентам один адрес.** В `overwritehost`
  остался адрес VPS, сменившийся 09.08, и **каждый** клиент — включая телефон в двух
  метрах от NAS — получал редирект на `https://193.8.215.130:8443`. Снято навязывание
  как таковое: клиент остаётся там, откуда пришёл, и следующая смена IP ничего не
  сломает. Попутно вернулась проверка доверенного домена, которую `overwritehost`
  фактически отключал.
  🇬🇧 Nextcloud no longer forces one address on every client.
- **nginx на VPS терял порт** в сгенерированных редиректах: `$host` отбрасывает порт,
  `$http_host` — нет. Правка через `reload`, без пересоздания контейнера.
- **Внешняя проверка в отчёте больше не кричит волком.** Она curl-ила порты VPS с
  публичного выхода Jetson — закрытые ещё Фазой 1 — и печатала ❌ на штатное состояние.
  Теперь цепочка `клиент → nginx → туннель → Jetson` меряется на самом VPS против
  `127.0.0.1`, а наружная проверка **инвертирована**: тревога — это порт, который
  ответил из интернета. 🇬🇧 The monitor now alarms on an *open* port, not a closed one.
- **`SERVER_IP` в `/etc/nasa-monitor/`** указывал на заблокированный адрес с 23 июня —
  из-за этого же молчал Beszel.
- **Immich перестал ежечасно давиться** файлом CorelDRAW: из автозагрузки снят альбом
  `WhatsApp Documents` (папка документов, а не фотографий).

### Добавлено / Added

- **Фаза E — системные алерты в чат.** Проверка каждые 15 минут: устаревшие бэкапы,
  отвал `/mnt/storage`, упавшие контейнеры, диск, память. Молчит, когда всё хорошо, и
  сообщает о выздоровлении. Проверено вживую, включая собственный сбой проверки.
  🇬🇧 Phase E: system alerts into the family chat; silent when healthy.
- **Слепок домашней сети** [`28_NETWORK_SNAPSHOT`](docs/28_NETWORK_SNAPSHOT_2026-08-22.md):
  Deco введён вторым роутером позади EC220 (двойной NAT), Jetson не тронут и **остался
  в гигабите**. Плюс проверка телефона владельца через adb.
- **План развития по вычислениям** [`29_COMPUTE_AND_LLM_ROADMAP`](docs/29_COMPUTE_AND_LLM_ROADMAP.md):
  Immich ML на рабочей станции, локальная модель в шлюз, честная оценка Kaggle и OpenRouter.
- **Волна 0 сдвинулась:** владелец согласовал Vostro, ключ авторизован на VPS
  (`restrict,permitopen`) и на Jetson (forced command только на чтение).
- **Правила для субагентов** в `CLAUDE.md`, включая требование отвечать по-русски.
- **Совместная доска работ** для двух проектов владельца: `BOARD.md` + обмен файлами.

### Изменено / Changed

- README сокращён с 717 до 205 строк: входная дверь, а не руководство.
- Лимиты памяти: `uptime_kuma` 128 → 192 МБ (было 92 % занятости), `netdata` 256 → 320 МБ.
- Новое жёсткое правило №14: документация и GitHub всегда актуальны, двуязычны и не раздуты.

### Отозвано / Retracted

- 🔴 **«Talk-бот 12 дней бил в стену» — неверно, шторм создал автор.** Замер базовой
  линии: вчера 13 626 опросов, **все `304`, ноль `400`**; все 7 975 отказов уложились
  в час, когда снимался `overwritehost`. То есть найдена, диагностирована и починена
  собственная регрессия двадцатиминутной давности, приписанная прошлому. Ошибка
  оставлена в документации вместе с тем, как она была поймана.
  🇬🇧 Retracted: the "12-day outage" was a self-inflicted 20-minute regression.
- 🔴 **«Считать не на чем» — неверно.** Рабочая станция, с которой ведётся проект, —
  это RTX 3050 Ti (4 ГБ VRAM), Ryzen 7 4800H, 31 ГБ RAM. Она никуда не выводилась.

---

## [Unreleased]

### Исправлено / Fixed

- 🔴 **AmneziaVPN Desktop (Windows) не может сгенерировать нового VPN-клиента** —
  `ErrorCode 305` («тайм-аут подключения к серверу»), затем «SSH запрос отклонён».
  Проверено и отклонено как причина: смена IP VPS (TCP до старого и нового IP —
  одинаково ~50 мс), диск/память/docker на VPS, лимит частоты на порту 22,
  исчерпание пула IP `10.8.1.0/24`. Трассировка `sshd` на `LogLevel DEBUG3`
  (снята безопасно через `reload`, не `restart`) показала: транспорт и
  авторизация здоровы, но сессии приложения либо не доходят до `exec`, либо рвут
  канал сразу после — `awg0.conf` на сервере ни разу не изменился. Причина
  осталась в самом приложении (лога на диске нет, список серверов в реестре
  зашифрован) — не долблена дальше, т.к. владельцу нужен был рабочий VPN, а не
  починка чужого клиента. **Обход:** пиры добавляются вручную —
  `wg genkey`/`pubkey`/`genpsk` в контейнере `amnezia-awg2` → `wg set awg0 peer
  ...` живьём → тот же блок дописывается в `awg0.conf` с бэкапом
  `.bak.<unixtime>` → клиентский `.conf` собирается вручную с параметрами
  обфускации `Jc/Jmin/Jmax/S1-S4/H1-H4`, скопированными из `[Interface]`
  сервера. Добавлено 6 пиров (было 13, стало 19), один подтверждён владельцем
  как рабочий на Vostro. Разбор и команды —
  [`05_NETWORKING_VPN.md` §3.5](docs/05_NETWORKING_VPN.md#35-обход-генерации-клиента-amneziavpn-desktop-2026-08-25--amneziavpn-desktop-client-generation-workaround-2026-08-25),
  [`CHECKPOINT_2026-08-25.md`](docs/plans/CHECKPOINT_2026-08-25.md).
  🇬🇧 AmneziaVPN Desktop (Windows) cannot generate new VPN clients through its
  own SSH-based provisioning; root cause stayed inside the closed-source
  client. Workaround: peers added directly via `wg`/`awg` inside the
  `amnezia-awg2` container. VPN itself never went down — 19 peers, zero
  restarts of `amnezia-xray`/`amnezia-awg2` throughout.

### Добавлено / Added

- **Подкачка zram взята под наблюдение** — тревога при заполнении ≥ 85 % и при её
  отсутствии (значит `nvzramconfig` не поднялся). Раньше за ней не следил никто, а
  когда zram кончается, следующая остановка — снятие процессов по памяти.
  🇬🇧 Swap is now monitored; it was not before.
- `vm.page-cluster` → 0 в `/etc/sysctl.d/60-nasa-zram.conf`: упреждающее чтение
  бессмысленно, когда подкачка лежит в ОЗУ.
- `docs/33_ZRAM.md` — разбор с замерами. Вывод честный: **zram уже работает и
  тюнить в нём почти нечего.** Сжатие 2.27×, занято 33 %, трафик ~6 МБ/час.
  🔴 `lz4`/`zstd` в ядро 4.9-tegra **не собраны** — решение соседнего проекта с
  `zstd` здесь физически неприменимо, а `deflate` дал бы ~62 МБ ценой процессора.
  Настоящий рычаг по памяти — вынести вычисления с Jetson, а не сжимать сильнее.

- 🔴 **Ворота качества — обязательное условие проекта** (`docs/32_QUALITY_GATE.md`,
  правило №14). Ошибка ловится локально, а не в бою. `scripts/quality/preflight.sh`
  проверяет: синтаксис bash и Python, ShellCheck, **совместимость `scripts/` с
  Python 3.6** (vermin), значения `.env`, секреты, docker-compose, регрессионные
  тесты. Хук `.githooks/pre-commit` запускает ворота автоматически.
  🇬🇧 Mandatory local quality gate: defects must be caught before deployment.
- `scripts/quality/check_env_syntax.py` — разбор `.env` на значения, которые
  уронят `source` под `set -euo pipefail`.
- `tests/unit/test_talk_alert_selftest.py` — регрессия на дефект, который **не
  ловит ни один статический анализатор**: подстрока `error` внутри
  `Completed without error`. Тест дополнительно следит, что боевой код не потерял
  защиту от возврата дефекта.

### Исправлено / Fixed

- 🔴 **`config/.env.example` содержал два незакавыченных значения с пробелами**, и
  одно из них — `TALK_BOT_DISPLAY_NAME=NAS Bot`, ровно та строка, что оставила
  проект без бэкапов на 16 дней. Она лежала в шаблоне, с которого все копируют.
  Найдено собственными воротами на первом же прогоне.
- **Дефект в самих воротах.** Первая версия проверки `.env` делала
  `if ( set -euo pipefail; . "$f" )` — bash отключает `errexit` внутри условия, и
  проверка **пропустила** файл, который обязана была отклонить. Разбор вынесен в
  отдельный скрипт с явным кодом возврата. Тот же класс дефекта независимо
  повторился у соседнего проекта: упавший линтер рапортовал успех.

### Добавлено / Added

- **Контроль здоровья 2-ТБ HDD.** Атрибуты SMART проверяются каждые 15 минут вместе с
  остальными алертами (`-n standby`, спящий диск не будим); короткий самотест —
  еженедельно по таймеру `nas_jetson_nano-hdd2tb-selftest.timer`.
  🇬🇧 SMART health monitoring for the 2 TB archive HDD.

### Отозвано / Retracted

- 🔴 **«SMART невозможен» относилось к обоим дискам — неверно.** Вывод, полученный на
  мосту JMS583 (USB SSD), был перенесён на RTL9201 (USB HDD) без проверки и записан в
  `CLAUDE.md` и `13_MONITORING_RUNBOOK`. Проверка 2026-08-22: `smartctl -d sat /dev/sdb`
  читает всё, включая запуск самотестов.

  Замер: `WDC WD20EADS-00W4B0` — **PASSED**, наработка **2553 ч** (~106 суток),
  Reallocated / Current_Pending / Offline_Uncorrectable — **0**, UDMA_CRC 0, 31 °C,
  журнал ошибок пуст, короткий самотест без ошибок, чтение 99.5 / 84.8 / 51.6 МБ/с
  по зонам. Диск старый по модели (WD Green ~2009), но почти не работал.

  🇬🇧 Retracted: SMART is impossible only on the SSD's JMS583 bridge; the 2 TB HDD
  behind RTL9201 reports full SMART and is healthy — 2553 power-on hours, zero bad
  sectors of any kind.

  **Урок шире случая:** вывод, полученный на одном устройстве, нельзя переносить на
  другое только потому, что они одного класса.

---

## [1.5.0] — 2026-08-11 · Семейный ИИ-помощник + честность вместо обещаний

> 🇷🇺 Релиз о двух вещах сразу. Первая — в доме появился ИИ-помощник, у каждого
> свой чат и свой лимит. Вторая, менее приятная и более важная: несколько функций,
> которые документация давно объявляла работающими, **не работали никогда**, и этот
> релиз их либо чинит, либо честно снимает обещание.
>
> 🇬🇧 A release about two things. One: the family got an AI assistant — a private
> chat and a personal budget each. Two, less pleasant and more important: several
> features the docs had long claimed as working **had never worked at all**. This
> release either fixes them or honestly withdraws the promise.
>
> Точка состояния с замерами: [`docs/plans/CHECKPOINT_2026-08-11.md`](docs/plans/CHECKPOINT_2026-08-11.md)

### Fixed / Исправлено (2026-08-11)

- 🇷🇺 🔴 **Системные алерты в семейный чат не работали никогда.** `POST /v1/talk/notify` —
  документированный способ сообщать о заполнении диска и перезапуске контейнера —
  падал с `404`. Дефект оказался **двойным**: общий помощник `_ocs_post` слал `json=`
  вместо формы, а базовый URL указывал на API **v4**, тогда как чат в spreed живёт
  только в **v1**. Накануне была починена только отправка бота, и работала она
  случайно — там URL собирался вручную сразу с `v1` и обходил обе проблемы разом.
  Исправлено централизованно; проверено вживую: `notify` → `message_id: 116`,
  `нас пинг` → `pong`, `@бобик` → ответ.
- 🇬🇧 🔴 **System alerts to the family chat had never worked.** The defect was double:
  `_ocs_post` sent JSON where OCS needs form data, and the base URL pointed at API v4
  while spreed keeps chat under v1 only. Fixed centrally and verified live.

### Security / Безопасность (2026-08-11)

- 🇷🇺 **Канал фотографий наружу закрыт обратно.** `LLM_ALLOW_IMAGE_ANALYSIS` возвращён
  в `false` на устройстве. Флаг включали ради эксперимента с ретушью через GigaChat;
  эксперимент показал, что **провайдер фотографии не редактирует вообще**, — значит
  открытый канал, по которому настоящие семейные снимки уходили наружу, не покупал
  ничего. Проверено: `/v1/image/edit` → `403`, при этом текстовый разговор не пострадал.
- 🇬🇧 **The outbound photo channel is shut again.** The flag bought nothing, because the
  provider does not edit photographs at all; verified `403` with text chat unaffected.

### Changed / Изменено (2026-08-11)

- 🇷🇺 **Роль ноутбука Dell Vostro 15 пересмотрена: не ML-узел.** Живая проверка вместо
  доверия плану: **CUDA нет** (Intel HD 520 + AMD R5 M230), 2 ядра без turbo, 3.7 ГБ RAM,
  и машину уже делит второй проект владельца, которому нужен отзывчивый сервис.
  Взяты сильные стороны ноутбука — **825 ГБ и расположение в другом здании**:
  off-site хранилище и внешний сторож. Блокер L0 при этом снят — исходящий TCP/22
  на VPS работает.
- 🇬🇧 **The Vostro laptop is no longer the ML node.** A live audit found no CUDA, two
  cores without turbo, and a second project already sharing the machine. Its real
  strengths — 825 GB and a different building — make it off-site storage instead.

### Added / Добавлено (2026-08-11)

- 🇷🇺 **Канал между двумя проектами владельца.** Две сессии агента на одной машине
  делят ноутбук и VPS, но друг друга не видели, и это уже стоило дорого: соседний
  проект больше месяца стоял на блокере, которого нет (ждал наш старый IP), а его
  runbook собирался занять порт `10022`, который держит туннель Jetson. Сделана
  «забирающая» доска (вне git) + хуки `SessionStart` / `UserPromptSubmit`: никто
  не пишет в чужую сессию, факты забираются сами.
- 🇬🇧 **A channel between the owner's two projects** — a pull-based board plus hooks,
  after the missing channel cost both sides real time.

### Documentation / Документация (2026-08-11)

- 🇷🇺 Новая точка проекта [`docs/plans/CHECKPOINT_2026-08-11.md`](docs/plans/CHECKPOINT_2026-08-11.md) —
  снимок с замерами, что закрыто и что открыто, включая список решений, которые
  принимает владелец, а не агент.
- 🇷🇺 Четыре новые «грабли» в `CLAUDE.md`: `172.29.172.1` указывает на разные хосты
  из разных сетей; `ffmpeg` съедает stdin вместе с остатком ssh-скрипта; порты VPS —
  общий ресурс; консоль Windows `cp1251` роняет печать кириллицы из Python.
- 🇷🇺 Из публичного репозитория убраны имя и пути соседнего рабочего проекта —
  документ сам обещал их не содержать, а они там были.

---

## [1.4.2] — 2026-08-10 · Talk-бот Фаза C, GigaChat, персональные лимиты

### Deployed / Выкачено на устройство (2026-08-10, вечер)

- 🇷🇺 **Семейный ИИ-помощник заработал.** У каждого своя комната в Nextcloud Talk
  (`nx4ud9c6` Алексей · `qnxnugq4` olga · `2pnixgv2` ivan · `z6u9hsu4` ulyana ·
  `ta7cinuy` anna · `37pcobmf` общая), бот слушает все шесть параллельно.
  Два позывных: `нас <команда>` считается дома, **`@бобик <вопрос>`** уходит наружу.
- 🇷🇺 **GigaChat подключён вторым провайдером** — с полной проверкой TLS через бандл
  НУЦ Минцифры (`config/certs/`). Оба провайдера ходят через одно редактирование
  и один бюджет.
- 🇷🇺 **Персональный учёт токенов** — лимит на человека, на дом за сутки и на месяц
  по деньгам; `GET /v1/usage` показывает разбивку по людям.
- 🇷🇺 **Обработка фото из чата** — бот забирает вложение, отправляет в Кандинский
  и возвращает результат в ту же комнату.
- 🇬🇧 **Family AI assistant is live**: a private Talk room per person, two callsigns
  (local vs outbound), GigaChat as a second provider with proper TLS, per-user token
  quotas, and photo handling from the chat.

### Fixed / Исправлено (2026-08-10, вечер)

- 🇷🇺 🔴 **Talk-бот не отвечал НИКОМУ с момента запуска Фазы A.** Общий помощник
  `_ocs_post` слал `json=`, а OCS API Nextcloud принимает только form-encoded, и
  возвращал `404 / statuscode 998 "Invalid query"`. Ошибка глушилась в `except`,
  поэтому в статусе месяцами копилось `processed`, а `replied` оставался 0 — и это
  читалось как «никто не пишет команд». Исправлено точечно в `_send`; тот же дефект
  вероятен у других вызывающих сторон `_ocs_post` — не проверено.
- 🇷🇺 🔴 **Фильтр имён молча выбрасывал короткие уменьшительные.** `/health` показал
  `names_configured=8` при 11 именах: защита `len(stem) < 3` срезала «Оля», «Уля»,
  «Аня» — то есть именно те формы, которыми в семье и разговаривают. Подстановочный
  шаблон заменён на явный список падежных окончаний; побочно ушло ложное срабатывание
  на «Олег». Добавлено `names_dropped` в `/health`, чтобы пропуск нельзя было не заметить.
- 🇷🇺 🔴 **Убраны обещания редактировать фотографии, которых провайдер не выполняет.**
  Проверено прямым запросом: GigaChat отвечает «Я не могу редактировать изображения».
  Реально работает связка «модель посмотрела и описала → Kandinsky нарисовал новое»,
  поэтому лицо человека не сохраняется в принципе. Пресеты `restore` / `colorize` /
  `glamour` / `upscale` убраны и возвращают `422` с объяснением; остались
  `anime` / `cartoon` / `artistic` с честной формулировкой «по мотивам».
- 🇬🇧 Three honesty fixes: the bot had never delivered a single reply (OCS wants form
  data, not JSON); the name filter silently dropped short diminutives; the image
  presets promised editing the provider cannot do.

### Added / Добавлено (2026-08-10, вечер)

- 🇷🇺 **`docs/plans/PHOTO_PROCESSING_FEASIBILITY.md`** — разбор предложенной архитектуры
  фото-сервиса против реального железа. Вывод: **Qwen-Image-Edit (20B) и FLUX Kontext
  не влезают в 4 ГБ VRAM** RTX 3050 Ti даже в Q4. Зато GFPGAN, Real-ESRGAN, BiRefNet и
  OpenCV поедут свободно — и именно они решают задачу «обработай красиво, а не
  сгенерируй», сохраняя человека и **не отправляя фото наружу**.
- Публичные корневые сертификаты НУЦ Минцифры в `config/certs/` — чтобы развёртывание
  GigaChat было воспроизводимым (точечное исключение из правила `*.pem`).

### Decided / Принятые решения (2026-08-10)

- 🇷🇺 **Домашняя сеть переводится на mesh TP-Link Deco E4 с полной заменой роутера
  EC220-G5.** Режим Router, LAN IP переводится на `192.168.0.1/24` — подсеть проекта и
  адрес Jetson `192.168.0.50` сохраняются. Регламент: `docs/27_HOME_NETWORK_MESH.md`.
  **Принятая цена решения:** порты Deco аппаратно 10/100, линк Jetson упадёт
  1000 → 100 Мбит/с, Wi-Fi → NAS с 141 до ≈ 94 Мбит/с. Владелец принял осознанно:
  интернет-тариф ≤ 100 Мбит/с, узким местом становится сеть, а не диски.
  Путь отхода — гигабитный свитч между Deco и проводными устройствами.
- 🇬🇧 **Home network moves to a TP-Link Deco E4 mesh, fully replacing the EC220-G5
  router.** Router mode with LAN IP changed to `192.168.0.1/24`, so the project subnet and
  the Jetson's address are preserved. Accepted cost: the Jetson's link drops from 1000 to
  100 Mbit/s because Deco ports are 10/100.
- 🇷🇺 **Ноутбук Vostro 15 остаётся в корпоративной сети** `192.168.75.177` и становится
  **удалённым** ML-узлом: связь с Jetson строится исходящим SSH-туннелем через VPS
  (порт `3003` → loopback VPS `13003` → Jetson). Прямого LAN-пути не будет.
  Цена: задержка ML-запроса ≈ 200–400 мс и ~1.5–2 ГБ разового трафика на бэклог.
- 🇬🇧 **The Vostro 15 stays in the corporate network** and becomes a **remote** ML node,
  reached through an outbound SSH tunnel via the VPS.
- 🇷🇺 **План по Keenetic Omni KN-1410 закрыт** — Deco решает ту же задачу лучше.
  Устройство остаётся холодным резервом.

### Added / Добавлено (2026-08-10)

- 🇷🇺 **`docs/plans/ROADMAP_STEP2_2026-08.md` — сквозной план развития проекта (Шаг 2).**
  Шесть волн с жёсткими зависимостями: страховка (git↔устройство, restic off-site,
  проверка авто-восстановления реальным отвалом SSD, guard от повторения истории с `.env`)
  → сеть → ML-узел → разгрузка Jetson → GPU-эксперимент с таймбоксом → Talk B/C/E → статья.
  У каждой волны — измеримый критерий приёмки, оценка риска, критерий отката и материал
  для Части 2 статьи. Отдельным разделом зафиксировано, что **сознательно не делается**
  в Шаге 2 и почему.
- 🇬🇧 **`docs/plans/ROADMAP_STEP2_2026-08.md` — the Step 2 roadmap:** six waves with hard
  dependencies, measurable acceptance criteria per wave, rollback criteria, and the article
  material each wave produces; plus an explicit out-of-scope list.
- `docs/27_HOME_NETWORK_MESH.md` — регламент перевода домашней сети на Deco E4:
  проверенные по спецификации возможности режимов Router/AP, замеры «до», целевая
  топология, адресный план, пошаговая настройка с сохранением доступа к NAS,
  приёмочные тесты, откат, путь отхода по скорости, источники.
- `docs/plans/POST_HABR_FEEDBACK_2026-08.md` — новая **Фаза 7** (перестройка сети) и
  таблица статусов всех фаз; Фаза 4 (температура SSD) переведена в статус
  **⛔ невозможна** с полным разбором почему — материал для Части 2 статьи.

### Changed / Изменено (2026-08-10)

- `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md` **переписан** под удалённое размещение:
  сетевые параметры узла взяты из локального источника вне git, добавлены
  схема двойного туннеля через VPS, честная оценка задержки и трафика, фаза освобождения
  ресурсов от стенда ZTN, таблица рисков. Уточнено: ОС уже Ubuntu 24.04 — переустановка
  не требуется.
- `docs/26_DECO_E4_NETWORK.md` помечен как заменённый; в шапке зафиксировано, **что
  именно в нём оказалось неверно** (утверждение, будто режим роутера обязательно меняет
  подсеть — LAN IP меняется в приложении) и что перенесено в документ 27.
- `docs/25_KEENETIC_OMNI_KN1410.md` помечен как закрытый план.
- `CLAUDE.md`: новые правила №10–12 (Deco только в режиме Router с переводом на
  `192.168.0.1` до подключения Jetson; не сбрасывать EC220-G5 до приёмки; записать
  параметры WAN до замены роутера).

### Fixed / Исправлено

- 🇷🇺 **Бэкапы БД не создавались 16 дней (24.07 → 09.08) — исправлено.** Причина: строка
  `TALK_BOT_DISPLAY_NAME=NAS Bot` в `config/.env` **без кавычек**; `source` под
  `set -euo pipefail` падал с кодом 127 до первого `pg_dump`, а systemd рапортовал
  `Result=success`. Тем же обрывом были сломаны `storage_preflight.sh`,
  `nasa-ssd-recovery.service` (автовосстановление при hotplug SSD) и `jetson-nas-health`.
  **Восстановление из дампов проверено впервые** — накатом во временную БД, счётчики сошлись
  с live один-в-один. Методика и правило проверки записаны в `docs/12_BACKUP_RESTORE.md`.
- 🇬🇧 **Nightly DB backups were silently dead for 16 days — fixed.** An unquoted value in
  `config/.env` killed every script that sources it under `set -e`, including the SSD
  hotplug auto-recovery. Restore verified for the first time; procedure documented.
- 🇷🇺 **Реверс-туннель смотрел на заблокированный IP VPS — исправлено.** `193.8.215.130`
  заблокирован российскими ISP; переведён на `95.163.176.103`. Хост живёт в root-owned
  `/opt/nasa/config/.env`, а не в `~/nasa/config/.env`.
- 🇬🇧 **Reverse tunnel was dialing a blocked VPS IP — fixed** (`95.163.176.103`).
- 🇷🇺 Погашен забытый тестовый `python3 -m http.server` на порту 8123, висевший 14 ч и
  слушавший всю домашнюю сеть (остаток от замеров скорости Wi-Fi).

### Security / Безопасность

- 🇷🇺 **Сервисы уведены из интернета** (закрыта находка №1 аудита 2026-08-01): ufw на VPS
  пускает 8080/8443/2283/2443/8090/9443/**8099**/8091/8765/8766 только с `172.29.172.0/24`
  и `10.8.1.0/24`. Наружу остались 22 (нужен для реверс-туннелей), 443 и 40568/udp.
  Правило №4 проекта соблюдено.
- 🇬🇧 **Service ports removed from the public internet** — VPN-only access; only 22, 443 and
  40568/udp remain world-reachable.
- 🇷🇺 Отмечен остаточный риск: **внутри домашней LAN сегментации нет** — все сервисы
  доступны любому, кто знает пароль Wi-Fi.

### Added / Добавлено

- 🇷🇺 **HDD 2 ТБ подключён как семейный архив:** WD20EADS, **NTFS сохранён** (1.4 ТБ
  существующих данных, форматирование исключено), смонтирован в `/mnt/hdd2tb` и опубликован
  как Nextcloud external storage `/HDD-2TB` и Samba-шара `hdd2tb`. Мосту RTL9201 потребовался
  тот же UAS-quirk, что и SSD (`0bda:9201:u`) — без него диск отваливался с шины.
  As-built описан в `docs/04_STORAGE_DESIGN.md` (раздел 3б).
- 🇬🇧 **2 TB HDD added as the family archive** — NTFS kept as-is, mounted at `/mnt/hdd2tb`,
  published via Nextcloud external storage and Samba; needed the same UAS quirk as the SSD.
- 🇷🇺 **Аудит работоспособности 2026-08-10** — `docs/plans/SYSTEM_AUDIT_2026-08-10.md`:
  обе находки предыдущего аудита закрыты, замеры по хосту/дискам/контейнерам/сервисам,
  семь остаточных рисков.
- 🇷🇺 **План перестройки домашней сети** — `docs/26_DECO_E4_NETWORK.md` (TP-Link Deco E4):
  🔴 порты 100 Мбит/с → только режим Access Point, Jetson остаётся в гигабитном порту.
  Решение не принято.
- 🇷🇺 Задокументировано, почему **`smartd` отключён намеренно**: UAS-quirk переводит мосты в
  usb-storage BOT, который не пропускает ATA/SCSI passthrough — SMART недоступен структурно
  (`docs/13_MONITORING_RUNBOOK.md`, раздел 3).

### Changed / Изменено

- 🇷🇺 Адрес VPS обновлён с `193.8.215.130` на `95.163.176.103` во всей операционной
  документации, скриптах и тестах. Исторические документы (статьи, ADR, отчёты об инцидентах)
  оставлены как есть; в ADR-0005 и ADR-0006 добавлены пометки об изменении.
- 🇷🇺 `CLAUDE.md` полностью переписан под фактическое состояние на 2026-08-10: два диска,
  закрытый периметр, новые правила (№7 — не форматировать HDD, №8 — кавычки в `.env`,
  №10 — Deco только в режиме AP) и раздел «Грабли, проверенные на практике».

- 🇷🇺 **Шаг 2 (развитие проекта):** разбор отзывов с Habr и дорожная карта
  (`docs/plans/POST_HABR_FEEDBACK_2026-08.md`, двуязычный); решение ввести старый
  Dell Vostro 15 (2018) как выделенный Immich ML-узел
  (`docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`, двуязычный); раздел «Шаг 2» в README;
  трекинг — issue #9.
- 🇬🇧 **Step 2 (project evolution):** Habr feedback review and roadmap
  (`docs/plans/POST_HABR_FEEDBACK_2026-08.md`, bilingual); decision to add the old
  Dell Vostro 15 (2018) as a dedicated Immich ML node
  (`docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`, bilingual); a "Step 2" section in README;
  tracked in issue #9.
- Added a sanitized inventory and commissioning runbook for the physical
  Keenetic Omni KN-1410 planned as a Wi-Fi extender:
  `docs/25_KEENETIC_OMNI_KN1410.md`.
- Linked the planned extender into `docs/19_NETWORK_INVENTORY.md` and
  `docs/05_NETWORKING_VPN.md`, `README.md`, `docs/index.md`, and `CLAUDE.md`;
  added public-only placeholders to `config/.env.example` without copying label
  credentials or unique identifiers.

### Corrected / Исправлено

- 🇷🇺 Исправлено недостоверное заявление о публикации статьи на Habr: статья не опубликована; в репозитории находятся только черновики и материалы подготовки. **(Обновление 2026-08-01: статья Часть 1 опубликована — https://habr.com/ru/articles/1062914/; статусные доки приведены в соответствие.)**
- 🇬🇧 Corrected the unsupported claim that the Habr article had been published: it is unpublished; the repository contains drafts and preparation materials only. **(Update 2026-08-01: Part 1 is now published — https://habr.com/ru/articles/1062914/; status docs updated accordingly.)**

---

## [1.4.1] — 2026-06-29 · GitHub Pages + Habr preparation

### Added / Добавлено

- **GitHub Pages** (`docs/` → `main` branch):
  - `docs/_config.yml` — Jekyll theme (jekyll-theme-minimal)
  - `docs/index.md` — landing page: highlights, status table, links
  - `docs/pages/architecture.md` · `reliability.md` · `android.md` · `evidence.md`
  - `docs/assets/screenshots/article/redacted/` — 7 редактированных скриншотов (01–07)
  - URL: https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
- **Habr article / Статья для Habr** — подготовлены черновики и форматы для редактора; публикация не подтверждена и фактически не состоялась.
  - `docs/articles/habr_article_ru.md` — канонический вариант для GitHub Pages (пути 01–07)
  - `docs/articles/habr_ready.md` — чистая версия для вставки в Markdown-редактор Хабра
  - `docs/articles/habr_wysiwyg.html` — HTML для вставки в WYSIWYG-редактор Хабра
  - `docs/articles/hackaday_project_en.md` — черновик для Hackaday.io
- **`.gitleaks.toml`** — конфиг подавления ложных срабатываний (placeholders)
- **README.md**: раздел «Статьи и публикации / Articles» с черновиком Habr и ссылкой на GitHub Pages
- **`docs/prompts/CODEX_GITHUB_PAGES_PUBLICATION_PROMPT.md`** — сохранён промпт публикации

---

## [1.4.0] — 2026-06-29 · JMS583 USB SSD + Nextcloud Talk + NAS_Jetson_Nano API v0.6.0

### Added / Добавлено

- **JMS583 USB SSD enclosure** (152d:a583, USB 3.0 SuperSpeed, 5 Gbps) — заменил RTL9210B-CG:
  - Write **250 MB/s**, Read **172 MB/s** подтверждены (`dd bs=1M`)
  - `usb-storage.quirks=152d:a583:u` в `/boot/extlinux/extlinux.conf` — UAS quirk, BOT mode
  - `scripts/monitoring/jms583_health.sh` + `systemd/nas_jetson_nano-jms583-health.{service,timer}` —
    ежечасный мониторинг: USB ошибки, скорость I/O, статус очереди; Telegram-алерт
- **Nextcloud Talk** — семейный чат на базе Nextcloud spreed v23.0.7:
  - Группа «Семья» (`token: 37pcobmf`), 5 участников: admin, olga, ivan, ulyana, anna
  - Пользователь `anna` (Talk-only) добавлен в Nextcloud
  - `artifacts/users/ANNA_setup.txt` — памятка для Anna (Talk-only)
  - Памятки OLGA/IVAN/ULYANA переписаны: Talk → первый раздел
- **NAS_Jetson_Nano API v0.6.0** — новые роутеры:
  - `GET /v1/talk/rooms` · `GET /v1/talk/rooms/{token}` · `POST /v1/talk/notify` — Talk интеграция
  - `GET /v1/users` · `GET /v1/users/{username}` · `POST /v1/users/{username}/notify` — пользователи
  - `GET /v1/photos/stats` · `GET /v1/photos/users` — статистика Immich (6484 фото, 210 видео, 4.24 GB)
  - `POST /v1/actions/containers/{name}/restart` · `POST /v1/actions/backup/now` · `GET /v1/actions/history`
  - `main.py` v0.6.0: 9 Swagger-секций, `tryItOutEnabled`, `persistAuthorization`
  - `config.py`: `NEXTCLOUD_ADMIN_PASSWORD`, `IMMICH_API_KEY`, `TALK_FAMILY_ROOM`, `RESTARTABLE_CONTAINERS`
  - `docker-compose.nas_jetson_nano-api.yml`: новые env vars пробрасываются в контейнер
  - Immich API key `nas_jetson_nano-api-monitor` создан (permission: all), сохранён в `config/secrets.json`
- **goss**: 40/40 тестов (было 34) — добавлены тесты для JMS583, Talk, новых systemd-сервисов
- **`docs/plans/NAS_Jetson_Nano_API_ROADMAP.md`** — дорожная карта NAS_Jetson_Nano API, v0.2.0→v0.6.0

### Fixed / Исправлено

- **exec bit loss** — 33 bash-скрипта потеряли exec bit после Windows pull;
  `git update-index --chmod=+x` для 9 критических; `nas_jetson_nano-ssd-recovery.service` восстановлен
- **NEXTCLOUD_ADMIN_PASSWORD** в `.env` на Jetson исправлен (регистр: `all270174bae` → `ALL_270174_bae`)
- **Nextcloud `overwrite.cli.url`** → `https://193.8.215.130:8443` — исправлен для корректного
  browser redirect при login через Talk/Nextcloud app на Android
- **Дубликаты Talk-комнат** (3 шт.) удалены через `occ talk:room:delete`; осталась одна `37pcobmf`

### Security / Безопасность

- Immich API key добавлен в `config/secrets.json` (gitignored)

---

## [1.3.9] — 2026-06-28 · SSD hotplug auto-recovery + Android family setup + users

### Added / Добавлено

- **`scripts/storage/ssd_hotplug_recovery.sh`** + **`systemd/nas_jetson_nano-ssd-recovery.service`** —
  udev hotplug auto-recovery: `sda1 ADD` → mount → preflight → `systemctl start docker` →
  `docker start` stopped containers. Logs: `/var/log/nas_jetson_nano-monitor/ssd-recovery.log`
- **udev rule** (in `install_usb_watchdog.sh`): `ACTION=="add", KERNEL=="sda1"` → start recovery service
- **Family users** — OLGA, IVAN, ULYANA created in Nextcloud and Immich; setup memos: `artifacts/users/`
- **2151 contacts imported** to Nextcloud via CardDAV PUT (Python script, bulk VCF → individual vCards)
- **Android apps configured**: Immich ✅ (6719 photos, backup active), Nextcloud ✅, DAVx⁵ ✅ (CalDAV/CardDAV)
- **Samba `config.yml`** (`configs/samba/config.yml`) — proper YAML config for crazymax/samba;
  shares: `public` (guest OK), `nextcloud` (read-only), `immich` (read-only)
- **`docs/plans/API_MOBILE_PLAN.md`** — NAS_Jetson_Nano API expansion plan: FastAPI facade + JWT + Flutter MVP
- **`docs/articles/habr_draft.md`** — Habr article first draft

### Fixed / Исправлено

- **Immich admin password** — reset via bcrypt + PostgreSQL after rotation; saved to `config/secrets.json`
- **Samba `config.yml` was a directory** — Docker bind-mount created dir when file missing; fixed + YAML added
- **SSD mounted at boot** — `nas_jetson_nano-usb-preboot.service` ensures power cycle before `fstab` mount attempt
- **immich-microservices `mem_limit: 512m`** — applied and confirmed on Jetson

### Security / Безопасность

- **`config/secrets.json`** updated with Immich admin + family user credentials (gitignored)
- All service passwords rotated 2026-06-28; git history clean (filter-repo done in v1.3.8)

---

## [1.3.8] — 2026-06-27 · Password rotation + repo refactor + tech debt closure

### Added / Добавлено

- **Repository structure refactor** per open-source conventions: new dirs `assets/`, `artifacts/`, `archive/`, `docs/prompts/`; agent prompts moved `prompts/` → `docs/prompts/`; hardware photos → `assets/photos/`; audit reports → `artifacts/reports/`; migration log at `docs/quality/STRUCTURE_REFACTOR_REPORT.md`
- **`docs/REPOSITORY_STRUCTURE.md`** — guide for where to put new files, Docker Compose commands reference
- **`tests/storage/smart_check.sh`** — updated for RTL9210B-CG: detects USB bridge, skips SMART (blocked), checks USB bus speed, runs `dd` read test; reports USB 2.0 degradation (480 Mbps / ~40 MB/s vs expected 5 Gbps)
- **`.gitattributes`** — enforces LF for `*.md` docs (prevents Windows CRLF in documentation files)

### Fixed / Исправлено

- **Security: git history rewrite** — removed leaked password hash from 87 commits using `git filter-repo`; force-pushed clean history to GitHub
- **Password rotation** — Jetson sudo, Nextcloud admin, Portainer admin, Beszel Hub admin all rotated; `config/secrets.json` updated (gitignored, never committed)
- **`immich-microservices` mem_limit** — 512 MB applied and confirmed (`MemoryLimit: 536870912`); container recreated to apply
- **CLAUDE.md** — comprehensive update: watchdog ⚠️ STOPPED (pending JMS583 swap), prompts path → `docs/prompts/`, password rotation dated, mem_limit confirmed
- **Stale path references** in README.md: `photo/test_sys.jpg` → `assets/photos/test_sys.jpg`, `prompts/` → `docs/prompts/`
- **README.md bilingual** — Security and Contributing sections fully bilingual (🇷🇺+🇬🇧), broken image table removed (images not tracked in git)
- **`docs/references/EXTERNAL_DOCS_CACHE.md`** — all path references updated `external_docs/` → `docs/references/external_docs/`

### Security / Безопасность

- Leaked password removed from git history via `git filter-repo` (87 commits rewritten, force-pushed)
- All 4 service passwords rotated; old credentials invalidated on Jetson, Nextcloud, Portainer, Beszel Hub
- `config/secrets.json` confirmed gitignored; `config/.env` confirmed gitignored

---

## [1.3.7] — 2026-06-26 · USB SSD audit + watchdog hardening

### Added / Добавлено

- **`.gitattributes`** — force LF line endings для *.sh, *.service, *.timer, *.yml;
  предотвращает CRLF-коррупцию скриптов при работе из Windows
- **`scripts/storage/usb_preboot_cycle.sh`** + **`systemd/nas_jetson_nano-usb-preboot.service`** —
  power cycle USB порта ДО монтирования SSD при каждом boot;
  сбрасывает RTL9210B-CG из crashed-состояния (выживает software reboot)
- **`scripts/monitoring/usb_error_monitor.sh`** + **`systemd/nas_jetson_nano-usb-monitor.service`** —
  real-time dmesg watcher: Telegram-алерт при первом `error -71` до того,
  как Docker начнёт падать; немедленно запускает watchdog (не ждать 3 мин)
- **`scripts/storage/deploy_usb_fix.sh`** — идемпотентный деплой-скрипт
  с `sed 's/\r$//'` для защиты от CRLF при копировании из git

### Fixed / Исправлено

- **RTL9210B-CG root cause audit**:
  - CRLF в shebang (`#!/usr/bin/env bash\r`) → systemd 203/EXEC →
    watchdog не работал 4+ часов → SSD в broken state без recovery
  - watchdog `POWER_OFF_SECS` увеличен 15s→45s (15s недостаточно для
    разряда bypass-конденсаторов RTL9210B-CG)
  - watchdog `WAIT_ENUM_SECS` увеличен 20s→30s
  - watchdog timer `OnBootSec` уменьшен 5min→2min
- **dos2unix** установлен на Jetson; деплой-скрипт использует его автоматически

### Root cause / Анализ

Два независимых сбоя:
1. RTL9210B-CG (Realtek USB-SATA bridge) сохраняет crashed-состояние через
   software reboot (USB hub остаётся под питанием) и не восстанавливается
   через uhubctl power cycle (паразитное питание через bypass-конденсаторы).
   Единственный надёжный сброс — физическое отключение USB кабеля.
2. Git на Windows конвертировал LF→CRLF в shell-скриптах, что при `cp`
   из репозитория создавало нерабочие shebang-строки.

**Hardware note**: RTL9210B-CG ненадёжен по дизайну.
Рекомендация: заменить энклоужер на JMicron JMS578 или ASMedia ASM1153E.

---

## [1.3.6] — 2026-06-26 · Android Immich backup + USB SSD port fix

### Added / Добавлено

- **Immich Android полностью настроен** (сессия 2026-06-26):
  - Создан admin-аккаунт через API: `admin@nas_jetson_nano.local`
  - Приложение авторизовано через VPS: `http://193.8.215.130:2283`
  - Выбраны все 31 альбом устройства (6710 фото/видео)
  - Бэкап активирован (toggle "Активировать" = ON)
  - Включена загрузка фото по мобильному интернету
  - Включена синхронизация альбомов

### Fixed / Исправлено

- **USB SSD порт 4 (1-2.4) сломан → переткнут в порт 2 (1-2.2)**:
  error -71 (EPROTO) при каждом boot — аппаратная неисправность порта;
  смена физического порта решила проблему мгновенно
- **Watchdog PORT=4 → PORT=2** в `scripts/storage/usb_recovery_watchdog.sh`
  и на Jetson `/usr/local/sbin/nas_jetson_nano-usb-watchdog.sh`
- **SCSI timeout 120s подтверждён**: `cat /sys/block/sda/device/timeout` = 120 ✅
- **usb-storage.quirks=0bda:9210:rw подтверждён**: dmesg показывает
  `Quirks match for vid 0bda pid 9210: 220` при enumeration

### Validated / Проверено

- Все 13 Docker контейнеров healthy через 3 мин после boot
- SSD монтируется при каждом boot (7 boot подряд на порту 2)
- USB watchdog timer active: `nas_jetson_nano-usb-watchdog.timer`
- Immich API: `GET /api/server/ping` → `{"res":"pong"}`

---

## [1.3.5] — 2026-06-25 · Android mobile sync + HTTPS

### Added / Добавлено

- **Android mobile module** — `docs/android/`:
  - `ANDROID_SETUP.md` — пошаговая настройка Immich, Nextcloud, DAVx⁵ на Xiaomi MIUI/HyperOS
  - `GOOGLE_MIGRATION.md` — миграция с Google Photos/Contacts/Calendar/Drive через Google Takeout;
    чеклист, инструкция по immich-go для массового импорта с метаданными GPS/дата
  - `XIAOMI_MIUI_QUIRKS.md` — whitelist батарея, автозапуск, блокировка в RAM для Immich/DAVx⁵
- **nginx HTTPS на VPS** — `scripts/setup/install_nginx_vps.sh`:
  добавляет TLS (самоподписанный, 10 лет) к уже работающему `nas_jetson_nano_nginx` Docker контейнеру;
  открывает порты 8443 (Nextcloud), 2443 (Immich), 9443 (LLM) в ufw;
  без конфликта с Amnezia (443 занят xray → используются alt-порты)

### Fixed / Исправлено

- **usbcore.autosuspend=-1 подтверждён** после ребута Jetson (2026-06-25):
  `/sys/module/usbcore/parameters/autosuspend = -1` — kernel param активен
- **Nextcloud trusted proxy** настроен через `occ`: `trusted_proxies`, `overwriteprotocol=https`,
  `forwarded_for_headers` — HTTPS-заголовки корректно проксируются

---

## [1.3.4] — 2026-06-24 · Beszel monitoring + USB watchdog

### Added / Добавлено

- **Beszel: оба агента зарегистрированы и активны** (2026-06-24):
  - `jetson-nano` (127.0.0.1:45876) → status `up`, CPU 17%, RAM 58%
  - `vps-vienna` (127.0.0.1:45877) → status `up`, CPU 2%, RAM 27%
  - `scripts/monitoring/install_beszel_agent_vps.sh` — установщик amd64 агента на VPS;
    читает Hub pubkey из `/opt/nas_jetson_nano/beszel-hub/data/id_ed25519` автоматически;
    wrapper-скрипт обходит systemd ExecStart-ограничения при ключе с пробелами

---

## [1.3.4] — 2026-06-24 · Beszel monitoring + USB watchdog

### Added / Добавлено

- **Beszel monitoring** — Hub на VPS (порт 8091, Docker host network, SQLite история),
  Agent на Jetson (binary 0.18.7, arm64, systemd, порт 45876).
  Telegram алерты через Shoutrrr (23+ канала).
  `docker/vps/docker-compose.yml` — beszel-hub сервис.
  `scripts/monitoring/install_beszel_agent.sh` — установщик агента.
- **USB storage watchdog** — `scripts/storage/install_usb_watchdog.sh`:
  - udev rule: `power/control=on` для RTL9210B-CG (0bda:9210) **и USB-хаба** (0bda:5411 / 0411);
    хаб в autosuspend убивает дочерние устройства вне зависимости от настроек bridge
  - `usbcore.autosuspend=-1` в `/boot/extlinux/extlinux.conf` (belt-and-suspenders, после ребута)
  - smartd с явным `/dev/sda` (DEVICESCAN не работает на Tegra kernel 4.9)
  - Telegram alert на remove/add `/dev/sda` через VPS SSH relay
  - Root cause: RTL9210B-CG входит в ELPG цикл при USB reset mid-write →
    только физический power cycle выводит. Fix предотвращает сам вход.
- **Tunnel port 45876** — `systemd/nas_jetson_nano-tunnel.service`: добавлен
  `-R 45876:localhost:45876` для Beszel Agent → Hub через VPS.
- **GitHub traffic monitoring** — `docs/metrics/GITHUB_TRAFFIC.md`:
  ежедневный лог просмотров, клонов, источников трафика, звёзд.
  Первая запись: 2026-06-24 (371 клон / 149 уник. за 14 дней, 0 звёзд).

### Fixed / Исправлено

- `install_usb_watchdog.sh`: добавлены udev-правила для USB-хаба (0bda:5411/0411) —
  без них хаб мог засыпить шину, роняя SSD
- `install_usb_watchdog.sh`: `DEVICESCAN` → явный `/dev/sda` в smartd.conf —
  DEVICESCAN падает на Tegra kernel 4.9 (нет `/dev/discs/disc*`)

### Changed / Изменено

- `README.md`: статус обновлён до 2026-06-24; Beszel Hub/Agent добавлены в таблицу сервисов;
  USB watchdog в Known Limitations заменён описанием применённого фикса

- `scripts/storage/storage_preflight.sh`: fail-closed sudo storage preflight before
  starting Nextcloud/Immich/backup; checks mountpoint, backing device, fstab UUID,
  read-only mounts, critical paths and Nextcloud `.ncdata`.
- `scripts/storage/install_mount_service.sh`: safe installer for
  `jetson-nas-mount.service`; install/enable by default, immediate mount only with
  explicit `--start`.
- `scripts/storage/install_docker_storage_guard.sh` and
  `systemd/docker.service.d/10-nas_jetson_nano-storage.conf`: optional strict boot guard
  that makes Docker wait for `/mnt/storage` after power loss or USB failure.
- `docs/plans/RELIABILITY_AUDIT_2026-06-23.md`: live reliability audit via VPS
  with confirmed Jetson findings, repo mitigations, and SSD recovery paths.

### Changed / Изменено

- `docker/compose/docker-compose.nas_jetson_nano-api.yml`,
  `services/nas_jetson_nano-api/app/config.py`, and
  `scripts/monitoring/nas_jetson_nano-daily-report.sh`: expected containers now use real
  `homecloud_*` container names instead of stale compose-generated names.
- `scripts/monitoring/nas_jetson_nano-daily-report.sh`: adds storage mount health,
  Nextcloud `.ncdata` presence check, recent kernel storage errors, and separate
  VPS checks for Nextcloud, Immich, and LLM Gateway.
- `scripts/backup/backup_databases.sh`: refuses to write database dumps when
  `${STORAGE_ROOT}` is not a mountpoint, cannot be resolved, points to microSD, or
  is not writable.
- `systemd/nas_jetson_nano-backup.service` and `systemd/jetson-nas-health.service`: require
  `/mnt/storage` to be a real mountpoint before running.
- `systemd/jetson-nas-mount.service`: uses `STORAGE_ROOT=/mnt/storage` default,
  reads `/home/admin/nas_jetson_nano/config/.env`, and avoids unsupported shell-style
  `${VAR:-default}` expansion in systemd `ExecStart`.
- `docker/compose/docker-compose.samba.yml`, `docker/compose/docker-compose.stage1.yml`,
  and `docker/vps/docker-compose.yml`: normalized restart policy to `always`.
- `docs/13_MONITORING_RUNBOOK.md`: added USB storage failure runbook for
  `error -71`, ext4 read-only remounts, safe recovery order, and preflight usage.
- Top-level and operational docs now reflect the recovered SSD state, intentional
  Nextcloud stop, live DB backup success, and the remaining hardware risk in the
  USB cable/enclosure/power chain.
- Jetson `~/nas_jetson_nano` checkout synchronized to `6844447`; the pre-sync live diff is
  preserved on Jetson as `stash@{0}` for audit/recovery.
- Nextcloud data/app review completed read-only: 503 traced to the earlier
  read-only storage remount; `.ncdata`, ownership, config and DB checks are
  clean, with controlled start left as the next step.
- Nextcloud controlled start completed: `homecloud_nextcloud` is running,
  `restart=always`, healthcheck is healthy, local and VPS `/status.php` return
  HTTP 200, and no new kernel storage errors were observed after start.
- Reboot/autorecovery test completed: Jetson returned with a new boot id, the
  VPS reverse tunnel recovered, `/mnt/storage` mounted as `/dev/sda1`, preflight
  passed, storage-backed containers became healthy, VPS endpoints returned HTTP
  200, and `jetson-nas-health.timer` finished with `issues: 0`.

## [1.3.3] — 2026-06-21 · Client setup + HDD hybrid storage

### Added / Добавлено

- **`docs/24_CLIENT_SETUP.md`**: полное руководство по подключению устройств —
  Android (Nextcloud app, DAVx⁵, Immich, Samba), Windows (Desktop client, WebDAV, net use),
  Linux (nextcloudcmd, cifs-utils, Nautilus); таблица URL для LAN и внешнего доступа
- **`docs/04_STORAGE_DESIGN.md` §3а**: новый раздел "HDD с данными — NTFS + ext4 гибрид":
  пошаговый план сжатия NTFS (Windows), создания ext4 на Jetson, двойного fstab-монтирования,
  добавления NTFS-шары в Samba (`archive`); таблица "что где хранится"
- **`README.md`**: добавлены docs/23 и docs/24 в таблицу документации

## [1.3.2] — 2026-06-21 · GitHub integration + promotion

### Added / Добавлено

- **`CLAUDE.md`**: контекстный файл проекта для Claude Code — автоматически читается
  при открытии репозитория; содержит адреса сервисов, команды SSH, workflow, ограничения
- **`docs/23_GITHUB_INTEGRATION.md`**: полное руководство по GitHub CLI интеграции —
  авторизация PAT, `gh issue/pr/release`, стандартный workflow сессии, AI-assisted DevOps цикл
- **`AGENTS.md` §6**: новый раздел GitHub CLI — разрешённые операции, аварийное восстановление auth
- **`gh` CLI** (`C:\tools\gh\bin\`, v2.74.1): авторизован через Windows keyring (полные права `repo`)
- **GitHub Discussions** включены; Welcome-дискуссия (#7) создана
- **GitHub Issues** #4, #5, #6 — три `good first issue` задачи (HTTPS, RPi guide, Netdata alerts)

### Changed / Изменено

- **`README.md`**: полный рерайт вводной части — личная история (Jetson в ящике, HDD через раз),
  убрана таблица цен, более живой и человеческий язык в секциях "О проекте" и "Для кого"
- **`README.md`**: добавлены бейджи stars/discussions/issues/CI, призыв поставить ⭐
- **`README.md`**: секция Contributing — прямые ссылки на good first issues
- **GitHub**: homepage очищен (был бессмысленный `#readme`)

## [1.3.1] — 2026-06-21 · Phase 1 ops tasks

### Added / Добавлено

- **`systemd/nas_jetson_nano-backup.{service,timer}`**: systemd timer for daily automated
  `pg_dump` at 03:00 (±15 min randomized delay); `Persistent=true` so missed
  runs are retried on next boot
- **`scripts/backup/install_backup_timer.sh`**: one-command installer — copies
  units, patches `NAS_JETSON_NANO_PROJECT_DIR`, calls `daemon-reload`, enables and starts timer
- **`docs/13_MONITORING_RUNBOOK.md` §12-14**: added operational setup sections:
  backup timer install & verify, Uptime Kuma initial monitor list (5 services),
  Netdata Telegram alerts config via `docker exec`

## [1.3.0] — 2026-06-21 · Stage 1G + 1H complete

### Added / Добавлено

- **Monitoring stack deployed** (Stage 1F): Netdata (19999), Uptime Kuma (3001), Portainer (9000)
  running on Jetson via `docker-compose.monitoring.yml`
- **nas_jetson_nano-api** (Stage 1G): FastAPI service on port 8099 with Swagger UI at `/docs`
  — endpoints: `/v1/metrics`, `/v1/containers`, `/v1/logs`, `POST /v1/report/now`
  — pydantic-settings config, JSON structured logging (RotatingFileHandler 10 MB × 5)
  — `docker/compose/docker-compose.nas_jetson_nano-api.yml`
- **Telegram daily health report** (09:00): `scripts/monitoring/nas_jetson_nano-daily-report.sh`
  collects RAM, CPU, disk, container states, HTTP checks; sent via VPS SSH relay
  (`scripts/monitoring/nas_jetson_nano-send-report-telegram.sh`)
  — systemd timer: `nas_jetson_nano-daily-report-telegram.{service,timer}`
- **Docker healthchecks** added to all 10 containers:
  Nextcloud (`curl /status.php`), nextcloud-db/immich-db (`pg_isready`),
  nextcloud-redis/immich-redis (`redis-cli ping` with auth),
  immich-server (`curl /api/server/ping`), llm-gateway/nas_jetson_nano-api (`python3 urllib`),
  netdata (`curl /api/v1/info`), uptime-kuma (`extra/healthcheck`),
  portainer (`disable: true` — scratch image, no shell)
- **`depends_on: condition: service_healthy`** for nextcloud and immich stacks
  — containers wait for DB + Redis to be healthy before starting
- **`mem_limit`** added to all remaining containers:
  llm-gateway 256m, nas_jetson_nano-api 128m, netdata 256m, uptime-kuma 128m, portainer 128m
- **`restart: always`** applied to llm-gateway, nas_jetson_nano-api, and all monitoring services
- **`NETDATA_UPDATE_EVERY=5`** — reduces Netdata CPU from 19.5% to ~4%
- **goss v0.4.9 spec**: `tests/goss/goss.yaml` — 34 tests (ports, services, files, HTTP)
- **docs/21_LOGGING_API.md**: bilingual documentation for logging subsystem and nas_jetson_nano-api
- **docs/22_AUDIT_RESILIENCE.md**: resilience audit report — tools, 10 findings, fixes

### Fixed / Исправлено

- **F-05 (SC2029)**: `nas_jetson_nano-send-report-telegram.sh` — Telegram token no longer appears
  in `ps aux` on VPS; passed via ephemeral SSH env file on remote
- **F-06**: `nas_jetson_nano-daily-report-telegram.service` — added `Restart=on-failure` + `RestartSec=60`
- **F-08 (SC2046)**: `scripts/fetch_external_docs.sh:182` — `$(find ...)` replaced with `xargs`
- **Immich healthcheck endpoint**: corrected from deprecated `/api/server-info/ping`
  to `/api/server/ping` (Immich v1.100+)

### Changed / Изменено

- README: complete rewrite to reflect Stage 1 complete state — all services live,
  accurate architecture diagram, updated stages/docs/stack tables
- `docker-compose.nextcloud.yml`, `docker-compose.immich.yml`: `restart: unless-stopped`
  → `restart: always` for all services (applied live via `docker update`)
- Audit report status updated: F-02 → MEDIUM/Mitigated, F-03/F-04/F-06/F-07 → Fixed

### Added / Добавлено (deep audit 2026-06-20)

- `config/.env.example`: `STORAGE_DEVICE` variable for SMART monitoring; `SAMBA_NAS_PASSWORD`
  for Samba secrets; `VPS_HOST` changed from real IP to placeholder `your.vps.ip.here`
- `docker/compose/docker-compose.stage1.yml`: `mem_limit` on all services (protect 4 GB / no-swap Jetson);
  `immich-microservices` moved to `profiles: [microservices]` (off by default); `immich-redis`
  now password-protected; removed incorrect `depends_on: nextcloud` from `llm-gateway`;
  added `REDIS_PASSWORD` env to `immich-server`
- `.github/workflows/validate-compose.yml`: added CI validation for 3 new compose files
  (`docker-compose.samba.yml`, `docker-compose.monitoring.yml`, `docker/vps/docker-compose.yml`)
- `systemd/jetson-nas-mount.service`: replaced `mount -a` (all fstab) with targeted
  `mount ${STORAGE_ROOT}` + added `Before=docker.service`

### Changed / Изменено (deep audit 2026-06-20)

- `CHANGELOG.md`: fixed repo URL in footer links (`NAS_Jetson_Nano` not `nas-jetson-nano`)
- `README.md`: fixed clone URL; Samba marked as implemented (not "planned"); updated
  Stack, Architecture, Stages, Known Limitations tables; added all new compose files to table;
  removed stale `IMMICH_DISABLE_MACHINE_LEARNING` limitation note
- `PROJECT_TREE.txt`: fully regenerated — now reflects all directories added since v0.1.0
  (`systemd/`, `tests/`, `configs/samba/`, `scripts/storage/`, `scripts/network/`,
  `docker/vps/`, `docs/articles/`, `docs/17-20_*.md`, `docs/decisions/ADR-0002..0004`, etc.)
- `scripts/network/setup_vps_tunnel.sh`: removed hardcoded fallback `193.8.215.130`;
  script now exits with error if `VPS_HOST` is not set in `.env`

### Added / Добавлено

- NAS research report (`docs/18_NAS_RESEARCH_REPORT.md`): analysis of 6 open-source NAS projects
  (JetsonHacks bootFromUSB, OMV, NextcloudPi, RetroNAS, NasberryPi, docker-samba)
- Samba SMB layer: `docker/compose/docker-compose.samba.yml` (crazymax/samba, ARM64 native)
  + `configs/samba/config.yml` (YAML config) + `configs/samba/smb.conf` (native reference)
- `systemd/` directory: `jetson-nas-health.service`, `jetson-nas-health.timer` (6h),
  `nas_jetson_nano-tunnel.service` (autossh), `jetson-nas-mount.service`
- `tests/` directory: `test_samba_config.sh`, `test_mount.sh`, `test_healthcheck.sh`
- `scripts/storage/setup_disk.sh` — USB HDD mount setup with UUID/fstab (NasberryPi pattern)
- `scripts/storage/benchmark_io.sh` — sequential I/O benchmark (JetsonHacks reference speeds)
- VPS integration: reverse SSH tunnel architecture (`docs/plans/VPS_INTEGRATION_PLAN.md`)
  - autossh tunnel script for Jetson Nano (`scripts/network/setup_vps_tunnel.sh`)
  - nginx reverse proxy compose for VPS (`docker/vps/docker-compose.yml`)
  - VPS UFW rules configured (SSH, Amnezia ports, NAS_Jetson_Nano tunnel ports 8080/2283/8090)
  - Docker Compose v5.1.4 installed on VPS
- `config/.env.example`: added VPS_HOST, VPS_USER, VPS_SSH_KEY section
- Monitoring stack analysis and documentation (`docs/17_MONITORING_OBSERVABILITY.md`)
- Docker Compose for monitoring stack (`docker/compose/docker-compose.monitoring.yml`): Netdata + Uptime Kuma + Portainer, ARM64-native
- `prompts/CODEX_MONITORING_PROMPT.md` — bilingual agent prompt for monitoring deployment
- ADR-0002 (storage design), ADR-0003 (networking LAN-only), ADR-0004 (Tailscale external access)
- `docs/plans/TAILSCALE_ACCESS_PLAN.md` — step-by-step Tailscale setup on Jetson Nano
- Full operational bash scripts: `backup_databases.sh`, `restic_backup_example.sh`, `docker_health.sh`, `storage_health.sh`, `docker_update_plan.sh`, `network_health.sh` (in `scripts/network/`)
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1, bilingual RU/EN)
- Existing-data HDD intake documentation: read-only NTFS check flow before using
  `/mnt/storage` or `scripts/storage/setup_disk.sh`
- `docs/19_NETWORK_INVENTORY.md` — sanitized home LAN/router/Jetson/HDD/VPS
  inventory table with secret values kept in `config/.env`
- `docs/20_AGENT_OPERATING_MODEL.md` — standard subagent roles, safety gates,
  report format, and workflow integration

### Changed / Изменено

- `README.md`: added "Old hardware should live" tagline, AI-Assisted badge, updated Samba stack entry
- `AGENTS.md`: added the mandatory subagent operating model pointer and report
  requirements
- `scripts/diagnostics/storage_health.sh`: added SMART monitoring section (smartctl, USB-SATA bridge handling)
- `docs/articles/habr_draft.md`: rewritten with "human vision + AI implementation" angle
- `README.md` переписан по стандартам GitHub open-source проектов: badges, двуязычные секции, ASCII-диаграмма, таблицы стека и документации, Quick Start / README.md rewritten to GitHub open-source standards
- `AGENTS.md` дополнен разделом сетевых ограничений (Amnezia, nas_jetson_nano-lan, Tailscale)
- `docs/13_MONITORING_RUNBOOK.md` расширен: ссылки на мониторинг-стек, таблица алертов
- `docs/16_GITHUB_PUBLICATION.md` дополнен: GitHub Actions, Issue templates, pre-release checklist
- `docker/compose/docker-compose.stage1.yml`: добавлен `immich-microservices`, `IMMICH_DISABLE_MACHINE_LEARNING`, `container_name` для всех сервисов

---

## [0.1.0] - 2026-06-20

### Added / Добавлено

- Initial project structure: `docs/`, `scripts/`, `services/`, `config/`, `docker/`, `prompts/`
- Bilingual documentation (RU/EN) for all stages (Stage 0–3):
  - `docs/00_OVERVIEW.md` — project overview
  - `docs/01_HARDWARE_AUDIT.md` — hardware audit guide
  - `docs/01A_JETSON_SD_BOOTSTRAP.md` — Jetson Nano microSD bootstrap recipe
  - `docs/03_ARCHITECTURE.md` — architecture overview
  - `docs/04_STORAGE_DESIGN.md` — USB HDD storage design
  - `docs/05_NETWORKING_VPN.md` — networking and VPN setup (wg-nas_jetson_nano, EU VPS)
  - `docs/06_NEXTCLOUD_DESIGN.md` — Nextcloud deployment design
  - `docs/07_IMMICH_DESIGN.md` — Immich deployment design (Jetson-safe mode)
  - `docs/08_LLM_GATEWAY_DEEPSEEK.md` — LLM Gateway and DeepSeek API integration
  - `docs/12_BACKUP_RESTORE.md` — backup and restore workflow
  - `docs/14_TEST_PLAN.md` — test plan for staged rollout
  - `docs/16_GITHUB_PUBLICATION.md` — GitHub publication checklist
- Docker Compose drafts (modern Compose spec, top-level `name:` key):
  - `docker/compose/docker-compose.stage1.yml` — full Stage 1 stack
  - `docker/compose/docker-compose.nextcloud.yml` — Nextcloud + PostgreSQL + Redis
  - `docker/compose/docker-compose.immich.yml` — Immich (ML disabled for Jetson Nano)
  - `docker/compose/docker-compose.llm-gateway.yml` — LLM Gateway FastAPI service
- `services/llm-gateway/` — FastAPI privacy shim for DeepSeek API:
  - personal data redaction (email, phone, tokens, private keys)
  - mock mode when `DEEPSEEK_API_KEY` is not set
  - Stage 1 raw-mode block
- `services/backup-api/` — Stage 2 placeholder for Android backup/restore
- `config/.env.example` — public environment variable template (no real secrets)
- `config/llm-policy.yaml` — LLM privacy policy draft
- Diagnostic scripts:
  - `scripts/diagnostics/hardware_audit.sh` — Jetson Nano hardware audit
  - `scripts/diagnostics/docker_health.sh` — Docker and container health check
  - `scripts/diagnostics/storage_health.sh` — USB HDD and mount point health check
- Backup scripts:
  - `scripts/backup/backup_databases.sh` — PostgreSQL dump skeleton
  - `scripts/backup/restic_backup_example.sh` — restic snapshot workflow example
- Security tooling:
  - `scripts/security/check_no_secrets.sh` — pre-publish secret scanner (scans git-tracked files only)
- Agent and Codex prompts:
  - 8 prompt templates in `prompts/CODEX_*` covering Stage 0–2 tasks
- Architecture decision records:
  - `docs/decisions/ADR-0001-nextcloud-immich-deepseek.md` — selected stack rationale
- Project meta files:
  - `README.md` — bilingual project overview (RU/EN)
  - `CONTRIBUTING.md` — contribution rules and good first issues
  - `SECURITY.md` — security policy and LLM privacy rules
  - `AGENTS.md` — agent/Codex onboarding instructions
  - `PROJECT_CONTEXT.md` — fixed decisions and hardware constraints
  - `LICENSE` — MIT License
- GitHub infrastructure:
  - `.github/ISSUE_TEMPLATE/bug_report.md` — bilingual bug report template
  - `.github/ISSUE_TEMPLATE/feature_request.md` — bilingual feature request template
  - `.github/ISSUE_TEMPLATE/config.yml` — issue template configuration
  - `.github/pull_request_template.md` — bilingual PR checklist
  - `.github/CODEOWNERS` — code ownership declaration
  - `.github/workflows/secrets-check.yml` — CI secret scanner on push/PR
  - `.github/workflows/validate-compose.yml` — CI Docker Compose validation

[Unreleased]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.9...v1.4.0
[1.3.9]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.8...v1.3.9
[1.3.8]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.7...v1.3.8
[1.3.4]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/releases/tag/v1.3.0
[0.1.0]: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/releases/tag/v0.1.0
