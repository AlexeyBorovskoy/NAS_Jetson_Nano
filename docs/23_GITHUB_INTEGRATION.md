# 23. GitHub Integration — Claude Code + gh CLI

> 🇷🇺 Этот документ описывает полный рабочий процесс проекта NAS_Jetson_Nano: как Claude Code взаимодействует с GitHub через `gh` CLI на Windows-машине.
>
> 🇬🇧 This document describes the complete NAS_Jetson_Nano workflow: how Claude Code interacts with GitHub via `gh` CLI on a Windows machine.
>
> 🇷🇺 **Фишка проекта:** весь жизненный цикл (задача → код → тест → commit → PR → release) выполняется одним агентом (Claude Code) без переключения инструментов.
>
> 🇬🇧 **Project highlight:** the entire lifecycle (task → code → test → commit → PR → release) is handled by a single agent (Claude Code) without tool switching.

---

## Установка gh CLI / Install gh CLI

```bash
# gh CLI распакован в C:\tools\gh\bin\ (в PATH пользователя)
# Версия: 2.74.1 (GitHub CLI, 2025-06-10)

gh --version
# → gh version 2.74.1 (2025-06-10)
```

**Установка на другой машине:**
```bash
# Windows (ZIP, без winget/scoop):
$version = "2.74.1"
Invoke-WebRequest "https://github.com/cli/cli/releases/download/v$version/gh_${version}_windows_amd64.zip" -OutFile "$env:TEMP\gh.zip"
Expand-Archive "$env:TEMP\gh.zip" -DestinationPath "C:\tools\gh" -Force
# Добавить C:\tools\gh\bin в PATH
```

## Авторизация / Authentication

```bash
# Первичная авторизация (нужен PAT с правами repo):
echo "ghp_TOKEN" | gh auth login --with-token  # из Git Bash (НЕ PowerShell pipe)

# Проверить статус:
gh auth status

# Если gh разлогинился — восстановить из Windows Credential Manager:
printf 'protocol=https\nhost=github.com\n' | git credential fill | grep password
echo "ghp_restored_token" | gh auth login --with-token
```

> **PAT создаётся на:** https://github.com/settings/tokens/new  
> Нужные права: `repo` (весь верхний чекбокс)  
> Рекомендуемый срок: No expiration  
> Хранить в Windows keyring через `gh auth login` — НЕ в файлах репозитория.

## Что умеет gh в этом проекте / What gh can do in this project

### Issues — задачи и баги / Issues — tasks and bugs

```bash
# Создать issue:
gh issue create \
  --title "feat: добавить HTTPS для VPS nginx" \
  --body "Let's Encrypt + домен. ADR: docs/decisions/ADR-0006." \
  --label "enhancement"

# Список открытых:
gh issue list

# Закрыть issue:
gh issue close 5 --comment "Реализовано в v1.4.0"
```

### Pull Requests

```bash
# Создать PR (из ветки feature → main):
gh pr create \
  --title "feat: HDD migration guide (Stage 3.1)" \
  --body "$(cat <<'EOF'
## Summary
- Added docs/01C_HDD_MIGRATION.md
- Script for safe ext4 partition creation alongside NTFS

## Test plan
- [ ] Tested on real HDD with NTFS data preserved
EOF
)"

# Список PR:
gh pr list

# Merge PR:
gh pr merge 3 --squash --delete-branch
```

### Releases

```bash
# Стандартный цикл выпуска релиза:
git tag -a v1.4.0 -m "Stage 3.1 — HDD migration"
git push origin v1.4.0

gh release create v1.4.0 \
  --title "v1.4.0 — HDD Migration Ready" \
  --notes "$(cat <<'EOF'
## Что нового
- HDD подключён и смонтирован (ext4 рядом с NTFS)
- Данные перенесены с microSD → HDD
- Samba шары настроены на новом пути

## Сервисы
Всё то же, что в v1.3.0, плюс полноценный HDD-бэкап.
EOF
)"
```

### Управление репозиторием / Repository management

```bash
# Обновить описание:
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano \
  -X PATCH \
  -f description="Новое описание"

# Обновить topics (через API — gh api не поддерживает topics напрямую):
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano/topics \
  -X PUT \
  --input - <<< '{"names":["jetson-nano","homelab","nextcloud","immich"]}'

# Посмотреть статистику:
gh repo view AlexeyBorovskoy/NAS_Jetson_Nano \
  --json name,description,stargazerCount,forkCount,latestRelease

# Список всех релизов:
gh release list
```

### CI / GitHub Actions

```bash
# Статус последних workflow runs:
gh run list --limit 10

# Детали конкретного run:
gh run view <run-id>

# Перезапустить упавший run:
gh run rerun <run-id>

# Просмотр логов:
gh run view <run-id> --log
```

## Стандартный workflow сессии / Standard session workflow

```
1. Начало сессии:
   - Claude читает CLAUDE.md (автоматически)
   - Claude читает memory/ (через MEMORY.md)
   
2. Работа над задачей:
   - Редактирование файлов (Edit/Write tools)
   - SSH на Jetson (Bash tool → ssh admin@192.168.0.50)
   - Тесты (goss, curl)
   
3. Фиксация изменений:
   git add <files>
   git commit -m "тип: описание\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
   git push
   
4. Применение на Jetson:
   ssh admin@192.168.0.50 "cd ~/nas_jetson_nano && git pull --ff-only"
   
5. GitHub management (при необходимости):
   gh issue create / gh pr create / gh release create
   
6. Конец сессии:
   - Обновить memory/ (MEMORY.md → project checkpoint)
   - При крупных изменениях: обновить README и CHANGELOG
```

## Почему это фишка проекта / Why this is the project's highlight

🇷🇺 Проект NAS_Jetson_Nano демонстрирует **полный AI-assisted DevOps цикл**:
🇬🇧 NAS_Jetson_Nano demonstrates a **complete AI-assisted DevOps cycle**:

| Этап | Инструмент | Кто делает |
|---|---|---|
| Задача / идея | GitHub Issues | Человек формулирует → Claude создаёт |
| Реализация | Claude Code (Edit/Write) | Claude |
| Тесты на железе | SSH → Jetson → docker/goss | Claude через SSH |
| Коммит | git | Claude |
| PR / Review | `gh pr create` | Claude создаёт → человек approves |
| Релиз | `gh release create` | Claude |
| Документация | Edit README/CHANGELOG | Claude |
| Мониторинг | Telegram daily report | Автономно |

🇷🇺 **Человек формулирует цели. Claude Code реализует, тестирует и документирует.**
🇬🇧 **The human defines goals. Claude Code implements, tests, and documents.**

🇷🇺 Все решения задокументированы в ADR (`docs/decisions/`) и промптах (`docs/prompts/`).
🇬🇧 All decisions are documented in ADRs (`docs/decisions/`) and prompts (`docs/prompts/`).

## Безопасность токена / Token security

- **Хранится:** Windows keyring (через `gh auth login`)
- **НЕ хранится:** в файлах репозитория, `.env`, коммитах
- **Проверка перед push:** `./scripts/security/check_no_secrets.sh`
- **CI проверяет:** `.github/workflows/secrets-check.yml`
- **Ротация:** при подозрении на компрометацию → github.com/settings/tokens → Regenerate
