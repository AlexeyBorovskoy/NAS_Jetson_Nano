# GitHub Publication Checklist

## Before commit

- [ ] 🇷🇺 Все пути к изображениям в `habr_article_ru.md` используют нумерованные имена (`01_` … `07_`), совпадающие с `images_ready/` / 🇬🇧 All image paths in `habr_article_ru.md` use numbered names (`01_` … `07_`) matching `images_ready/`
- [ ] 🇷🇺 Нет реальных IP / 🇬🇧 No real IPs: `grep -r "192\.168\.0\." docs/articles/ docs/pages/`
- [ ] 🇷🇺 Нет реальных IP / 🇬🇧 No real IPs: `grep -r "193\.8\." docs/articles/ docs/pages/`
- [ ] 🇷🇺 Нет личных имён в тексте статьи (замазаны на скриншотах) / 🇬🇧 No personal names in article text (blurred in screenshots)
- [ ] 🇷🇺 Нет токенов, паролей или значений `.env` ни в одном документе / 🇬🇧 No tokens, passwords, or `.env` values in any doc
- [ ] 🇷🇺 `./scripts/security/check_no_secrets.sh` — проходит / 🇬🇧 `./scripts/security/check_no_secrets.sh` — passes

## Files present

- [ ] `docs/_config.yml`
- [ ] `docs/index.md`
- [ ] `docs/articles/habr_article_ru.md`
- [ ] `docs/articles/hackaday_project_en.md`
- [ ] `docs/pages/architecture.md`
- [ ] `docs/pages/reliability.md`
- [ ] `docs/pages/android.md`
- [ ] `docs/pages/evidence.md`
- [ ] `docs/assets/screenshots/article/redacted/01_beszel_systems_overview.png`
- [ ] `docs/assets/screenshots/article/redacted/02_beszel_jetson_metrics.png`
- [ ] `docs/assets/screenshots/article/redacted/03_nas_jetson_nano_api_swagger_redacted.png`
- [ ] `docs/assets/screenshots/article/redacted/04_nextcloud_dashboard_redacted.png`
- [ ] `docs/assets/screenshots/article/redacted/05_nextcloud_talk_redacted.png`
- [ ] `docs/assets/screenshots/article/redacted/06_android_clients_card_redacted.png`
- [ ] `docs/assets/screenshots/article/redacted/07_immich_web_redacted.png`

## After commit + push

- [ ] 🇷🇺 Перейти в Settings репозитория → Pages → Deploy from branch → `main` → `/docs` → Save / 🇬🇧 Go to repo Settings → Pages → Deploy from branch → `main` → `/docs` → Save
- [ ] 🇷🇺 Подождать 1–3 минуты сборки / 🇬🇧 Wait 1–3 minutes for build
- [ ] 🇷🇺 Открыть https://alexeyborovskoy.github.io/NAS_Jetson_Nano/ — лендинг загружается / 🇬🇧 Open https://alexeyborovskoy.github.io/NAS_Jetson_Nano/ — landing page loads
- [ ] 🇷🇺 Открыть https://alexeyborovskoy.github.io/NAS_Jetson_Nano/articles/habr_article_ru.html — статья рендерится / 🇬🇧 Open https://alexeyborovskoy.github.io/NAS_Jetson_Nano/articles/habr_article_ru.html — article renders
- [ ] 🇷🇺 Все 7 изображений видны в статье (нет битых иконок) / 🇬🇧 All 7 images visible in article (no broken image icons)
- [ ] 🇷🇺 Ссылки в index.md открываются (architecture, reliability, android, evidence) / 🇬🇧 Links in index.md resolve (architecture, reliability, android, evidence)

## Publication links

🇷🇺 Ссылки публикации / 🇬🇧 Publication links:

- GitHub Pages: https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
- Habr — Часть 1 / Part 1: **опубликовано / published** → https://habr.com/ru/articles/1062914/ (2026-07-25)
- Habr — Часть 2 / Part 2: в подготовке / in preparation (Шаг 2 / Step 2)
- Hackaday.io: TBD (see `docs/articles/hackaday_project_en.md`)
