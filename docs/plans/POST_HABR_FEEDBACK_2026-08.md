# Обратная связь с Habr и план развития / Habr feedback and development plan

> 🇷🇺 Разбор комментариев к статье, наши ответы и дорожная карта доводки проекта
> **строго на имеющемся железе, без дополнительных покупок.**
> Составлено: 2026-08-01. Основано на live-аудите устройства (RAM, GPU/CUDA, контейнеры, термика).
>
> 🇬🇧 Review of the article comments, our responses, and a roadmap to refine the project
> **strictly on existing hardware, with no additional purchases.**
> Written: 2026-08-01. Based on a live audit of the device (RAM, GPU/CUDA, containers, thermals).

## Статья / The article

- **Habr — Часть 1 / Part 1:** «Старому Jetson Nano — домашнее облако: Nextcloud, Immich, CGNAT и три USB-сбоя»
  → https://habr.com/ru/articles/1062914/ (автор / author: Alexey_git, 2026-07-25).
- 🇷🇺 9 комментариев (4 читателя + ответы автора), обсуждение 25–30 июля 2026.
- 🇬🇧 9 comments (4 readers + author replies), discussion 25–30 July 2026.

## Инвентарь железа / Hardware inventory

> 🇷🇺 Что есть — покупок не планируем. 🇬🇧 What we have — no purchases planned.

| Узел / Node | Спеки / Specs | Роль / Role |
|---|---|---|
| Jetson Nano Dev Kit | 4 ГБ RAM, Maxwell 128 CUDA, **CUDA 10.2 / JetPack R32.7.1 (aarch64)**, без DLA/NPU | основной сервер / main server |
| USB SSD JMS583 | 229 ГБ, USB 3.0, `/mnt/storage` (5% занято / used) | хранилище / storage |
| VPS Vienna | 2 ГБ RAM, nginx, Amnezia VPN (~25 клиентов — НЕ трогать / do NOT touch) | внешний вход / external entry |
| HDD 2 ТБ | «старый», уже в наличии / owned, ещё не подключён / not attached yet | расширение / backup |
| Windows-ПК (dev) | периодически включён / on intermittently | dev + возможный ML-узел / potential ML node |

## Разбор замечаний и ответы / Feedback review and responses

### 1. vvzvlad: «Зачем JetPack, если ускоритель не используется?» / "Why JetPack if the accelerator is unused?"
- 🇷🇺 **Справедливо:** GPU Nano простаивает — проект работает как обычный x86-NAS. Смысл Jetson именно в CUDA-ядрах. План — дать GPU полезную нагрузку, совместимую с CUDA 10.2 (Фаза 5). До этого фиксируем как техдолг, а не как «фичу».
- 🇬🇧 **Fair:** the Nano's GPU sits idle — the project runs like a plain x86 NAS. The point of a Jetson is its CUDA cores. Plan: give the GPU a CUDA-10.2-compatible workload (Phase 5). Until then it's tracked as tech debt, not a "feature."

### 2. tklim: 4 ГБ мало · перегрев SSD · открытые порты / 4 GB is low · SSD overheating · open ports
- 🇷🇺 **RAM — подтверждено аудитом:** total 3.9 ГБ, свободно ~520 МБ, zram-swap уже занят на ~711 МБ. → Фаза 2 (оптимизация RAM) обязательна. **Термика:** SoC холодный (CPU 44 °C), температуру SSD датчики не отдают → Фаза 4 добавит съём (SMART 194). **Безопасность:** справедливо, это противоречит правилу №4 → Фаза 1, приоритет №1 (есть `TAILSCALE_ACCESS_PLAN.md`).
- 🇬🇧 **RAM — confirmed by audit:** total 3.9 GB, ~520 MB free, zram-swap already ~711 MB used. → Phase 2 (RAM optimization) is mandatory. **Thermals:** the SoC is cool (CPU 44 °C); sensors don't expose the SSD temp → Phase 4 adds it (SMART attr 194). **Security:** fair — it violates our own rule #4 → Phase 1, top priority (`TAILSCALE_ACCESS_PLAN.md` exists).

### 3. dE1l: «Распознавание в Immich отключено, хотя есть NPU» / "Immich recognition is off despite the NPU"
- 🇷🇺 **Уточнение:** у Jetson **Nano нет DLA/NPU** (он есть у Xavier/Orin), есть только Maxwell-GPU. ML действительно выключен (контейнера нет — подтверждено). Официальные CUDA-образы Immich ML требуют CUDA 11/12, а на Nano CUDA 10.2 → GPU-ускорения официальными образами нет. Реальные no-purchase пути — ниже.
- 🇬🇧 **Clarification:** the **Nano has no DLA/NPU** (those are on Xavier/Orin), only a Maxwell GPU. ML is indeed off (no container — confirmed). Official Immich ML CUDA images need CUDA 11/12, but the Nano has CUDA 10.2 → no GPU acceleration via official images. Realistic no-purchase paths below.

### 4. falcon4fun: «Immich без ML — деньги на ветер; вынести ML на ПК с GPU» / "Immich without ML is money down the drain; offload ML to a GPU PC"
- 🇷🇺 **Идея верная, но покупка бокса исключена.** Immich поддерживает удалённый ML-сервер через `IMMICH_MACHINE_LEARNING_URL`. Вместо покупки — направить ML на **уже имеющуюся машину** (Фаза 5). Тот же offload, но без затрат.
- 🇬🇧 **Right idea, but buying a box is out of scope.** Immich supports a remote ML server via `IMMICH_MACHINE_LEARNING_URL`. Instead of buying — point ML at **existing hardware** (Phase 5). Same offload, zero cost.

## Дорожная карта / Roadmap

> 🇷🇺 Приоритет: сначала безопасность и стабильность, затем — оживление GPU/ML.
> 🇬🇧 Priority: security and stability first, then reviving GPU/ML.
>
> **Статус фаз на 2026-08-10 / Phase status as of 2026-08-10:**
>
> | Фаза | Статус | Чем закрыта |
> |---|---|---|
> | 1 — Безопасность | ✅ **выполнена** | ufw на VPS: сервисные порты только из VPN |
> | 2 — Оптимизация RAM | 🔄 в работе | лимиты выставлены, три контейнера на 85–92 % |
> | 3 — Хранилище и бэкап | ✅ **выполнена** (HDD) | 2 ТБ подключён; restic off-site — остаётся |
> | 4 — Температура SSD | ⛔ **невозможна** | структурное ограничение, см. ниже |
> | 5 — Immich ML на Vostro | 📋 переработана | узел остаётся в корпоративной сети |
> | 6 — Оркестратор и API | 📋 план | без изменений |

### Фаза 1 — Безопасность / Phase 1 — Security ✅ ВЫПОЛНЕНА 2026-08-07
- 🇷🇺 **Сделано:** сервисные порты (8080/8443/2283/2443/8090/9443/**8099**/8091) на VPS закрыты для интернета — `ufw` пускает их только с `172.29.172.0/24` и `10.8.1.0/24`. Наружу остались 22 (нужен для реверс-туннелей), 443 и 40568/udp. Правило №4 реально соблюдается. Замечание tklim снято.
- 🇬🇧 **Done:** service ports on the VPS are VPN-only now; only 22, 443 and 40568/udp remain world-reachable. Rule #4 is genuinely honored. tklim's point is closed.
- 🇷🇺 **Остаётся:** fail2ban на VPS; Let's Encrypt при появлении домена. И отдельно — **внутри домашней LAN сегментации по-прежнему нет** (см. Фазу 7).

### Фаза 2 — Оптимизация RAM / Phase 2 — RAM optimization 🔄
- 🇷🇺 Аудит `mem_limit` всех 13 контейнеров; вынести часть мониторинга (netdata/uptime-kuma/portainer) на VPS или на ML-узел; тюнинг zram. Итог: появляется бюджет RAM под ML.
- 🇬🇧 Audit `mem_limit` across all 13 containers; move some monitoring to the VPS or the ML node; tune zram.
- 🇷🇺 **Замер 2026-08-10:** `uptime_kuma` 92 %, `immich_microservices` 88 %, `netdata` 85 % своих лимитов; сумма лимитов превышает физическую RAM. Кандидаты на вынос — первые и третий.

### Фаза 3 — Хранилище и бэкап / Phase 3 — Storage and backup ✅ ЧАСТИЧНО ВЫПОЛНЕНА
- 🇷🇺 **Сделано 2026-08-09:** подключён HDD 2 ТБ — WD20EADS, NTFS сохранён (1.4 ТБ семейного архива), `/mnt/hdd2tb`, доступен через Nextcloud `/HDD-2TB` и Samba `hdd2tb`. Мосту RTL9201 потребовался тот же UAS-quirk, что и SSD.
- 🇬🇧 **Done 2026-08-09:** the 2 TB HDD is attached, NTFS preserved, published via Nextcloud and Samba.
- 🇷🇺 **Остаётся:** restic off-site backup. Кандидат для цели — 1 ТБ HDD ноутбука Vostro.
- 🇷🇺 **Бонусом закрыто:** обнаружена и устранена поломка бэкапов БД (16 дней молчания из-за незакавыченного значения в `.env`); **восстановление проверено впервые**.

### Фаза 4 — Мониторинг накопителя / Phase 4 — Drive monitoring ⛔ НЕВОЗМОЖНА
- 🇷🇺 **Честный итог, готовый для Части 2 статьи:** снять температуру SSD **нельзя в принципе**. Kernel-quirk `152d:a583:u`, без которого мост JMS583 роняет диск с шины, переводит его в режим **usb-storage BOT**, а BOT не пропускает ATA/SCSI passthrough, на котором держится SMART. Перебрано всё: `-d sat`, `sat,12`, `sat,16`, `usbjmicron`, `-T permissive` — везде `unsupported scsi opcode`. `-d scsi -H` даёт разовый `SMART Health Status: OK`, но `-d scsi -s on` возвращает `unable to fetch IEC (SMART) mode page`, а без включённой IEC-страницы `smartd` отказывается регистрировать устройство. Поэтому `smartd` **отключён намеренно**.
- 🇬🇧 **Honest outcome:** SSD temperature cannot be read at all. The UAS quirk required for stability forces usb-storage BOT mode, which blocks the ATA passthrough SMART needs. `smartd` is disabled by design.
- 🇷🇺 **Чем закрыт мониторинг вместо SMART:** `nasa-jms583-health.timer` ежечасно (драйвер, активность quirk, USB-ошибки) и `nasa-usb-monitor.service` (dmesg → Telegram в реальном времени). На 2026-08-10 — 0 ошибок с момента загрузки.
- 🇷🇺 **Ответ tklim:** тезис о перегреве не подтверждён и не опровергнут — измерить нечем. Косвенно: SoC 45 °C, за 30 дней ни одного теплового сбоя, 0 USB-ошибок.

### Фаза 5 — Immich ML на узле Vostro 15 / Phase 5 — Immich ML on the Vostro 15 node 📋 ПЕРЕРАБОТАНА 2026-08-10
- 🇷🇺 **Решение (2026-08-01):** в проект вводится старый ноутбук **Dell Vostro 15 (2018)** как выделенный always-on ML-узел. Это снимает ограничение Jetson (CUDA 10.2, 4 ГБ) без покупок — то, что советовал falcon4fun, но на своём железе.
- 🇷🇺 **Изменение (2026-08-10):** ноутбук **остаётся в корпоративной сети** `192.168.75.177`, а не переезжает домой. Значит, ML-узел удалённый: связь строится **исходящим SSH-туннелем Vostro → VPS**, а Jetson забирает порт обратно через свой уже работающий туннель. Прямого LAN-пути `192.168.0.60:3003` не будет.
- 🇷🇺 **Цена:** задержка ML-запроса ≈ 200–400 мс (через Франкфурт) и ~1.5–2 ГБ разового трафика на бэклог 7098 ассетов. Для асинхронной фоновой очереди это приемлемо.
- 🇷🇺 **Ограничения узла:** нет CUDA (AMD Radeon 520) → только CPU; 2 ядра без turbo; RAM 3.7 ГБ; HDD 5400 rpm. Обработка бэклога растянется на несколько ночей.
- 🇬🇧 **Revised 2026-08-10:** the laptop stays in the corporate network; the ML node becomes remote, connected via an outbound SSH tunnel to the VPS. CPU-only, expect a multi-night backlog run.
- 🇷🇺/🇬🇧 Полный план / full plan — [VOSTRO_ML_NODE_ONBOARDING.md](VOSTRO_ML_NODE_ONBOARDING.md).

### Фаза 6 — Оркестратор и API / Phase 6 — Orchestrator and API
- 🇷🇺 Довести оркестрацию сервисов и `homecloud_nasa_api` (см. `NAS_Jetson_Nano_API_ROADMAP.md`).
- 🇬🇧 Advance service orchestration and `homecloud_nasa_api` (see `NAS_Jetson_Nano_API_ROADMAP.md`).

### Фаза 7 — Перестройка домашней сети / Phase 7 — Home network rebuild 📋 НОВАЯ 2026-08-10

- 🇷🇺 **Решение владельца:** домашняя сеть переводится на mesh **TP-Link Deco E4** с
  **полной заменой роутера** EC220-G5. Полный регламент — [`docs/27_HOME_NETWORK_MESH.md`](../27_HOME_NETWORK_MESH.md).
- 🇬🇧 **Owner's decision:** the home network moves to a TP-Link Deco E4 mesh, fully
  replacing the EC220-G5 router. Runbook — [`docs/27_HOME_NETWORK_MESH.md`](../27_HOME_NETWORK_MESH.md).

**Что это закрывает из отзывов и рисков проекта:**

| Проблема | Как закрывается |
|---|---|
| 🔴 **Внутри LAN сегментации нет** — Immich, Nextcloud, Portainer, admin-API `:8099`, Samba открыты любому, кто знает пароль Wi-Fi | **Гостевая сеть Deco** изолирует гостей, ТВ и IoT от подсети NAS. Это вторая половина замечания tklim про открытые порты — внешний контур уже закрыт в Фазе 1, теперь внутренний |
| Автозагрузка Immich рвётся при переходе по квартире | **Единый SSID + Fast Roaming.** Прямое попадание в главную функцию проекта: 6710 фото перестанут перезапускать очередь |
| Телефоны залипают на 2.4 ГГц (3–5 МБ/с вместо 17) | Smart Connect уводит на 5 ГГц автоматически |
| Сигнал 48 % у рабочей станции — одна точка не покрывает квартиру | Два модуля с бесшовным роумингом |
| Ручная статика для новых узлов | Address Reservation (доступен только в режиме роутера — это и определило выбор режима) |

**Чего перестройка НЕ решает — и это важно сказать честно:**

- 🔴 **Jetson теряет гигабит:** порты Deco аппаратно 10/100, линк упадёт 1000 → 100 Мбит/с.
  Wi-Fi → NAS станет ≈ 94 Мбит/с вместо измеренных 141. Владелец принял это осознанно:
  интернет-тариф ≤ 100 Мбит/с, а узким местом становится сеть, а не диски (SSD отдаёт 250 МБ/с).
  Путь отхода — гигабитный свитч между Deco и проводными устройствами.
- 🔴 **CGNAT никуда не девается:** проброс портов бесполезен при любой топологии.
  Внешний доступ был и остаётся через реверс-туннель на VPS (ADR-0005).
- 🟠 **Управление только через приложение и аккаунт TP-Link** — веб-интерфейса нет.
  Для проекта «уход от облаков» это осознанный компромисс, и его стоит назвать в статье.

## Сводка «замечание → действие» / Summary "comment → action"

| Замечание / Comment | Фаза / Phase | Статус на 2026-08-10 / Status |
|---|---|---|
| Открытые порты / Open ports (tklim) | 1 | ✅ **закрыто** — сервисы на VPS только из VPN; внутри LAN закроет гостевая сеть (Фаза 7) |
| Ёмкость/бэкап / Capacity & backup (автор/author) | 3 | ✅ **HDD 2 ТБ подключён**; restic off-site остаётся |
| Перегрев SSD / SSD overheating (tklim) | 4 | ⛔ **измерить невозможно** — UAS-quirk → BOT-режим → нет ATA passthrough. Косвенно: SoC 45 °C, 0 сбоев за 30 д |
| 4 ГБ мало / 4 GB low (tklim) | 2 | 🔄 лимиты выставлены; три контейнера на 85–92 %; вынос мониторинга — кандидат |
| ML offload (falcon4fun) | 5 | 📋 Vostro 15, но **удалённо** через VPS-туннель — ноутбук остаётся в корпоративной сети |
| GPU простаивает / GPU idle (vvzvlad, dE1l) | 5 | 📋 техдолг: CUDA 10.2 → офиц. GPU-ускорения нет; сетью не решается |
| Роуминг и покрытие / roaming & coverage (наше) | 7 | 📋 Deco E4 заменяет роутер; цена — Jetson 1000 → 100 Мбит/с |
