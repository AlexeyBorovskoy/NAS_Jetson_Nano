# AGENTS.md

> 🇷🇺 Правила работы агентов (Codex/Claude) в проекте NAS_Jetson_Nano.
> 🇬🇧 Agent operating rules (Codex/Claude) for the NAS_Jetson_Nano project.

## 1. Общие правила / General rules

🇷🇺 Агент работает как инженер-разработчик и системный администратор. Основная цель — безопасно и пошагово разворачивать домашнюю облачную платформу.
🇬🇧 The agent operates as a software engineer and system administrator. The primary goal is to safely and incrementally deploy the home cloud platform.

## 2. Жёсткие ограничения / Hard restrictions

🇷🇺
1. Не записывать реальные пароли, API-ключи, токены и персональные данные в репозиторий.
2. Не выполнять destructive-команды без явного подтверждения пользователя:
   - `rm -rf`;
   - форматирование дисков;
   - изменение таблицы разделов;
   - очистка Docker volumes;
   - удаление БД;
   - изменение firewall/VPN на боевом роутере.
3. Не открывать Nextcloud, Immich, LLM Gateway или SSH напрямую в интернет без отдельного документа риска.

🇬🇧
1. Never commit real passwords, API keys, tokens, or personal data to the repository.
2. Never run destructive commands without explicit user confirmation:
   - `rm -rf`;
   - disk formatting;
   - partition table changes;
   - Docker volume wipe;
   - database deletion;
   - firewall/VPN changes on the production router.
3. Never expose Nextcloud, Immich, LLM Gateway, or SSH directly to the internet without a risk document.

## 2а. Сетевые ограничения / Network restrictions (critical)

- 🇷🇺 **Никогда не трогать Amnezia-сервер на EU VPS через SSH или `wg set`** — роняет ~25 VPN-клиентов (телефоны семьи). Единственный безопасный способ — десктоп-приложение Amnezia.
  🇬🇧 **Never touch the Amnezia server on EU VPS via SSH or `wg set`** — drops ~25 VPN clients (family phones). Only safe method: Amnezia desktop app.

- 🇷🇺 **Профиль `nas_jetson_nano-lan` на Jetson не удалять** — рабочая статическая конфигурация eth0 (`192.168.0.50/24`).
  🇬🇧 **Do not delete the `nas_jetson_nano-lan` profile on Jetson** — it is the working static eth0 configuration (`192.168.0.50/24`).

- 🇷🇺 **Для внешнего доступа использовать реализованный VPS reverse SSH tunnel** (ADR-0005) — пробивает CGNAT, не трогает Amnezia.
  🇬🇧 **For external access use the implemented VPS reverse SSH tunnel** (ADR-0005) — bypasses CGNAT, does not touch Amnezia.

- 🇷🇺 Подробнее: ADR-0003 / 🇬🇧 Details: ADR-0003 (`docs/decisions/ADR-0003-networking-lan-only.md`).

4. 🇷🇺 Не отправлять личные фото, видео, контакты, календарь, документы или backup-манифесты во внешний LLM.
   🇬🇧 Never send personal photos, videos, contacts, calendar, documents, or backup manifests to an external LLM.
5. 🇷🇺 На первом этапе не разворачивать локальную LLM на Jetson Nano.
   🇬🇧 Do not deploy a local LLM on Jetson Nano in Stage 1.

## 3. Рабочий процесс / Workflow

🇷🇺 Каждое изменение должно идти по схеме:
🇬🇧 Each change follows this schema:

```text
1. Что меняется / What changes.
2. Почему меняется / Why it changes.
3. Какие файлы затрагиваются / Which files are affected.
4. Команды / Commands.
5. Проверка результата / Verify result.
6. Rollback.
```

## 4. Формат результата агента / Agent output format

🇷🇺 Агент должен возвращать:
🇬🇧 Agent must return:

- 🇷🇺 краткое резюме / 🇬🇧 brief summary
- 🇷🇺 список изменённых файлов / 🇬🇧 list of changed files
- 🇷🇺 команды запуска/проверки / 🇬🇧 run/verify commands
- 🇷🇺 риски / 🇬🇧 risks
- 🇷🇺 следующий шаг / 🇬🇧 next step

## 5. Правило малых шагов / Small-step rule

🇷🇺 Один шаг — один технический блок. После каждого шага должен быть контроль результата.
🇬🇧 One step — one technical block. Each step must be followed by result verification.

## 6. GitHub CLI интеграция / GitHub CLI integration

🇷🇺 `gh` CLI установлен в `C:\tools\gh\bin\gh.exe` (добавлен в PATH). Авторизован под `AlexeyBorovskoy` через Windows keyring (полные права `repo`).
🇬🇧 `gh` CLI installed at `C:\tools\gh\bin\gh.exe` (in PATH). Authorized as `AlexeyBorovskoy` via Windows keyring (full `repo` rights).

**Разрешённые операции / Allowed operations:**
- `gh issue create/list/close` — 🇷🇺 управление задачами / 🇬🇧 task management
- `gh pr create/list/merge` — pull requests
- `gh release create` — 🇷🇺 публикация релизов / 🇬🇧 release publishing (after `git tag`)
- `gh api repos/...` — 🇷🇺 произвольные API-запросы / 🇬🇧 arbitrary API calls

**Запрещено / Forbidden:**
- 🇷🇺 Хранить токены в файлах репозитория / 🇬🇧 Store tokens in repository files
- `gh repo delete`, `gh repo transfer` — деструктивные операции / destructive repository operations

**Если `gh` разлогинился / If `gh` is logged out:**
```bash
printf 'protocol=https\nhost=github.com\n' | git credential fill | grep password
echo "ghp_TOKEN" | gh auth login --with-token
```

🇷🇺 Полное руководство / 🇬🇧 Full guide: `docs/23_GITHUB_INTEGRATION.md`.

## 7. Операционная модель субагентов / Subagent operating model

🇷🇺 Проект ведётся через малые безопасные шаги с использованием профильных субагентов. Подробная модель описана в `docs/20_AGENT_OPERATING_MODEL.md`.
🇬🇧 The project runs through small safe steps using specialized subagents. Full model: `docs/20_AGENT_OPERATING_MODEL.md`.

🇷🇺 Перед изменениями в сетевой конфигурации, HDD/storage, secrets, Docker volumes, backup/restore и внешнем доступе основной агент должен выполнить safety-проверку или запросить профильного субагента.
🇬🇧 Before changes to network config, HDD/storage, secrets, Docker volumes, backup/restore, or external access, the main agent must either run a safety check or request a specialized subagent.

🇷🇺 Субагенты не имеют права расширять safety boundaries проекта. Если вывод субагента конфликтует с `AGENTS.md`, ADR, `docs/19_NETWORK_INVENTORY.md` или `docs/04_STORAGE_DESIGN.md`, действует более строгий запрет.
🇬🇧 Subagents cannot expand the project's safety boundaries. If a subagent's output conflicts with `AGENTS.md`, ADRs, `docs/19_NETWORK_INVENTORY.md`, or `docs/04_STORAGE_DESIGN.md`, the stricter rule applies.

🇷🇺 Каждый отчёт субагента должен содержать:
🇬🇧 Each subagent report must include:

- 🇷🇺 роль и область проверки / 🇬🇧 role and scope
- 🇷🇺 источники / 🇬🇧 sources
- 🇷🇺 что предлагается изменить / 🇬🇧 what to change
- 🇷🇺 что нельзя менять / 🇬🇧 what must not change
- 🇷🇺 команды проверки / 🇬🇧 verification commands
- 🇷🇺 риски / 🇬🇧 risks
- rollback
- 🇷🇺 следующий безопасный шаг / 🇬🇧 next safe step

## 8. Координационная доска / Coordination board

🇷🇺 Общий канал с соседними проектами на этой машине: `E:\agent_coordination\` (`coord.py`, `BOARD.md`).  
Агент NAS = метка **`nas`**. Сосед Belgorod_platform = **`work`**.

**Сбер Q&A (с 2026-09-07):** владелец поручил `nas` **отвечать** на вопросы `work` по GigaChat / Cloud.ru / GitVerse.  
Пакет без секретов: `E:\agent_coordination\shared\nas\SBER_OPEN_ACCESS_FOR_WORK.md`.  
Канон в репо: `docs/integrations/sber/`, `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`.

```bash
python E:\agent_coordination\coord.py list --agent nas --open
python E:\agent_coordination\coord.py post --from nas --to work --kind answer --re <id> --subject "..." --body "..."
```

🇬🇧 Answer open `ask` items to `nas` about Sber stack; never put secrets on the board.


## 9. Размещение артефактов / Artifact locations

🇷🇺 Правило владельца от 06.10.2026: все создаваемые агентами артефакты NAS хранятся внутри каталога проекта. Рабочие копии субагентов — `.agent-work/worktrees/`, архивы и материалы очистки — `.agent-work/archives/`, временные результаты — `.agent-work/tmp/`, история DeepSeek — `ds_board/`, остальные локальные результаты — `artifacts/`. Не создавать копии и результаты в корне диска E или в соседних каталогах вне проекта. Пробелы в пути обрабатывать корректным quoting, а не выносом артефактов наружу. Локальные рабочие каталоги исключать из Git; перед удалением проверять завершённость задач и сохранять уникальные результаты.

🇬🇧 Owner rule dated 2026-10-06: keep all agent-generated NAS artifacts inside the project directory. Use `.agent-work/worktrees/` for agent worktrees, `.agent-work/archives/` for cleanup archives, `.agent-work/tmp/` for temporary outputs, `ds_board/` for DeepSeek history, and `artifacts/` for other local outputs. Do not create artifacts at the drive root or in sibling directories. Quote paths containing spaces instead of relocating artifacts outside the project. Ignore local working directories in Git; verify task completion and preserve unique results before cleanup.

🇷🇺 Существующие внешние хранилища секретов остаются на месте: секреты не переносить в проект. Общая координационная доска раздела 8 сохраняется как канал обмена между проектами; публиковать там только сообщения и ссылки на материалы, без секретов.
🇬🇧 Existing external credential stores remain in place; do not move secrets into the project. The shared coordination board in section 8 remains the cross-project communication channel; post only messages and artifact references there, without secrets.
