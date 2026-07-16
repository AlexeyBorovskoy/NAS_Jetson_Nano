# Project Plans / Планы проекта

## 1. Назначение / Purpose

🇷🇺 Эта папка содержит стратегические планы развития и публичной упаковки проекта.
🇬🇧 This folder contains strategic development plans and public packaging plans.
Документы перенесены из:

```text
/home/alexey/shared_vm/plans_nas_jetson_nano
```

Текущий путь:

```text
docs/plans/
```

## 2. Документы

| Документ | Назначение |
|---|---|
| `GITHUB_PROJECT_PROMOTION_WORKPLAN.md` | подробный план GitHub-упаковки, релизов, issue templates, roadmap, контента и community-процессов |
| `OLD_HARDWARE_PROJECT_PROMOTION_PLAN.md` | продуктовая концепция «оживим старое железо», позиционирование, аудитории, MVP и публичная матрица совместимости |
| `VPS_INTEGRATION_PLAN.md` | реализованный внешний доступ через VPS reverse SSH tunnel |
| `STORAGE_INCIDENT_2026-06-23.md` | live-инцидент USB storage: симптомы, безопасное восстановление, guardrails |
| `RELIABILITY_AUDIT_2026-06-23.md` | аудит автовосстановления после power loss/USB failure и список hardening-мер |

## 3. Главный вывод

Проект не должен позиционироваться как частный `docker-compose` для Jetson.
Сильнее выглядит концепция:

```text
старое железо -> домашнее семейное облако -> Android sync -> backup/restore -> безопасная LLM-диагностика
```

Jetson Nano остаётся первым hardware profile, но публичная ценность проекта
шире: Raspberry Pi, mini-PC, старые ноутбуки и другие low-power устройства.

## 4. Что уже учтено в проекте

| Идея из планов | Статус |
|---|---|
| Двуязычный README | выполнено |
| Чёткое privacy-first позиционирование | выполнено |
| Запрет прямой публикации сервисов в интернет | выполнено |
| Запрет локальной LLM на Jetson Nano в Stage 1 | выполнено |
| Jetson Nano как первый hardware profile | выполнено |
| Stage 0 для microSD и первого boot | выполнено |
| External documentation cache | выполнено |
| Secret scan перед публикацией | выполнено |
| Roadmap Stage 1 / Stage 2 / Stage 3 | частично выполнено; Stage 1 recovered после USB-инцидента, reboot/autorecovery verified, hardware watch |
| LLM Gateway как диагностический privacy-layer | частично выполнено |
| VPS reverse tunnel | выполнено |
| Storage preflight / fail-closed backup | выполнено после USB-инцидента |
| Reliability audit + Docker storage boot guard | подготовлено в repo и установлено live; Docker restart/boot применит guard |

## 5. Что стоит добавить следующим

Ближайшие полезные документы:

1. `QUICK_START.md` — короткий путь от microSD до первого сервиса.
2. `PROJECT_STATUS.md` — честный статус Alpha / hardware validation.
3. `HARDWARE_COMPATIBILITY.md` — матрица Jetson Nano, Raspberry Pi, mini-PC, old laptop.
4. `OLD_HARDWARE_GUIDE.md` — как выбрать и проверить старое железо.
5. `ROADMAP.md` — публичные milestones `v0.1.0-alpha`, `v0.2.0`, `v1.0.0`.
6. `PRIVACY.md` — отдельная privacy policy для домашних данных и LLM.
7. `.github/ISSUE_TEMPLATE/` — bug report, installation problem, hardware compatibility report.

## 6. Что отложить

| Идея | Почему отложить |
|---|---|
| One-click installer | опасно до проверки ручного runbook |
| Публичный Habr/Reddit launch | сначала нужен реальный Jetson audit и хотя бы один сервис |
| GitHub Actions с запуском тяжёлых контейнеров | рано и может быть нестабильно |
| Android restore client | Stage 2 после стабилизации Stage 1 |
| Immich ML на слабом железе | не включать до нагрузочных тестов |
| Локальная LLM | прямо запрещено на Stage 1 |

## 7. Рекомендуемые GitHub topics

```text
self-hosted
home-cloud
old-hardware
jetson-nano
raspberry-pi
nextcloud
immich
android-backup
family-cloud
docker-compose
nas
privacy
deepseek
llm-gateway
backup
homelab
```

## 8. Рекомендуемые milestones

| Milestone | Цель |
|---|---|
| `v0.1.0-alpha` | публичная документация, Stage 0, Jetson hardware validation |
| `v0.2.0` | стабильный Stage 1 Docker Compose |
| `v0.3.0` | hardware profiles для Raspberry Pi / mini-PC |
| `v0.4.0` | проверенный backup/restore |
| `v0.5.0` | LLM Gateway MVP с policy enforcement |
| `v1.0.0` | стабильный self-hosted blueprint |
| `v2.0.0` | Android Stage 2 client |

## 9. Практический порядок

На текущем этапе не нужно начинать с продвижения. Нужно:

1. Завершить Stage 0: microSD, first boot, SSH.
2. Выполнить hardware audit Jetson Nano.
3. Зафиксировать первый hardware report без серийников и личных IP.
4. Подготовить HDD и storage.
5. Поднять минимальный сервисный MVP.
6. В текущем состоянии: наблюдать Nextcloud/USB storage после успешного reboot/autorecovery test.
7. Только после этого расширять публичный запуск.
