# 16. Публикация на GitHub / GitHub Publication

> 🇷🇺 **Статус: ✅ Репозиторий публичный** (сделано 2026-06-21).
> 🇬🇧 **Status: ✅ Repository is public** (done 2026-06-21).
> URL: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano

## 1. Проект опубликован / Project published

🇷🇺 Репозиторий переведён в public mode. Все CI workflows активны, секреты проверены.
🇬🇧 Repository switched to public mode. All CI workflows are active, secrets verified.

## 2. Рекомендуемое имя / Recommended repository name

```text
selfhosted-family-cloud
```

🇷🇺 Наиболее универсальное имя — проект можно расширить за пределы Jetson Nano.
🇬🇧 Most versatile name — the project can expand beyond Jetson Nano.

## 3. Позиционирование / Positioning

```text
A Codex-ready self-hosted family cloud blueprint for ARM/SBC devices:
Nextcloud + Immich + Android backup roadmap + privacy-controlled DeepSeek LLM gateway.
```

## 4. Что даст шанс на рост / Growth factors

| Фактор / Factor | Почему важно / Why it matters |
|---|---|
| Поддержка разных устройств / Multi-device support | Jetson Nano — too narrow audience |
| Пошаговые install scripts / Step-by-step install scripts | Users don't like manual assembly |
| Реальные тесты / Real tests | Builds trust |
| Скриншоты / Screenshots | Simplifies understanding |
| Xiaomi/Android инструкции / instructions | Concrete practical pain |
| LLM Gateway с privacy policy / with privacy policy | Differentiates from typical docker-compose projects |
| Codex-ready prompts | New documentation format for agentic development |

## 5. Что убрать перед публикацией / What to remove before publishing

🇷🇺
- реальные IP
- серийные номера
- семейные имена
- фото оборудования с серийниками
- реальные токены
- личные домены
- dumps/logs

🇬🇧
- real IPs
- serial numbers
- family names
- equipment photos with serials
- real tokens
- personal domains
- dumps/logs

## 6. Минимальный pre-release checklist / Minimal pre-release checklist

```bash
./scripts/security/check_no_secrets.sh
shellcheck scripts/**/*.sh || true
docker compose -f docker/compose/docker-compose.stage1.yml config
find . -name '.env' -o -name '*.key' -o -name '*.pem'
```

## 7. GitHub labels

```text
stage-1           stage-2-android    security
backup            documentation      jetson
raspberry-pi      nextcloud          immich
deepseek          help-wanted        good-first-issue
```

## 8. Roadmap для публичного README / Public README roadmap

| Версия / Version | Содержание / Content |
|---|---|
| v0.1 | документация и шаблоны / docs and templates |
| v0.2 | аппаратный аудит и storage scripts / hardware audit + storage scripts |
| v0.3 | Nextcloud compose |
| v0.4 | Immich compose |
| v0.5 | backup/restore |
| v0.6 | LLM Gateway |
| v0.7 | Android Stage 2 API draft |
| v1.0 | verified install on Jetson Nano / Raspberry Pi / mini-PC |

---

## 9. Реализованная публичная инфраструктура / Implemented public infrastructure

### README с badges / README with badges

🇷🇺
- Badges line вверху (License, Stage, Platform, Docker, PRs Welcome)
- Двуязычность (RU/EN) в каждой секции
- ASCII-диаграмма архитектуры
- Таблица стека с версиями и ролями
- Quick Start — реально работающий, шаг за шагом

🇬🇧
- Badges line at top (License, Stage, Platform, Docker, PRs Welcome)
- Bilingual (RU/EN) in each section
- ASCII architecture diagram
- Stack table with versions and roles
- Quick Start — actually working, step by step

### GitHub Actions (CI/CD)

| Workflow | Файл / File | Назначение / Purpose |
|---|---|---|
| Security Check | `.github/workflows/secrets-check.yml` | Проверка секретов / Secret check on push/PR to `main` |
| Validate Compose | `.github/workflows/validate-compose.yml` | Валидация Docker Compose / Compose validation on push/PR |

### Issue Templates / шаблоны

| Шаблон / Template | Файл / File | Назначение / Purpose |
|---|---|---|
| Bug report | `.github/ISSUE_TEMPLATE/bug_report.md` | Двуязычный / Bilingual bug report |
| Feature request | `.github/ISSUE_TEMPLATE/feature_request.md` | Запрос функциональности / Feature request |
| Config | `.github/ISSUE_TEMPLATE/config.yml` | Конфигурация шаблонов / Template config |

🇷🇺 PR template: `.github/pull_request_template.md`. Владельцы кода: `.github/CODEOWNERS`.
🇬🇧 PR template: `.github/pull_request_template.md`. Code owners: `.github/CODEOWNERS`.

---

## 10. Чеклист перед тегом v0.1.0 / Pre-tag v0.1.0 checklist

### Безопасность / Security

- [ ] 🇷🇺 Запустить `./scripts/security/check_no_secrets.sh` / 🇬🇧 Run — output clean
- [ ] 🇷🇺 Проверить find на .env/.key/.pem / 🇬🇧 Check find for .env/.key/.pem — nothing real
- [ ] 🇷🇺 `config/.env` в `.gitignore` / 🇬🇧 `config/.env` in `.gitignore` and not staged
- [ ] 🇷🇺 Нет реальных IP, токенов, серийников / 🇬🇧 No real IPs, tokens, serials

### Документация / Documentation

- [ ] `README.md` — badges рабочие / working, links not broken
- [ ] `CODE_OF_CONDUCT.md` — создан / created
- [ ] `CONTRIBUTING.md` — актуален / up to date
- [ ] `CHANGELOG.md` — содержит / contains `[v1.3.x]` entries
- [ ] `LICENSE` — присутствует / present (MIT)
- [ ] `AGENTS.md` — присутствует / present

### Код и конфигурация / Code and configuration

- [ ] `config/.env.example` — только placeholder-значения / placeholder values only
- [ ] Docker Compose config validates
- [ ] shellcheck — нет критических ошибок / no critical errors

### GitHub Infrastructure

- [ ] Issue templates configured
- [ ] PR template configured
- [ ] CI workflows active
- [ ] CODEOWNERS configured
- [ ] GitHub labels created
- [ ] Description and Topics filled on GitHub
