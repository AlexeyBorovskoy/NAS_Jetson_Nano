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

### Фаза 1 — Безопасность / Phase 1 — Security
- 🇷🇺 Увести Nextcloud/Immich/LLM с публичного nginx **за VPN** (Tailscale / Amnezia); fail2ban на VPS; ужесточить nginx; при появлении домена — Let's Encrypt. Итог: правило №4 реально соблюдается.
- 🇬🇧 Move Nextcloud/Immich/LLM off public nginx **behind a VPN** (Tailscale / Amnezia); fail2ban on the VPS; harden nginx; Let's Encrypt once a domain exists. Result: rule #4 is actually honored.

### Фаза 2 — Оптимизация RAM / Phase 2 — RAM optimization
- 🇷🇺 Аудит `mem_limit` всех 13 контейнеров; вынести часть мониторинга (netdata/uptime-kuma/portainer) на VPS или на ML-узел; тюнинг zram. Итог: появляется бюджет RAM под ML.
- 🇬🇧 Audit `mem_limit` across all 13 containers; move some monitoring (netdata/uptime-kuma/portainer) to the VPS or the ML node; tune zram. Result: RAM budget frees up for ML.

### Фаза 3 — Хранилище и бэкап / Phase 3 — Storage and backup
- 🇷🇺 Подключить 2 ТБ HDD (уже в наличии); restic off-site backup. Итог: закрыт вопрос ёмкости и оффлайн-копий.
- 🇬🇧 Attach the 2 TB HDD (already owned); restic off-site backup. Result: capacity and off-site copies covered.

### Фаза 4 — Мониторинг накопителя / Phase 4 — Drive monitoring
- 🇷🇺 Снимать температуру SSD через `smartctl -d sat -a` (attr 194) в рамках `nasa-jms583-health.timer`; Telegram-алерт при пороге. Итог: тезис о перегреве подтверждается/снимается данными.
- 🇬🇧 Read SSD temperature via `smartctl -d sat -a` (attr 194) within `nasa-jms583-health.timer`; Telegram alert on threshold. Result: the overheating claim is settled with data.

### Фаза 5 — Immich ML на выделенном узле Vostro 15 / Phase 5 — Immich ML on a dedicated Vostro 15 node
- 🇷🇺 **Решение (2026-08-01):** в проект вводится старый ноутбук **Dell Vostro 15 (2018)** как выделенный always-on ML-узел (ZTN закрыт → ноут свободен). Это снимает ограничение Jetson (CUDA 10.2, 4 ГБ) без покупок — то, что советовал falcon4fun, но на своём железе. `immich-machine-learning` крутится на Vostro (`192.168.0.60:3003`), Immich на Jetson указывает через `IMMICH_MACHINE_LEARNING_URL`. Бонус: ML уходит с Nano → разгрузка RAM. Полный план — [VOSTRO_ML_NODE_ONBOARDING.md](VOSTRO_ML_NODE_ONBOARDING.md).
- 🇬🇧 **Decision (2026-08-01):** bring the old **Dell Vostro 15 (2018)** laptop into the project as a dedicated always-on ML node (ZTN wrapped up → the laptop is free). This lifts the Jetson's limit (CUDA 10.2, 4 GB) with no purchase — falcon4fun's advice, on our own hardware. `immich-machine-learning` runs on the Vostro (`192.168.0.60:3003`); the Jetson's Immich points to it via `IMMICH_MACHINE_LEARNING_URL`. Bonus: ML leaves the Nano → RAM relief. Full plan — [VOSTRO_ML_NODE_ONBOARDING.md](VOSTRO_ML_NODE_ONBOARDING.md).

### Фаза 6 — Оркестратор и API / Phase 6 — Orchestrator and API
- 🇷🇺 Довести оркестрацию сервисов и `homecloud_nasa_api` (см. `NAS_Jetson_Nano_API_ROADMAP.md`).
- 🇬🇧 Advance service orchestration and `homecloud_nasa_api` (see `NAS_Jetson_Nano_API_ROADMAP.md`).

## Сводка «замечание → действие» / Summary "comment → action"

| Замечание / Comment | Фаза / Phase | Ограничение / Constraint |
|---|---|---|
| GPU простаивает / GPU idle (vvzvlad, dE1l) | 5 | CUDA 10.2 → нет офиц. GPU-ускорения; CPU-путь или offload / no official GPU accel; CPU or offload |
| 4 ГБ мало / 4 GB low (tklim) | 2 | без покупок, только оптимизация / no purchases, optimization only |
| Перегрев SSD / SSD overheating (tklim) | 4 | измерить, а не спорить / measure, don't argue |
| Открытые порты / Open ports (tklim) | 1 | Tailscale/Amnezia — no-purchase |
| ML offload (falcon4fun) | 5 | вместо покупки — Vostro 15 / Vostro 15 instead of buying |
| Ёмкость/бэкап / Capacity & backup (автор/author) | 3 | 2 ТБ HDD уже есть / already owned |
