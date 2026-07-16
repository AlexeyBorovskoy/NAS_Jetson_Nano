# ARTICLE_IMAGE_AUDIT
> Generated: 2026-06-29  
> Purpose: Audit of all images referenced in habr_final.md before Habr publication

---

## Изображения, referenced в статье

| # | Изображение | Раздел статьи | Файл существует? | Риск чувствительных данных | Действие |
|---|---|---|---|---|---|
| 1 | beszel_systems_overview.png | Шаг 2 — Мониторинг | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — Beszel UI показывает имена серверов, может отображать IP-адреса (jetson-nano → 127.0.0.1:45876, VPS → реальный IP) | Проверить: нет ли реального VPS IP в интерфейсе. Если есть — размыть или заменить на VPS_IP. |
| 2 | beszel_jetson_metrics.png | Шаг 2 — Мониторинг | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — метрики могут показывать hostname, возможен LAN IP в деталях агента | Проверить hostname и IP в отображаемых данных. Размыть при наличии. |
| 3 | android_immich_backup_stats.jpg | Шаг 5 — Android | ✅ publication/screenshots/ только (нет в assets/article/) | ВЫСОКИЙ — Android screenshot: видно имя телефона, возможен аккаунт Google/Immich email (admin@nas_jetson_nano.local), статус батареи/сети | Проверить: нет ли email'а в верхней части экрана. Проверить имя устройства. admin@nas_jetson_nano.local — приемлемо (не реальный email). |
| 4 | android_davx5_caldav.jpg | Шаг 5 — Android | ✅ publication/screenshots/ только (нет в assets/article/) | ВЫСОКИЙ — DAVx⁵ показывает URL сервера (https://VPS_IP:8443/remote.php/dav), может показывать имя пользователя | Критически важно: URL в DAVx⁵ содержит реальный VPS IP. Необходимо размыть/редактировать IP. |
| 5 | nextcloud_talk.png | Шаг 6 — Семейный чат | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | ВЫСОКИЙ — чат содержит реальные имена участников, историю переписки, возможны личные данные | Проверить содержимое чата. Имена (Olga, Ivan, Ulyana, Anna) — решить: публиковать или заменить. Сообщения — скрыть если личные. |
| 6 | nextcloud_dashboard.png | Шаг 6 — Семейный чат | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — dashboard может показывать имена файлов, структуру папок, username в углу | Проверить: нет ли чувствительных имён файлов или папок. URL в адресной строке. |
| 7 | nas_jetson_nano_api_swagger.png | Шаг 7 — REST API | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — Swagger UI в браузере: URL адресной строки может содержать реальный IP (192.168.0.50:8099 или VPS_IP:8099) | Проверить URL в адресной строке браузера. IP должен быть размыт. |
| 8 | immich_web.png | «Что получилось» | ✅ assets/screenshots/article/ ✅ publication/screenshots/ | СРЕДНИЙ — Immich web UI: может показывать email аккаунта, названия альбомов, реальные лица на фото (GDPR) | ВАЖНО: фотографии людей в Immich требуют согласия. Если показывается grid фото — убедиться что нет чужих лиц или скрыть. Username виден в профиле. |

---

## Критичность по приоритету

### КРИТИЧНО — редактировать до публикации:
1. **android_davx5_caldav.jpg** — реальный VPS IP в URL DAVx⁵
2. **immich_web.png** — сетка фотографий с реальными лицами людей (согласие всей семьи?)
3. **nextcloud_talk.png** — история переписки семейного чата

### СРЕДНИЙ ПРИОРИТЕТ — проверить и решить:
4. **beszel_systems_overview.png** — IP в интерфейсе Beszel
5. **nas_jetson_nano_api_swagger.png** — URL в адресной строке браузера
6. **android_immich_backup_stats.jpg** — email/имя устройства

### НИЗКИЙ ПРИОРИТЕТ:
7. **beszel_jetson_metrics.png** — hostname в метриках (jetson-nano — не чувствительно)
8. **nextcloud_dashboard.png** — имена файлов (если не личные)

---

## Изображения в assets/ но НЕ использованные в статье

Дополнительные файлы в `assets/screenshots/article/`:
- `telegram_report_containers.png`
- `telegram_report_full.png`
- `telegram_report_external.png`

Рекомендация: Добавить `telegram_report_full.png` в Шаг 2 вместо или рядом с Beszel — это наглядно показывает ежедневный отчёт, о котором написано в тексте.

---

## Инструкции по редактированию скриншотов

**Инструменты:**
- Windows: встроенный Paint / Snipping Tool (прямоугольник заливки)
- Онлайн: Photopea (photopea.com) — бесплатный Photoshop-клон
- macOS: Preview (прямоугольный маркер с заливкой)

**Что редактировать:**
- Реальные IP-адреса → заменить на `VPS_IP` / `192.168.x.x` / `JETSON_IP`
- Email домашний → заменить на `user@example.com` если отличается от `admin@nas_jetson_nano.local`
- Личные сообщения в Talk → заменить на test-сообщения типа «Привет всем!»
- Лица в Immich → рассмотреть использование Immich blur feature или cropped view

**Рекомендация формата:** PNG для UI screenshots, JPEG приемлем для фото телефона. Для Habr максимальный размер файла 2 МБ, рекомендуемая ширина не более 1920px.
