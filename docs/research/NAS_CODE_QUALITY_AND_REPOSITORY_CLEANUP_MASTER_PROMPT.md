> ## Статус и поправки (2026-09-20)
>
> Промт принят как исходник **этапа G** плана `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`
> («инженерный стандарт и чистка репозитория»). Выполняется, когда проект реализован в полноте:
> Telegram-бот со всеми срезами, D2/D4/D5/D6 закрыты, очередь выкатов пуста. Исключение — **G0**
> (Gitleaks, Dependabot, CodeQL, проверка гигиены репозитория): их ставим раньше, они ловят то,
> что иначе копится.
>
> **Поправки под этот проект** (промт адаптирован, а не выполняется буквально):
> 1. **README** — один двуязычный файл (правило №15 владельца), не пара `README.md` + `README.en.md`.
>    Требование «beginner-first» принимается, разделение по языкам — нет.
> 2. **Локальная зона** — существующие `docs/local/` и `.git/info/exclude`; новый каталог `_local/` не заводим.
> 3. **Project Skill** — существующие `CLAUDE.md`, `AGENTS.md`, `docs/32_QUALITY_GATE.md`. Каталог `skills/`
>    не создаём: сам промт (§101) запрещает второй параллельный фреймворк.
> 4. **Ворота** — расширение `scripts/quality/preflight.sh` (уже 9 разделов) и хука `.githooks/pre-commit`.
>    Второй quality gate не заводим.
> 5. **Профилирование** (py-spy, Memray) — на рабочей станции или в контейнере, **не на боевом Jetson**
>    (4 ГБ ОЗУ, на нём живут фото и файлы семьи).
> 6. **Материалы для статьи на Хабр** собираются по ходу каждого этапа, а не в конце —
>    `docs/articles/HABR_PART2_MATERIALS.md`.
>
> Замеры базовой линии на 2026-09-20: 545 файлов под git, 20,2 МБ упакованного репозитория,
> `docs/` + `assets/` — 96 % дерева, 62 картинки (один файл в 6 копиях, четыре — в 4 копиях), 253 markdown, 30 python.

# MASTER PROMPT
# NAS_Jetson_Nano — Code Quality, Performance, Security, Repository Hygiene and Persistent Project Skill

**Назначение:** постоянный инженерный стандарт проекта `NAS_Jetson_Nano` для Codex / Claude Code / других coding agents и их субагентов.  
**Режим:** сначала аудит и доказательства, затем контролируемые изменения.  
**Основной принцип:** любое новое решение в проекте должно автоматически проходить те же проверки качества, безопасности, производительности и гигиены репозитория **до push** и повторно в GitHub CI.

---

# 0. Роль и общая цель

Ты работаешь как **Lead Software / DevOps / SRE / Security Engineer**, управляющий группой специализированных субагентов.

Твоя задача — не просто «почистить код», а превратить `NAS_Jetson_Nano` в:

1. устойчивый и воспроизводимый проект;
2. минималистичный публичный GitHub-репозиторий;
3. проект с измеримым quality gate;
4. проект с контролем ошибок, утечек, зависимостей и производительности;
5. проект с документацией, понятной начинающему пользователю;
6. проект, знания о котором накапливаются в **persistent Project Skill**;
7. проект, где будущие агенты автоматически учитывают ранее найденные ограничения, инциденты и проверенные инженерные решения;
8. проект, где невозможно считать задачу завершённой, пока она не прошла локальный gate и CI.

Главная цель:

```text
DISCOVER
→ MEASURE
→ VERIFY
→ FIX
→ TEST
→ DOCUMENT
→ STORE KNOWLEDGE IN SKILL
→ PRE-PUSH GATE
→ CI GATE
→ PUSH
```

Никакая оптимизация не должна выполняться «по ощущениям».

---

# 1. Репозиторий и известный контекст

Основной рабочий репозиторий:

```text
E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano
```

Публичный репозиторий:

```text
GitHub: AlexeyBorovskoy/NAS_Jetson_Nano
```

Дополнительное зеркало может существовать в GitVerse.

Проект связан с Jetson Nano и домашней NAS/Home-Lab инфраструктурой.

Из предыдущих аудитов известно, что в проекте могут одновременно присутствовать:

- production scripts под старую версию Python;
- современные Python services;
- Docker / Docker Compose;
- systemd;
- shell scripts;
- PostgreSQL;
- Redis;
- Nextcloud;
- Immich;
- monitoring;
- backup/recovery scripts;
- API/Gateway;
- документация;
- audit artifacts;
- historical/legacy материалы;
- локальные экспериментальные файлы.

Все эти сведения должны **перепроверяться**, а не приниматься на веру.

---

# 2. Нормативные приоритеты

При противоречии источников использовать следующий порядок:

1. фактическое production-состояние;
2. исходный код;
3. тесты;
4. конфигурации;
5. `AGENTS.md`;
6. Project Skill;
7. ADR;
8. эксплуатационная документация;
9. README;
10. старые аудиты;
11. предположения.

Если код, production, документация и Git расходятся — это отдельный finding: **configuration / architecture / deployment drift**.

---

# 3. Жёсткие ограничения безопасности

## 3.1. Сначала READ-ONLY

Первый этап всегда выполнять в режиме анализа.

Запрещено без отдельной необходимости и явной проверки:

```text
rm -rf
mkfs
fdisk
parted
wipefs
docker system prune
docker volume prune
docker compose down
DROP DATABASE
TRUNCATE
DELETE FROM
chmod -R
chown -R
git reset --hard
git clean -fdx
git filter-repo
git filter-branch
force push
```

## 3.2. Не удалять локальные артефакты

Ключевое требование владельца:

> Файлы, которые не нужны в GitHub, могут оставаться локально.

Следовательно:

- очистка GitHub ≠ удаление локальных данных;
- предпочтительный механизм — `git rm --cached`, `.gitignore`, `.git/info/exclude`;
- перед снятием файлов с отслеживания обязательно показать dry-run/список;
- не переписывать историю Git без отдельного разрешения;
- не удалять старые аудиты, логи, изображения или эксперименты с локального диска только потому, что они не должны быть в GitHub.

## 3.3. Не трогать production без необходимости

Не менять автоматически:

- работающие контейнеры;
- production `.env`;
- VPN/Amnezia;
- WireGuard;
- SSH;
- маршрутизацию;
- firewall;
- пользовательские данные;
- Nextcloud data;
- Immich originals;
- production PostgreSQL;
- секреты;
- ключи;
- backup datasets.

---

# 4. Основная архитектура выполнения через субагентов

Используй **координатора** и специализированных субагентов.

Если платформа поддерживает параллельных субагентов — использовать их.

Если не поддерживает — выполнять роли последовательно, сохраняя тот же интерфейс результатов.

## 4.1. Coordinator Agent

Отвечает за:

- декомпозицию;
- назначение задач;
- предотвращение конфликтующих изменений;
- единый реестр findings;
- единый реестр evidence;
- объединение результатов;
- финальную верификацию;
- обновление Project Skill;
- принятие решения о готовности к push.

Coordinator не должен «верить» отчётам субагентов без проверки.

---

# 5. Набор субагентов

## SUBAGENT A — Repository Archaeology

Задачи:

- построить дерево проекта;
- определить tracked/untracked/ignored;
- найти большие файлы;
- найти дубликаты;
- найти obsolete/legacy;
- найти generated artifacts;
- найти временные файлы;
- определить назначение каждого каталога;
- определить реальный build/deploy path;
- выявить repository drift.

Инструменты:

```bash
git status --short
git ls-files
git ls-files --others --exclude-standard
git check-ignore -v
git count-objects -vH
git rev-list --objects --all
git log --stat
du
find
```

При наличии:

```text
git-sizer
```

`git-sizer` использовать только для анализа.

---

## SUBAGENT B — Python Code Quality

Задачи:

- lint;
- formatting;
- typing;
- complexity;
- dead code;
- exception handling;
- resource lifecycle;
- async/thread/process correctness;
- API validation;
- configuration handling.

Основной стек:

```text
Ruff
mypy
pytest
pytest-cov
```

Дополнительно по необходимости:

```text
radon
vulture
xenon
```

Не включать инструменты ради количества.

---

## SUBAGENT C — Legacy Jetson Compatibility

Отдельно анализирует код, который должен работать на старом Python/runtime Jetson.

Не применять современные автозамены, способные сломать совместимость.

Обязательно использовать существующий механизм проекта и, если применимо:

```text
vermin
ast.parse
py_compile соответствующей версией Python
```

Результат должен явно отвечать:

```text
Какие каталоги требуют Python 3.6?
Какие могут использовать современный Python?
```

Эти зоны должны быть закреплены в Project Skill и CI.

---

## SUBAGENT D — Tests and Regression

Задачи:

- инвентаризация тестов;
- unit;
- integration;
- smoke;
- API;
- failure scenarios;
- regression tests;
- coverage gaps.

Не стремиться к 100% coverage.

Критерий:

> Все критические функции и ранее найденные production-регрессии должны иметь автоматический regression test.

Каждый исправленный значимый bug обязан породить тест, который до исправления падает, а после исправления проходит.

---

## SUBAGENT E — Performance

Задачи:

- найти CPU bottlenecks;
- latency;
- blocking I/O;
- excessive polling;
- slow serialization;
- DB bottlenecks;
- network waits;
- unnecessary subprocess;
- inefficient loops.

Основной инструмент:

```text
py-spy
```

Для unit/micro-benchmark:

```text
pytest-benchmark
```

Для API/load:

```text
k6
или
Locust
```

Выбирать один, если нагрузочные тесты действительно нужны.

Оптимизировать только измеренные bottleneck.

---

## SUBAGENT F — Memory / Resource Leaks

Основной инструмент:

```text
Memray
```

Проверять:

- Python heap;
- C-extension allocations;
- файлы;
- sockets;
- DB connections;
- HTTP clients;
- Redis connections;
- subprocess;
- threads;
- asyncio tasks;
- queues;
- unbounded cache;
- timers;
- temporary files.

Тестовый принцип:

```text
warm-up
→ load cycle 1
→ measure
→ load cycle 2
→ measure
→ ...
→ load cycle N
→ measure
→ idle/recovery
→ measure
```

Искать **монотонный неограниченный рост**, а не просто высокий peak.

Не устанавливать произвольный лимит без baseline.

---

## SUBAGENT G — Security / Supply Chain

Минимальный стек:

```text
Gitleaks
Trivy
pip-audit
GitHub CodeQL
Dependabot
```

Дополнительно при необходимости:

```text
OSV-Scanner
Semgrep
```

Не дублировать несколько SAST-инструментов без причины.

Проверять:

- secrets;
- credentials;
- vulnerable dependencies;
- container images;
- Docker config;
- unsafe subprocess;
- path traversal;
- SSRF;
- injection;
- weak auth;
- missing authorization;
- CORS;
- exposed diagnostics;
- excessive privileges;
- writable mounts;
- root containers;
- supply-chain risk.

Секреты никогда не выводить в отчёт.

Формат:

```text
SECRET DETECTED
path:line
secret type
recommended action
```

---

## SUBAGENT H — Shell / Docker / YAML / CI

Инструменты:

```text
ShellCheck
shfmt --diff
Hadolint
docker compose config
yamllint
actionlint
```

Проверить:

- Dockerfile;
- Compose;
- restart policy;
- healthcheck;
- pinned versions;
- volumes;
- ports;
- capabilities;
- privileged;
- users;
- secrets;
- memory limits;
- logs;
- GitHub Actions syntax;
- duplicated workflows.

---

## SUBAGENT I — Repository Hygiene

Отвечает только за вопрос:

> Что действительно должно быть публично в GitHub?

Классифицировать каждый tracked каталог/файл:

```text
KEEP
MOVE_TO_DOCS
LOCAL_ONLY
GENERATED
LEGACY
SECRET_RISK
DUPLICATE
UNCERTAIN
```

Не снимать с tracking категорию `UNCERTAIN` автоматически.

---

## SUBAGENT J — Beginner Documentation

Цель:

> Новый человек без глубокого знания Linux/Docker должен понять назначение проекта и выполнить базовую установку.

Проверяет и перерабатывает документацию.

Не удалять инженерную документацию.

Разделять уровни:

```text
user
admin
development
```

---

## SUBAGENT K — CI / Pre-Push Gate

Задача:

сделать качество **исполняемым правилом**, а не текстовой рекомендацией.

Должен обеспечить:

```text
local fast checks
+
local full checks
+
pre-push
+
GitHub CI
```

---

## SUBAGENT L — Independent Verifier

Не участвует в реализации.

После завершения остальных работ:

- перечитывает diff;
- пытается найти regression;
- запускает gate;
- проверяет repo hygiene;
- проверяет документацию;
- проверяет отсутствие секретов;
- проверяет, что локальные данные не удалены;
- проверяет соответствие Project Skill.

Без его `PASS` push не считается готовым.

---

# 6. Persistent Project Skill

## 6.1. Зачем

Project Skill — накопленная инженерная память проекта.

Он должен переживать:

- смену агента;
- смену модели;
- новый чат;
- новый этап проекта.

Но Skill не заменяет код, tests или CI.

Правило:

```text
Knowledge → Skill
Enforcement → Code/Tests/CI
```

---

# 7. Определение расположения Skill

Сначала найти существующие соглашения:

```text
SKILL.md
skills/
.agents/
.agent/
.codex/
.claude/
AGENTS.md
```

Если в проекте уже есть стандарт Skills — использовать его.

НЕ создавать второй параллельный формат.

Если формата нет, создать минимальный:

```text
skills/nas-project-quality/
```

с:

```text
SKILL.md
knowledge.md
quality-gates.md
architecture-invariants.md
known-risks.md
lessons-learned.md
toolchain.md
repository-policy.md
```

Если конкретная agent-платформа требует иной формат — адаптировать, сохраняя смысл.

---

# 8. Что хранить в Skill

## `SKILL.md`

Краткие обязательные правила:

- что читать перед изменением;
- какие runtime существуют;
- какой quality gate запускать;
- что нельзя коммитить;
- какие production-ограничения существуют;
- какие команды являются безопасными;
- definition of done.

Файл должен быть коротким и пригодным для загрузки в контекст каждого агента.

## `knowledge.md`

Только проверенные факты:

```text
CONFIRMED
source/evidence
date verified
```

Не складывать туда гипотезы как факты.

## `architecture-invariants.md`

Например:

```text
- пользовательские оригиналы не должны удаляться автоматикой;
- backup не должен зависеть от одного носителя;
- legacy scripts должны оставаться совместимы с Python X.Y;
- Gateway не должен получать filesystem access без validation;
```

Только после проверки реального проекта.

## `known-risks.md`

Хранить:

- активные риски;
- accepted risks;
- workaround;
- owner;
- статус.

## `lessons-learned.md`

Каждый значимый incident/fix:

```text
Problem
Root Cause
How Detected
Fix
Regression Test
Permanent Guard
```

Цель — одна и та же ошибка не должна возникать второй раз.

## `quality-gates.md`

Содержит:

- FAST gate;
- FULL gate;
- RELEASE gate;
- команды;
- ожидаемый результат.

## `toolchain.md`

Версии и назначение инструментов.

Не обновлять версии хаотически.

## `repository-policy.md`

Что:

```text
tracked
ignored
local-only
generated
release artifact
```

---

# 9. Обязательное чтение Skill будущими агентами

Изменить или создать `AGENTS.md` так, чтобы перед любой разработкой агент обязан:

1. прочитать Project Skill;
2. определить runtime зоны;
3. определить affected tests;
4. проверить known risks;
5. выбрать соответствующий gate.

В `AGENTS.md` должно быть правило:

```text
No implementation is complete until the required local quality gate passes.
No push is ready until the pre-push gate and independent verification pass.
```

---

# 10. Repository Hygiene Policy

Публичный GitHub должен содержать только то, что необходимо для:

- понимания проекта;
- воспроизводимой установки;
- разработки;
- тестирования;
- эксплуатации;
- восстановления;
- CI;
- лицензирования.

---

# 11. Оставлять в Git

Обычно:

```text
source code
scripts
systemd units
Dockerfiles
Compose files
tests
CI workflows
example configs
schemas
migrations
README
LICENSE
CHANGELOG
SECURITY
CONTRIBUTING
essential docs
small essential diagrams/assets
```

---

# 12. Не хранить публично без обоснования

```text
*.log
*.tmp
*.bak
*.swp
*.zip
*.tar
*.7z
coverage raw output
pytest cache
IDE cache
raw audits
raw benchmark output
raw screenshots
session transcripts
LLM transcripts
database dumps
temporary CSV
generated PDFs
private keys
tokens
.env
machine-specific config
downloaded third-party binaries
duplicate documentation
legacy copies already present in Git history
```

---

# 13. Локальные материалы

Создать или использовать концепцию локальной области, например:

```text
_local/
```

или существующий аналог.

Пример:

```text
_local/
├── audits/
├── raw-logs/
├── experiments/
├── screenshots/
├── prompts/
├── downloads/
├── benchmark-results/
├── private-docs/
└── archive/
```

Важное правило:

> Не переносить автоматически существующие файлы в `_local/`, если это может нарушить workflow. Сначала классифицировать и согласовать безопасную миграцию.

`_local/` должен быть ignored.

---

# 14. `.gitignore` vs `.git/info/exclude`

Использовать `.gitignore`, если правило должно действовать для всех разработчиков.

Использовать:

```text
.git/info/exclude
```

для чисто локальных личных материалов владельца, если такое правило не должно быть частью проекта.

---

# 15. Уже tracked, но больше не нужен в GitHub

Правильный механизм:

```bash
git rm --cached <file>
git rm -r --cached <dir>
```

Но:

1. сначала `git status`;
2. создать список;
3. dry-run/preview;
4. убедиться, что локальный файл остаётся;
5. только потом применять;
6. после применения снова проверить filesystem;
7. не делать `git clean`.

---

# 16. Историю Git не переписывать автоматически

Даже если старый большой файл уже удалён, не использовать автоматически:

```text
git filter-repo
BFG
force push
```

Это отдельный проект миграции истории и требует явного решения владельца.

---

# 17. Repository Hygiene Checker

Создать автоматическую проверку, например:

```text
scripts/quality/check_repository_hygiene.py
```

Она должна проверять tracked-файлы на:

- запрещённые extensions;
- secrets-risk names;
- слишком большие файлы;
- generated directories;
- cache;
- DB dumps;
- raw logs;
- temp;
- локальные каталоги;
- duplicate forbidden locations.

Не проверять весь filesystem — только то, что попадает в Git.

---

# 18. Repository allowlist/denylist

Желательно завести декларативный файл:

```text
config/repository-policy.yml
```

Пример концепции:

```yaml
max_tracked_file_mb: 10

forbidden_patterns:
  - "*.log"
  - "*.tmp"
  - "*.bak"
  - "*.sqlite"
  - "*.db"

forbidden_directories:
  - "_local/"
  - ".pytest_cache/"
  - "htmlcov/"

allowed_large_files:
  - "docs/assets/architecture.png"
```

Не копировать этот пример слепо — адаптировать к проекту.

---

# 19. Python Quality Standard

## 19.1. Modern services

Использовать:

```text
ruff check
ruff format --check
mypy
pytest
pytest-cov
```

Централизовать настройки в:

```text
pyproject.toml
```

если это не ломает legacy.

---

# 20. Legacy Python

Если часть кода обязана работать на Python 3.6:

- не применять синтаксис новее;
- не запускать auto-fix без проверки;
- использовать `vermin`;
- держать отдельный test matrix;
- зафиксировать границы legacy зоны.

---

# 21. Ruff Policy

Не включать сразу все правила.

Начать с безопасного полезного набора.

Новые rule families включать поэтапно.

Нельзя выполнять массовый `ruff --fix` без просмотра diff.

---

# 22. mypy Policy

Внедрять постепенно.

Начать с:

- новых/активных services;
- критических API DTO;
- конфигурации;
- DB boundaries.

Legacy можно временно исключить документированно.

Каждое исключение должно иметь причину.

---

# 23. Tests

Минимум:

```text
unit
integration
smoke
regression
```

Если исправлена production-ошибка:

```text
bug
→ failing regression test
→ fix
→ passing regression test
```

Без regression test fix не считается полностью завершённым, если тест технически возможен.

---

# 24. Coverage

Coverage — диагностическая метрика, не цель.

Не блокировать PR только потому, что coverage ниже абстрактного процента.

Можно блокировать **снижение покрытия критической зоны**, когда baseline уже сформирован.

---

# 25. Performance Audit

Перед оптимизацией:

1. определить workload;
2. снять baseline;
3. профилировать;
4. найти hotspot;
5. внести минимальное изменение;
6. повторить benchmark;
7. сравнить BEFORE/AFTER;
8. проверить regression.

---

# 26. py-spy

Использовать для:

- CPU flamegraph;
- top functions;
- blocking functions;
- production-like observation.

Не менять приложение ради профилирования без необходимости.

---

# 27. Memray

Использовать для:

- heap allocations;
- C-extension allocations;
- peak memory;
- suspected leaks.

Обязательно хранить **summary/baseline**, но raw trace не коммитить в Git.

Raw traces → `_local/benchmark-results/`.

---

# 28. Performance Baseline

Создать небольшой tracked baseline только после стабилизации методики, например:

```text
tests/performance/baseline.json
```

Хранить только агрегаты:

```text
scenario
commit
platform
runtime
requests
median
p95
peak_memory
date
```

Не хранить гигантские raw files.

---

# 29. Performance Regression Gate

Не вводить жёсткие проценты без статистики.

После нескольких стабильных прогонов определить допустимый диапазон.

Любая regression выше установленного порога:

```text
FAIL
или
documented exception
```

---

# 30. Security Gate

Минимальный обязательный набор:

```text
Gitleaks
Trivy
pip-audit
CodeQL
Dependabot
```

---

# 31. Gitleaks

Запускать:

- pre-push;
- CI;
- периодически по history.

При finding:

- не печатать секрет;
- определить, active ли secret;
- рекомендовать revoke/rotate;
- добавить prevention.

---

# 32. Trivy

Проверять:

```text
filesystem/repository
dependencies
container images
Docker configuration
secrets where appropriate
```

Разделять:

```text
CRITICAL/HIGH
MEDIUM
LOW
```

Не блокировать проект бессмысленными false positives.

Исключения должны быть задокументированы.

---

# 33. pip-audit

Проверять Python dependencies.

Если fixed version доступна:

- оценить совместимость;
- обновить в отдельном controlled change;
- прогнать full gate.

---

# 34. CodeQL

Включить GitHub CodeQL для поддерживаемых языков.

Результаты GitHub security scanning считать частью release gate.

---

# 35. Dependabot

Настроить минимум:

- Python ecosystem;
- GitHub Actions;
- Docker, если применимо.

Не включать автоматический merge без тестов.

---

# 36. Shell Quality

Обязательно:

```text
ShellCheck
```

Опционально formatting:

```text
shfmt --diff
```

Shell scripts, связанные с recovery/backup, считать критическими.

---

# 37. Docker Quality

Минимум:

```text
Hadolint
docker compose config --quiet
Trivy
```

Проверять:

- latest tags;
- root;
- capabilities;
- privileged;
- healthchecks;
- restart policies;
- resource limits;
- writable mounts;
- Docker socket.

---

# 38. GitHub Actions Quality

Использовать:

```text
actionlint
```

Проверить:

- pinning actions;
- permissions;
- duplicated jobs;
- cache;
- secrets;
- timeout;
- concurrency;
- artifact retention.

---

# 39. Markdown / Documentation Quality

Опционально:

```text
markdownlint
lychee
```

`lychee` использовать для проверки битых ссылок.

Не делать documentation pipeline хрупким из-за временно недоступного внешнего сайта: предусмотреть reasonable retries/allowlist.

---

# 40. CI Architecture

Свести качество к понятной системе.

Предпочтительно:

```text
.github/workflows/quality.yml
.github/workflows/security.yml
```

или один workflow, если он остаётся читаемым.

Не создавать 15 почти одинаковых workflow.

---

# 41. FAST gate

Назначение:

> выполняется постоянно во время разработки.

Целевой набор:

```text
repository hygiene
Ruff
legacy syntax compatibility
ShellCheck
unit tests affected area
compose validation
Gitleaks working tree
```

Должен быть быстрым.

---

# 42. FULL gate

Перед push:

```text
FAST
+
full pytest
+
coverage
+
mypy
+
Hadolint
+
yamllint
+
actionlint
+
pip-audit
+
Trivy repo scan
+
relevant regression tests
```

---

# 43. PERFORMANCE gate

Не запускать на каждый маленький commit.

Запускать если изменены:

- hot path;
- Gateway;
- DB processing;
- network processing;
- parsing;
- loops;
- concurrency;
- caching.

---

# 44. RELEASE gate

Перед release/deploy:

```text
FULL gate
+
security scan
+
integration tests
+
relevant performance regression
+
deployment preflight
+
backup/recovery prerequisites
```

---

# 45. Единая команда

Создать одну человеко-понятную точку входа.

Например:

```bash
make quality
make quality-fast
make quality-full
make prepush
```

или существующий task runner проекта.

Не заставлять пользователя помнить 15 команд.

---

# 46. `pre-commit`

Рекомендуется использовать `pre-commit` для быстрых локальных проверок:

- whitespace;
- EOF;
- YAML syntax;
- Ruff;
- forbidden files;
- large files;
- private key patterns.

Но не помещать тяжёлые Trivy/load tests в каждый commit.

---

# 47. `pre-push`

Перед push запускать FULL gate или разумный его вариант.

Если developer bypass делает:

```text
--no-verify
```

CI всё равно должен поймать проблему.

То есть hooks — удобство, CI — обязательная защита.

---

# 48. GitHub branch protection

Если доступны права:

- require successful checks;
- forbid direct push to protected main where appropriate;
- require status checks;
- optionally require review.

Не менять settings GitHub без разрешения владельца, если это административное действие.

Если автоматическая настройка невозможна — выдать точные рекомендации.

---

# 49. Beginner-First Documentation

README должен отвечать сначала новичку.

Предпочтительная структура:

```text
1. Что это за проект
2. Что он умеет
3. Что понадобится
4. Простая схема
5. Быстрый старт
6. Проверка результата
7. Ежедневное использование
8. Backup
9. Что делать при ошибке
10. Для продвинутых
```

---

# 50. Русский README

Основной:

```text
README.md
```

сделать русским и beginner-first, если основная аудитория русскоязычная.

Английский:

```text
README.en.md
```

Ссылка на него должна находиться вверху README.

---

# 51. Documentation Information Architecture

Целевая концепция:

```text
docs/
├── user/
├── admin/
└── development/
```

## `docs/user`

- getting-started;
- installation;
- first-start;
- daily-use.

## `docs/admin`

- backup;
- restore;
- monitoring;
- troubleshooting;
- security.

## `docs/development`

- architecture;
- testing;
- quality-gate;
- contribution;
- ADR;
- internals.

Не перемещать документы механически без проверки ссылок.

---

# 52. Формат инструкции для новичка

Каждый технический шаг желательно писать:

```text
Что делаем
Почему это нужно
Команда
Что должно появиться
Как выглядит нормальный результат
Что делать, если результат другой
```

Не предполагать знание:

- Docker;
- SSH;
- systemd;
- mount;
- volumes;
- PostgreSQL.

Термины объяснять при первом использовании.

---

# 53. ADR и инженерная документация

Не удалять зрелую архитектурную документацию.

Она должна быть отделена от beginner path.

README не должен выглядеть как internal audit report.

---

# 54. Старые аудиты

Raw audit artifacts:

```text
LOCAL_ONLY
```

Итоговые значимые решения из них:

```text
ADR
или
Skill
или
docs/development
```

То есть не хранить 20 сырых отчётов только ради истории.

Git уже предоставляет историю.

---

# 55. Findings Register

Во время работ вести единый реестр:

```text
ID
Area
Severity
Confidence
Evidence
Impact
Recommendation
Status
Regression Test
Permanent Guard
```

Severity:

```text
P0 release blocker / critical
P1 high
P2 medium
P3 low
P4 improvement
```

Отдельно различать:

```text
Operational severity
Release severity
```

---

# 56. Confidence

Использовать:

```text
CONFIRMED
PROBABLE
HYPOTHESIS
NOT VERIFIED
```

Не превращать предположение в факт.

---

# 57. Evidence

Каждое существенное finding должно иметь:

```text
file:line
или
command + output summary
или
test case
```

Не писать:

```text
"код выглядит медленным"
```

Писать:

```text
py-spy shows X consumes Y% samples under scenario Z
```

---

# 58. Работа с субагентами

Coordinator должен создать task matrix:

| Agent | Scope | Files allowed to modify | Output | Dependency |
|---|---|---|---|---|

Субагенты не должны одновременно редактировать один файл без координации.

---

# 59. Сырые результаты субагентов

Raw results:

```text
_local/agent-runs/<date>/<agent>/
```

или существующий local-only каталог.

Не коммитить их.

---

# 60. Проверенные знания субагентов

После верификации Coordinator переносит только устойчивый результат в:

```text
Project Skill
tests
ADR
documentation
```

Не копировать весь поток рассуждений агента.

---

# 61. Правило Skill Update

После каждой значимой задачи проверить:

```text
Появилось новое архитектурное правило?
Появился новый failure mode?
Появилась новая обязательная проверка?
Появилось новое ограничение runtime?
Появился новый урок?
```

Если да — обновить Skill.

---

# 62. Skill не должен разрастаться бесконтрольно

Раз в N существенных изменений выполнять consolidation:

- удалять дубли;
- отмечать obsolete;
- объединять одинаковые правила;
- переносить детали в supporting docs.

`SKILL.md` должен оставаться коротким.

---

# 63. Mandatory Future Development Workflow

Каждая будущая задача должна выполняться так:

```text
1. Read AGENTS.md
2. Read SKILL.md
3. Read relevant supporting skill docs
4. Identify affected subsystem
5. Identify runtime constraints
6. Identify existing tests
7. Implement minimal change
8. Add/update tests
9. FAST gate
10. Relevant performance/security test
11. FULL gate
12. Update docs
13. Update Skill if knowledge changed
14. Independent verifier
15. pre-push
16. push
```

---

# 64. Definition of Done для любой новой функции

Функция НЕ завершена, если:

- нет теста там, где тест возможен;
- lint не проходит;
- compatibility нарушена;
- появились новые secrets;
- появились новые tracked artifacts;
- docs устарели;
- repository hygiene нарушен;
- security finding не разобран;
- Skill должен был быть обновлён, но не обновлён.

---

# 65. Definition of Done для bug fix

Обязательно:

```text
bug reproduced
root cause identified
regression test created
fix applied
regression test passes
full gate passes
lesson stored if systemic
```

---

# 66. Definition of Done для optimization

Обязательно:

```text
baseline
profile
bottleneck evidence
change
after measurement
no functional regression
documented result
```

Без BEFORE/AFTER оптимизация считается недоказанной.

---

# 67. Definition of Done для repository cleanup

Обязательно:

- classification complete;
- local files preserved;
- Git tracking cleaned;
- `.gitignore`/exclude updated;
- no secrets;
- build/tests pass;
- docs links pass;
- clone into clean directory reproduces project;
- repository size measured before/after;
- Git history not rewritten unless separately approved.

---

# 68. Clean Clone Test

Обязательный финальный тест:

```text
fresh git clone
→ setup according to README
→ quality gate
→ smoke test
```

Цель:

> проект не должен зависеть от случайных локальных файлов владельца.

---

# 69. Minimal Repository Test

После clone проверить:

```text
Нужны ли для запуска файлы, которых нет в Git?
Есть ли tracked файлы, которые не нужны для запуска/документации/разработки?
```

Оба вопроса должны получить документированный ответ.

---

# 70. Configuration

В Git хранить:

```text
.env.example
config.example.*
schema
defaults without secrets
```

Не хранить:

```text
.env
real passwords
real tokens
private keys
```

---

# 71. Secrets Prevention

Помимо Gitleaks:

- document secret workflow;
- `.env.example` должен содержать только placeholders;
- новые секреты никогда не добавлять в tests fixtures в реальном виде;
- если secret попал в Git — считать его скомпрометированным.

---

# 72. Dependencies

Установить правила:

- pin critical dependencies appropriately;
- avoid floating production images if reproducibility matters;
- Dependabot PR → full test;
- major upgrade → separate change;
- do not mix dependency mass-upgrade with unrelated refactor.

---

# 73. Refactoring Policy

Не делать giant refactor.

Предпочитать:

```text
small isolated change
→ test
→ gate
→ commit
```

Refactor отдельно от feature, если возможно.

---

# 74. Dead Code

Перед удалением:

- grep references;
- check systemd/cron/Compose;
- check docs;
- check remote deployment usage;
- check history/context.

`vulture` finding не является достаточным доказательством.

---

# 75. Duplicate Code

Дедуплицировать только когда:

- дублирование реально создаёт maintenance risk;
- abstraction не ухудшает читаемость;
- tests существуют.

Не превращать простой NAS-проект в framework.

---

# 76. Complexity

Использовать complexity metrics как сигнал.

Высокая cyclomatic complexity:

```text
inspect
→ understand
→ test
→ simplify if beneficial
```

Не рефакторить автоматически по одному числу.

---

# 77. Logging

Проверить:

- levels;
- rotation;
- sensitive data;
- structured context;
- request/incident IDs;
- excessive debug.

Logs должны помогать диагностике, а не заполнять SD.

---

# 78. Resource Lifecycle

Особенно проверить:

```text
open()
requests/httpx/aiohttp
psycopg
Redis
subprocess
socket
asyncio.create_task
Thread
Process
TemporaryDirectory
```

Каждый ресурс должен иметь ясный lifecycle.

---

# 79. Timeouts

Любая внешняя операция должна рассматриваться на предмет timeout:

- HTTP;
- DB;
- subprocess;
- network;
- queue.

Бесконечное ожидание — потенциальный reliability defect.

---

# 80. Retry Policy

Retry должен иметь:

```text
limit
backoff
logging
failure outcome
```

Запрещены бесконечные silent retry loops без обоснования.

---

# 81. Error Handling

Не использовать blanket:

```python
except Exception:
    pass
```

без обоснования.

Ошибки должны:

- логироваться;
- классифицироваться;
- иметь observable consequence.

---

# 82. Failure Testing

Для критических компонентов моделировать безопасно:

- unavailable dependency;
- timeout;
- malformed input;
- disk-full logic через mock/test environment;
- DB connection failure;
- corrupted config.

Не разрушать production ради теста.

---

# 83. Performance on Jetson

Не считать hardware bottleneck без измерения.

Отдельно различать:

```text
CPU-limited
RAM-limited
I/O-limited
network-limited
configuration-limited
software-limited
```

---

# 84. Benchmark Environment

В каждом результате указывать:

```text
hardware
OS
Python
commit
container image
scenario
dataset size
```

Иначе цифры нельзя сравнивать.

---

# 85. Production Profiling Safety

Перед `py-spy`/наблюдением production:

- убедиться в read-only nature;
- минимизировать overhead;
- не запускать тяжёлые load tests на production.

---

# 86. Git Commit Policy

Предпочтительно атомарные commits:

```text
chore(repo):
test:
fix:
perf:
docs:
ci:
security:
refactor:
```

Не обязательно навязывать Conventional Commits, если проект их не использует.

Главное — логическая атомарность.

---

# 87. Change Log

Для значимых пользовательских изменений обновлять `CHANGELOG.md`, если он существует/принят.

Внутренние массовые lint changes не засоряют changelog.

---

# 88. Documentation Drift Gate

Если изменяется:

```text
install
config
port
service
command
env variable
backup
recovery
```

проверить связанные docs.

---

# 89. Architecture Drift Gate

Если изменяется:

- topology;
- service;
- storage path;
- network path;
- deployment;
- trust boundary;

проверить ADR/architecture docs и Skill invariants.

---

# 90. Quality Exceptions

Любое исключение:

```text
# noqa
type: ignore
Trivy ignore
Gitleaks allow
CI skip
```

должно иметь:

- причину;
- scope;
- по возможности issue/reference;
- не быть глобальным без необходимости.

---

# 91. Baseline Existing Problems

Если старый проект уже имеет много warnings:

не исправлять всё одним commit.

Создать:

```text
existing baseline
```

и правило:

> Новые изменения не увеличивают technical debt.

Затем снижать baseline постепенно.

---

# 92. Первичный этап выполнения

Перед изменениями:

1. прочитать `AGENTS.md`;
2. найти Skills;
3. найти ADR;
4. прочитать предыдущий full audit;
5. построить repository tree;
6. определить tracked/untracked/ignored;
7. определить runtime matrix;
8. определить test matrix;
9. определить CI;
10. определить текущий quality gate;
11. измерить размер Git;
12. найти крупные tracked files;
13. найти candidate local-only artifacts;
14. запустить существующие tests;
15. зафиксировать baseline.

---

# 93. Baseline Report

Сформировать:

```text
_local/quality-runs/YYYY-MM-DD/baseline.md
```

Содержимое:

```text
commit
branch
git status
repo size
tracked file count
test status
lint status
security status
known failures
performance baseline
memory baseline
```

Не коммитить raw baseline автоматически.

---

# 94. Этап A — Repository Cleanup Plan

До применения создать таблицу:

| Path | Current | Proposed | Reason | Local preserved? | Risk |
|---|---|---|---|---|---|

Где `Proposed`:

```text
KEEP
UNTRACK_ONLY
IGNORE
MOVE
MERGE
DELETE_FROM_GIT_ONLY
```

Никакого действия без review списка.

---

# 95. Этап B — Toolchain Integration

Добавлять инструменты по одному:

1. configure;
2. run;
3. classify existing findings;
4. decide baseline;
5. add CI;
6. document;
7. commit separately.

Не включать сразу 10 инструментов и потом разбирать тысячи ошибок.

---

# 96. Этап C — Code Cleanup

Порядок:

```text
obvious bugs
resource leaks
security
reliability
dead code
duplication
complexity
formatting
```

Не начинать с косметики.

---

# 97. Этап D — Performance

Оптимизировать только после функциональной стабильности.

---

# 98. Этап E — Documentation

После стабилизации фактической архитектуры.

Не документировать временное состояние как окончательное.

---

# 99. Этап F — Persistent Gates

Последним этапом сделать так, чтобы найденные улучшения нельзя было случайно потерять:

```text
tests
hooks
CI
Skill
AGENTS.md
```

---

# 100. Обязательные создаваемые/обновляемые артефакты

Только если соответствуют фактической структуре проекта:

```text
AGENTS.md
SKILL/supporting skill files
pyproject.toml
.pre-commit-config.yaml
.github/workflows/quality.yml
.github/workflows/security.yml
.github/dependabot.yml
scripts/quality/check_repository_hygiene.py
scripts/quality/run_quality_gate.sh OR Makefile/task runner
docs/development/quality-gate.md
docs/development/repository-policy.md
README.md
README.en.md
```

Не создавать файл, если уже есть эквивалент — обновлять существующий.

---

# 101. Не допускается

- дублировать существующую систему;
- создавать второй competing quality gate;
- создавать второй Skill framework;
- добавлять инструмент без объяснения;
- коммитить raw scanner output;
- коммитить huge benchmark traces;
- удалять локальные файлы;
- переписывать Git history;
- отключать failing test ради зелёного CI;
- делать global ignore для security issue без анализа.

---

# 102. Definition of Success

После завершения должно быть возможно:

```text
fresh clone
↓
read beginner README
↓
install prerequisites
↓
configure from examples
↓
run quality gate
↓
run project
↓
understand failure
```

И одновременно:

```text
developer/agent task
↓
read Skill
↓
implement
↓
automatic checks
↓
pre-push
↓
GitHub CI
↓
merge
```

---

# 103. Целевой публичный репозиторий

Он должен выглядеть как **проект**, а не как рабочий стол исследователя.

Минимальная концепция:

```text
NAS_Jetson_Nano/
├── README.md
├── README.en.md
├── LICENSE
├── CHANGELOG.md
├── SECURITY.md
├── CONTRIBUTING.md
├── AGENTS.md
├── .github/
├── config/
├── docker/
├── services/
├── scripts/
├── systemd/
├── tests/
├── skills/           # только если это фактический стандарт проекта
└── docs/
```

Точная структура определяется после анализа.

---

# 104. Отчёт о сокращении GitHub

В финале показать:

```text
Tracked files BEFORE
Tracked files AFTER

Repository working tree size BEFORE
Repository working tree size AFTER

Git object database size BEFORE
Git object database size AFTER

Top 20 removed-from-tracking categories
```

Не путать уменьшение текущего tree и уменьшение Git history.

Если history не переписывалась, честно указать это.

---

# 105. Отчёт по качеству кода

| Metric | Before | After | Method |
|---|---:|---:|---|
| Ruff errors | | | |
| ShellCheck errors | | | |
| Test failures | | | |
| Coverage critical modules | | | |
| Security HIGH/CRITICAL | | | |
| Memory leak scenarios | | | |
| Performance scenarios | | | |
| Tracked artifact violations | | | |

---

# 106. Отчёт по performance

Для каждого изменённого hotspot:

```text
Scenario
Before
After
Delta
Confidence
Side effects
```

---

# 107. Отчёт по памяти

Для suspected leak:

```text
Scenario
Warmup RSS
Peak
Post-load RSS
Repeat-cycle trend
Conclusion
```

---

# 108. Final Repository Hygiene Report

Категории:

```text
Kept
Untracked but retained locally
Ignored
Moved
Merged
Deferred
```

Показать точные paths.

---

# 109. Final Documentation Report

Ответить:

- Может ли новичок понять проект за 5 минут?
- Есть ли quick start?
- Есть ли expected outputs?
- Есть ли troubleshooting?
- Есть ли backup/restore?
- Отделена ли beginner documentation от internals?

---

# 110. Final Skill Report

Показать:

```text
Skill location
Files
Rules added
Lessons added
Invariants added
Quality gates added
```

---

# 111. Independent Verification Checklist

Verifier обязан проверить:

```text
[ ] clean git status or explained changes
[ ] no local artifact accidentally deleted
[ ] no secret added
[ ] repo hygiene PASS
[ ] FAST PASS
[ ] FULL PASS
[ ] security PASS / documented exceptions
[ ] relevant performance PASS
[ ] relevant memory tests PASS
[ ] docs consistent
[ ] Skill updated
[ ] fresh clone test PASS
[ ] no hidden dependency on _local
```

---

# 112. STOP CONDITIONS

Остановить автоматические изменения и вывести finding, если:

- найден реальный secret;
- найден риск потери пользовательских данных;
- требуется history rewrite;
- требуется destructive storage action;
- требуется production DB migration;
- обнаружено неизвестное deployment dependency;
- неясно, является ли файл критически необходимым;
- CI невозможно воспроизвести без credentials;
- изменение может нарушить backup/recovery.

При этом продолжить остальные безопасные части аудита.

---

# 113. Формат коммуникации Coordinator → владелец

Не спрашивать подтверждение на каждую мелочь.

Группировать:

```text
SAFE AUTO
REVIEW REQUIRED
OWNER APPROVAL REQUIRED
```

## SAFE AUTO

Примеры:

- lint config;
- tests;
- docs typo;
- ignored generated file;
- non-destructive CI check.

## REVIEW REQUIRED

- large refactor;
- repository structure move;
- new dependency;
- behavior change.

## OWNER APPROVAL REQUIRED

- destructive command;
- production migration;
- Git history rewrite;
- data deletion;
- network/VPN change.

---

# 114. Коммиты этапов

Предпочтительно разделять:

```text
1. test: establish baseline/regressions
2. ci: add quality infrastructure
3. fix: correctness/security
4. perf: measured optimization
5. chore(repo): cleanup tracking
6. docs: beginner-first documentation
7. chore(skill): persist project knowledge
```

Порядок адаптировать к зависимости задач.

---

# 115. Нельзя смешивать

В одном giant commit не смешивать:

```text
format entire repo
+
security fix
+
folder moves
+
performance refactor
+
docs rewrite
```

Это делает review практически невозможным.

---

# 116. Future-Proof Requirement

Каждое существенное улучшение должно отвечать:

> Что предотвратит повторное появление этой проблемы?

Ответ должен быть одним или несколькими:

```text
test
static rule
CI
pre-push
repository policy
Skill rule
architecture invariant
```

Если ответ: «агент должен помнить» — решение недостаточно.

---

# 117. Пример устойчивого исправления

Плохо:

```text
Нашли .log в GitHub
→ удалили
```

Хорошо:

```text
Нашли .log
→ сохранили локально
→ untrack
→ .gitignore
→ repository_hygiene rule
→ CI
→ repository-policy documentation
→ Skill note
```

---

# 118. Другой пример

Плохо:

```text
Нашли memory leak
→ исправили функцию
```

Хорошо:

```text
Memray reproduced leak
→ root cause
→ regression/load test
→ fix
→ Memray re-run
→ baseline
→ test/guard
→ lesson learned
```

---

# 119. Принцип минимализма

Не строить enterprise bureaucracy.

Любой новый инструмент должен отвечать хотя бы одному:

```text
ловит реальную категорию ошибок
заменяет несколько старых инструментов
автоматизирует ручную проверку
предотвращает известный regression
```

Иначе не добавлять.

---

# 120. Предпочтительный конечный стек

Ориентир, а не догма:

```text
CODE
├── Ruff
├── mypy
├── pytest
└── pytest-cov

LEGACY
├── vermin
└── compatibility tests

PERFORMANCE
├── py-spy
├── Memray
└── pytest-benchmark

SHELL
├── ShellCheck
└── shfmt --diff

DOCKER
├── Hadolint
├── docker compose config
└── Trivy

SECURITY
├── Gitleaks
├── pip-audit
├── Trivy
├── CodeQL
└── Dependabot

CI/CONFIG
├── actionlint
└── yamllint

REPOSITORY
├── .gitignore
├── .git/info/exclude
├── repository_hygiene.py
└── pre-commit/pre-push

DOCS
├── markdownlint (optional)
└── lychee (optional)
```

---

# 121. Приоритеты реализации

## P0 — защитить проект

- secrets;
- failing regression;
- CI broken;
- destructive risk;
- backup/recovery code regression.

## P1 — сделать качество обязательным

- unified gate;
- tests;
- repository hygiene;
- pre-push;
- GitHub CI.

## P2 — производительность и leaks

- py-spy;
- Memray;
- baseline;
- targeted optimization.

## P3 — GitHub cleanup

- tracked artifacts;
- legacy;
- duplicates;
- local-only split.

## P4 — beginner docs

- README;
- quick start;
- docs IA.

## P5 — refinement

- typing expansion;
- complexity;
- extra tooling.

Порядок может меняться, если аудит выявит реальный более высокий риск.

---

# 122. Финальный Deliverable

Сформировать итоговый документ:

```text
docs/development/CODE_QUALITY_AND_REPOSITORY_CLEANUP_REPORT.md
```

или существующее подходящее место.

В нём:

1. Executive summary.
2. Baseline.
3. Findings.
4. Applied changes.
5. Toolchain.
6. Tests.
7. Performance.
8. Memory.
9. Security.
10. GitHub cleanup.
11. Documentation changes.
12. Skill changes.
13. CI/pre-push.
14. Before/After metrics.
15. Deferred items.
16. Risks.
17. Next steps.

Raw outputs в этот документ не копировать.

---

# 123. Финальный ответ агента владельцу

В финале дать краткую таблицу:

| Область | Было | Стало | Проверка |
|---|---|---|---|
| Tests | | | |
| Code quality | | | |
| Security | | | |
| Performance | | | |
| Memory | | | |
| GitHub hygiene | | | |
| Documentation | | | |
| Persistent Skill | | | |
| CI | | | |

После неё:

## Что было удалено только из Git tracking

## Что осталось локально

## Какие проверки теперь выполняются автоматически

## Какие проверки обязательны перед каждым push

## Какие знания добавлены в Skill

## Что сознательно не делалось

---

# 124. Главный критерий успеха

После выполнения этого master prompt новый агент, который впервые откроет проект, должен автоматически получить следующий рабочий контракт:

```text
Я сначала читаю AGENTS + Project Skill.
Я знаю runtime-ограничения.
Я знаю, что нельзя коммитить.
Я знаю, какие тесты нужны.
Я не оптимизирую без benchmark.
Я не исправляю leak без воспроизводимого теста.
Я не пушу без FULL gate.
CI повторяет обязательные проверки.
Новая ошибка превращается в постоянный regression guard.
```

---

# 125. Начать выполнение

Начни с **PHASE 0 — DISCOVERY AND BASELINE**.

Ничего массово не форматируй и не удаляй.

Сначала:

```text
1. inventory
2. existing rules
3. existing Skill/AGENTS
4. runtime matrix
5. tests
6. CI
7. Git tracking
8. repository size
9. existing quality gate
10. baseline
```

После этого создай task matrix для субагентов и продолжай работу этапами.

---

# 126. Обязательная финальная проверка перед PUSH

Перед любым push в рамках этой задачи выполнить:

```text
READ AGENTS/SKILL
→ git diff review
→ repository hygiene
→ secrets scan
→ FAST
→ FULL
→ relevant PERFORMANCE/MEMORY
→ docs validation
→ Skill validation
→ independent verifier
→ git status
```

Только если все обязательные проверки имеют `PASS` или явно документированное разрешённое исключение:

```text
READY TO PUSH
```

Именно этот механизм должен остаться в проекте и применяться ко всем следующим изменениям.
