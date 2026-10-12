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
| Worktree исполнителя | `.agent-work/worktrees/nas-ds-<task_id>`, ветка `deepseek/<task_id>` |
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

### OpenRouter: дополнительное мнение — 2026-10-10

По запросу владельца проверены [Decision Model Rankings](https://openrouter.ai/rankings/decisions)
и существующая интеграция. Рейтинг отражает число запросов классификации/оценки,
не качество разработки. [Описание Decisions API](https://openrouter.ai/blog/insights/what-is-jev/)
показывает отдельный формат: заданные варианты ответа и вероятности вместо текста.
Его нельзя подключить как обычную chat-модель в `second-opinion`.

Авторизация действующим ключом подтверждена (`GET /api/v1/key`); значение ключа
не выводилось и остаётся во внешнем хранилище. Живой `GET /api/v1/models`
вернул 458 моделей, без найденных decision-моделей. Однако последующий прямой
вызов владельца подтвердил Decisions API: отсутствие модели в этом каталоге
не является доказательством недоступности отдельного endpoint.

Владелец запустил `.agent-work/tmp/openrouter_decisions_check.py` и предоставил
ответ 2026-10-10: фактическая модель `inception/mercury-decide-20260930`,
`choice=documentation`, вероятность этой категории 0,9999303,
`confidence=0,9998955`; usage: 100 входных / 1 выходной токен, cost=0.
Запрос — один синтетический пример улучшения публичного README. Подключение
подтверждено выводом владельца; это не независимый повторный вызов ведущего
и не измерение качества модели на выборке. Confidence не заменяет проверку.

В `ds_worker.toml` задан `openrouter/free`: в проверенном каталоге prompt/completion
имеют цену 0. Это бесплатный маршрутизатор, конкретная модель может меняться;
он подходит для пробного второго мнения, не сравнения фиксированных моделей.
Платного fallback в этом списке нет. Разрешён только `data_class=public`;
закрытые материалы, реальные журналы, конфиги, секреты и неопубликованный код
не отправлять. DeepSeek остаётся исполнителем, решения принимает ведущий.

Живая проба 2026-10-10: ответ через `openrouter/free` получен, 218 входных /
650 выходных токенов, 35,875 с; учёт `ds-worker` — $0. Запрос содержал только
три синтетических примера, без файлов проекта. Ответ оборвался на лимите
токенов: связь подтверждена, полнота результата и качество классификатора
не приняты. Текущий helper сохраняет текст и имя маршрута, а не фиксированный
идентификатор фактически выбранной модели; для сравнения моделей этого недостаточно.
Локальные запрос/ответ — `.agent-work/tmp/openrouter-public-second-opinion*`;
метрика — `ds_board/metrics.jsonl`. Это обычный chat-вызов, не Decisions API.

```powershell
ds-worker second-opinion --data-class public --prompt-file .agent-work/tmp/public-question.txt --max-tokens 650 --out .agent-work/tmp/openrouter-opinion.txt
```

Перед вызовом ведущий проверяет файл запроса. Ответ — рекомендация, не разрешение
выполнить действие и не подтверждение исправности. Соблюдать установленный владельцем
предел 50 запросов/сутки; автоматический вызов на каждой задаче не включён.

Кандидаты применения: предварительная классификация публичных задач;
проверка, что вывод соответствует предоставленным открытым фактам;
оценка ясности публичных инструкций. Класс данных, точные пороги свежести,
разбор структурных ошибок CLI, права команд и DONE остаются детерминированными
правилами/решением ведущего.

### Decisions API: размеченная синтетическая проверка — 2026-10-10

В 14:18 МСК выполнена проверка 25 русскоязычных вымышленных задач:
по 5 documentation/implementation/tests/architecture/ambiguous.
DeepSeek подготовил черновик, ведущий проверил всю разметку и уточнил два
примера **до** вызова API. Никаких реальных задач, конфигов или исходников нет.
Эталонные метки и пояснения в запрос не включаются.

Пять последовательных запросов по пять вопросов, перемешивание seed=42;
модель запроса `inception/mercury-decide:free`, фактическая во всех ответах
`inception/mercury-decide-20260930`. Платных fallback и автоматических повторов нет.

Результат: **25/25 верно**, каждая категория **5/5**, 25 валидных ответов,
HTTP/форматных отказов 0. Заранее заданный advisory-порог: confidence≥0,90
и отрыв от второго варианта≥0,20; ambiguous всегда передаётся ведущему.
20 рекомендаций прошли порог, 5 неоднозначных задач переданы ведущему;
ошибок среди рекомендаций и уверенных пропусков ambiguous на этой выборке 0.
Это рекомендации, а не выдача прав или автоматический запуск работ.

Стоимость API по пяти ответам **$0**, 2127 входных / 25 выходных токенов.
Задержки пакетов: 5,156 / 2,235 / 2,750 / 2,812 / 2,203 с;
медиана **2,750 с на пакет**, сумма **15,156 с**. DeepSeek: одна попытка
подготовки данных **$0,017529**, cache 56,08%, автоповторов 0.
Его отчёт нарушил тип `test_results`; ведущий принял только независимо
проверенный JSON-набор через `--accept-manual`, не заявление о тестах.

Ведущий написал оценщик, 8 unit-тестов прошли; результаты отдельно пересчитаны
из сохранённого JSON без вызова модели. Проверены SHA набора, все ID/метки,
пять нулевых стоимостей и передача ambiguous ведущему.

```powershell
# Только валидация, без сети:
python scripts/quality/evaluate_decisions.py
python -m pytest tests/unit/test_decisions_evaluation.py -q
# Повторный эксперимент расходует квоту; нужен новый каталог результата:
python scripts/quality/evaluate_decisions.py --live --out .agent-work/tmp/decisions-next-run
```

Набор: `tests/fixtures/decisions_tasks.json`; оценщик:
`scripts/quality/evaluate_decisions.py`. Сырые метаданные ответов/CSV:
`.agent-work/tmp/decisions-evaluation-20261010/results.json`, `cases.csv`.
SHA-256 набора: `4d29c0baf77e633a6748e1c484c4a8d52bbc638254ba032fab3669fbbdf7cd7b`.

**Граница:** маленький синтетический smoke-тест, не оценка качества на реальных
задачах. Пять задач разделяют контекст каждого запроса; независимых повторов,
отложенной выборки и проверки калибровки нет. Порог на результатах не подбирался.
Автоматическое распределение задач не включено. Следующий шаг при расширении —
отдельная более сложная публичная выборка с пограничными формулировками и
проверкой устойчивости, затем решение ведущего о применении только рекомендаций.

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
- worktree создаётся внутри каталога проекта, в `.agent-work/worktrees/nas-ds-<task>`, и содержит только файлы git;
- `security.deny_read` перечисляет текущие непосредственные файлы и каталоги основной копии,
  кроме `.agent-work`; маски закрывают архивы, временные результаты, `E:/agent_coordination`,
  `~/.claude`, `~/.config`, `~/.ssh` и типовые секреты. При добавлении нового каталога корня
  список обновляется. Это разрешения Claude Code, а не изоляция ОС: чужие worktree и выполнение
  кода технически не изолированы. Для документации разрешены только Read/Grep/Glob/Write/Edit;
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

OpenRouter update (2026-10-10): authentication verified; project configuration
pins the free router `openrouter/free` for optional second opinions on public
data. DeepSeek remains the executor; the lead owns permissions and acceptance.
The live catalog returned 458 models without matching decision models; however,
the owner's subsequent direct Decisions call succeeded with
`inception/mercury-decide-20260930`: documentation, 100 input/1 output tokens,
reported cost 0. One synthetic case verifies connectivity, not classifier quality.
Subsequent balanced synthetic evaluation: 25/25 correct across five classes,
five zero-cost batches (2127 input/25 output tokens), batch median 2.750 s.
The fixed advisory threshold admits 20 recommendations and escalates all five
ambiguous tasks. Dataset preparation by DeepSeek cost $0.017529; lead reviewed
labels before inference and independently recomputed results. Eight evaluator
unit tests passed. Small shared-context smoke test; no holdout, calibration,
production routing or permission automation is claimed.
The rankings page measures
usage, not coding quality. Free chat routing is not the Decisions API.

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
| Worker worktree | `.agent-work/worktrees/nas-ds-<task_id>`, branch `deepseek/<task_id>` |
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


### NAS/Spektr: эксперимент с семантикой здоровья, 2026-10-10

> Восстановлено 2026-10-12 (Claude): исходный русский текст Codex был сохранён как `?????`
> (запись из PowerShell без UTF-8) и утрачен. Раздел написан заново по уцелевшим числам,
> английскому резюме ниже и `results.json`; формулировки — не исходные.

Публичный синтетический набор по мотивам семантики Spektr — 12 случаев:
3 healthy, 3 fault, 6 unknown. Каждый случай — ряд из 96 значений с шагом 15 минут
(сутки) и короткий контекст: NAS endpoint, ночные нули, timeout и неоднозначные паузы.
Пропуски данных передаются как null. Это эксперимент NAS по мотивам Spektr, а не
повторение прикладных тестов Spektr; совместного прогона не было.

Проверялась бесплатная модель Decisions через OpenRouter — без DeepSeek, без fallback и
без платных моделей; пороги заданы заранее и не подстраивались под результат.
Итог `inception/mercury-decide-20260930`: **4/12 верно (33,3 %)**, 12 валидных
ответов, HTTP/транспортных ошибок 0. Recall healthy 1/3, fault 0/3, unknown 3/6.
Один ложный healthy; две неподтверждённые неисправности (fault), в том числе timeout,
признанный неисправностью. Timeout→fault прошёл с confidence **0,93347**
и margin **0,91859** — то есть через неизменённые пороги 0,90/0,20. Рекомендацией
прошёл только этот один ответ, и он ошибочен; остальные 11 эскалированы ведущему.

Стоимость API — **$0**, 3462 input / 12 output токенов. Задержки трёх пакетов
1,671 / 1,079 / 1,015 с, медиана 1,079 с. Живой E3 не вызывался, данные E3 в OpenRouter
не отправлялись. E3 по-прежнему строит статус детерминированно по собранным фактам, без LLM.

Код: `scripts/quality/evaluate_health_semantics.py`; 9 тестов в
`tests/unit/test_health_semantics_evaluation.py`, вместе с тестами Decisions — 17 passed.
Отчёт хранит ID случаев, модель, SHA набора и параметры порогов.
Данные/результаты: `.agent-work/tmp/health-semantics-20261010/fixtures.json`,
`results.json`. SHA-256:
`02522e253a7272ed0a261269679366425a36f21db31e83e1d872f89e7a2c6365`.
Повтор без сети: `python scripts/quality/evaluate_health_semantics.py`.
Живой вызов — только с `--live` и записью в `--out`.
Вывод: модель не допускается как источник статуса E3.

> ⚠️ **Отзыв 2026-10-12 (Claude).** Порча кодировки задела не только этот раздел:
> русский контекст случаев в `scripts/quality/evaluate_health_semantics.py` и в
> `fixtures.json` тоже сохранён как `?????` (в скрипте 12 таких строк и ни одной
> кириллической буквы). Модель получала ряды чисел и вопросительные знаки вместо описания.
> Значит, 4/12 — оценка поведения на нечитаемом контексте, **а не точности понимания**.
> Вывод «не источник статуса» остаётся в силе (уверенность 0,933 на нечитаемом входе его
> только подкрепляет), но цифру точности нельзя цитировать до повтора на исправленных данных.
> В `tests/fixtures/decisions_tasks_boundary.json` есть 4 такие строки — результат 24/25
> на граничном наборе тоже перепроверить.

EN: 12 public synthetic health-evidence cases inspired by Spektr; free Decisions
scored 4/12. Timeout incorrectly became a confirmed fault at confidence 0.933,
passing unchanged thresholds. API $0, 17 evaluator tests passed. No live E3
or joint Spektr execution; deterministic evidence remains the source of truth.
**Revoked 2026-10-12:** the Russian case context in the evaluator and fixtures was saved
as `?????`, so the model saw numbers and question marks; 4/12 does not measure semantic
accuracy. Re-run on repaired data before quoting it; re-check the 24/25 boundary result too.
