# Исполнитель DeepSeek / DeepSeek worker

> 🇷🇺 Регламент владельца от 25.09.2026 «Claude — ведущий, DeepSeek — дешёвый исполнитель».
> Передан проектом `work` 26.09 (доска `m0207`, `m0208`) и **принят в проект целиком**: правила ниже —
> полная копия, решение — `docs/decisions/ADR-0012-deepseek-worker.md`, ядро — сабмодуль
> `tools/deepseek-worker`. EN — во второй половине.

## 🇷🇺 Русский

### Состав

| Что | Где |
|---|---|
| Ядро (пакет `ds_worker`, CLI `ds-worker`) | сабмодуль **`tools/deepseek-worker`**, закреплён на `0311914`; источник — приватный `github.com/AlexeyBorovskoy/deepseek-worker` (зеркало — GitLab РИПАС `analyzer/deepseek-worker`) |
| Протокол целиком (§1–20) | `tools/deepseek-worker/docs/PROTOCOL.md` |
| Skill ведущего Claude | `tools/deepseek-worker/skill/deepseek-worker/SKILL.md`, установлен в `~/.claude/skills/deepseek-worker/` |
| Конфигурация проекта | `ds_worker.toml` в корне репозитория |
| История задач | `ds_board/` (в `.gitignore`, не в git) |
| Worktree исполнителя | `E:/nas-ds-<task_id>`, ветка `deepseek/<task_id>` |
| Ключ API | файл владельца `C:/Users/Alexey/.config/belgorod/deepseek-worker-key` — **общий счёт с ботом Белгорода** |

⚠️ Репозиторий проекта **публичный**, ядро — **приватное**. Сабмодуль публикует только ссылку и хеш;
код видит лишь учётная запись владельца. CI сабмодули не тянет — ему ядро не нужно.

### Установка на новой машине

```bash
git submodule update --init tools/deepseek-worker
pip install -e tools/deepseek-worker
python tools/deepseek-worker/install_skill.py      # skill → ~/.claude/skills/
# ключ кладёт владелец лично; путь — [key] в ds_worker.toml
```

### Цикл

```bash
ds-worker new <карточка>.json          # ядро откажет EXPENSIVE/CRITICAL и карточкам с секретами
ds-worker run <task_id>                # → READY_FOR_CLAUDE_REVIEW | BLOCKED | REWORK
ds-worker status <task_id>
ds-worker review <task_id> --accept    # или --rework "замечания" / --reject
```

`--accept` — единственный путь к DONE, и ставит его только ведущий.

### Правила использования (полная копия регламента, обязательны)

Роли:
- **Claude — ведущий:** понимание задачи, декомпозиция, архитектура, сложные рассуждения и отладка,
  интеграция, рецензия, итоговая проверка, решение о завершении.
- **DeepSeek — дешёвый исполнитель** ограниченной работы.
- **Владелец** — необратимые решения, выкладка в бой, разрушительные операции, утверждение всего,
  что влияет на безопасность, продуктовые решения.

**1. Класс каждой задачи — до начала работы.**
- **CHEAP:** поиск, grep, инвентарь, документация, генерация тестов, правки линтера, мелкие
  механические изменения, разбор логов, сравнение конфигов, повторяющиеся правки, сбор доказательств.
- **MEDIUM:** ограниченная реализация, локальная отладка, несколько связанных файлов, умеренный рефакторинг.
- **EXPENSIVE:** архитектура, неясные требования, межмодульные изменения, сложная отладка,
  конкурентность, поиск причин проблем производительности, изменения безопасности, крупный рефакторинг.
- **CRITICAL:** логика безопасности и отказоустойчивости, миграции в бою, разрушительные операции
  с БД и данными, изменение границ безопасности, необратимые действия в бою.
  **Для этого проекта:** всё, что трогает туннели, VPS, Amnezia/WireGuard/xray, доступ снаружи,
  данные на дисках NAS (`/mnt/storage`, `/mnt/hdd2tb`) и живой Jetson.

**2. Кому отдавать задачу.**
- CHEAP — исполнителю по умолчанию, **карточкой через `ds-worker`, а не своим субагентом Claude**.
- MEDIUM — разбить на CHEAP-подзадачи; исполнителю — сбор доказательств, тесты, механика;
  интеграция и рецензия — за Claude.
- EXPENSIVE — рассуждения и проект делает Claude, исполнителю — только ограниченная вспомогательная работа.
- CRITICAL — анализирует и проверяет Claude; перед необратимым шагом — согласие владельца.

Не делегировать ради делегирования: если завести карточку дороже, чем сделать самому, — сделать самому.
Карточку EXPENSIVE или CRITICAL ядро не сохранит.

**3. Карточка.** Поля: `task_id`, `cost_class`, `goal`, `scope` (какие файлы), `inputs`, критерии
приёмки, `needs_edit`, `base`. Одна карточка — одна ограниченная цель с проверяемым результатом.
Контекст — минимальный: пути и точные вопросы, а не пересказ проекта.

**4. Что нельзя класть в карточки и отдавать в API DeepSeek.** Значения ключей, токенов и паролей,
`.env`, приватные данные владельца и семьи, доступы соседей из `E:/agent_coordination/shared/`.
Встроенный страж отказывает на похожее на секрет, но решает здесь ведущий, а не страж.

**5. Что исполнитель не делает никогда:** не ставит DONE; не пушит и не сливает; не ходит по
ssh/scp/curl и в веб; не выкладывает в бой. CLI запрещает это технически, ведущий запреты не снимает.

**6. Приёмка (обязательна).** Ведущий сам читает дифф и `RESULT.json` и проверяет утверждения
исполнителя по коду или командой — на слово не верить. Затем `--accept`, `--rework "конкретные
замечания"` или `--reject`. После двух неудачных доработок задачу забирает Claude.

**7. Запуск кода.** Задача только на чтение код не запускает. `needs_edit: true` открывает запуск
кода, а с ним обход `deny_read` и доступ к ключу в окружении — такие задачи давать только
в worktree без секретов рядом.

**8. Стоимость.** Считать по тарифу DeepSeek (`[price]` в конфиге). `total_cost_usd` из вывода
Claude Code посчитан по тарифам Anthropic и завышен примерно в 80 раз. Ключ общий с ботом
Белгорода: **крупные серии задач согласовывать с владельцем**.

**9. Эскалация.** Необратимое, разрушительное, влияющее на бой или безопасность — только после
явного согласия владельца.

### Решения этого проекта

**Что можно отправлять в API DeepSeek:** только файлы, отслеживаемые git. Репозиторий публичный,
поэтому утечки сверх уже опубликованного нет.

**Что нельзя:** `config/.env` и любые `.env`; `docs/local/` (логины семьи, идентификаторы комнат);
`DNS/` (токен dynv6); `.claude/` (в allowlist копятся настоящие секреты); ключи; пароли restic;
доступы Cloud.ru/Сбер; содержимое доски соседей.

**Как это закрыто технически** (`ds_worker.toml`):
- worktree создаётся вне основной копии, в `E:/nas-ds-<task>`, и содержит только файлы git;
- `security.deny_read` запрещает основную копию проекта целиком (там лежат `.env`, `docs/local`,
  `.claude`), `E:/agent_coordination`, `~/.claude`, `~/.config`, `~/.ssh` и маски секретов;
- ключ передаётся только в окружение дочернего процесса — не в argv, не в лог, не в `RESULT.json`.

**Соотношение с субагентами Claude** (`CLAUDE.md`, `docs/20_AGENT_OPERATING_MODEL.md`):
механика, которая раньше уходила Haiku-субагенту, теперь идёт исполнителю DeepSeek. Субагенты
Claude остаются для работы с суждением (Sonnet/Opus) и для всего, где нужен доступ к устройству
или сети, — у исполнителя его нет по построению.

### Пробный цикл 2026-09-26

Задача `nas-trial-systemd-inventory` (CHEAP, только чтение): инвентарь `systemd/`.

| Шаг | Итог |
|---|---|
| Первый прогон | 1 мин 34 с, **$0.0394** по тарифу DeepSeek. Содержание верное, но нарушен контракт §9 (`test_results` строкой, а не списком) → REWORK автоматически |
| Доработка | **$0.0082**, READY_FOR_CLAUDE_REVIEW → `--accept` → DONE. Итого **≈ $0.048** |
| Сверка ведущим | 17 таймеров, 24 сервиса, 28 вхождений `ExecStart*` — совпало; выборочные `OnCalendar`/`ExecStart` — совпали; в worktree изменён только `RESULT.json` |
| Проверка запрета | попытка прочитать `CLAUDE.md` основной копии вне worktree → **отказ**, содержимое не получено |

Попутная находка исполнителя, подтверждённая ведущим: сервисы `ddns-update`, `sd-wear` и `ssd-recovery`
в git держат захардкоженный `/home/admin/nas_jetson_nano/...`, `boot-alert` — `/home/admin/nasa/...`.
Это тот класс дефекта, что ломал восстановление SSD 08–19.09. На устройстве сейчас работают
юниты `nasa-*`, поэтому в бою это не стреляет; выстрелит при переезде Part B.

---

## 🇬🇧 English

Owner's policy of 2026-09-25, "Claude leads, DeepSeek is the cheap worker", handed over by project
`work` on 2026-09-26 and **adopted in full**: the rules below are a complete copy, the decision is
`docs/decisions/ADR-0012-deepseek-worker.md`, the core is the submodule `tools/deepseek-worker`.

### Components

| What | Where |
|---|---|
| Core (`ds_worker` package, `ds-worker` CLI) | submodule **`tools/deepseek-worker`** pinned at `0311914`; private upstream `github.com/AlexeyBorovskoy/deepseek-worker` |
| Full protocol (§1–20) | `tools/deepseek-worker/docs/PROTOCOL.md` |
| Lead's skill | `tools/deepseek-worker/skill/deepseek-worker/SKILL.md` → `~/.claude/skills/` |
| Project config | `ds_worker.toml` at the repo root |
| Task history | `ds_board/` (git-ignored) |
| Worker worktree | `E:/nas-ds-<task_id>`, branch `deepseek/<task_id>` |
| API key | owner's file `C:/Users/Alexey/.config/belgorod/deepseek-worker-key` — **billing shared with the Belgorod bot** |

⚠️ This repository is **public**, the core is **private**: the submodule publishes only a URL and a
hash. CI does not fetch submodules and does not need the core.

Setup: `git submodule update --init tools/deepseek-worker`, `pip install -e tools/deepseek-worker`,
`python tools/deepseek-worker/install_skill.py`; the owner places the key personally.
Cycle: `ds-worker new` → `run` → `status` → `review --accept | --rework "…" | --reject`.
Only the lead's `--accept` sets DONE.

### Usage rules (full copy, mandatory)

Roles: **Claude leads** (understanding, decomposition, architecture, hard reasoning and debugging,
integration, review, final verification, the done decision); **DeepSeek is the cheap worker** for
bounded tasks; **the owner** makes irreversible, production, destructive, security and product decisions.

1. **Classify every task first.** CHEAP: search, grep, inventory, docs, test generation, lint fixes,
   small mechanical edits, log analysis, config comparison, repetitive edits, evidence gathering.
   MEDIUM: bounded implementation, local debugging, a few related files, moderate refactoring.
   EXPENSIVE: architecture, unclear requirements, cross-module changes, hard debugging, concurrency,
   performance root causes, security changes, large refactors. CRITICAL: safety and resilience logic,
   production migrations, destructive data operations, security boundary changes, irreversible
   production actions — **for this project: tunnels, the VPS, Amnezia/WireGuard/xray, external access,
   data on the NAS disks and the live Jetson.**
2. **Who does it.** CHEAP → the worker by default, **as a `ds-worker` card, not a Claude subagent**.
   MEDIUM → split into CHEAP parts; integration and review stay with Claude. EXPENSIVE → Claude does
   the reasoning, the worker only bounded auxiliary work. CRITICAL → Claude analyses and verifies;
   the owner approves any irreversible step. Don't delegate for its own sake.
3. **Card:** `task_id`, `cost_class`, `goal`, `scope`, `inputs`, acceptance criteria, `needs_edit`,
   `base`. One card, one bounded, verifiable goal; minimal context — paths and precise questions.
4. **Never in cards or sent to the API:** key/token/password values, `.env`, owner's and family's
   private data, neighbours' credentials from `E:/agent_coordination/shared/`. The built-in guard
   helps; the lead decides.
5. **The worker never** sets DONE, pushes, merges, uses ssh/scp/curl/web, or deploys. The CLI
   enforces this; the lead never lifts it.
6. **Acceptance is mandatory:** read the diff and `RESULT.json`, verify claims against code or by a
   command; then accept, rework with precise notes, or reject. After two failed reworks Claude takes over.
7. **Code execution:** read-only tasks never run code. `needs_edit: true` enables it — and with it a
   `deny_read` bypass and access to the key in the environment; use only in a worktree with no
   secrets nearby.
8. **Cost:** count at DeepSeek rates (`[price]`); Claude Code's `total_cost_usd` is ~80× too high.
   The key is shared with the Belgorod bot: agree large batches with the owner.
9. **Escalation:** anything irreversible, destructive, or affecting production or security only
   with the owner's explicit consent.

### This project's decisions

**May be sent:** git-tracked files only (the repository is public). **Must not:** any `.env`,
`docs/local/` (family logins, room IDs), `DNS/` (dynv6 token), `.claude/` (allowlists accumulate
real secrets), keys, restic passwords, Cloud.ru/Sber credentials, the neighbours' board.
**Enforcement:** worktree outside the main checkout with git files only; `deny_read` blocks the
whole main checkout, `E:/agent_coordination`, `~/.claude`, `~/.config`, `~/.ssh` and secret masks;
the key goes only into the child process environment.
**Versus Claude subagents:** mechanical work that used to go to a Haiku subagent now goes to the
DeepSeek worker. Claude subagents remain for judgement work and for anything needing the device
or the network — which the worker has no access to by design.

### Trial run 2026-09-26

`nas-trial-systemd-inventory` (CHEAP, read-only). First run 1 min 34 s, **$0.0394**: content correct,
contract §9 violated (`test_results` as a string) → auto-REWORK. Rework **$0.0082** → accepted.
Total **≈ $0.048**. Lead verified 17 timers, 24 services, 28 `ExecStart*` lines. **Read denial
verified:** the main checkout's `CLAUDE.md` was refused. Side finding, confirmed: `ddns-update`,
`sd-wear`, `ssd-recovery` hardcode `/home/admin/nas_jetson_nano/...`, `boot-alert` uses
`/home/admin/nasa/...` — the defect class that broke SSD recovery on 2026-09-08…19; harmless on the
live `nasa-*` units today, it will bite during the Part B migration.
