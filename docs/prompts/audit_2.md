# Prompt for Codex / Claude Agent: Project Audit for Article Planning

Ты работаешь как технический аудитор, архитектор self-hosted решений, DevOps-reviewer, technical writer и редактор инженерных статей.

Проект: `NAS_Jetson_Nano` / `NAS_Jetson_Nano`

Рабочая идея проекта:

```text
Old Hardware Must Live — домашняя облачная платформа на базе старого железа:
Jetson Nano / старый HDD или SSD / Docker Compose / Nextcloud / Android-клиент / AI-assisted automation.
```

Контекст:

Проект значительно изменился. Архитектура могла уйти вперёд по сравнению с предыдущими audit report.
Старые отчёты считать историческими, но не считать их абсолютной правдой.
Текущий репозиторий является главным источником истины.

Главная цель аудита:

Подготовить такой отчёт, по которому можно будет написать сильную техническую статью для:

* Хабр;
* Hackaday.io;
* DEV.to;
* GitHub README / project page.

Аудит должен ответить не только на вопрос “что есть в проекте”, но и на вопрос:

```text
Какую инженерную историю можно честно и интересно рассказать на основе текущего состояния проекта?
```

---

# 0. Режим работы

Работай в режиме read-only.

На этом этапе:

* не меняй архитектуру;
* не переписывай README;
* не перемещай файлы;
* не удаляй файлы;
* не исправляй код;
* не запускай destructive-команды;
* не форматируй диски;
* не меняй Docker Compose;
* не меняй Android-устройство;
* не устанавливай приложения;
* не выполняй `adb install`, `adb uninstall`, `adb shell pm clear`, `rm -rf`, `mkfs`, `fdisk`, `parted`, `dd`.

Разрешено:

* читать файлы;
* анализировать структуру;
* запускать безопасные read-only команды;
* формировать отчёты;
* создавать только новые audit/report файлы в `docs/articles/` или `docs/audits/`, если это принято в проекте.

Если не уверен, можно ли выполнять команду — не выполняй, а укажи её как рекомендуемую ручную проверку.

---

# 1. Определи текущее состояние проекта

Сначала выполни read-only обзор:

```bash
pwd
git status --short
find . -maxdepth 4 -type d | sort
find . -maxdepth 4 -type f | sort
```

Если доступно:

```bash
tree -a -L 4
```

Найди и изучи:

* `README.md`;
* `docs/`;
* `docs/quality/`;
* `docs/articles/`;
* `docs/prompts/`;
* `scripts/`;
* `tests/`;
* `config/`;
* `compose/`;
* `services/`;
* `hardware/`;
* `assets/`;
* `.github/workflows/`;
* `docker-compose.yml`;
* `compose.yaml`;
* все `docker-compose*.yml`;
* все `Dockerfile*`;
* `CLAUDE.md`;
* `AGENTS.md`;
* `.env.example`;
* `CHANGELOG.md`;
* `SECURITY.md`;
* `CONTRIBUTING.md`;
* release notes;
* audit reports;
* quality reports;
* Android-related docs/scripts;
* Hackaday/Habr article drafts, если они есть.

---

# 2. Сформируй “снимок архитектуры”

Определи текущую архитектуру проекта.

Нужно явно описать:

## 2.1. Hardware layer

* Jetson Nano или другое основное устройство;
* HDD/SSD;
* SATA/USB/M.2 адаптеры;
* питание;
* сеть;
* охлаждение;
* Android-телефон;
* дополнительные устройства, если есть.

## 2.2. OS / platform layer

* ОС;
* Docker / Docker Compose;
* systemd, cron, scripts;
* файловая система;
* mount points;
* storage layout.

## 2.3. Service layer

Определи, какие сервисы реально есть в проекте:

* Nextcloud;
* database;
* Redis;
* Immich;
* Samba;
* monitoring;
* backup;
* reverse proxy;
* VPN / HTTPS / remote access;
* LLM gateway / AI automation, если есть;
* Android tools;
* другие сервисы.

Для каждого сервиса составь таблицу:

| Сервис | Назначение | Где описан | Где запускается | Статус | Риски |
| ------ | ---------- | ---------- | --------------- | ------ | ----- |

## 2.4. Network layer

Опиши:

* локальная сеть;
* какие порты используются;
* HTTP/HTTPS;
* VPN или reverse proxy;
* DNS / local domain;
* доступ с Android;
* доступ с Windows/Linux;
* какие сетевые решения устарели или были отменены.

## 2.5. Android layer

Отдельно проанализируй Android-контур:

* зачем Android нужен проекту;
* какие приложения используются;
* что настраивает Codex/агент;
* используется ли ADB;
* есть ли Nextcloud client;
* есть ли Immich;
* есть ли DAVx5;
* есть ли Syncthing;
* есть ли VPN-клиент;
* есть ли инструкция по безопасности Android;
* есть ли rollback/cleanup;
* есть ли риск утечки личных данных.

## 2.6. AI-agent automation layer

Определи, как в проекте используются AI-агенты:

* Codex;
* Claude;
* ChatGPT;
* локальные агенты;
* промты;
* audit reports;
* автоматизация настройки;
* генерация документации;
* настройка Android;
* проверка качества;
* ограничения и риски AI-agent подхода.

---

# 3. Найди архитектурные изменения

Если в проекте есть старые документы, changelog, audit reports, ADR или заметки, сравни их с текущей структурой.

Определи:

| Было раньше | Стало сейчас | Почему изменилось | Важно ли для статьи |
| ----------- | ------------ | ----------------- | ------------------- |

Особенно проверь:

* изменилась ли роль Jetson Nano;
* изменился ли подход к HDD/SSD;
* появился ли SSD под систему/Docker;
* изменился ли состав Docker-сервисов;
* появился ли Android-контур;
* изменилась ли стратегия remote access;
* отказались ли от VPN/HTTPS решения;
* появились ли quality tests;
* появились ли monitoring / backup / restore checks;
* изменилась ли структура репозитория;
* появились ли Hackaday/Habr материалы.

---

# 4. Проверь готовность проекта к статье

Оцени проект именно как материал для публичной статьи.

Поставь оценки от 1 до 10:

| Категория                    | Оценка | Комментарий |
| ---------------------------- | -----: | ----------- |
| Ясность идеи                 |        |             |
| Интересность для Хабра       |        |             |
| Интересность для Hackaday.io |        |             |
| Интересность для DEV.to      |        |             |
| Архитектурная зрелость       |        |             |
| Воспроизводимость            |        |             |
| Документация                 |        |             |
| Фото/визуальные материалы    |        |             |
| Наличие схем                 |        |             |
| Наличие результатов тестов   |        |             |
| Безопасность                 |        |             |
| Android-контур               |        |             |
| AI-agent automation          |        |             |
| Честность ограничений        |        |             |
| Готовность к публикации      |        |             |

---

# 5. Определи главную историю проекта

Нужно предложить 3–5 возможных “сюжетов” статьи.

Примеры направлений:

## Вариант A — Hardware / reuse story

```text
Old Hardware Must Live: как я превращаю Jetson Nano и старый HDD в домашнее облако
```

## Вариант B — Self-hosted / cloud story

```text
Домашнее облако вместо платных сервисов: Jetson Nano, Docker, Nextcloud и Android-клиент
```

## Вариант C — AI-assisted engineering story

```text
Как AI-агенты помогают собрать и проверить домашнее облако на старом железе
```

## Вариант D — Reliability story

```text
Не просто поднять Nextcloud: как я проверял сеть, диски, backup, Android и устойчивость проекта
```

## Вариант E — Hackaday-style hardware log

```text
Building a home cloud from forgotten hardware: Jetson Nano, old storage and Android automation
```

Для каждого сюжета укажи:

| Сюжет | Для какой площадки | Сильная сторона | Риск | Что нужно доказать |
| ----- | ------------------ | --------------- | ---- | ------------------ |

---

# 6. Определи, что уже можно публиковать

Составь таблицу:

| Тема | Можно публиковать сейчас? | Доказательства в проекте | Чего не хватает |
| ---- | ------------------------- | ------------------------ | --------------- |

Темы:

* идея Old Hardware Must Live;
* выбор Jetson Nano;
* HDD/SSD storage;
* Docker Compose архитектура;
* Nextcloud;
* Android-клиент;
* настройка Android через Codex/агента;
* backup/restore;
* сетевые проверки;
* мониторинг;
* безопасность;
* проблемы и откаты;
* ограничения старого железа;
* roadmap.

---

# 7. Найди слабые места перед статьёй

Определи, что может вызвать критику читателей.

Проверь:

* нет ли голословных утверждений;
* нет ли обещания production-grade;
* проверен ли backup restore;
* не игнорируются ли риски старого HDD;
* есть ли HTTPS/VPN или честное объяснение, почему нет;
* безопасен ли Android-контур;
* нет ли персональных данных в скриншотах;
* нет ли секретов в репозитории;
* есть ли схемы;
* есть ли реальные фото;
* есть ли понятная инструкция;
* есть ли reproducibility;
* не выглядит ли проект как “набор промтов”, а не инженерное решение.

Составь таблицу:

| Риск критики | Почему возникнет | Как закрыть до публикации |
| ------------ | ---------------- | ------------------------- |

---

# 8. Какие доказательства нужны для статьи

Сформируй список evidence-пакета.

Нужно определить, какие материалы стоит собрать:

## 8.1. Фото

* Jetson Nano;
* HDD/SSD;
* питание;
* подключение к сети;
* общий стенд;
* Android-телефон;
* возможно, корпус/охлаждение.

## 8.2. Скриншоты

* GitHub README;
* Docker Compose / `docker ps`;
* Nextcloud web UI;
* Android Nextcloud client;
* monitoring dashboard;
* backup/restore result;
* SMART status без serial;
* network test result;
* GitHub traffic;
* Hackaday project page draft.

## 8.3. Командные выводы

* `docker compose ps`;
* `docker compose config`;
* `smartctl` summary;
* `lsblk`;
* `df -h`;
* `curl status.php`;
* `ping/mtr`;
* `iperf3`;
* `backup restore diff`;
* `adb readonly check`.

## 8.4. Таблицы

* hardware bill of materials;
* architecture components;
* risks and mitigations;
* test matrix;
* roadmap.

Сформируй итоговую таблицу:

| Evidence | Где взять | Нужно ли обезличить | Для какой части статьи |
| -------- | --------- | ------------------- | ---------------------- |

---

# 9. Подготовь план статьи

На основе текущего проекта сформируй 2 варианта плана статьи:

## 9.1. План для Хабра

Структура:

```markdown
# Рабочее название

## 1. Зачем я это делаю
## 2. Исходное железо
## 3. Как изменилась архитектура проекта
## 4. Серверная часть
## 5. Хранилище: HDD/SSD, риски и проверки
## 6. Docker Compose и сервисы
## 7. Android как полноценный клиент
## 8. Как Codex/AI-агент помогает в проекте
## 9. Проверка устойчивости: сеть, backup, мониторинг
## 10. Что получилось
## 11. Что не получилось / что пришлось изменить
## 12. Безопасность и честные ограничения
## 13. Roadmap
## 14. Выводы
```

Для каждого раздела укажи:

* ключевой тезис;
* какие доказательства вставить;
* какие файлы проекта использовать как источник;
* какие риски не забыть упомянуть.

## 9.2. План для Hackaday.io

Структура project page + logs:

```markdown
# Project page

## What is this?
## Why old hardware?
## Hardware
## Architecture
## Current status
## Android client
## Reliability checks
## Project logs
## GitHub repository
```

Project logs:

1. `Why old hardware must live`
2. `Hardware baseline: Jetson Nano and storage`
3. `The architecture changed: from NAS to home cloud ecosystem`
4. `Docker, Nextcloud and service layout`
5. `Android phone as a real client`
6. `AI agents in the loop`
7. `Reliability checks: network, storage, backup`
8. `What failed and what I changed`
9. `Roadmap`

Для каждого лога укажи:

* короткое описание;
* какие фото нужны;
* какие ссылки на GitHub добавить.

---

# 10. Подготовь короткие тезисы для статьи

Сформируй:

## 10.1. Один главный тезис

Например:

```text
Это уже не просто NAS на старом железе, а маленькая домашняя облачная экосистема, где сервер, хранилище, Android-клиент и AI-агенты работают как единый инженерный проект.
```

## 10.2. 5 сильных тезисов

## 10.3. 5 честных ограничений

## 10.4. 5 вещей, которые стоит показать скриншотами

## 10.5. 5 вещей, которые лучше не обещать

---

# 11. Сформируй итоговый audit report

Создай файл:

```text
docs/articles/ARTICLE_AUDIT_REPORT.md
```

Если `docs/articles/` нет — создай.

Структура файла:

```markdown
# Article Audit Report: NAS_Jetson_Nano

## 1. Executive summary
## 2. Current project state
## 3. Current architecture snapshot
## 4. Architecture changes
## 5. Hardware layer
## 6. Service layer
## 7. Network layer
## 8. Storage layer
## 9. Android client layer
## 10. AI-agent automation layer
## 11. Reliability and validation layer
## 12. What is already article-ready
## 13. What is not ready yet
## 14. Risks before publication
## 15. Evidence package checklist
## 16. Habr article plan
## 17. Hackaday.io project plan
## 18. Recommended article angle
## 19. Priority fixes before publication
## 20. Final recommendation
```

---

# 12. Итоговый вывод в чат

После завершения выведи:

1. Краткое резюме текущего состояния проекта.
2. Главные архитектурные изменения.
3. Самый сильный сюжет для статьи.
4. Что уже можно публиковать.
5. Что нужно доделать до публикации.
6. Какие evidence нужно собрать.
7. Где создан итоговый отчёт.
8. Команды для commit:

```bash
git status
git add docs/articles/ARTICLE_AUDIT_REPORT.md
git commit -m "Add article-oriented project audit report"
git push
```

---

# 13. Стиль отчёта

Стиль:

* инженерный;
* честный;
* без маркетинговой воды;
* без завышенных обещаний;
* с акцентом на проверяемость;
* с фиксацией ограничений;
* с явным разделением “готово” и “не готово”.

Не придумывай несуществующие результаты.
Если тест не найден — так и напиши.
Если фото нет — так и напиши.
Если Android-контур не документирован — так и напиши.
Если архитектура непонятна — укажи, какие файлы надо уточнить.

Начинай с read-only аудита текущего репозитория.

---

---

# Prompt for Codex / Claude Agent: Project Audit for Article Planning (English)

You are working as a technical auditor, self-hosted-solutions architect, DevOps reviewer, technical writer, and engineering-article editor.

Project: `NAS_Jetson_Nano` / `NAS_Jetson_Nano`

Working idea of the project:

```text
Old Hardware Must Live — a home cloud platform built on old hardware:
Jetson Nano / an old HDD or SSD / Docker Compose / Nextcloud / an Android client / AI-assisted automation.
```

Context:

The project has changed significantly. The architecture may have moved ahead of previous audit reports.
Treat old reports as historical, not as absolute truth.
The current repository is the primary source of truth.

Main audit goal:

Prepare a report strong enough to write a solid technical article for:

* Habr;
* Hackaday.io;
* DEV.to;
* the GitHub README / project page.

The audit must answer not only "what exists in the project" but also:

```text
What engineering story can be told honestly and interestingly based on the project's current state?
```

---

# 0. Operating mode

Work in read-only mode.

At this stage:

* do not change the architecture;
* do not rewrite the README;
* do not move files;
* do not delete files;
* do not fix code;
* do not run destructive commands;
* do not format disks;
* do not change Docker Compose;
* do not touch the Android device;
* do not install apps;
* do not run `adb install`, `adb uninstall`, `adb shell pm clear`, `rm -rf`, `mkfs`, `fdisk`, `parted`, `dd`.

Allowed:

* reading files;
* analyzing the structure;
* running safe read-only commands;
* producing reports;
* creating only new audit/report files under `docs/articles/` or `docs/audits/`, if that convention is already used in the project.

If you're unsure whether a command is safe to run — don't run it; list it as a recommended manual check instead.

---

# 1. Determine the project's current state

First perform a read-only overview:

```bash
pwd
git status --short
find . -maxdepth 4 -type d | sort
find . -maxdepth 4 -type f | sort
```

If available:

```bash
tree -a -L 4
```

Find and study:

* `README.md`;
* `docs/`;
* `docs/quality/`;
* `docs/articles/`;
* `docs/prompts/`;
* `scripts/`;
* `tests/`;
* `config/`;
* `compose/`;
* `services/`;
* `hardware/`;
* `assets/`;
* `.github/workflows/`;
* `docker-compose.yml`;
* `compose.yaml`;
* every `docker-compose*.yml`;
* every `Dockerfile*`;
* `CLAUDE.md`;
* `AGENTS.md`;
* `.env.example`;
* `CHANGELOG.md`;
* `SECURITY.md`;
* `CONTRIBUTING.md`;
* release notes;
* audit reports;
* quality reports;
* Android-related docs/scripts;
* Hackaday/Habr article drafts, if any exist.

---

# 2. Build an "architecture snapshot"

Determine the project's current architecture.

You need to explicitly describe:

## 2.1. Hardware layer

* Jetson Nano or another primary device;
* HDD/SSD;
* SATA/USB/M.2 adapters;
* power supply;
* network;
* cooling;
* Android phone;
* additional devices, if any.

## 2.2. OS / platform layer

* OS;
* Docker / Docker Compose;
* systemd, cron, scripts;
* filesystem;
* mount points;
* storage layout.

## 2.3. Service layer

Determine which services actually exist in the project:

* Nextcloud;
* database;
* Redis;
* Immich;
* Samba;
* monitoring;
* backup;
* reverse proxy;
* VPN / HTTPS / remote access;
* LLM gateway / AI automation, if any;
* Android tools;
* other services.

For each service, build a table:

| Service | Purpose | Where documented | Where it runs | Status | Risks |
| ------- | ------- | ----------------- | -------------- | ------ | ----- |

## 2.4. Network layer

Describe:

* the local network;
* which ports are used;
* HTTP/HTTPS;
* VPN or reverse proxy;
* DNS / local domain;
* access from Android;
* access from Windows/Linux;
* which network solutions are obsolete or were abandoned.

## 2.5. Android layer

Separately analyze the Android layer:

* why the project needs Android;
* which apps are used;
* what the Codex/agent configures;
* whether ADB is used;
* whether a Nextcloud client exists;
* whether Immich exists;
* whether DAVx5 exists;
* whether Syncthing exists;
* whether a VPN client exists;
* whether an Android security instruction exists;
* whether rollback/cleanup exists;
* whether there is a risk of personal-data leakage.

## 2.6. AI-agent automation layer

Determine how AI agents are used in the project:

* Codex;
* Claude;
* ChatGPT;
* local agents;
* prompts;
* audit reports;
* setup automation;
* documentation generation;
* Android configuration;
* quality checks;
* limitations and risks of the AI-agent approach.

---

# 3. Find architectural changes

If the project has old documents, a changelog, audit reports, ADRs, or notes, compare them to the current structure.

Determine:

| What it was before | What it is now | Why it changed | Important for the article? |
| ------------------- | ---------------- | ----------------- | --------------------------- |

Specifically check:

* whether the Jetson Nano's role has changed;
* whether the approach to HDD/SSD has changed;
* whether an SSD for the system/Docker was added;
* whether the set of Docker services has changed;
* whether an Android layer has appeared;
* whether the remote-access strategy has changed;
* whether a VPN/HTTPS solution was abandoned;
* whether quality tests appeared;
* whether monitoring / backup / restore checks appeared;
* whether the repository structure changed;
* whether Hackaday/Habr materials appeared.

---

# 4. Assess the project's readiness for an article

Evaluate the project specifically as material for a public article.

Score from 1 to 10:

| Category                     | Score | Comment |
| ------------------------------ | -----: | ----------- |
| Clarity of the idea             |        |             |
| Interest for Habr               |        |             |
| Interest for Hackaday.io        |        |             |
| Interest for DEV.to             |        |             |
| Architectural maturity          |        |             |
| Reproducibility                 |        |             |
| Documentation                   |        |             |
| Photos/visual materials         |        |             |
| Presence of diagrams            |        |             |
| Presence of test results        |        |             |
| Security                        |        |             |
| Android layer                   |        |             |
| AI-agent automation             |        |             |
| Honesty about limitations       |        |             |
| Readiness for publication       |        |             |

---

# 5. Determine the project's main story

You need to propose 3–5 possible article "storylines".

Example directions:

## Option A — Hardware / reuse story

```text
Old Hardware Must Live: how I turn a Jetson Nano and an old HDD into a home cloud
```

## Option B — Self-hosted / cloud story

```text
A home cloud instead of paid services: Jetson Nano, Docker, Nextcloud, and an Android client
```

## Option C — AI-assisted engineering story

```text
How AI agents help build and verify a home cloud on old hardware
```

## Option D — Reliability story

```text
Not just standing up Nextcloud: how I verified network, disks, backup, Android, and the project's resilience
```

## Option E — Hackaday-style hardware log

```text
Building a home cloud from forgotten hardware: Jetson Nano, old storage and Android automation
```

For each storyline, state:

| Storyline | Target platform | Strength | Risk | What needs to be proven |
| --------- | ---------------- | -------- | ---- | ------------------------ |

---

# 6. Determine what can already be published

Build a table:

| Topic | Publishable now? | Evidence in the project | What's missing |
| ----- | ------------------- | ------------------------- | ---------------- |

Topics:

* the Old Hardware Must Live idea;
* choosing the Jetson Nano;
* HDD/SSD storage;
* the Docker Compose architecture;
* Nextcloud;
* the Android client;
* configuring Android via Codex/an agent;
* backup/restore;
* network checks;
* monitoring;
* security;
* problems and rollbacks;
* old-hardware limitations;
* roadmap.

---

# 7. Find weak points before the article

Determine what could draw reader criticism.

Check:

* whether there are unsubstantiated claims;
* whether production-grade status is promised;
* whether backup restore has been tested;
* whether old-HDD risks are being ignored;
* whether HTTPS/VPN exists, or there's an honest explanation of why not;
* whether the Android layer is secure;
* whether there's personal data in screenshots;
* whether there are secrets in the repository;
* whether diagrams exist;
* whether there are real photos;
* whether there's a clear instruction;
* whether reproducibility exists;
* whether the project looks like "a bunch of prompts" rather than an engineering solution.

Build a table:

| Criticism risk | Why it will arise | How to close it before publication |
| ---------------- | -------------------- | -------------------------------------- |

---

# 8. What evidence is needed for the article

Build an evidence-package list.

Determine what materials are worth collecting:

## 8.1. Photos

* Jetson Nano;
* HDD/SSD;
* power supply;
* network connection;
* the overall setup;
* the Android phone;
* possibly the case/cooling.

## 8.2. Screenshots

* GitHub README;
* Docker Compose / `docker ps`;
* Nextcloud web UI;
* the Android Nextcloud client;
* the monitoring dashboard;
* backup/restore result;
* SMART status without the serial number;
* network test result;
* GitHub traffic;
* a Hackaday project page draft.

## 8.3. Command output

* `docker compose ps`;
* `docker compose config`;
* `smartctl` summary;
* `lsblk`;
* `df -h`;
* `curl status.php`;
* `ping/mtr`;
* `iperf3`;
* `backup restore diff`;
* `adb readonly check`.

## 8.4. Tables

* hardware bill of materials;
* architecture components;
* risks and mitigations;
* test matrix;
* roadmap.

Build the final table:

| Evidence | Where to get it | Needs anonymizing? | For which part of the article |
| -------- | ----------------- | --------------------- | -------------------------------- |

---

# 9. Prepare an article plan

Based on the current project, build 2 versions of an article plan.

## 9.1. Plan for Habr

Structure:

```markdown
# Working title

## 1. Why I'm doing this
## 2. The starting hardware
## 3. How the project's architecture changed
## 4. The server side
## 5. Storage: HDD/SSD, risks and checks
## 6. Docker Compose and services
## 7. Android as a full-fledged client
## 8. How Codex/an AI agent helps with the project
## 9. Resilience checks: network, backup, monitoring
## 10. What worked out
## 11. What didn't work out / what had to change
## 12. Security and honest limitations
## 13. Roadmap
## 14. Conclusions
```

For each section, state:

* the key thesis;
* which evidence to insert;
* which project files to use as a source;
* which risks not to forget to mention.

## 9.2. Plan for Hackaday.io

Project page + logs structure:

```markdown
# Project page

## What is this?
## Why old hardware?
## Hardware
## Architecture
## Current status
## Android client
## Reliability checks
## Project logs
## GitHub repository
```

Project logs:

1. `Why old hardware must live`
2. `Hardware baseline: Jetson Nano and storage`
3. `The architecture changed: from NAS to home cloud ecosystem`
4. `Docker, Nextcloud and service layout`
5. `Android phone as a real client`
6. `AI agents in the loop`
7. `Reliability checks: network, storage, backup`
8. `What failed and what I changed`
9. `Roadmap`

For each log, state:

* a short description;
* which photos are needed;
* which GitHub links to add.

---

# 10. Prepare short theses for the article

Build:

## 10.1. One main thesis

For example:

```text
This is no longer just a NAS on old hardware, but a small home cloud ecosystem where the server, storage, Android client, and AI agents work as a single engineering project.
```

## 10.2. 5 strong theses

## 10.3. 5 honest limitations

## 10.4. 5 things worth showing with screenshots

## 10.5. 5 things better not to promise

---

# 11. Produce the final audit report

Create the file:

```text
docs/articles/ARTICLE_AUDIT_REPORT.md
```

If `docs/articles/` doesn't exist — create it.

File structure:

```markdown
# Article Audit Report: NAS_Jetson_Nano

## 1. Executive summary
## 2. Current project state
## 3. Current architecture snapshot
## 4. Architecture changes
## 5. Hardware layer
## 6. Service layer
## 7. Network layer
## 8. Storage layer
## 9. Android client layer
## 10. AI-agent automation layer
## 11. Reliability and validation layer
## 12. What is already article-ready
## 13. What is not ready yet
## 14. Risks before publication
## 15. Evidence package checklist
## 16. Habr article plan
## 17. Hackaday.io project plan
## 18. Recommended article angle
## 19. Priority fixes before publication
## 20. Final recommendation
```

---

# 12. Final output to chat

After finishing, output:

1. A brief summary of the project's current state.
2. The main architectural changes.
3. The strongest storyline for the article.
4. What can already be published.
5. What needs finishing before publication.
6. What evidence needs to be collected.
7. Where the final report was created.
8. Commands for committing:

```bash
git status
git add docs/articles/ARTICLE_AUDIT_REPORT.md
git commit -m "Add article-oriented project audit report"
git push
```

---

# 13. Report style

Style:

* engineering-grade;
* honest;
* no marketing fluff;
* no inflated promises;
* focused on verifiability;
* with limitations explicitly recorded;
* with a clear split between "done" and "not done".

Do not invent results that don't exist.
If a test wasn't found — say so.
If there's no photo — say so.
If the Android layer isn't documented — say so.
If the architecture is unclear — state which files need clarifying.

Start with a read-only audit of the current repository.
