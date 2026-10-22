# Статус публикаций / Publication status

> Проверено / Verified: 2026-10-22 (Part 2 materials and OBS status); Habr publication metrics remain the dated 2026-09-08 snapshot.
> DEV.to: план обновлён 2026-10-02 / plan updated 2026-10-02; other entries retain their dated evidence.

## Habr — Часть 1 (запуск) / Part 1 (launch)

- 🇷🇺 **Статус: опубликовано.** «Старому Jetson Nano — домашнее облако: Nextcloud, Immich, CGNAT и три USB-сбоя».
- 🇬🇧 **Status: published.** "Old Jetson Nano as a home cloud: Nextcloud, Immich, CGNAT and three USB failures".
- URL: https://habr.com/ru/articles/1062914/
- 🇷🇺 Автор: Alexey_git · 2026-07-25 · **13K** reach · +6 · 22 bookmarks · **9 comments** (без новых после 30.07.2026).
- 🇬🇧 Author: Alexey_git · 2026-07-25 · 13K reach · 9 comments (none after 2026-07-30).
- Snapshot: `artifacts/reports/HABR_GITHUB_ACTIVITY_2026-09-08.md`

## Habr — Часть 2 (развитие) / Part 2 (evolution)

- 🇷🇺 **Статус: план и рабочий прототип.** Текущая ось — шесть инцидентов и проверка утверждений; Sber-era служит контекстом. «ML на Vostro» каноном не является.
- 🇬🇧 **Status: plan and working prototype.** Six incidents and evidence checks are the current narrative; Sber-era is context, Vostro ML is not the architecture canon.
- План / Plan: [`HABR_PART2_ARTICLE_PLAN_2026-09.md`](HABR_PART2_ARTICLE_PLAN_2026-09.md)
- 🇷🇺 Есть расширенный рабочий прототип от 10.10 и редакторские заметки; финальный авторский текст ещё не готов и не опубликован. 🇬🇧 An extended working prototype and editorial notes exist (2026-10-10); the final author-written text is not ready or published.
- 🇷🇺 Дополнение 22.10 до ресурсной правки: часовая приёмка OBS-1 21.10 14:11:59–15:11:59 UTC принята; в последующем срезе VmHWM превысил цель 40 МиБ, cgroup peak достиг 64 МиБ, а дневной SSD-бюджет ≤60 МБ не подтверждён. `process write_bytes` — счётчик процесса, не измерение NAND. Исторический срез и границы вывода — в `HABR_PART2_MATERIALS.md` и контрольной точке.
- 🇷🇺 Обновление 22.10: двухчасовая OBS-приёмка завершена `accepted=true` / success (121 замер, 7200,053 с; CPU 2,5665%, VmHWM peak 22,3008 МиБ, cgroup peak 35,9883 МиБ, heartbeat max 11 с, рестартов 0). Дельты `write_bytes` процесса и раздела SSD составили 59 826 176 Б и 181 403 648 Б за два часа; счётчик раздела включает других писателей, ни одна дельта не равна NAND или суточному замеру. Суточная цель ≤60 МБ не подтверждена. 24-часовой observer идёт до 23.10 около 08:48 UTC.
- 🇬🇧 October 22 update: the two-hour OBS acceptance completed successfully (121 samples / 7,200.053 s; CPU 2.5665%, VmHWM peak 22.3008 MiB, cgroup peak 35.9883 MiB, heartbeat max 11 s, no restarts). Process and SSD-partition write-counter deltas were 59,826,176 B and 181,403,648 B over two hours; the partition counter includes other writers. Neither is NAND wear or a daily measurement. The ≤60 MB/day target remains unverified; the 24-hour observer is running until about 08:48 UTC Oct 23.

## GitHub Pages

- 🇷🇺 **Статус: доступно.** HTTP 200 подтверждён 16.07.2026.
- 🇬🇧 **Status: reachable.** HTTP 200 was confirmed on 2026-07-16.
- URL: https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
- Source / Источник: `main/docs`

## Hackaday.io

- 🇷🇺 **Статус: черновик; публикация не подтверждена.**
- 🇬🇧 **Status: draft; publication is not confirmed.**
- Draft / Черновик: `docs/articles/hackaday_project_en.md`

## DEV.to — семейное облако / Family cloud

- 🇷🇺 **Статус: редакционный план принят владельцем 2026-10-02.** Статья не написана и не опубликована.
- 🇬🇧 **Status: editorial plan approved by the owner on 2026-10-02.** Article not written or published.
- Title / Заголовок: **From NAS to Family Cloud: Lessons from a 4GB Jetson Nano**.
- Plan / План: [RU](DEVTO_PUBLICATION_PLAN_2026-10.ru.md) · [EN](DEVTO_PUBLICATION_PLAN_2026-10.md).
- 🇷🇺 Семь разделов, три подтверждаемые истории, 2 000–2 500 английских слов;
  следующий шаг — таблица «утверждение → источник → дата → статус реализации».
- 🇬🇧 Seven sections, three evidence-backed stories, 2,000–2,500 English words;
  next step: the claim → source → date → implementation-status table.
- 🇷🇺 Финальная редактура и публикация — владельцем; URL записать только после публикации.
- 🇬🇧 Final editing and publication belong to the owner; record the URL only after publication.

## Социальные анонсы / Social announcements

- 🇷🇺 **Статус: черновики; публикация не подтверждена.**
- 🇬🇧 **Status: drafts; publication is not confirmed.**
