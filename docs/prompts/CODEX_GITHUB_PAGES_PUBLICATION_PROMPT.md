# CODEX: GitHub Pages Publication Prompt / Промт публикации на GitHub Pages

🇷🇺 **Назначение:** подготовить полную структуру публикации для NAS_Jetson_Nano:
`README.md → docs/articles/ → GitHub Pages`

🇬🇧 **Purpose:** Prepare full publication structure for NAS_Jetson_Nano:
`README.md → docs/articles/ → GitHub Pages`

🇷🇺 **Сессия, в которой это выполнялось:** 2026-06-29
🇬🇧 **Session where this was executed:** 2026-06-29

---

## Scope / Объём работ

1. **README.md** — add "Статьи и публикации / Articles" section with Habr link and GitHub Pages URL.

2. **docs/articles/** — ensure canonical article versions are present:
   - `habr_article_ru.md` — canonical RU article (source: `habr_final_edited.md`), image paths rewritten to `../assets/screenshots/article/redacted/`
   - `hackaday_project_en.md` — English Hackaday.io project draft
   - `README.md` — version history table, publication links
   - `publication_status.md` — per-platform status tracker

3. **GitHub Pages** (`docs/` as source):
   - `docs/_config.yml` — Jekyll theme config
   - `docs/index.md` — landing page with highlights, status table, links
   - `docs/pages/architecture.md` — architecture overview
   - `docs/pages/reliability.md` — USB incidents and reliability stack
   - `docs/pages/android.md` — Android client setup
   - `docs/pages/evidence.md` — screenshots, goss results, artifact links
   - `docs/GITHUB_PAGES_SETUP.md` — manual steps to enable Pages in repo Settings

4. **Screenshots** — copy from `docs/articles/publication/images_ready/` to `docs/assets/screenshots/article/redacted/` using numbered names (`01_` … `07_`).

5. **Image filename mapping** (images_ready → article):
   - `01_beszel_systems_overview.png`
   - `02_beszel_jetson_metrics.png`
   - `03_nas_jetson_nano_api_swagger_redacted.png`
   - `04_nextcloud_dashboard_redacted.png`
   - `05_nextcloud_talk_redacted.png`
   - `06_android_clients_card_redacted.png`
   - `07_immich_web_redacted.png`

6. **Checklists:**
   - `docs/articles/GITHUB_PUBLICATION_CHECKLIST.md`
   - `docs/articles/GITHUB_PAGES_IMAGE_AUDIT.md`

7. **Security checks / Проверки безопасности:**
   - No real IPs in any public-facing docs (use `192.168.x.x`, `ваш_VPS_IP`) / Никаких реальных IP в публичных документах
   - No personal names in article text / Никаких личных имён в тексте статьи
   - No tokens or passwords / Никаких токенов и паролей
   - Run `./scripts/security/check_no_secrets.sh` before commit / Прогнать перед коммитом

8. **Commit** all new docs files (not images already in git). Push. Enable GitHub Pages manually in Settings → Pages → main /docs.
   🇷🇺 **Закоммитить** все новые файлы документации (кроме изображений, уже лежащих в git). Запушить. Включить GitHub Pages вручную: Settings → Pages → main /docs.

---

## Hard constraints (do not violate) / Жёсткие ограничения (не нарушать)

🇷🇺

- НЕ коммитить реальные `.env`, пароли, токены, ключи.
- НЕ трогать Amnezia VPN контейнеры на VPS.
- НЕ удалять сетевой профиль `nas_jetson_nano-lan`.
- Все публичные статьи: IP-адреса заменены на плейсхолдеры, имена участников не раскрываются.

🇬🇧

- Do NOT commit real `.env` files, passwords, tokens, or keys.
- Do NOT touch the Amnezia VPN containers on the VPS.
- Do NOT delete the `nas_jetson_nano-lan` network profile.
- In all public articles: IP addresses replaced with placeholders, participants' names never disclosed.

---

## Verification / Проверка

🇷🇺 После завершения: / 🇬🇧 After completing:

```bash
# No real IPs in public docs:
grep -r "192\.168\.0\." docs/articles/ docs/pages/ docs/index.md
grep -r "193\.8\." docs/articles/ docs/pages/ docs/index.md

# Image files exist:
ls docs/assets/screenshots/article/redacted/0*.png

# Jekyll config present:
cat docs/_config.yml
```

🇷🇺 Затем включить GitHub Pages: Settings → Pages → Deploy from branch → main → /docs → Save.

🇬🇧 Then enable GitHub Pages: Settings → Pages → Deploy from branch → main → /docs → Save.
URL: https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
