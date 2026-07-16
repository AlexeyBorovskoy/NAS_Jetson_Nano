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
