# ARTICLE_IMAGE_AUDIT
> Generated: 2026-06-29
> Purpose: Audit of all images referenced in habr_final.md before Habr publication

---

## Изображения, referenced в статье / Images referenced in the article

| # | Изображение / Image | Раздел статьи / Article section | Файл существует? / File exists? | Риск чувствительных данных / Sensitive-data risk | Действие / Action |
|---|---|---|---|---|---|
| 1 | beszel_systems_overview.png | Шаг 2 — Мониторинг / Step 2 — Monitoring | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — Beszel UI показывает имена серверов, может отображать IP-адреса (jetson-nano → 127.0.0.1:45876, VPS → реальный IP) / MEDIUM — the Beszel UI shows server names and may display IP addresses (jetson-nano → 127.0.0.1:45876, VPS → real IP) | Проверить: нет ли реального VPS IP в интерфейсе. Если есть — размыть или заменить на VPS_IP. / Check whether the real VPS IP appears in the UI. If it does, blur it or replace it with VPS_IP. |
| 2 | beszel_jetson_metrics.png | Шаг 2 — Мониторинг / Step 2 — Monitoring | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — метрики могут показывать hostname, возможен LAN IP в деталях агента / MEDIUM — the metrics may show a hostname, a LAN IP may appear in the agent details | Проверить hostname и IP в отображаемых данных. Размыть при наличии. / Check the hostname and IP in the displayed data. Blur if present. |
| 3 | android_immich_backup_stats.jpg | Шаг 5 — Android / Step 5 — Android | ✅ publication/screenshots/ только (нет в assets/article/) / only (not in assets/article/) | ВЫСОКИЙ — Android screenshot: видно имя телефона, возможен аккаунт Google/Immich email (admin@nas_jetson_nano.local), статус батареи/сети / HIGH — Android screenshot: phone name visible, possible Google/Immich account email (admin@nas_jetson_nano.local), battery/network status | Проверить: нет ли email'а в верхней части экрана. Проверить имя устройства. admin@nas_jetson_nano.local — приемлемо (не реальный email). / Check whether an email appears at the top of the screen. Check the device name. admin@nas_jetson_nano.local is acceptable (not a real email). |
| 4 | android_davx5_caldav.jpg | Шаг 5 — Android / Step 5 — Android | ✅ publication/screenshots/ только (нет в assets/article/) / only (not in assets/article/) | ВЫСОКИЙ — DAVx⁵ показывает URL сервера (https://VPS_IP:8443/remote.php/dav), может показывать имя пользователя / HIGH — DAVx⁵ shows the server URL (https://VPS_IP:8443/remote.php/dav), may show the username | Критически важно: URL в DAVx⁵ содержит реальный VPS IP. Необходимо размыть/редактировать IP. / Critically important: the URL in DAVx⁵ contains the real VPS IP. The IP must be blurred/edited out. |
| 5 | nextcloud_talk.png | Шаг 6 — Семейный чат / Step 6 — Family chat | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | ВЫСОКИЙ — чат содержит реальные имена участников, историю переписки, возможны личные данные / HIGH — the chat contains real participant names, message history, possible personal data | Проверить содержимое чата. Имена (Olga, Ivan, Ulyana, Anna) — решить: публиковать или заменить. Сообщения — скрыть если личные. / Review the chat content. Decide whether to publish or replace the names (Olga, Ivan, Ulyana, Anna). Hide the messages if they are personal. |
| 6 | nextcloud_dashboard.png | Шаг 6 — Семейный чат / Step 6 — Family chat | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — dashboard может показывать имена файлов, структуру папок, username в углу / MEDIUM — the dashboard may show file names, folder structure, username in the corner | Проверить: нет ли чувствительных имён файлов или папок. URL в адресной строке. / Check for sensitive file or folder names. Check the URL in the address bar. |
| 7 | nas_jetson_nano_api_swagger.png | Шаг 7 — REST API / Step 7 — REST API | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — Swagger UI в браузере: URL адресной строки может содержать реальный IP (192.168.0.50:8099 или VPS_IP:8099) / MEDIUM — Swagger UI in the browser: the address bar URL may contain a real IP (192.168.0.50:8099 or VPS_IP:8099) | Проверить URL в адресной строке браузера. IP должен быть размыт. / Check the URL in the browser address bar. The IP must be blurred. |
| 8 | immich_web.png | «Что получилось» / "What came of it" | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — Immich web UI: может показывать email аккаунта, названия альбомов, реальные лица на фото (GDPR) / MEDIUM — Immich web UI: may show the account email, album names, real faces in photos (GDPR) | ВАЖНО: фотографии людей в Immich требуют согласия. Если показывается grid фото — убедиться что нет чужих лиц или скрыть. Username виден в профиле. / IMPORTANT: photos of people in Immich require consent. If the photo grid is shown, make sure no unrelated faces appear, or hide it. The username is visible in the profile. |

---

## Критичность по приоритету / Priority by criticality

### КРИТИЧНО — редактировать до публикации / CRITICAL — edit before publication:
1. **android_davx5_caldav.jpg** — реальный VPS IP в URL DAVx⁵ / real VPS IP in the DAVx⁵ URL
2. **immich_web.png** — сетка фотографий с реальными лицами людей (согласие всей семьи?) / photo grid with real people's faces (does the whole family consent?)
3. **nextcloud_talk.png** — история переписки семейного чата / family chat message history

### СРЕДНИЙ ПРИОРИТЕТ — проверить и решить / MEDIUM PRIORITY — review and decide:
4. **beszel_systems_overview.png** — IP в интерфейсе Beszel / IP in the Beszel interface
5. **nas_jetson_nano_api_swagger.png** — URL в адресной строке браузера / URL in the browser address bar
6. **android_immich_backup_stats.jpg** — email/имя устройства / email/device name

### НИЗКИЙ ПРИОРИТЕТ / LOW PRIORITY:
7. **beszel_jetson_metrics.png** — hostname в метриках (jetson-nano — не чувствительно) / hostname in the metrics (jetson-nano — not sensitive)
8. **nextcloud_dashboard.png** — имена файлов (если не личные) / file names (if not personal)

---

## Изображения в assets/ но НЕ использованные в статье / Images in assets/ but NOT used in the article

🇷🇺 Дополнительные файлы в `assets/screenshots/article/`:
- `telegram_report_containers.png`
- `telegram_report_full.png`
- `telegram_report_external.png`

Рекомендация: Добавить `telegram_report_full.png` в Шаг 2 вместо или рядом с Beszel — это наглядно показывает ежедневный отчёт, о котором написано в тексте.

🇬🇧 Additional files in `assets/screenshots/article/`:
- `telegram_report_containers.png`
- `telegram_report_full.png`
- `telegram_report_external.png`

Recommendation: Add `telegram_report_full.png` to Step 2, either instead of or alongside Beszel — it visually demonstrates the daily report described in the text.

---

## Инструкции по редактированию скриншотов / Screenshot editing instructions

🇷🇺 **Инструменты:**
- Windows: встроенный Paint / Snipping Tool (прямоугольник заливки)
- Онлайн: Photopea (photopea.com) — бесплатный Photoshop-клон
- macOS: Preview (прямоугольный маркер с заливкой)

**Что редактировать:**
- Реальные IP-адреса → заменить на `VPS_IP` / `192.168.x.x` / `JETSON_IP`
- Email домашний → заменить на `user@example.com` если отличается от `admin@nas_jetson_nano.local`
- Личные сообщения в Talk → заменить на test-сообщения типа «Привет всем!»
- Лица в Immich → рассмотреть использование Immich blur feature или cropped view

**Рекомендация формата:** PNG для UI screenshots, JPEG приемлем для фото телефона. Для Habr максимальный размер файла 2 МБ, рекомендуемая ширина не более 1920px.

🇬🇧 **Tools:**
- Windows: built-in Paint / Snipping Tool (filled rectangle)
- Online: Photopea (photopea.com) — a free Photoshop clone
- macOS: Preview (rectangular marker with fill)

**What to edit:**
- Real IP addresses → replace with `VPS_IP` / `192.168.x.x` / `JETSON_IP`
- Home email → replace with `user@example.com` if it differs from `admin@nas_jetson_nano.local`
- Personal messages in Talk → replace with test messages like "Hi everyone!"
- Faces in Immich → consider using the Immich blur feature or a cropped view

**Format recommendation:** PNG for UI screenshots, JPEG is acceptable for phone photos. Habr's maximum file size is 2 MB, recommended width no more than 1920px.
