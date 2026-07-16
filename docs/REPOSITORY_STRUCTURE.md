# Repository Structure — NAS_Jetson_Nano / Структура репозитория

> 🇬🇧 Where things live and why. Follow this guide when adding new files.
> 🇷🇺 Где лежат файлы и почему. Следуй этому гайду при добавлении новых файлов.

## Top-level layout / Структура верхнего уровня

```
NAS_Jetson_Nano/
├── README.md                  — project entry point / точка входа
├── CHANGELOG.md               — version history / история версий
├── CLAUDE.md                  — Claude Code agent instructions / инструкции для агента
├── AGENTS.md                  — multi-agent operating model / модель агентов
├── CONTRIBUTING.md            — contribution guide / руководство для участников
├── SECURITY.md                — security policy / политика безопасности
├── CODE_OF_CONDUCT.md         — community norms / нормы сообщества
├── LICENSE                    — MIT
├── .gitignore / .gitattributes / .editorconfig
├── config/                    — service config templates (no secrets) / шаблоны конфигов
├── docker/                    — Docker Compose files / файлы Docker Compose
├── scripts/                   — operational scripts / операционные скрипты
├── systemd/                   — systemd units and overrides / юниты systemd
├── services/                  — custom microservice source code / исходный код микросервисов
├── tests/                     — automated test scripts / автоматические тесты
├── docs/                      — all documentation / вся документация
├── assets/                    — images, diagrams, screenshots / изображения, схемы
├── artifacts/                 — generated reports, audit outputs / отчёты, аудиты
├── archive/                   — deprecated but preserved files / устаревшее, но сохранённое
└── .github/                   — CI/CD workflows, issue templates / CI/CD, шаблоны issues
```

## Where to put new files / Куда класть новые файлы

| Type of file / Тип файла | Location / Расположение |
|---|---|
| New feature documentation / Документация новой функции | `docs/NN_TOPIC.md` |
| Architecture decisions / Архитектурные решения | `docs/decisions/ADR-NNN-title.md` |
| Hardware notes / Заметки о железе | `docs/hardware/` |
| Android docs / Документация Android | `docs/android/` |
| Agent prompts (Codex/Claude/ChatGPT) / Промпты агентов | `docs/prompts/` |
| Article drafts / Черновики статей (Habr, Hackaday) | `docs/articles/` |
| Quality / test documentation / Тестовая документация | `docs/quality/` |
| Test results / baseline reports / Результаты тестов | `docs/quality/results/` |
| External reference links / Ссылки на внешние ресурсы | `docs/references/` |
| Test scripts / Тестовые скрипты | `tests/<category>/` |
| Operational scripts / Операционные скрипты | `scripts/<category>/` |
| Service configs (templates only) / Конфиги (только шаблоны) | `config/<service>/` |
| Docker Compose files / Файлы Docker Compose | `docker/compose/` |
| VPS-specific compose / Compose для VPS | `docker/vps/` |
| Hardware photos / Фото железа | `assets/photos/` |
| Architecture diagrams / Схемы архитектуры | `assets/diagrams/` |
| UI screenshots / Скриншоты UI | `assets/screenshots/` |
| Audit reports, generated JSON / Аудит-отчёты | `artifacts/reports/` |
| Old/superseded files / Устаревшие файлы | `archive/legacy/` |
| Old documentation versions / Старые версии документов | `docs/archive/` (create if needed) |

## Key rules / Ключевые правила

1. **No secrets in git** / **Без секретов в git** — use `config/.env.example` with placeholders; real `.env` is gitignored.
2. **No moving `docker/`, `systemd/`, `scripts/`** / **Не перемещать эти папки** — many references in deploy scripts and systemd units / на них ссылаются юниты systemd и deploy-скрипты.
3. **Agent prompts** go in `docs/prompts/` / **Промпты агентов** — только в `docs/prompts/`, не в корне репозитория.
4. **Audit reports** go in `artifacts/reports/` (machine output) or `docs/quality/results/` (human-readable baselines).
5. **Old files** go to `archive/legacy/` via `git mv`, never deleted / Устаревшие файлы — в `archive/legacy/` через `git mv`, не удалять.
6. **VPN configs** (`wg-*.conf`, `wg-*.png`) are gitignored — contain private keys / содержат приватные ключи.
7. **Reference HTML docs cache** (`docs/references/external_docs/`) is gitignored — too large / слишком большой размер.

## Docker Compose commands / Команды Docker Compose

```bash
# Stage 1 (base infra / базовая инфраструктура)
docker compose -f docker/compose/docker-compose.stage1.yml --env-file config/.env up -d

# Nextcloud
docker compose -f docker/compose/docker-compose.nextcloud.yml --env-file config/.env up -d

# Immich
docker compose -f docker/compose/docker-compose.immich.yml --env-file config/.env up -d

# Monitoring / Мониторинг
docker compose -f docker/compose/docker-compose.monitoring.yml --env-file config/.env up -d

# VPS (run from VPS / запускать с VPS)
docker compose -f docker/vps/docker-compose.yml --env-file config/.env up -d
```
