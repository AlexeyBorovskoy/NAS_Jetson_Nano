# CODEX_ARTICLE_EDIT_AND_EVIDENCE_PROMPT

> 🇷🇺 Размещён здесь по указанию владельца 2026-06-29.
> 🇬🇧 Placed here per user instruction on 2026-06-29.

🇷🇺 Этот файл — заглушка. Полное содержимое промта (редакторская вычитка + сбор
доказательств для статьи на Habr) ведёт владелец, а исполняется оно в сессии Claude Code.

🇬🇧 This file is a stub placeholder. The full prompt content (editorial review + evidence
collection workflow for the Habr article) is managed by the user and executed via Claude
Code session.

🇷🇺 Промт ведёт по шагам:
1. Сбор живых доказательств с Jetson Nano (SSH только на чтение)
2. Редакторская вычитка `habr_final.md`
3. Создание EVIDENCE_REPORT, ARTICLE_FACTS_TABLE, HABR_ARTICLE_EDITOR_REPORT
4. Аудит изображений и чек-лист редактирования персональных данных
5. Получение `habr_final_edited.md` со всеми рекомендованными правками

🇬🇧 The prompt guides:
1. Collecting live evidence from Jetson Nano (SSH read-only)
2. Editorial review of habr_final.md
3. Creating EVIDENCE_REPORT, ARTICLE_FACTS_TABLE, HABR_ARTICLE_EDITOR_REPORT
4. Image audit and redaction checklist
5. Producing habr_final_edited.md with all recommended improvements

🇷🇺 Фактические редакторские находки — в `docs/articles/HABR_ARTICLE_EDITOR_REPORT.md`.

🇬🇧 See `docs/articles/HABR_ARTICLE_EDITOR_REPORT.md` for the actual editorial findings.
