# Repository hygiene / Чистота репозитория

Стандарт NAS_Jetson_Nano, принят в проект 2026-10-06 на основе предложенного владельцем
`AGENT_REPOSITORY_HYGIENE.md`. Применяется к агентам и их результатам.
AGENTS.md, запреты безопасности и прямые указания владельца имеют приоритет.
Этот документ не разрешает удаление данных, публикацию или развёртывание.

Project standard adapted from the owner's proposed document on 2026-10-06.
AGENTS.md, safety restrictions and explicit owner instructions take precedence.
This policy grants no permission to delete data, publish or deploy.

## 1. Необходимые файлы / Necessary files

Создавать файл только для реализации, постоянного теста, конфигурации/сборки,
развёртывания, постоянной документации или явно запрошенного результата.
Сначала найти существующий файл подходящего назначения и предпочесть его обновление.
Корень сохранять для необходимых проектных файлов; одноразовые отчёты, дампы,
скриншоты, архивы и экспериментальные скрипты туда не помещать.

Create files only for implementation, durable tests, configuration/build,
deployment, permanent documentation or an explicitly requested deliverable.
Search for an existing suitable file first. Keep the root for necessary project
files; put temporary reports, dumps, screenshots, archives and experiments elsewhere.

## 2. Размещение / Locations

Все новые артефакты агента находятся **внутри проекта** (AGENTS.md §9).
Не использовать системный temp или соседние каталоги для собственных результатов.
Временные каталоги создаваемых агентом скриптов также явно направлять внутрь проекта.
Существующие внешние хранилища секретов и координационная доска — исключения §9;
секреты не переносить сюда. Внутренние временные файлы сторонних программ не
считаются собственными результатами агента; при наличии настройки направлять их сюда.

All new agent outputs stay **inside the project** (AGENTS.md §9), including temporary
folders explicitly created by agent scripts. Do not use system temp or sibling
folders for those outputs. Existing credential stores and the coordination board
retain their §9 exceptions; never move secrets here. Third-party program internals
are not agent deliverables; redirect their temporary output when configurable.

| Каталог / Location | Назначение / Purpose | Git |
|---|---|---|
| `.agent-work/tmp/` | Одноразовые скрипты и данные / Disposable scripts and data | Ignored |
| `.agent-work/logs/`, `reports/`, `cache/` | Временные журналы, отчёты, кэш / Temporary logs, reports, cache | Ignored |
| `.agent-work/worktrees/` | Рабочие копии Git / Git worktrees | Ignored |
| `.agent-work/archives/` | Уникальные результаты и материалы очистки / Preserved results and cleanup archives | Ignored |
| `ds_board/` | Локальная история DeepSeek / Local DeepSeek task history | Ignored |
| `artifacts/` | Остальные локальные результаты / Other local outputs | New files ignored |
| `tests/` | Постоянные регрессионные тесты / Durable regression tests | Tracked |
| `docs/` | Постоянные правила, решения, инструкции / Durable rules, decisions, runbooks | Tracked |

Игнорирование Git не означает, что файл безопасно удалить. `.agent-work/` **не является
целиком удаляемым каталогом**: там могут быть активные задачи, незакоммиченные изменения
и единственные архивы. Уже tracked-файлы `artifacts/` сохраняются: `.gitignore` не снимает
их с учёта. Новый постоянный результат обычно переносится в подходящий каталог проекта;
сохранение в `artifacts/` под Git требует явного обоснования и адресного добавления.

Git ignore is not permission to delete. `.agent-work/` **is not wholly disposable**:
it may contain active tasks, uncommitted changes and unique archives. Existing tracked
`artifacts/` files remain tracked. Place new durable results in the appropriate project
folder; tracking a new artifact requires an explicit reason and targeted addition.

## 3. Исходники и генерируемые данные / Source and generated data

Не оставлять рядом с реализацией версии `old`, `copy`, `backup`, `final2` и аналогичные
копии исходников. История и откат исходников — Git; рабочая изоляция — ветка/worktree.
Не добавлять кэши, сборки, coverage, временные БД/логи, зависимости и Docker-архивы в Git.
Большие бинарные файлы, модели, datasets и дампы требуют явного решения владельца;
при необходимости выбирать release/registry/LFS, не загружать автоматически.
Имена файлов — сигнал для проверки назначения, а не основание для автоматического
удаления или запрета: штатные backup-скрипты, fixtures и `.env.example` допустимы.

Avoid alternate source copies such as `old`, `copy`, `backup` and `final2`; use Git history
and branches/worktrees. Keep caches, builds, coverage, temporary DB/log files,
dependencies and Docker archives out of Git. Large binaries, models, datasets and dumps
require an explicit owner decision; release/registry/LFS storage is never automatic.
Names prompt a purpose review, not automatic deletion: backup tools, fixtures and
`.env.example` can be legitimate.

Операционные резервные копии БД/данных NAS и атомарные backup-файлы состояния службы
не заменяются Git и регулируются существующими правилами backup/restore и приватности.
Проектный `.gitignore` адаптировать адресно; универсальные маски не должны скрывать
нужные исходники, тестовые fixtures или публичные сертификаты.

Operational NAS/database backups and service state backup files are not replaced by
Git; existing backup/restore and privacy rules apply. Adapt ignore rules narrowly;
do not hide required source, fixtures or public certificates with generic masks.

## 4. Документация и контекст / Documentation and context

AGENTS.md — точка входа правил, этот документ — канон гигиены. В CLAUDE.md оставлять
ссылку, не копировать полный стандарт. Существующий полезный контекст не сокращать
автоматически. README и рабочие планы должны ссылаться на правила, а не повторять их.
Не создавать журнал/отчёт на каждую мелкую задачу; временные заметки — `.agent-work/`.
Постоянные ADR, доказательства приёмки, аудиты, контрольные точки, инструкции деплоя
и необходимые версии RU/EN сохранять. Дата, перевод и слово «audit» не делают файл мусором.
Искать относящиеся к задаче файлы через `rg`, читать нужные фрагменты и зависимости;
не загружать весь репозиторий или историю отчётов без причины.

AGENTS.md is the entry point; this document is the hygiene authority. CLAUDE.md links
here without duplicating the standard; preserve existing useful context. Prefer
references in README/plans. Avoid per-task permanent journals; keep temporary notes
under `.agent-work/`. Retain durable ADRs, acceptance evidence, audits, checkpoints,
runbooks and required RU/EN pairs. Dates, translations and “audit” are not trash markers.
Search with `rg` and read relevant fragments/dependencies instead of loading the entire
repository or report history without a task-related reason.

## 5. Безопасная очистка / Safe cleanup

Без отдельного разрешения запрещены широкие `git clean -fd/-fdx`, `git reset --hard`
и рекурсивное удаление каталогов. Не удалять неизвестные untracked-файлы владельца.
Очищать только точно установленные одноразовые файлы своей задачи; чужие результаты,
worktree и архивы требуют проверки состояния/уникальности и нужного разрешения.
Перед удалением на Windows проверить полный разрешённый путь; использовать одну
оболочку с literal paths. Worktree удалять через Git после проверки status и состояния
задачи; активную или незавершённую копию сохранять. Уникальные результаты сначала
сохранить и проверить в `.agent-work/archives/`. Не переписывать Git-историю ради чистоты.

Broad `git clean -fd/-fdx`, `git reset --hard` and recursive directory deletion require
separate authorization. Never delete unknown owner-created untracked files. Remove
only identified disposable files from the current task; other results, worktrees and
archives need state/uniqueness checks and applicable authorization. Verify resolved
Windows paths; use one shell and literal paths. Remove worktrees through Git only after
checking status and task completion; preserve active/unfinished work. Archive and verify
unique results under `.agent-work/archives/` first. Never rewrite history for hygiene.

## 6. Приёмка / Completion

Перед завершением проверить:

```bash
git status --short
git diff --stat
git diff --check
git diff --cached --stat
git diff --cached --check
git ls-files -- .agent-work ds_board
git ls-files -- artifacts
git check-ignore .agent-work/tmp/probe ds_board/probe artifacts/probe
```

Просмотреть итоговый diff; объяснить назначение новых постоянных файлов. Для staging
использовать конкретные пути; не добавлять неизвестные результаты через `git add -A`.
Не оставлять временные исходники и debug-настройки в постоянном решении. Не публиковать
секреты или персональные данные даже из ignored-файлов. Оставленные локальные файлы
сообщать честно: чистота означает отсутствие случайных публикаций и лишних результатов
задачи, а не обязательный пустой status или удаление всех прежних файлов.

Review the final diff and justify new durable files. Stage specific paths rather than
unknown outputs with `git add -A`. Remove temporary source/debug changes from the durable
solution. Never publish secrets or personal data from ignored files either. Report
remaining local files accurately: hygiene does not require empty status or removal of
all pre-existing files.

## 7. Автоматический gate / Automated gate

Реализация — `scripts/quality/repo_hygiene.py`, политика —
`scripts/quality/repo_hygiene_policy.json`. Стандартная библиотека Python, без внешних
пакетов. Локальный preflight и commit-hook проверяют **весь Git index** до дорогих
тестов; GitHub Quality Checks сначала проверяет **дерево HEAD**, затем остальные jobs.
Непроиндексированные файлы владельца и ignored-данные не читаются и не удаляются.

The implementation uses Python's standard library. Local preflight/commit-hook
checks the **entire index** before expensive tests; GitHub Quality Checks first checks
**the HEAD tree**, then its remaining jobs. Unstaged owner files and ignored data are
neither read nor deleted.

Блокируются `.agent-work/` и `ds_board/` в любом месте дерева, новые локальные
`artifacts/`, известные кэши/результаты сборки и временные расширения, архивы/образы
дисков/пакеты/модели/видео, неизвестные файлы в корне и blob больше **2 MiB**.
Проверяются пути, типы и размеры Git-объектов; рабочая копия файла не подменяет staging.
Само имя `backup`, `old`, `copy` или дата документа не считается нарушением.

Blocked: agent workspaces anywhere in the tree, new local artifacts, known caches/build
outputs and temporary extensions, archives/disk images/packages/models/videos,
unknown root files and blobs over **2 MiB**. Checks use Git paths/types/sizes rather than
worktree content. Names such as `backup`, `old`, `copy` or document dates alone do not fail.

Исключения только по точному пути и с непустой причиной; для большого файла нужен
явный предел размера. В baseline сохранены ровно 18 ранее tracked материалов
`artifacts/` на коммите `5c48980`. Изменение политики проверять в ревью; не создавать
исключение только ради зелёного статуса. Agent workspace исключать нельзя.
Политика по умолчанию тоже читается из index/выбранного дерева, поэтому её правку
надо проиндексировать вместе с намеренными изменениями.

Exceptions require exact paths and nonempty reasons; large files need explicit size
ceilings. The baseline retains precisely 18 historical artifacts at `5c48980`.
Review policy changes; never add exceptions merely to turn a check green. Agent
workspaces cannot be exempted. Default policy comes from the same index/tree,
so stage intended policy changes together with the related files.

```bash
python scripts/quality/repo_hygiene.py --staged
python scripts/quality/repo_hygiene.py --tree HEAD
bash scripts/quality/preflight.sh --hygiene-only
python tests/unit/test_repo_hygiene.py
```

Для контролируемого локального предварительного просмотра без staging доступен
`--policy scripts/quality/repo_hygiene_policy.json`; hooks и CI этот override не используют.
Коды выхода: 0 — чисто, 1 — нарушения, 2 — ошибка политики/Git metadata.
Gate не распознаёт все виды бинарных данных, смысл документов или секреты; он не
заменяет privacy review, secret scanner и проверку истории перед публикацией.
Существующие отдельные CI workflows не зависят от Quality Checks; порядок «сначала
hygiene» гарантируется внутри Quality Checks, а не между всеми workflows платформы.

An explicit `--policy` enables controlled local previews without staging; hooks and CI
never use this override. Exit codes: 0 clean, 1 violations, 2 policy/Git metadata error.
The gate cannot identify every binary format, document purpose or secret; it does not
replace privacy review, secret scanning or publication-history checks. Other independent
CI workflows remain separate; hygiene-first ordering applies within Quality Checks.
