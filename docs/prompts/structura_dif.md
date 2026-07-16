Ты работаешь как senior open-source maintainer, repository architect, DevOps reviewer и technical writer.

Проект: `NAS_Jetson_Nano` / `NAS_Jetson_Nano`

Идея проекта:

```text
Old Hardware Must Live — домашняя облачная платформа на Jetson Nano первого поколения / Jetson Nano 4GB, старом HDD/SSD, Docker Compose, Nextcloud и Android-клиенте.
```

Главная задача:

Привести структуру папок и файлов проекта к максимально хорошим практикам open-source / DevOps / self-hosted / Docker Compose проекта.

Важно:

* ничего не удалять;
* не терять историю файлов;
* не ломать существующий проект;
* не перемещать файлы без понятной причины;
* использовать `git mv`, если файл перемещается;
* все “лишние”, устаревшие или непонятные файлы не удалять, а переносить в правильную архивную структуру;
* после реорганизации обновить ссылки в README и документации;
* сформировать подробный отчёт, что и куда перемещено.

---

# 0. Режим безопасности

Работай аккуратно.

Запрещено:

* удалять файлы;
* выполнять `rm -rf`;
* форматировать диски;
* менять системные файлы;
* запускать destructive-команды;
* удалять историю;
* переписывать содержимое конфигов без необходимости;
* удалять “непонятные” файлы только потому, что они выглядят лишними.

Если файл кажется лишним — перемести его в архивную зону, а не удаляй.

Используй такие зоны:

```text
archive/legacy/          — устаревшие или неиспользуемые файлы проекта
docs/archive/            — старые версии документации
artifacts/reports/       — результаты аудитов, тестов, метрик
docs/drafts/             — черновики статей и материалов
docs/prompts/            — промты для Codex/Claude/ChatGPT
tmp/                     — временные локальные файлы, должен быть в .gitignore
```

---

# 1. Сначала выполни read-only аудит структуры

Ничего не меняй на первом этапе.

Выполни:

```bash
pwd
git status --short
find . -maxdepth 4 -type f | sort
find . -maxdepth 4 -type d | sort
```

Если доступна команда `tree`, используй:

```bash
tree -a -L 4
```

Проанализируй:

1. Какие файлы лежат в корне проекта.
2. Есть ли лишний мусор в корне.
3. Есть ли дублирующие документы.
4. Есть ли неструктурированные промты.
5. Есть ли отчёты аудитов в неправильных местах.
6. Есть ли временные файлы.
7. Есть ли скриншоты/картинки в корне.
8. Есть ли конфиги рядом с документацией.
9. Есть ли scripts/tests/docs/config/assets.
10. Есть ли `.github/`, workflows, issue templates.
11. Есть ли Docker Compose файлы.
12. Есть ли Android-материалы.
13. Есть ли quality/test-документация.
14. Есть ли файлы, которые нельзя перемещать.

Сформируй таблицу:

| Текущий файл/папка | Назначение | Проблема | Предлагаемое место |
| ------------------ | ---------- | -------- | ------------------ |

После аудита покажи план миграции и только потом переходи к изменениям.

---

# 2. Целевая структура проекта

Приведи проект к такой логике структуры.

Целевая структура верхнего уровня:

```text
NAS_Jetson_Nano/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── .gitignore
├── .editorconfig
├── .env.example
├── docker-compose.yml
├── compose/
├── services/
├── config/
├── scripts/
├── tests/
├── docs/
├── assets/
├── hardware/
├── tools/
├── artifacts/
├── archive/
└── .github/
```

Не обязательно создавать все папки, если они не нужны. Но если в проекте уже есть соответствующие файлы — разложи их по этой логике.

---

# 3. Правила для корня проекта

В корне должны остаться только действительно важные файлы:

```text
README.md
LICENSE
CHANGELOG.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md
.gitignore
.editorconfig
.env.example
docker-compose.yml
compose.yaml, если это основной compose-файл
CLAUDE.md, если используется как главный файл инструкций агента
AGENTS.md, если используется
```

В корне не должны лежать:

* старые отчёты;
* черновики промтов;
* скриншоты;
* временные файлы;
* результаты тестов;
* старые версии README;
* случайные `.md` без роли;
* логи;
* дампы;
* архивы;
* изображения без структуры;
* персональные заметки.

Такие файлы нужно переместить в правильные папки.

---

# 4. Правила для документации

Папка `docs/` должна быть основной зоной документации.

Рекомендуемая структура:

```text
docs/
├── 00_overview.md
├── 01_architecture.md
├── 02_hardware.md
├── 03_installation.md
├── 04_storage.md
├── 05_networking.md
├── 06_nextcloud.md
├── 07_android_client.md
├── 08_backup_restore.md
├── 09_security.md
├── 10_monitoring.md
├── 11_troubleshooting.md
├── 12_roadmap.md
├── quality/
├── prompts/
├── drafts/
├── articles/
└── archive/
```

Если уже есть документы с похожим смыслом — не создавать дубли, а аккуратно переименовать или переместить существующие.

Для важных документов используй понятные имена:

```text
docs/quality/TEST_PLAN.md
docs/quality/TEST_MATRIX.md
docs/quality/RELIABILITY_REPORT.md
docs/quality/RELEASE_ACCEPTANCE_CHECKLIST.md
docs/prompts/CODEX_RELIABILITY_VALIDATION_PROMPT.md
docs/prompts/CODEX_REPO_STRUCTURE_REFACTOR_PROMPT.md
docs/articles/HACKADAY_PROJECT_DRAFT.md
docs/articles/HABR_ARTICLE_DRAFT.md
```

Старые версии документов переносить в:

```text
docs/archive/
```

---

# 5. Правила для Docker Compose

Если compose-файлов несколько, разложить так:

```text
docker-compose.yml              — основной production/MVP compose
compose/
├── docker-compose.dev.yml
├── docker-compose.monitoring.yml
├── docker-compose.android-tools.yml
├── docker-compose.override.example.yml
└── README.md
```

Если в проекте уже есть compose-файлы с другим назначением, не переименовывай вслепую. Сначала определи их роль.

Обязательно:

1. Обновить ссылки в README.
2. Обновить команды запуска.
3. Проверить:

```bash
docker compose config
```

Если compose-файлы требуют разные `-f`, добавить примеры команд в `compose/README.md`.

---

# 6. Правила для сервисов

Если есть собственные сервисы, микросервисы или кастомные Dockerfile, использовать структуру:

```text
services/
├── nextcloud/
├── backup-api/
├── llm-gateway/
├── monitoring/
└── README.md
```

Внутри сервиса:

```text
services/service-name/
├── Dockerfile
├── README.md
├── src/
├── config/
└── tests/
```

Если сервисов нет — не создавать пустую структуру ради красоты.

---

# 7. Правила для конфигов

Папка `config/` должна хранить только примеры и шаблоны конфигов, которые можно безопасно публиковать.

```text
config/
├── samba/
│   └── smb.conf.example
├── nextcloud/
│   └── config.example.php
├── nginx/
│   └── site.conf.example
├── systemd/
│   └── nas-jetson-nano.service.example
├── smartd/
│   └── smartd.conf.example
└── README.md
```

Правила:

* реальные секреты не хранить;
* реальные `.env` не коммитить;
* использовать `.env.example`;
* пароли заменить на placeholders;
* приватные ключи не хранить.

---

# 8. Правила для скриптов

Папка `scripts/` — для пользовательских и административных скриптов.

Рекомендуемая структура:

```text
scripts/
├── install/
├── maintenance/
├── backup/
├── android/
├── diagnostics/
└── README.md
```

Примеры:

```text
scripts/install/install_base_packages.sh
scripts/diagnostics/healthcheck.sh
scripts/diagnostics/check_hdd.sh
scripts/backup/backup_to_usb.sh
scripts/android/check_adb.sh
```

Все `.sh` должны иметь:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

После перемещения скриптов проверить:

```bash
find scripts tests -name "*.sh" -print0 | xargs -0 -r bash -n
```

Если доступен ShellCheck:

```bash
find scripts tests -name "*.sh" -print0 | xargs -0 -r shellcheck
```

---

# 9. Правила для тестов

Папка `tests/` — для автоматизированных и полуавтоматических проверок.

```text
tests/
├── network/
├── service/
├── storage/
├── backup/
├── android/
├── load/
└── README.md
```

Результаты тестов не хранить рядом с тестами. Результаты складывать в:

```text
artifacts/reports/
```

или:

```text
docs/quality/results/
```

Если отчёт нужен для документации — `docs/quality/results/`.
Если это машинный output или временный результат — `artifacts/reports/`.

---

# 10. Правила для assets

Папка `assets/` — для изображений, схем, фото и медиа.

```text
assets/
├── photos/
├── diagrams/
├── screenshots/
├── social-preview/
└── README.md
```

Требования:

* фото железа — `assets/photos/`;
* схемы архитектуры — `assets/diagrams/`;
* скриншоты интерфейсов — `assets/screenshots/`;
* social preview для GitHub/Hackaday — `assets/social-preview/`;
* не публиковать скриншоты с персональными данными;
* при необходимости замазывать чувствительные данные.

---

# 11. Правила для hardware

Папка `hardware/` — для материалов по железу.

```text
hardware/
├── bill_of_materials.md
├── jetson_nano.md
├── storage_options.md
├── power.md
├── cooling.md
└── photos.md
```

Туда переносить материалы, связанные с:

* Jetson Nano;
* HDD/SSD;
* SATA/USB адаптерами;
* питанием;
* охлаждением;
* корпусом;
* измерениями температуры.

---

# 12. Правила для tools

Папка `tools/` — для вспомогательных утилит разработчика.

```text
tools/
├── github_metrics/
├── markdown/
├── release/
└── README.md
```

Сюда помещать:

* скрипты сбора GitHub Traffic;
* генераторы отчётов;
* вспомогательные Python-утилиты;
* release helper scripts.

---

# 13. Правила для artifacts и archive

## 13.1. artifacts/

Использовать для результатов работы, отчётов, логов, сгенерированных файлов:

```text
artifacts/
├── reports/
├── logs/
├── exports/
└── README.md
```

Примеры:

```text
artifacts/reports/audit_report_2026-06-25.md
artifacts/reports/github_traffic_2026-06-20.md
artifacts/logs/docker_compose_check_2026-06-25.log
```

Если файлы большие, бинарные или временные — не коммитить, а добавить в `.gitignore`.

## 13.2. archive/

Использовать для устаревших, но потенциально полезных файлов:

```text
archive/
├── legacy/
├── old-docs/
├── experiments/
└── README.md
```

Правила:

* не удалять старые файлы;
* переносить через `git mv`;
* в `archive/README.md` объяснить, что это неактуальные материалы;
* если файл устарел, но может быть полезен исторически — `archive/legacy/`.

---

# 14. Правила для .github

Проверить и привести к структуре:

```text
.github/
├── workflows/
│   ├── quality-checks.yml
│   ├── security-scan.yml
│   └── validate-compose.yml
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   ├── documentation_task.md
│   ├── hardware_test_report.md
│   └── feature_request.md
└── pull_request_template.md
```

Не ломать существующие workflow.

После изменений проверить YAML.

---

# 15. Обязательная карта перемещений

Создай файл:

```text
docs/REPOSITORY_STRUCTURE.md
```

В нём опиши:

1. текущую целевую структуру;
2. назначение каждой папки;
3. правила, куда добавлять новые файлы;
4. куда складывать отчёты;
5. куда складывать старые файлы;
6. куда складывать промты;
7. куда складывать статьи;
8. куда складывать фото и схемы.

Создай файл:

```text
docs/quality/STRUCTURE_REFACTOR_REPORT.md
```

В нём укажи:

| Старый путь | Новый путь | Причина |
| ----------- | ---------- | ------- |

---

# 16. Порядок выполнения изменений

Работай в таком порядке:

1. Read-only аудит.
2. План целевой структуры.
3. Показать таблицу перемещений.
4. Создать недостающие папки.
5. Перемещать файлы только через `git mv`, если файл уже отслеживается Git.
6. Если файл не отслеживается Git — использовать `mv`.
7. Обновить ссылки в README и docs.
8. Обновить команды в документации.
9. Обновить `.gitignore`.
10. Запустить безопасные проверки.
11. Сформировать отчёт.

---

# 17. Проверки после реорганизации

Выполни:

```bash
git status --short
find . -maxdepth 4 -type d | sort
find . -maxdepth 4 -type f | sort
```

Проверить shell:

```bash
find scripts tests -name "*.sh" -print0 | xargs -0 -r bash -n
```

Проверить compose:

```bash
docker compose config
```

Если есть несколько compose-файлов, проверить основной.

Проверить ссылки в Markdown, если есть инструмент. Если нет — хотя бы grep по старым путям, которые были перемещены.

---

# 18. Что не делать

Не делай:

* не создавай слишком сложную enterprise-структуру без необходимости;
* не перемещай файлы, если от этого станет менее понятно;
* не создавай пустые папки без README или смысла;
* не удаляй файлы;
* не переименовывай главный README;
* не прячь важные файлы глубоко;
* не ломай GitHub Actions;
* не ломай Docker Compose команды;
* не меняй смысл проекта;
* не превращай проект в монорепозиторий без причины.

---

# 19. Итоговый вывод

В конце выведи:

1. Что было найдено.
2. Какие проблемы структуры были обнаружены.
3. Какая целевая структура применена.
4. Какие папки созданы.
5. Какие файлы перемещены.
6. Какие файлы остались на месте и почему.
7. Какие ссылки обновлены.
8. Какие проверки прошли.
9. Какие проверки не удалось выполнить.
10. Какие ручные действия нужны.

Также дай команды для commit:

```bash
git status
git add .
git commit -m "Refactor repository structure according to open-source best practices"
git push
```

Начинай с read-only аудита структуры проекта.
