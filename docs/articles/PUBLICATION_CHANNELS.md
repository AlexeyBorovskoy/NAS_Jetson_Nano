# One project, three entry points / Один проект, три точки входа

**Status: publication plan, 2026-09-20.** This page describes how to explain the same project to different readers. It does not announce an unpublished article or a feature still in development.

| Channel | Reader's first question | Lead with | Link to evidence |
|---|---|---|---|
| **GitHub** | “What is implemented, and can I inspect or reuse it?” | Current architecture, status with dates, setup constraints, code, tests, decisions, known limitations | README, ADRs, runbooks, source and CI |
| **DEV Community** | “What can I learn from this build?” | An English engineering story: a 4 GB Jetson, mostly free components, failure analysis, measurements and trade-offs | [DEV brief](DEV_ARTICLE_BRIEF.md), selected public commits and diagrams |
| **Хабр** | «Зачем это понадобилось семье и как проект пережил рост?» | Русская история эксплуатации, развитие функций, ошибки и честная стоимость | [Часть 1](https://habr.com/ru/articles/1062914/), [план части 2](HABR_PART2_ARTICLE_PLAN_2026-09.md) |

## Shared factual core / Общая основа фактов

The Jetson Nano is the home's system of record for files and photos. A VPS provides a network edge. Text questions to the family assistant use a gateway and an external provider. GitVerse is a source mirror. Kaggle is prepared for experiments on public data; its GPU benefit to this project has not yet been measured. Voice recognition on the Jetson is being investigated. These statuses must be rechecked before any article is published.

Данные о сбоях, замерах, затратах и статусе функций ведутся один раз в проекте, затем отбираются для площадки. Английская публикация для DEV должна читаться самостоятельно; русский текст на Хабре не обязан быть её дословным переводом.

## What makes the work credible internationally

1. **A bounded claim.** State the exact hardware, date, workload and measurement method. Do not describe the Nano as a local LLM host or quote benchmark numbers from other devices as its results.
2. **A reproducible slice.** Provide a small, sanitized example of one decision or check. Full family infrastructure is not a safe one-command demo.
3. **A failure story.** Show symptom, discarded hypothesis if relevant, cause, fix and verification. Keep unresolved limits visible.
4. **An honest cost model.** Distinguish open-source software, free service quotas and paid hardware/VPS/electricity.
5. **A usable way to respond.** Keep GitHub issues open for technical corrections, answer questions on the article, and make the public profile point to the repo. Employment or consulting contacts may follow from demonstrable work; readership metrics alone do not establish engineering quality.

## DEV profile and publishing checklist

On 2026-09-20 the public [@alex3d profile](https://dev.to/alex3d) had no published posts and showed “404 bio not found”. Before the first article, add a short English bio and a GitHub/project link. Suggested copy for the owner to review:

> Building a family cloud on a 4 GB Jetson Nano. I write about self-hosting, reliability, privacy and measured trade-offs on constrained hardware.

Useful “currently hacking on” copy:

> A Jetson-based family NAS and Telegram assistant; testing local speech recognition and documenting failures as well as fixes.

The profile text is a proposal, not a live profile change. Do not display the account email solely to invite contact. DEV's [editor guide](https://dev.to/p/editor_guide) supports up to four tags and a `canonical_url`; [AI-assisted content guidelines](https://dev.to/guidelines-for-ai-assisted-articles-on-dev) require disclosure and fact checking. A draft link can be shared with anyone who has it, so sanitize a draft before sharing that link.

## Release sequence / Порядок публикации

1. Verify current project facts and choose one publishable result. Collect dated measurements and sanitized figures.
2. Review the GitHub landing page, example commands and linked docs for accuracy and private data. Keep article source and evidence tied to public commits or appropriately redacted records.
3. Write and review the DEV article in English using the [brief](DEV_ARTICLE_BRIEF.md). Mark the actual level of AI assistance. Publish when its central result is demonstrated.
4. Adapt the story for Хабр with its own reader context. If the same text is cross-posted, set a deliberate canonical URL; an independently written article can stand on its own.
5. Share further only where the technical result fits the community. Measure useful discussion, corrections and contributions before considering more channels.

**Privacy boundary:** never put passwords, API keys, family identifiers, private photos, messages or raw backup manifests in article examples, public commits or external writing tools.
