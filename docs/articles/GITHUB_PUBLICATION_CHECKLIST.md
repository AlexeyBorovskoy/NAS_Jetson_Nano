# GitHub Publication Checklist

## Before commit

- [ ] All image paths in `habr_article_ru.md` use numbered names (`01_` … `07_`) matching `images_ready/`
- [ ] No real IPs: `grep -r "192\.168\.0\." docs/articles/ docs/pages/`
- [ ] No real IPs: `grep -r "193\.8\." docs/articles/ docs/pages/`
- [ ] No personal names in article text (blurred in screenshots)
- [ ] No tokens, passwords, or `.env` values in any doc
- [ ] `./scripts/security/check_no_secrets.sh` — passes

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

- [ ] Go to repo Settings → Pages → Deploy from branch → `main` → `/docs` → Save
- [ ] Wait 1–3 minutes for build
- [ ] Open https://alexeyborovskoy.github.io/NAS_Jetson_Nano/ — landing page loads
- [ ] Open https://alexeyborovskoy.github.io/NAS_Jetson_Nano/articles/habr_article_ru.html — article renders
- [ ] All 7 images visible in article (no broken image icons)
- [ ] Links in index.md resolve (architecture, reliability, android, evidence)

## Publication links

- GitHub Pages: https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
- Habr: не опубликовано / not published (ранее записанная ссылка Песочницы возвращает HTTP 404 / the previously recorded Sandbox URL returns HTTP 404)
- Hackaday.io: TBD (see `docs/articles/hackaday_project_en.md`)
