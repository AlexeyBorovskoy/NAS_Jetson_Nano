# Аудит честности документации / Documentation truth audit

**Дата проверки / Audit date:** 2026-07-16  
**Область / Scope:** корневые Markdown-файлы, `docs/**/*.md`, связанные HTML/TXT и пять DOCX; архивные копии и вложенные рабочие деревья исключены. / Root Markdown files, `docs/**/*.md`, related HTML/TXT, and five DOCX files; archived copies and nested worktrees were excluded.

## 1. Итог / Outcome

🇷🇺 В документации находилось недостоверное утверждение, что статья для Habr опубликована или отправлена в Песочницу 29.06.2026. Пользователь подтвердил, что публикации не было. Записанный URL 16.07.2026 возвращает HTTP 404. Активная документация исправлена: материал теперь называется неопубликованным черновиком.

🇬🇧 The documentation contained an unsupported claim that the Habr article was published or submitted to the Sandbox on 2026-06-29. The user confirmed that no publication occurred. The recorded URL returned HTTP 404 on 2026-07-16. Active documentation now identifies the material as an unpublished draft.

## 2. Что подтверждено / What was confirmed

| Утверждение / Claim | Доказательство / Evidence | Статус / Status |
|---|---|---|
| Репозиторий GitHub публичный / GitHub repository is public | `gh api`: `visibility=public`, `private=false`, 2026-07-16 | Подтверждено / Confirmed |
| Ветка по умолчанию `main` / Default branch is `main` | `gh api`, 2026-07-16 | Подтверждено / Confirmed |
| GitHub Pages доступен / GitHub Pages is reachable | HTTP 200 и `has_pages=true`, 2026-07-16 | Подтверждено / Confirmed |
| Статья опубликована на Habr / Habr article is published | Пользователь: публикации не было; записанный URL: HTTP 404 | Ложно, исправлено / False, corrected |

## 3. Исправленные файлы / Corrected files

- `README.md`
- `CHANGELOG.md`
- `docs/articles/publication_status.md`
- `docs/articles/README.md`
- `docs/pages/evidence.md`
- `docs/index.md`
- `docs/articles/publication/traffic_tracker.md`
- `docs/articles/ARTICLE_FACTS_TABLE.md`
- `docs/articles/GITHUB_PUBLICATION_CHECKLIST.md`
- основные варианты статьи и WYSIWYG HTML / principal article variants and WYSIWYG HTML
- `docs/articles/publication/NAS_Jetson_Nano_HOME_CLOUD_PROJECT_PROMPTS_RU_EN.docx`

## 4. Правила честных формулировок / Honest wording rules

🇷🇺

1. «Текущий» допускается только после датированной повторной проверки.
2. Скриншот доказывает состояние только на момент снимка.
3. Наличие файла `publication/` не доказывает внешнюю публикацию.
4. Успешный исторический тест нельзя описывать как действующий результат без повторного запуска.
5. Прогнозы просмотров, звёзд и производительности должны называться прогнозами, а не результатами.
6. Невозможность подтвердить утверждение означает «не проверено», а не «работает».

🇬🇧

1. “Current” is allowed only after a dated re-verification.
2. A screenshot proves state only at the time it was captured.
3. A file under `publication/` does not prove external publication.
4. A historical successful test must not be presented as a current result without a rerun.
5. Forecasts for views, stars, and performance must be labelled as forecasts, not outcomes.
6. If a claim cannot be confirmed, its status is “unverified,” not “working.”

## 5. Оставшиеся ограничения аудита / Remaining audit limitations

🇷🇺 Автоматически просмотрено 136 активных Markdown-документов. У 54 есть явные маркеры русской и английской частей; у 82 таких маркеров нет. Это не доказывает отсутствие перевода во всех 82 файлах, но показывает, что требование двуязычности пока нельзя честно считать выполненным для всей документации. Русскоязычная статья и англоязычный Hackaday-черновик являются разными редакционными материалами и не образуют построчный перевод.

🇬🇧 The automated scan covered 136 active Markdown documents. Fifty-four contain explicit Russian and English section markers; 82 do not. This does not prove that every one of those 82 files is monolingual, but it means repository-wide bilingual coverage cannot honestly be claimed yet. The Russian Habr draft and English Hackaday draft are separate editorial pieces, not line-by-line translations.

🇷🇺 Полный семантический фактчекинг каждой фразы о живом Jetson/VPS не выполнялся в этом проходе: он потребовал бы нового read-only аудита живых систем. Поэтому старые метрики, версии, uptime, количества контейнеров, файлов и результаты тестов следует считать историческими до повторной проверки.

🇬🇧 A complete semantic fact-check of every live Jetson/VPS statement was not performed in this pass because it requires a new read-only audit of the live systems. Old metrics, versions, uptime, container/file counts, and test results must therefore be treated as historical until re-verified.

## 6. Следующий безопасный этап / Next safe phase

🇷🇺 Выполнять перевод по одному техническому блоку: сначала активные пользовательские документы (`README`, установка, архитектура, сеть, storage, backup, security), затем runbooks и ADR, затем исторические отчёты. После каждого блока проверять ссылки, смысловое соответствие RU/EN и отсутствие секретов.

🇬🇧 Translate one technical block at a time: active user-facing documents first (`README`, installation, architecture, networking, storage, backup, security), then runbooks and ADRs, then historical reports. After each block, verify links, RU/EN semantic parity, and absence of secrets.
