# Подробный план и содержание работ по продвижению проекта на GitHub / A detailed plan and scope of work for promoting the project on GitHub

**Проект / Project:** Home Cloud for Old Hardware  
**Рабочий слоган / Working slogan:** «Оживим старое железо» / "Let's revive old hardware"  
**Техническое ядро / Technical core:** Nextcloud + Immich + Samba/SFTP + Docker Compose + Backup + DeepSeek Gateway  
**Первичная аппаратная цель / Primary hardware target:** NVIDIA Jetson Nano + USB HDD с отдельным питанием / NVIDIA Jetson Nano + a self-powered USB HDD  
**Расширяемые цели / Extended targets:** Raspberry Pi, Orange Pi, mini-PC, старые ноутбуки, x86-серверы / Raspberry Pi, Orange Pi, mini-PCs, old laptops, x86 servers  
**Назначение документа / Purpose of this document:** определить полный план работ по упаковке, публикации, продвижению и развитию проекта на GitHub. / to define the complete plan of work for packaging, publishing, promoting and developing the project on GitHub.

---

## 1. Цель продвижения / The goal of promotion

🇷🇺 Цель продвижения — не просто выложить репозиторий, а сформировать вокруг проекта понятную инженерную концепцию:

🇬🇧 The goal of promotion is not merely to publish a repository, but to build a clear engineering concept around the project:

```text
старое железо → домашнее облако → семейный архив → Android-синхронизация → backup/restore → контролируемая AI-диагностика
old hardware → home cloud → family archive → Android sync → backup/restore → controlled AI diagnostics
```

🇷🇺 Проект должен восприниматься как воспроизводимый набор методик, конфигураций и документации для превращения старого оборудования в полезную домашнюю инфраструктуру.

🇬🇧 The project should be perceived as a reproducible set of methods, configurations and documentation for turning old equipment into useful home infrastructure.

---

## 2. Ключевое позиционирование / Core positioning

### 2.1. Основная формулировка / The main statement

```text
Home Cloud for Old Hardware — инженерный проект по превращению старого оборудования в частное семейное облако с файлами, фотоархивом, контактами, календарями, Android-синхронизацией, резервным копированием и безопасной LLM-диагностикой.

Home Cloud for Old Hardware is an engineering project that turns old equipment into a private family cloud with files, a photo archive, contacts, calendars, Android synchronisation, backups and safe LLM-based diagnostics.
```

### 2.2. Короткое описание для GitHub / The short GitHub description

```text
Revive old hardware into a private family cloud with Nextcloud, Immich, Android sync, backup/restore and privacy-controlled DeepSeek diagnostics.
```

### 2.3. Русскоязычное описание / The Russian-language description

```text
Домашнее семейное облако на старом железе: Nextcloud, Immich, Android-синхронизация, резервное копирование и безопасная диагностика через DeepSeek API.
```

### 2.4. Главная идея / The core idea

```text
Старое железо не на свалку, а в домашнюю инфраструктуру.
Old hardware belongs in home infrastructure, not in the landfill.
```

---

## 3. Целевые аудитории / Target audiences

| № | Аудитория / Audience | Основная боль / Main pain point | Что показывать / What to show |
|---:|---|---|---|
| 1 | Владельцы старых SBC / Owners of old SBCs | Плата лежит без дела / The board sits unused | Jetson/Raspberry как домашний сервер / Jetson/Raspberry as a home server |
| 2 | Домашние пользователи / Home users | Фото, документы и контакты завязаны на облака / Photos, documents and contacts are tied to clouds | Локальное семейное облако / A local family cloud |
| 3 | Android/Xiaomi-пользователи / Android/Xiaomi users | Зависимость от Google/Xiaomi Cloud / Dependence on Google/Xiaomi Cloud | Свой центр синхронизации и восстановления / Your own sync and restore hub |
| 4 | Linux/self-hosted сообщество / The Linux/self-hosted community | Нужен воспроизводимый стек / They need a reproducible stack | Docker Compose, scripts, runbook |
| 5 | Homelab-сообщество / The homelab community | Нужен практический проект для дома / They need a practical project for the home | NAS + cloud + photo archive |
| 6 | Privacy-сообщество / The privacy community | Риск утечки личных данных / The risk of personal data leaking | Privacy policy и LLM-фильтр / A privacy policy and the LLM filter |
| 7 | Разработчики / Developers | Нужна хорошая архитектура под развитие / They need a good architecture to build on | Codex-ready структура, prompts, roadmap / A Codex-ready structure, prompts, a roadmap |
| 8 | Экологические инициативы / Environmental initiatives | Электронные отходы / Electronic waste | Повторное использование оборудования / Reusing equipment |

---

## 4. Продуктовая упаковка проекта / Packaging the project as a product

### 4.1. Что проект должен обещать / What the project should promise

🇷🇺 Проект должен обещать реалистичный результат:

🇬🇧 The project should promise a realistic outcome:

```text
1. Поднять домашнее облако на старом железе.
2. Хранить семейные фото, видео и документы локально.
3. Синхронизировать Android-фото, контакты и календари.
4. Иметь базовую стратегию backup/restore.
5. Получить диагностического AI-помощника без отправки личных данных.

1. Bring up a home cloud on old hardware.
2. Store family photos, videos and documents locally.
3. Synchronise Android photos, contacts and calendars.
4. Have a basic backup/restore strategy.
5. Get a diagnostic AI assistant without sending personal data anywhere.
```

### 4.2. Что проект не должен обещать / What the project must not promise

🇷🇺 Необходимо явно ограничить ожидания:

🇬🇧 Expectations must be limited explicitly:

```text
1. Это не полная замена Google/Xiaomi Cloud на уровне системного backup Android.
2. Один USB HDD не является полноценным backup.
3. Jetson Nano не предназначен для локальной LLM.
4. Immich ML на слабом железе должен быть ограничен или отключён.
5. Публичный доступ в интернет без VPN не является безопасным режимом первого этапа.

1. This is not a full replacement for Google/Xiaomi Cloud at the level of a system-wide Android backup.
2. A single USB HDD is not a real backup.
3. The Jetson Nano is not meant to run a local LLM.
4. Immich ML must be limited or disabled on weak hardware.
5. Public internet exposure without a VPN is not a safe mode for stage one.
```

---

## 5. Структура публичного репозитория / Public repository structure

🇷🇺 Рекомендуемая структура:

🇬🇧 The recommended structure:

```text
home-cloud-old-hardware/
├── README.md
├── QUICK_START.md
├── PROJECT_STATUS.md
├── ROADMAP.md
├── CHANGELOG.md
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── PRIVACY.md
├── SECRETS_POLICY.md
├── BACKUP_RESTORE.md
├── OLD_HARDWARE_GUIDE.md
├── HARDWARE_COMPATIBILITY.md
├── ARCHITECTURE.md
├── ANDROID_STAGE2.md
├── LLM_GATEWAY.md
│
├── docs/
│   ├── references/
│   ├── architecture/
│   ├── deployment/
│   ├── security/
│   ├── operations/
│   ├── promotion/
│   └── hardware/
│
├── docker/
│   ├── compose/
│   ├── env-templates/
│   └── profiles/
│
├── scripts/
│   ├── diagnostics/
│   ├── backup/
│   ├── maintenance/
│   └── fetch_external_docs.sh
│
├── services/
│   ├── llm-gateway/
│   └── backup-api/
│
├── profiles/
│   ├── jetson-nano/
│   ├── raspberry-pi-4/
│   ├── raspberry-pi-5/
│   ├── orange-pi/
│   ├── old-laptop/
│   ├── mini-pc/
│   └── x86-server/
│
├── docs/prompts/
│   ├── CODEX_PROJECT_BOOTSTRAP_PROMPT.md
│   ├── CODEX_JETSON_AUDIT_PROMPT.md
│   ├── CODEX_SECURITY_AUDIT_PROMPT.md
│   ├── CODEX_DEPLOYMENT_PROMPT.md
│   └── CODEX_ANDROID_STAGE2_PROMPT.md
│
├── examples/
│   ├── hardware-audit-report.example.md
│   ├── backup-report.example.md
│   └── diagnostic-report.example.md
│
└── .github/
    ├── ISSUE_TEMPLATE/
    ├── workflows/
    ├── pull_request_template.md
    └── dependabot.yml
```

---

## 6. Документы первого публичного релиза / Documents for the first public release

### 6.1. Обязательные документы / Mandatory documents

| Документ / Document | Содержание / Contents | Приоритет / Priority |
|---|---|---:|
| `README.md` | Суть проекта, схема, быстрый старт, ограничения / The essence of the project, a diagram, a quick start, the limitations | 1 |
| `QUICK_START.md` | Минимальный запуск / The minimal launch path | 1 |
| `OLD_HARDWARE_GUIDE.md` | Как выбрать старое железо / How to choose old hardware | 1 |
| `HARDWARE_COMPATIBILITY.md` | Таблица совместимости / A compatibility table | 1 |
| `ARCHITECTURE.md` | Архитектура системы / The system architecture | 1 |
| `SECURITY.md` | Безопасность доступа / Access security | 1 |
| `PRIVACY.md` | Защита персональных данных / Personal data protection | 1 |
| `BACKUP_RESTORE.md` | Backup/restore | 1 |
| `PROJECT_STATUS.md` | Статус Alpha, ограничения / Alpha status, the limitations | 1 |
| `ROADMAP.md` | Stage 1 / Stage 2 / Stage 3 | 1 |
| `CONTRIBUTING.md` | Как участвовать / How to contribute | 2 |
| `CODE_OF_CONDUCT.md` | Правила сообщества / Community rules | 2 |
| `CHANGELOG.md` | История изменений / The change history | 2 |

### 6.2. Технические документы / Technical documents

| Документ / Document | Содержание / Contents |
|---|---|
| `docs/deployment/JETSON_NANO_DEPLOYMENT.md` | Установка на Jetson Nano / Installation on the Jetson Nano |
| `docs/deployment/DOCKER_COMPOSE_DEPLOYMENT.md` | Docker Compose deployment |
| `docs/hardware/HARDWARE_AUDIT.md` | Проверка железа / Hardware verification |
| `docs/security/LLM_PRIVACY_POLICY.md` | Политика работы с DeepSeek API / The policy for working with the DeepSeek API |
| `docs/operations/RUNBOOK.md` | Операционные процедуры / Operational procedures |
| `docs/operations/TROUBLESHOOTING.md` | Диагностика типовых проблем / Diagnosing common problems |
| `docs/references/REFERENCE_LINKS.md` | Ссылки на документацию / Links to documentation |

---

## 7. README: обязательное содержание / README: mandatory contents

🇷🇺 README должен быть главным продающим и техническим документом.

🇬🇧 The README must be both the main sales document and the main technical document.

### 7.1. Структура README / README structure

```markdown
# Home Cloud for Old Hardware

## 1. What is this project?
## 2. Why old hardware?
## 3. Target use cases
## 4. Architecture
## 5. Supported hardware
## 6. Stage 1 stack
## 7. Quick start
## 8. Security and privacy model
## 9. Backup warning
## 10. Project roadmap
## 11. Screenshots / demo
## 12. Contributing
## 13. License
```

### 7.2. Блок «Why» / The "Why" block

```text
Many old SBCs, mini-PCs and laptops are still powerful enough for useful home infrastructure. This project provides a reproducible blueprint to turn them into a private family cloud instead of electronic waste.
```

### 7.3. Блок «What you get» / The "What you get" block

```text
- private file cloud with Nextcloud;
- contacts and calendar sync;
- photo/video archive with Immich;
- local NAS access with Samba/SFTP;
- backup and restore procedures;
- DeepSeek-based diagnostic assistant;
- roadmap for future Android restore client.
```

### 7.4. Блок предупреждений / The warnings block

```text
Important limitations:
- one HDD is not a backup;
- do not expose SMB/FTP directly to the Internet;
- local LLM is not part of Stage 1;
- Immich ML should be disabled on weak hardware;
- personal media must not be sent to external LLM APIs.
```

---

## 8. QUICK_START: содержание / QUICK_START: contents

🇷🇺 Цель `QUICK_START.md` — дать пользователю минимальный путь к результату.

🇬🇧 The purpose of `QUICK_START.md` is to give the user the shortest path to a result.

### 8.1. Структура / Structure

```markdown
# Quick Start

## 1. Requirements
## 2. Prepare storage
## 3. Run hardware audit
## 4. Install Docker
## 5. Configure environment
## 6. Start base services
## 7. Validate Nextcloud
## 8. Validate Immich
## 9. Configure Android apps
## 10. Configure backup
## 11. Troubleshooting
```

### 8.2. MVP-команды / MVP commands

🇷🇺 MVP-команды должны быть короткими и проверяемыми:

🇬🇧 The MVP commands must be short and verifiable:

```bash
./scripts/diagnostics/hardware_audit.sh
cp config/.env.example config/.env
nano config/.env
docker compose -f docker/compose/stage1.yml config
docker compose -f docker/compose/stage1.yml up -d
docker compose -f docker/compose/stage1.yml ps
```

---

## 9. GitHub Issues: шаблоны / GitHub Issues: templates

🇷🇺 Необходимо подготовить `.github/ISSUE_TEMPLATE/`.

🇬🇧 `.github/ISSUE_TEMPLATE/` has to be prepared.

### 9.1. `bug_report.yml`

🇷🇺 Содержит: / 🇬🇧 Contains:

```text
- description;
- expected behavior;
- actual behavior;
- logs;
- docker compose version;
- hardware profile;
- operating system;
- steps to reproduce.
```

### 9.2. `hardware_compatibility_report.yml`

🇷🇺 Содержит: / 🇬🇧 Contains:

```text
- device model;
- CPU architecture;
- RAM;
- storage type;
- OS version;
- Docker version;
- services tested;
- result;
- notes;
- logs.
```

### 9.3. `installation_problem.yml`

🇷🇺 Содержит: / 🇬🇧 Contains:

```text
- installation step;
- command used;
- error output;
- hardware profile;
- network setup;
- storage mount point.
```

### 9.4. `feature_request.yml`

🇷🇺 Содержит: / 🇬🇧 Contains:

```text
- use case;
- proposed feature;
- target hardware;
- priority;
- alternatives considered.
```

### 9.5. `security_report.md`

🇷🇺 Для security issue лучше направлять пользователя к `SECURITY.md` и не просить публиковать уязвимости публично.

🇬🇧 For a security issue it is better to point the user to `SECURITY.md` rather than ask them to disclose vulnerabilities publicly.

---

## 10. GitHub Discussions

🇷🇺 Рекомендуется включить Discussions и создать категории:

🇬🇧 It is recommended to enable Discussions and create the following categories:

| Категория / Category | Назначение / Purpose |
|---|---|
| Announcements | Релизы и новости / Releases and news |
| General | Общие вопросы / General questions |
| Hardware Builds | Отчёты по железу / Hardware reports |
| Installation Help | Помощь с установкой / Installation help |
| Android Sync | Вопросы Android-синхронизации / Android sync questions |
| Backup/Restore | Вопросы backup/restore / Backup/restore questions |
| Ideas | Идеи развития / Ideas for further development |
| Showcase | Фото и отчёты пользовательских стендов / Photos and reports of users' builds |

---

## 11. GitHub Projects / Roadmap

🇷🇺 Рекомендуется создать GitHub Project с колонками:

🇬🇧 It is recommended to create a GitHub Project with the following columns:

```text
Backlog
Ready
In Progress
Review
Done
Blocked
```

### 11.1. Milestones

| Milestone | Цель / Goal |
|---|---|
| `v0.1.0-alpha` | Публичная документация и Jetson Nano MVP / Public documentation and the Jetson Nano MVP |
| `v0.2.0` | Стабильный Stage 1 Docker Compose / A stable Stage 1 Docker Compose |
| `v0.3.0` | Raspberry Pi / mini-PC profiles |
| `v0.4.0` | Backup/restore validation |
| `v0.5.0` | DeepSeek Gateway MVP |
| `v1.0.0` | Стабильный self-hosted blueprint / A stable self-hosted blueprint |
| `v2.0.0` | Android Stage 2 client |

### 11.2. Labels

🇷🇺 Рекомендуемые labels:

🇬🇧 Recommended labels:

```text
area:docs
area:docker
area:hardware
area:security
area:backup
area:android
area:llm
area:nextcloud
area:immich
area:nas
priority:low
priority:medium
priority:high
status:blocked
status:needs-info
good-first-issue
help-wanted
```

---

## 12. GitHub Actions

🇷🇺 Для публичного проекта полезны проверки без развёртывания реального сервера.

🇬🇧 For a public project, checks that do not require deploying a real server are the useful ones.

### 12.1. Минимальный набор workflow / The minimal set of workflows

| Workflow | Назначение / Purpose |
|---|---|
| `markdown-lint.yml` | Проверка Markdown / Markdown linting |
| `shellcheck.yml` | Проверка shell-скриптов / Shell script checks |
| `docker-compose-config.yml` | Проверка валидности compose-файлов / Validating the compose files |
| `secret-scan.yml` | Поиск случайно закоммиченных секретов / Looking for accidentally committed secrets |
| `links-check.yml` | Проверка ссылок в документации / Checking links in the documentation |

### 12.2. Что не делать на первом этапе / What not to do at the first stage

```text
1. Не запускать тяжёлые контейнеры в CI.
2. Не тестировать реальный Immich/Nextcloud в GitHub Actions без необходимости.
3. Не хранить секреты DeepSeek в GitHub Actions на раннем этапе.
4. Не делать автоматический deploy из публичного репозитория.

1. Do not run heavy containers in CI.
2. Do not test a real Immich/Nextcloud in GitHub Actions unless it is necessary.
3. Do not store DeepSeek secrets in GitHub Actions at an early stage.
4. Do not set up automatic deployment from a public repository.
```

---

## 13. Release-стратегия / Release strategy

### 13.1. Первый релиз / The first release

```text
v0.1.0-alpha
```

🇷🇺 Состав: / 🇬🇧 Contents:

```text
- README.md;
- QUICK_START.md;
- ARCHITECTURE.md;
- OLD_HARDWARE_GUIDE.md;
- HARDWARE_COMPATIBILITY.md;
- SECURITY.md;
- PRIVACY.md;
- BACKUP_RESTORE.md;
- docker compose templates;
- .env.example;
- diagnostic scripts;
- backup scripts;
- Codex prompts.
```

### 13.2. Release notes

🇷🇺 Шаблон release notes:

🇬🇧 The release notes template:

```markdown
# v0.1.0-alpha

## Added
- Initial public documentation.
- Jetson Nano hardware profile.
- Stage 1 architecture.
- Nextcloud + Immich deployment templates.
- DeepSeek Gateway design.
- Backup/restore plan.

## Known limitations
- Not yet tested on multiple hardware profiles.
- Immich ML is disabled by default on weak hardware.
- Android restore client is planned for Stage 2.
- No one-click installer yet.

## Safety notes
- Do not expose services directly to the Internet.
- Use VPN for remote access.
- One HDD is not a backup.
```

---

## 14. Контент-план продвижения / The promotion content plan

### 14.1. Серия публикаций / A series of publications

| № | Тема / Topic | Цель / Goal |
|---:|---|---|
| 1 | Оживляем старое железо / Reviving old hardware | Объяснить идею / Explain the idea |
| 2 | Аппаратный аудит Jetson Nano / A hardware audit of the Jetson Nano | Показать инженерный подход / Show the engineering approach |
| 3 | USB HDD и структура хранения / The USB HDD and the storage layout | Объяснить storage layer / Explain the storage layer |
| 4 | Samba/SFTP как базовый NAS / Samba/SFTP as a basic NAS | Быстрый практический результат / A quick practical result |
| 5 | Nextcloud для файлов, контактов, календарей / Nextcloud for files, contacts and calendars | Основной cloud layer / The main cloud layer |
| 6 | Immich как домашний Google Photos / Immich as a home Google Photos | Фото/видео сценарий / The photo/video scenario |
| 7 | Backup без самообмана / Backups without self-deception | Защита от потери данных / Protection against data loss |
| 8 | DeepSeek Gateway | AI-диагностика без отправки личных данных / AI diagnostics without sending personal data anywhere |
| 9 | Android Stage 2 | Будущий restore client / The future restore client |
| 10 | Сравнение Jetson, Raspberry Pi, mini-PC / Comparing the Jetson, Raspberry Pi and mini-PCs | Масштабирование аудитории / Broadening the audience |

### 14.2. Habr-статья №1 / Habr article #1

🇷🇺 Заголовок: / 🇬🇧 Title:

```text
Оживляем старое железо: домашнее облако на Jetson Nano, USB HDD, Nextcloud и Immich

Reviving old hardware: a home cloud on a Jetson Nano, a USB HDD, Nextcloud and Immich
```

🇷🇺 Структура: / 🇬🇧 Structure:

```text
1. Почему возникла задача.
2. Какое железо использовано.
3. Почему не локальная LLM.
4. Почему Nextcloud + Immich.
5. Архитектура.
6. Первый MVP.
7. Ограничения Jetson Nano.
8. Что дальше.
9. Ссылка на GitHub.

1. Why the problem came up.
2. What hardware was used.
3. Why not a local LLM.
4. Why Nextcloud + Immich.
5. The architecture.
6. The first MVP.
7. The Jetson Nano's limitations.
8. What comes next.
9. The GitHub link.
```

### 14.3. Reddit-пост / The Reddit post

🇷🇺 Заголовок: / 🇬🇧 Title:

```text
I turned an old Jetson Nano into a private family cloud with Nextcloud, Immich and Android sync
```

🇷🇺 Краткая структура: / 🇬🇧 A short structure:

```text
- Hardware used.
- Services deployed.
- What works.
- What is limited.
- Why old hardware.
- GitHub link.
- Ask for hardware compatibility reports.
```

---

## 15. Демонстрационные материалы / Demonstration materials

### 15.1. Скриншоты / Screenshots

🇷🇺 Нужны: / 🇬🇧 Needed:

```text
1. Фото старого железа до сборки.
2. Фото собранного стенда.
3. Nextcloud dashboard.
4. Nextcloud files.
5. Nextcloud contacts/calendar.
6. Immich web gallery.
7. Android Immich upload.
8. Docker compose status.
9. Backup report.
10. DeepSeek diagnostic report.

1. A photo of the old hardware before assembly.
2. A photo of the assembled rig.
3. Nextcloud dashboard.
4. Nextcloud files.
5. Nextcloud contacts/calendar.
6. Immich web gallery.
7. Android Immich upload.
8. Docker compose status.
9. Backup report.
10. DeepSeek diagnostic report.
```

### 15.2. Видео / Video

🇷🇺 Первое видео: / 🇬🇧 The first video:

```text
Тема: Старый Jetson Nano как домашнее облако
Длина: 5–8 минут
Формат: проблема → железо → запуск → результат → ограничения → GitHub

Topic: An old Jetson Nano as a home cloud
Length: 5–8 minutes
Format: problem → hardware → launch → result → limitations → GitHub
```

### 15.3. Архитектурные схемы / Architecture diagrams

🇷🇺 Минимум три схемы: / 🇬🇧 At least three diagrams:

```text
1. High-level architecture.
2. Data flow: Android → Nextcloud/Immich → HDD.
3. Backup/restore flow.
```

---

## 16. Метрики успеха / Success metrics

### 16.1. GitHub-метрики / GitHub metrics

| Метрика / Metric | Цель на 1 месяц / 1-month goal | Цель на 3 месяца / 3-month goal |
|---|---:|---:|
| Stars | 50–100 | 300+ |
| Forks | 5–10 | 30+ |
| Issues | 10+ | 50+ |
| Hardware reports | 5+ | 25+ |
| Contributors | 1–3 | 5+ |
| Discussions | 5+ | 30+ |

### 16.2. Контент-метрики / Content metrics

| Метрика / Metric | Цель / Goal |
|---|---:|
| Habr views | 5 000+ |
| Reddit upvotes | 100+ |
| GitHub visits после публикации / GitHub visits after publication | 500+ |
| Комментарии с железом пользователей / Comments describing users' hardware | 20+ |

---

## 17. Работа с сообществом / Working with the community

### 17.1. Что просить у пользователей / What to ask users for

```text
1. Присылайте отчёты по вашему старому железу.
2. Проверяйте инструкции на Raspberry Pi / mini-PC / old laptop.
3. Добавляйте hardware compatibility reports.
4. Предлагайте улучшения backup/restore.
5. Не присылайте личные данные и реальные секреты в issues.

1. Send in reports about your own old hardware.
2. Test the instructions on a Raspberry Pi / mini-PC / old laptop.
3. Add hardware compatibility reports.
4. Suggest backup/restore improvements.
5. Do not put personal data or real secrets into issues.
```

### 17.2. Как отвечать на issues / How to respond to issues

🇷🇺 Стиль ответов: / 🇬🇧 The style of replies:

```text
1. Запросить hardware profile.
2. Запросить минимальный лог без секретов.
3. Уточнить шаг инструкции.
4. Предложить воспроизводимую проверку.
5. Зафиксировать результат в troubleshooting.

1. Ask for the hardware profile.
2. Ask for a minimal log with no secrets.
3. Clarify which step of the instructions is involved.
4. Propose a reproducible check.
5. Record the outcome in the troubleshooting document.
```

### 17.3. Как использовать вклад пользователей / How to use user contributions

```text
1. Все успешные стенды добавлять в HARDWARE_COMPATIBILITY.md.
2. Частые ошибки переносить в TROUBLESHOOTING.md.
3. Хорошие идеи переносить в ROADMAP.md.
4. Повторяемые вопросы переносить в FAQ.md.

1. Add every successful build to HARDWARE_COMPATIBILITY.md.
2. Move common mistakes into TROUBLESHOOTING.md.
3. Move good ideas into ROADMAP.md.
4. Move recurring questions into FAQ.md.
```

---

## 18. Расширение проекта за пределы Jetson Nano / Extending the project beyond the Jetson Nano

### 18.1. Почему это важно / Why this matters

🇷🇺 Если проект останется только про Jetson Nano, аудитория будет узкой. Нужно позиционировать Jetson Nano как первый hardware profile, а не единственную цель.

🇬🇧 If the project stays only about the Jetson Nano, the audience will be narrow. The Jetson Nano should be positioned as the first hardware profile, not as the only target.

### 18.2. Hardware profiles

```text
profiles/
├── jetson-nano/
│   ├── README.md
│   ├── limitations.md
│   └── compose.override.yml
├── raspberry-pi-4/
├── raspberry-pi-5/
├── orange-pi/
├── old-laptop/
├── mini-pc/
└── x86-server/
```

### 18.3. Матрица профилей / The profile matrix

| Профиль / Profile | Статус / Status | Особенности / Notes |
|---|---|---|
| Jetson Nano | Primary | 4 GB RAM, отключать тяжёлый ML / 4 GB RAM, heavy ML must be disabled |
| Raspberry Pi 4 | Planned | Популярная SBC-платформа / A popular SBC platform |
| Raspberry Pi 5 | Planned | Лучше для Immich / Better suited to Immich |
| Orange Pi | Planned | Дешёвые ARM-варианты / Cheap ARM options |
| Old laptop | Planned | Хорошая производительность, больше места / Good performance, more storage room |
| Mini-PC | Recommended | Лучший баланс мощности и энергопотребления / The best balance of power and consumption |
| x86-server | Advanced | Для больших архивов / For large archives |

---

## 19. DeepSeek Gateway как отдельная ценность / The DeepSeek Gateway as a value in its own right

### 19.1. Позиционирование / Positioning

🇷🇺 DeepSeek Gateway не должен быть «игрушкой». Его надо подать как безопасный диагностический слой:

🇬🇧 The DeepSeek Gateway must not look like a toy. It should be presented as a safe diagnostic layer:

```text
LLM assists with diagnostics, logs and documentation, but personal photos, contacts, calendars and private documents are not sent to the external API by default.
```

### 19.2. Сценарии / Scenarios

```text
1. Объяснить ошибку Docker Compose.
2. Сформировать диагностический отчёт.
3. Помочь восстановить сервис после сбоя.
4. Проверить backup status.
5. Объяснить пользователю, что делать дальше.

1. Explain a Docker Compose error.
2. Produce a diagnostic report.
3. Help restore a service after a failure.
4. Check the backup status.
5. Explain to the user what to do next.
```

### 19.3. Ограничения / Limits

```text
1. Не отправлять фото.
2. Не отправлять контакты.
3. Не отправлять календарь.
4. Не отправлять личные документы.
5. Не отправлять ключи, токены, .env.

1. Do not send photos.
2. Do not send contacts.
3. Do not send the calendar.
4. Do not send personal documents.
5. Do not send keys, tokens or .env.
```

---

## 20. Риски продвижения / Promotion risks

| Риск / Risk | Вероятность / Likelihood | Влияние / Impact | Меры / Measures |
|---|---:|---:|---|
| Проект воспримут как очередной compose-файл / The project is seen as yet another compose file | Средняя / Medium | Высокое / High | Усилить методику и old hardware focus / Emphasise the method and the old-hardware focus |
| Пользователи потеряют данные / Users lose data | Низкая/средняя / Low–medium | Критическое / Critical | Жёсткие backup warnings / Hard backup warnings |
| Jetson Nano окажется слабым / The Jetson Nano turns out to be too weak | Высокая / High | Среднее / Medium | Поддержать mini-PC и Raspberry Pi / Support mini-PCs and the Raspberry Pi |
| Issues будут без логов / Issues arrive without logs | Высокая / High | Среднее / Medium | Issue templates |
| Утечка секретов от пользователей / Users leak their own secrets | Средняя / Medium | Высокое / High | Security policy и redaction guide / A security policy and a redaction guide |
| Слишком сложный старт / Getting started is too hard | Средняя / Medium | Высокое / High | QUICK_START и минимальный MVP / QUICK_START and a minimal MVP |
| Споры по LLM/privacy / Arguments about LLM/privacy | Средняя / Medium | Среднее / Medium | Чёткая LLM privacy policy / A clear LLM privacy policy |

---

## 21. План работ по неделям / A week-by-week plan

### Неделя 1. Подготовка публичного репозитория / Week 1. Preparing the public repository

```text
[ ] Выбрать финальное название.
[ ] Очистить структуру проекта.
[ ] Подготовить README.md.
[ ] Подготовить QUICK_START.md.
[ ] Подготовить ARCHITECTURE.md.
[ ] Подготовить SECURITY.md.
[ ] Подготовить PRIVACY.md.
[ ] Подготовить BACKUP_RESTORE.md.
[ ] Добавить LICENSE.
[ ] Добавить .gitignore.

[ ] Choose the final name.
[ ] Clean up the project structure.
[ ] Prepare README.md.
[ ] Prepare QUICK_START.md.
[ ] Prepare ARCHITECTURE.md.
[ ] Prepare SECURITY.md.
[ ] Prepare PRIVACY.md.
[ ] Prepare BACKUP_RESTORE.md.
[ ] Add a LICENSE.
[ ] Add a .gitignore.
```

### Неделя 2. Техническая воспроизводимость / Week 2. Technical reproducibility

```text
[ ] Проверить hardware audit script.
[ ] Проверить storage preparation guide.
[ ] Проверить Docker installation guide.
[ ] Проверить stage1 compose config.
[ ] Проверить .env.example.
[ ] Проверить Nextcloud deployment.
[ ] Проверить Immich deployment.
[ ] Проверить backup script.

[ ] Verify the hardware audit script.
[ ] Verify the storage preparation guide.
[ ] Verify the Docker installation guide.
[ ] Verify the stage1 compose config.
[ ] Verify .env.example.
[ ] Verify the Nextcloud deployment.
[ ] Verify the Immich deployment.
[ ] Verify the backup script.
```

### Неделя 3. GitHub-оформление / Week 3. GitHub presentation

```text
[ ] Добавить topics.
[ ] Добавить issue templates.
[ ] Добавить pull request template.
[ ] Добавить GitHub Discussions.
[ ] Добавить GitHub Project/Roadmap.
[ ] Добавить labels.
[ ] Добавить first release draft.
[ ] Добавить CHANGELOG.md.

[ ] Add topics.
[ ] Add issue templates.
[ ] Add a pull request template.
[ ] Enable GitHub Discussions.
[ ] Add a GitHub Project/Roadmap.
[ ] Add labels.
[ ] Add the first release draft.
[ ] Add CHANGELOG.md.
```

### Неделя 4. Публичный запуск / Week 4. The public launch

```text
[ ] Создать release v0.1.0-alpha.
[ ] Опубликовать Habr-статью.
[ ] Опубликовать Reddit-пост.
[ ] Опубликовать Telegram-анонс.
[ ] Собрать первые hardware reports.
[ ] Обновить FAQ/TROUBLESHOOTING.

[ ] Create release v0.1.0-alpha.
[ ] Publish the Habr article.
[ ] Publish the Reddit post.
[ ] Publish the Telegram announcement.
[ ] Collect the first hardware reports.
[ ] Update the FAQ/TROUBLESHOOTING documents.
```

---

## 22. Контрольный чек-лист перед публикацией / The pre-publication checklist

```text
[ ] В репозитории нет .env.
[ ] В репозитории нет DeepSeek API key.
[ ] В репозитории нет личных фото/видео.
[ ] README объясняет идею за 30 секунд.
[ ] QUICK_START можно выполнить последовательно.
[ ] Есть предупреждение: один HDD не backup.
[ ] Есть предупреждение: не открывать сервисы напрямую в интернет.
[ ] Есть Jetson Nano limitations.
[ ] Есть hardware compatibility matrix.
[ ] Есть ROADMAP.
[ ] Есть LICENSE.
[ ] Есть SECURITY.md.
[ ] Есть Issue templates.
[ ] Есть release v0.1.0-alpha.
[ ] Есть хотя бы одна архитектурная схема.
[ ] Есть фото или план фото стенда.

[ ] There is no .env in the repository.
[ ] There is no DeepSeek API key in the repository.
[ ] There are no personal photos/videos in the repository.
[ ] The README explains the idea in 30 seconds.
[ ] QUICK_START can be followed step by step.
[ ] There is a warning: one HDD is not a backup.
[ ] There is a warning: do not expose the services directly to the internet.
[ ] The Jetson Nano limitations are documented.
[ ] There is a hardware compatibility matrix.
[ ] There is a ROADMAP.
[ ] There is a LICENSE.
[ ] There is a SECURITY.md.
[ ] There are issue templates.
[ ] There is a v0.1.0-alpha release.
[ ] There is at least one architecture diagram.
[ ] There is a photo of the rig, or a plan to take one.
```

---

## 23. Итоговая стратегия / The overall strategy

🇷🇺 Проект следует продвигать не как техническую сборку контейнеров, а как общественно и practically полезную методику:

🇬🇧 The project should be promoted not as a technical bundle of containers, but as a socially and practically useful method:

```text
Оживить старое железо.
Сохранить семейные данные локально.
Снизить зависимость от коммерческих облаков.
Сделать понятный open-source blueprint для повторения.

Revive old hardware.
Keep family data local.
Reduce dependence on commercial clouds.
Produce a clear open-source blueprint others can follow.
```

🇷🇺 Технический фокус первого публичного релиза:

🇬🇧 The technical focus of the first public release:

```text
Jetson Nano + USB HDD + Nextcloud + Immich + Samba/SFTP + restic + DeepSeek diagnostics.
```

🇷🇺 Продуктовый фокус: / 🇬🇧 The product focus:

```text
Private family cloud from old hardware.
```

🇷🇺 GitHub-фокус: / 🇬🇧 The GitHub focus:

```text
Documentation-first, reproducible, safe, extensible, community-driven.
```
