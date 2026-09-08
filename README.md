# NAS_Jetson_Nano

### _Old hardware should live_ · _Старое железо должно жить_

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Jetson%20Nano%204GB%20·%20ARM64-76B900)
![Services](https://img.shields.io/badge/containers-13%20up-blue)
![Docs](https://img.shields.io/badge/docs-RU%20%2F%20EN-informational)

> 🇷🇺 Семейное облако на NVIDIA Jetson Nano 2019 года: фотографии, файлы, контакты и
> календарь — дома, а не у корпорации. Заменяет Google Photos, Google Drive и облачный NAS.
>
> 🇬🇧 A family cloud on a 2019 NVIDIA Jetson Nano: photos, files, contacts and calendar
> at home instead of at a corporation. Replaces Google Photos, Google Drive and cloud NAS.

**Главное свойство проекта — честность замеров.** 🇷🇺 Всё, что здесь написано, проверено
живой командой, а дата замера указана. Ошибки и отозванные диагнозы не удаляются, а
остаются в документации вместе с тем, как они были найдены. / 🇬🇧 **Measured, not claimed.**
Everything here was verified by a live command, and the measurement date is stated. Mistakes
and retracted diagnoses stay in the docs, together with how they were caught.

---

## Состояние на 2026-09-08 / State as of 2026-09-08

🇷🇺 Канон развития: [Sber-era plan](docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md) · ADR-0007/8/9.  
🇬🇧 Development canon: same plan · ADR-0007/8/9.

| Что / What | Замер / Measurement |
|---|---|
| Контейнеры / Containers | **13 up** (live 2026-09-08) |
| Immich | library **~13 ГБ** on SSD; **L1 copy on HDD** `/mnt/hdd2tb/backups/immich` **13 ГБ** + timer |
| Nextcloud | live (family) |
| SSD `/mnt/storage` | 229 ГБ, ~6 % used (photos grow slowly) |
| HDD `/mnt/hdd2tb` | 1.9 ТБ, ~76 % (family archive NTFS + `backups/`) |
| LLM Gateway | **`provider=gigachat`** (GigaChat-2), DeepSeek fallback, Cloud.ru FM optional, `prefer_local=false` |
| Talk `@бобик` | `TALK_BOT_LLM_PROVIDER=gigachat` |
| DB dumps T0 | fresh **2026-09-08** → Vostro restic snapshot `3922949b` (emergency path) |
| Off-site L2 S3 | ⏳ Cloud.ru bucket blocked (tenant_id) — see [S3 checklist](docs/integrations/sber/S3_AND_BUDGET_CHECKLIST.md) |
| Git mirrors | GitHub canon + [GitVerse NAS_HOME](https://gitverse.ru/Alexey_Borovskoy/NAS_HOME) (SSH OK) |
| Реверс-туннель / Reverse tunnel | active Jetson → VPS `:10022` |
| Habr Part 1 | [1062914](https://habr.com/ru/articles/1062914/) · 13K · 9 comments · [Part 2 plan](docs/articles/HABR_PART2_ARTICLE_PLAN_2026-09.md) |

🟠 **Open debt / Открытый долг:** 🇷🇺 L2 off-site на **Cloud.ru S3** (не Vostro как канон). Vostro = legacy emergency dumps only.  
🇬🇧 L2 off-site target is **Cloud.ru S3** (Vostro is legacy emergency only).  
→ [ADR-0009](docs/decisions/ADR-0009-backup-ssd-hdd-s3.md) · [audit 2026-09-08](docs/audit/AUDIT_GITHUB_SBER_BILINGUAL_2026-09-08.md)

---

## Что работает / What works

🇷🇺 Каждый пункт — работающий сервис, а не план. / 🇬🇧 Each item is a running service, not a plan.

| Сервис / Service | Роль / Role |
|---|---|
| **Nextcloud** | файлы, контакты, календарь (CardDAV/CalDAV через DAVx⁵) |
| **Immich** | семейный фотоархив, автозагрузка с телефонов |
| **Samba** | сетевые шары `public` и `hdd2tb` (2 ТБ архива) |
| **LLM Gateway** | 🇬🇧 GigaChat-first + DeepSeek fallback + optional Cloud.ru FM; **PII redaction** and per-user budgets / 🇷🇺 GigaChat по умолчанию, DeepSeek fallback, Cloud.ru FM опционально; редактирование ПДн и лимиты |
| **Talk-бот `@бобик`** | семейный ассистент в чате Nextcloud: команды из домашних данных + свободные вопросы наружу по явному позывному |
| **Системные алерты** | проблемы приходят в чат владельца: устаревшие бэкапы, отвал диска, упавший контейнер |
| **REST API** | FastAPI поверх всего стека, JWT, Swagger на `:8099/docs` |
| **Мониторинг** | Beszel, Uptime Kuma, Netdata, ежедневный отчёт в Telegram |
| **Реверс-туннель** | внешний доступ через VPS в обход CGNAT — портов наружу не открыто |

---

## Архитектура / Architecture

```
   Интернет / Internet
          │
   ┌──────┴───────┐  VPS (Frankfurt) · 95.163.176.103 · borovskoy.dynv6.net
   │  nginx       │  наружу открыты только 22, 443, 40568/udp
   │  AmneziaWG   │  сервисные порты — ТОЛЬКО из VPN
   └──────┬───────┘
          │  обратный SSH-туннель (инициирует Jetson)
          │  reverse SSH tunnel (initiated by the Jetson)
   ┌──────┴───────────────────────────────┐
   │  Jetson Nano 4 GB · ARM64 · 13 контейнеров │
   │  ├── Nextcloud + PostgreSQL + Redis  │
   │  ├── Immich + PostgreSQL + Redis     │
   │  ├── LLM Gateway · REST API · Samba  │
   │  └── Netdata · Uptime Kuma · Portainer │
   └──────┬───────────────┬───────────────┘
          │               │
   USB SSD 250 GB   USB HDD 2 TB
   сервисы/данные   семейный архив
```

🇷🇺 Подробно: [`03_ARCHITECTURE.md`](docs/03_ARCHITECTURE.md).
Текущая домашняя сеть и её цена: [`28_NETWORK_SNAPSHOT`](docs/28_NETWORK_SNAPSHOT_2026-08-22.md).
🇬🇧 Details in the same files.

---

## Быстрый старт / Quick start

🇷🇺 Разворачивание — из документов, а не из README: шаги зависят от вашего железа и сети.
🇬🇧 Deployment lives in the docs, not here: the steps depend on your hardware and network.

```bash
git clone https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano.git
cd NAS_Jetson_Nano
cp config/.env.example config/.env      # заполнить своими значениями
sudo bash scripts/storage/storage_preflight.sh
docker compose -f docker/compose/docker-compose.nextcloud.yml --env-file config/.env up -d
```

| Шаг / Step | Документ / Document |
|---|---|
| Железо и подготовка SD | [`01A_JETSON_SD_BOOTSTRAP`](docs/01A_JETSON_SD_BOOTSTRAP.md) |
| Хранилище и USB-квирки | [`04_STORAGE_DESIGN`](docs/04_STORAGE_DESIGN.md) |
| Сеть, VPS, туннель | [`05_NETWORKING_VPN`](docs/05_NETWORKING_VPN.md) |
| Клиенты на Android | [`24_CLIENT_SETUP`](docs/24_CLIENT_SETUP.md) |
| Бэкап и восстановление | [`12_BACKUP_RESTORE`](docs/12_BACKUP_RESTORE.md) |
| Мониторинг | [`13_MONITORING_RUNBOOK`](docs/13_MONITORING_RUNBOOK.md) |

⚠️ 🇷🇺 **Минимум железа:** Jetson Nano 4 ГБ (2 ГБ не хватит), **USB SSD обязателен** —
на microSD база данных умирает. / 🇬🇧 **Minimum:** Jetson Nano 4 GB, and a **USB SSD is
mandatory** — a database on microSD will not survive.

---

## Документация / Documentation

🇷🇺 Вся документация двуязычная. Ниже — точки входа, полный список в
[`docs/`](docs/) и [`REPOSITORY_STRUCTURE`](docs/REPOSITORY_STRUCTURE.md).
🇬🇧 All docs are bilingual; entry points below.

**Понять проект / Understand**
[`00_OVERVIEW`](docs/00_OVERVIEW.md) ·
[`03_ARCHITECTURE`](docs/03_ARCHITECTURE.md) ·
[`15_ALTERNATIVES_REVIEW`](docs/15_ALTERNATIVES_REVIEW.md) — почему не Synology / why not a NAS box

**Эксплуатация / Operate**
[`12_BACKUP_RESTORE`](docs/12_BACKUP_RESTORE.md) ·
[`13_MONITORING_RUNBOOK`](docs/13_MONITORING_RUNBOOK.md) ·
[`22_AUDIT_RESILIENCE`](docs/22_AUDIT_RESILIENCE.md) ·
[`33_ZRAM`](docs/33_ZRAM.md) — почему тюнинг подкачки не рычаг

**Качество / Quality**
[`32_QUALITY_GATE`](docs/32_QUALITY_GATE.md) — обязательные ворота: ошибка ловится локально, а не в бою

**Безопасность / Security**
[`10_SECURITY_PRIVACY`](docs/10_SECURITY_PRIVACY.md) ·
[`11_SECRETS_POLICY`](docs/11_SECRETS_POLICY.md) ·
[`SECURITY.md`](SECURITY.md)

**Куда идём / Where next**
[`31_MASTER_PLAN`](docs/31_MASTER_PLAN.md) — **сводный план**: роли узлов, сеть, покупки ·
[`30_NEXT_LEAP`](docs/30_NEXT_LEAP.md) — следующий рывок: память, ответы и голос дома ·
[`29_COMPUTE_AND_LLM_ROADMAP`](docs/29_COMPUTE_AND_LLM_ROADMAP.md) — вычисления, Kaggle, локальные модели ·
[`ROADMAP_STEP2`](docs/plans/ROADMAP_STEP2_2026-08.md) ·
[`POST_HABR_FEEDBACK`](docs/plans/POST_HABR_FEEDBACK_2026-08.md) — разбор критики читателей

**Как это делалось / How it was built**
[`20_AGENT_OPERATING_MODEL`](docs/20_AGENT_OPERATING_MODEL.md) — работа с ИИ-агентами ·
[`AGENTS.md`](AGENTS.md) · [`CLAUDE.md`](CLAUDE.md)

---

## Безопасность — честно / Security — honestly

🇷🇺
- ✅ Наружу на VPS открыты **только** 22, 443 и 40568/udp. Сервисы — только через VPN.
- ✅ Секретов в git нет; история очищена, пароли ротированы (2026-06-28).
- ✅ Фотографии наружу не уходят: `LLM_ALLOW_IMAGE_ANALYSIS=false`.
- ✅ Свободные вопросы уходят к внешней модели **только по явному позывному** и после
  редактирования персональных данных.
- 🟠 **Внутри домашней LAN сегментации нет** — любой, кто знает пароль Wi-Fi, видит сервисы.
- 🟠 TLS самоподписанный, выписан на один адрес.

🇬🇧
- ✅ Only 22, 443 and 40568/udp are world-reachable; services are VPN-only.
- ✅ No secrets in git; history rewritten, passwords rotated.
- ✅ Photos never leave: `LLM_ALLOW_IMAGE_ANALYSIS=false`.
- ✅ Free-form questions leave only on an explicit callsign, after PII redaction.
- 🟠 **No segmentation inside the home LAN** — the Wi-Fi password is the real perimeter.
- 🟠 Self-signed TLS, issued for a single address.

---

## Чего здесь нет / What this is not

🇷🇺 Список нужен, чтобы не обещать лишнего:

- **Не готовый продукт.** Это домашний сервер одной семьи, опубликованный целиком.
- **GPU Jetson не используется** — CUDA 10.2 против требуемых 11/12. Это структурное
  ограничение платформы, а не недоделка. Machine learning выносится на другой узел.
- **Off-site бэкап фото пока не сделан** — БД (фаза 1) уже реплицируется на Vostro,
  фото Immich (~6 ГБ, фаза 2) — главный открытый долг.
- **Высокой доступности нет.** Одна плата, один блок питания.

🇬🇧 The same list: not a product, the Jetson GPU is unusable (CUDA 10.2 vs 11/12 required),
no off-site backup yet, no high availability.

---

## Статьи / Articles

- 🇷🇺 [Черновик статьи для Habr](docs/articles/habr_article_ru.md)
- 🇬🇧 [Hackaday.io project draft](docs/articles/hackaday_project_en.md)
- Разбор критики читателей / reader feedback: [`POST_HABR_FEEDBACK`](docs/plans/POST_HABR_FEEDBACK_2026-08.md)

## Вклад / Contributing

🇷🇺 Проект открыт, вопросы и замечания приветствуются — особенно те, что ловят ошибку. /
🇬🇧 Contributions welcome, especially ones that catch a mistake.
См. [`CONTRIBUTING.md`](CONTRIBUTING.md) и [открытые issues](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/issues).

## Лицензия / License

MIT — см. [`LICENSE`](LICENSE).
