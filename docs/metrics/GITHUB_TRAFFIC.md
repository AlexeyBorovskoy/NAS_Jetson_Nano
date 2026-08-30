# GitHub Traffic Metrics — NAS_Jetson_Nano

🇷🇺 Ежедневный мониторинг посещаемости и вовлечённости репозитория.
Данные берём через `gh api` (14-дневное окно GitHub).

🇬🇧 Daily monitoring of repository traffic and engagement.
Data is pulled via `gh api` (GitHub's 14-day window).

**Команды для обновления: / Commands to refresh the data:**
```bash
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano/traffic/views --jq '{views: .count, uniques: .uniques}'
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano/traffic/clones --jq '{clones: .count, uniques: .uniques}'
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano/traffic/popular/referrers
gh api repos/AlexeyBorovskoy/NAS_Jetson_Nano --jq '{stars: .stargazers_count, forks: .forks_count, watchers: .watchers_count}'
```

---

## Дневной лог / Daily log

| Дата / Date | Views (14d) | Uniq visitors | Clones (14d) | Uniq cloners | Stars | Forks | Топ источник / Top source | Примечание / Note |
|---|---|---|---|---|---|---|---|---|
| 2026-06-24 | 0 | 0 | 371 | 149 | 0 | 0 | — | Базовая линия; клоны вероятно боты / Baseline; clones are likely bots |
| 2026-06-25 | 0 | 0 | 371 | 149 | 0 | 0 | — | Без изменений; реальных людей ещё нет / No change; no real people yet |

---

## Анализ / Analysis

### 2026-06-25 — День 5 (обновление) / Day 5 (update)

**Детальная картина по дням (из API): / Detailed day-by-day picture (from the API):**

| Дата / Date | Клоны / Clones | Уник. клонеры / Uniq cloners | Характер / Nature |
|---|---|---|---|
| 10–12 июня / Jun 10–12 | 0 | 0 | до публикации / before going public |
| 13 июня / Jun 13 | 21 | 9 | репо было приватным — **только мы сами** / repo was private — **just us** |
| 14 июня / Jun 14 | 3 | 3 | — |
| 15–16 июня / Jun 15–16 | 0 | 0 | — |
| 17 июня / Jun 17 | 20 | 5 | — |
| 18–19 июня / Jun 18–19 | 3 | 3 | — |
| 20 июня / Jun 20 | 64 | 24 | активная разработка (много коммитов) / active development (many commits) |
| **21 июня / Jun 21** | **209** | **91** | **репо стало публичным → GitHub crawler spike / repo went public → GitHub crawler spike** |
| 22 июня / Jun 22 | 4 | 4 | спад после crawl / drop-off after the crawl |
| 23 июня / Jun 23 | 47 | 20 | повторный crawl-волна / repeat crawl wave |
| 24–25 июня / Jun 24–25 | ~0 | ~0 | тишина / silence |

**Ключевой вывод — всё честно: / Key takeaway — full honesty:**
- 🇷🇺 **0 просмотров страницы за всё время** — ни один живой человек не зашёл на страницу репозитория
- 🇬🇧 **0 page views ever** — not a single real person has visited the repository page
- 🇷🇺 Все 371 клон = **GitHub-боты и автоматические scanners**: они клонируют каждый новый публичный репозиторий за несколько часов, но не "смотрят" страницы
- 🇬🇧 All 371 clones = **GitHub bots and automated scanners**: they clone every new public repository within hours, but don't "look" at the pages
- 🇷🇺 91 уникальный "клонер" 21 июня — это волна crawler'ов в момент смены приватный→публичный
- 🇬🇧 The 91 unique "cloners" on June 21 are a wave of crawlers at the moment the repo switched from private to public
- 🇷🇺 **Реальная аудитория = 0** — проект нигде не опубликован и не упомянут
- 🇬🇧 **Real audience = 0** — the project has not been published or mentioned anywhere

🇷🇺 **Это нормально для нового репозитория без продвижения.** Органические звёзды и посетители появятся только после публикации на Habr / Reddit.

🇬🇧 **This is normal for a new repository with no promotion.** Organic stars and visitors will only appear after publication on Habr / Reddit.

### 2026-06-24 — Базовая точка / Baseline point

**Состояние: / State:** 🇷🇺 репозиторий публичен с 2026-06-21 (3 дня). Базовая линия установлена. 🇬🇧 the repository has been public since 2026-06-21 (3 days). Baseline established.

**Что влияет на рост: / What drives growth:**
- 🇷🇺 Публикация Habr-статьи (черновик: `docs/articles/habr_draft.md`) — **главный рычаг** / 🇬🇧 Publishing the Habr article (draft: `docs/articles/habr_draft.md`) — **the main lever**
- 🇷🇺 Упоминание в r/selfhosted, r/homelab, r/degoogle / 🇬🇧 A mention on r/selfhosted, r/homelab, r/degoogle
- 🇷🇺 HTTPS на VPS (доверие к проекту) / 🇬🇧 HTTPS on the VPS (trust in the project)
- 🇷🇺 Добавление "Use this template" кнопки / 🇬🇧 Adding a "Use this template" button
- 🇷🇺 Скриншоты реального UI Immich/Nextcloud в README / 🇬🇧 Screenshots of the real Immich/Nextcloud UI in the README

---

## Целевые метрики / Target metrics (90 дней / 90 days)

| Метрика / Metric | Цель / Target | Статус / Status |
|---|---|---|
| GitHub Stars | 50 | 0 / 50 |
| Уникальные клонеры / Unique cloners | 500 | 149 / 500 |
| Уникальные посетители/нед / Unique visitors/week | 100 | 0 / 100 |
| Habr публикация / Habr publication | 1 | 0 / 1 |
| Reddit posts | 2 | 0 / 2 |
| Issues от внешних users / Issues from external users | 3 | 0 / 3 |
| Forks | 5 | 0 / 5 |
