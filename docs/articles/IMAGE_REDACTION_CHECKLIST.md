# IMAGE_REDACTION_CHECKLIST
> Generated: 2026-06-29
> Use this checklist before uploading screenshots to Habr

---

## Чеклист — пройти по каждому скриншоту / Checklist — go through every screenshot

### 1. beszel_systems_overview.png

**Что проверить / What to check:**
- [ ] 🇷🇺 Адресная строка браузера — есть ли реальный VPS IP? / 🇬🇧 Browser address bar — does it show the real VPS IP?
- [ ] 🇷🇺 Имена серверов в Beszel (jetson-nano, vps-vienna) — приемлемо, не чувствительно / 🇬🇧 Server names in Beszel (jetson-nano, vps-vienna) — acceptable, not sensitive
- [ ] 🇷🇺 IP-адреса в таблице подключений агентов (127.0.0.1:45876 — приемлемо) / 🇬🇧 IP addresses in the agent connection table (127.0.0.1:45876 — acceptable)
- [ ] 🇷🇺 Нет ли email аккаунта Beszel admin в профиле? / 🇬🇧 Is the Beszel admin account email visible in the profile?

🇷🇺 **Нужна редакция:** ВОЗМОЖНО (зависит от того, виден ли реальный VPS IP)
**Действие:** Просмотреть файл вручную, размыть прямоугольником все IP кроме 127.0.0.1

🇬🇧 **Redaction needed:** POSSIBLY (depends on whether the real VPS IP is visible)
**Action:** Review the file manually, blur out every IP except 127.0.0.1 with a rectangle

---

### 2. beszel_jetson_metrics.png

**Что проверить / What to check:**
- [ ] 🇷🇺 Hostname в заголовке (jetson-nano — приемлемо) / 🇬🇧 Hostname in the header (jetson-nano — acceptable)
- [ ] 🇷🇺 IP-адреса если показаны / 🇬🇧 IP addresses, if shown
- [ ] 🇷🇺 Username/email в профиле / 🇬🇧 Username/email in the profile

🇷🇺 **Нужна редакция:** МАЛОВЕРОЯТНО
**Действие:** Беглый просмотр, редакция только если виден реальный IP

🇬🇧 **Redaction needed:** UNLIKELY
**Action:** Quick review, redact only if a real IP is visible

---

### 3. android_immich_backup_stats.jpg

**Что проверить / What to check:**
- [ ] 🇷🇺 Email аккаунта Immich (admin@nas_jetson_nano.local — приемлемо, но проверить) / 🇬🇧 Immich account email (admin@nas_jetson_nano.local — acceptable, but verify)
- [ ] 🇷🇺 Имя Android-устройства (если содержит реальное имя владельца) / 🇬🇧 Android device name (if it contains the owner's real name)
- [ ] 🇷🇺 URL сервера если отображается / 🇬🇧 Server URL, if displayed
- [ ] 🇷🇺 Статус Wi-Fi сети (имя точки доступа — TP-Link_828C упоминается в CLAUDE.md) / 🇬🇧 Wi-Fi network status (access point name — TP-Link_828C is mentioned in CLAUDE.md)

🇷🇺 **Нужна редакция:** ВОЗМОЖНО
**Действие:** Проверить имя устройства и имя Wi-Fi сети. Размыть если содержат персональные данные.

🇬🇧 **Redaction needed:** POSSIBLY
**Action:** Check the device name and Wi-Fi network name. Blur them if they contain personal data.

---

### 4. android_davx5_caldav.jpg

**Что проверить / What to check:**
- [ ] 🇷🇺 URL в поле сервера DAVx⁵ — **КРИТИЧНО**: скорее всего содержит https://193.x.x.x:8443 / 🇬🇧 URL in the DAVx⁵ server field — **CRITICAL**: most likely contains https://193.x.x.x:8443
- [ ] 🇷🇺 Username в настройках аккаунта / 🇬🇧 Username in the account settings
- [ ] 🇷🇺 Имя устройства Android / 🇬🇧 Android device name

🇷🇺 **Нужна редакция:** ОБЯЗАТЕЛЬНО — реальный VPS IP
**Действие:** Размыть/замазать IP в URL. Заменить на `https://VPS_IP:8443/remote.php/dav`. Проверить username.

🇬🇧 **Redaction needed:** MANDATORY — real VPS IP
**Action:** Blur/black out the IP in the URL. Replace it with `https://VPS_IP:8443/remote.php/dav`. Check the username.

---

### 5. nextcloud_talk.png

**Что проверить / What to check:**
- [ ] 🇷🇺 Имена участников чата (Olga, Ivan, Ulyana, Anna — решить: публиковать как есть или нет) / 🇬🇧 Chat participant names (Olga, Ivan, Ulyana, Anna — decide: publish as-is or not)
- [ ] 🇷🇺 Содержимое сообщений в чате — **КРИТИЧНО если личные данные** / 🇬🇧 Chat message content — **CRITICAL if it contains personal data**
- [ ] 🇷🇺 Email/username в шапке приложения / 🇬🇧 Email/username in the app header
- [ ] 🇷🇺 URL в адресной строке браузера / 🇬🇧 URL in the browser address bar

🇷🇺 **Нужна редакция:** ОБЯЗАТЕЛЬНО — проверить содержимое чата
**Действие:** Если сообщения личные — сделать новый скриншот с тестовыми сообщениями («Привет! Это NAS_Jetson_Nano чат 🏠»). Имена участников решить с семьёй.

🇬🇧 **Redaction needed:** MANDATORY — review chat content
**Action:** If the messages are personal, take a new screenshot with test messages ("Hi! This is the NAS_Jetson_Nano chat 🏠"). Decide on participant names with the family.

---

### 6. nextcloud_dashboard.png

**Что проверить / What to check:**
- [ ] 🇷🇺 URL в адресной строке (http://192.168.0.50:8080 — приемлемо для LAN IP, но можно размыть) / 🇬🇧 URL in the address bar (http://192.168.0.50:8080 — acceptable for a LAN IP, but can be blurred)
- [ ] 🇷🇺 Username в правом верхнем углу / 🇬🇧 Username in the top-right corner
- [ ] 🇷🇺 Имена файлов/папок в файловом менеджере / 🇬🇧 File/folder names in the file manager
- [ ] 🇷🇺 Активность/последние файлы в dashboard widgets / 🇬🇧 Activity/recent files in the dashboard widgets

🇷🇺 **Нужна редакция:** ВОЗМОЖНО
**Действие:** Проверить имена файлов. LAN IP (192.168.0.x) — менее критично, но аккуратнее размыть.

🇬🇧 **Redaction needed:** POSSIBLY
**Action:** Check the file names. A LAN IP (192.168.0.x) is less critical, but it's safer to blur it anyway.

---

### 7. nas_jetson_nano_api_swagger.png

**Что проверить / What to check:**
- [ ] 🇷🇺 URL в адресной строке браузера — **КРИТИЧНО**: может быть http://192.168.0.50:8099/docs или VPS IP / 🇬🇧 URL in the browser address bar — **CRITICAL**: could be http://192.168.0.50:8099/docs or the VPS IP
- [ ] 🇷🇺 Заголовок Swagger: имя API и версия (NAS_Jetson_Nano API v0.6.0 — приемлемо) / 🇬🇧 Swagger title: API name and version (NAS_Jetson_Nano API v0.6.0 — acceptable)
- [ ] 🇷🇺 Примеры запросов/ответов — нет ли токенов или паролей? / 🇬🇧 Request/response examples — any tokens or passwords present?

🇷🇺 **Нужна редакция:** ВЕРОЯТНО — URL в адресной строке
**Действие:** Размыть IP в адресной строке. Заменить на `JETSON_IP:8099/docs`.

🇬🇧 **Redaction needed:** LIKELY — URL in the address bar
**Action:** Blur the IP in the address bar. Replace it with `JETSON_IP:8099/docs`.

---

### 8. immich_web.png

**Что проверить / What to check:**
- [ ] 🇷🇺 Сетка фотографий — **КРИТИЧНО**: реальные лица членов семьи / 🇬🇧 Photo grid — **CRITICAL**: real faces of family members
- [ ] 🇷🇺 Email/username аккаунта Immich в профиле / 🇬🇧 Immich account email/username in the profile
- [ ] 🇷🇺 URL в адресной строке / 🇬🇧 URL in the address bar
- [ ] 🇷🇺 Имена альбомов (если видны) / 🇬🇧 Album names (if visible)

🇷🇺 **Нужна редакция:** ОБЯЗАТЕЛЬНО
**Действие:** Перед публикацией получить согласие членов семьи на публикацию фото. Альтернатива — использовать скриншот без сетки фото (только статистика/боковое меню без thumbnails). Размыть URL.

🇬🇧 **Redaction needed:** MANDATORY
**Action:** Get the family members' consent to publish the photos before publication. Alternative — use a screenshot without the photo grid (statistics/side menu only, no thumbnails). Blur the URL.

---

## Сводная таблица / Summary table

| Скриншот / Screenshot | Редакция нужна / Redaction needed | Приоритет / Priority | Ручное действие / Manual action |
|---|---|---|---|
| beszel_systems_overview.png | Возможно / Possibly | Средний / Medium | Проверить IP в UI / Check IP in the UI |
| beszel_jetson_metrics.png | Маловероятно / Unlikely | Низкий / Low | Беглый просмотр / Quick review |
| android_immich_backup_stats.jpg | Возможно / Possibly | Средний / Medium | Проверить имя устройства и Wi-Fi / Check device name and Wi-Fi |
| android_davx5_caldav.jpg | **Обязательно** / **Mandatory** | **Критический** / **Critical** | Размыть VPS IP в URL / Blur VPS IP in the URL |
| nextcloud_talk.png | **Обязательно** / **Mandatory** | **Критический** / **Critical** | Проверить/заменить содержимое чата / Check/replace chat content |
| nextcloud_dashboard.png | Возможно / Possibly | Средний / Medium | Проверить имена файлов / Check file names |
| nas_jetson_nano_api_swagger.png | Вероятно / Likely | Средний / Medium | Размыть IP в адресной строке / Blur IP in the address bar |
| immich_web.png | **Обязательно** / **Mandatory** | **Критический** / **Critical** | Согласие семьи или скриншот без фото / Family consent or a screenshot without photos |

---

## Быстрый план редактирования (30 минут) / Quick editing plan (30 minutes)

🇷🇺
1. Открыть `android_davx5_caldav.jpg` в Paint — замазать IP белым прямоугольником, подписать «VPS_IP»
2. Открыть `nextcloud_talk.png` — оценить содержимое переписки. Если OK — оставить; если нет — переснять.
3. Открыть `immich_web.png` — если видны лица — сделать crop только на статистику или размыть grid
4. Открыть `nas_jetson_nano_api_swagger.png` — проверить адресную строку, размыть если реальный IP
5. Остальные скриншоты — беглый просмотр, 5 минут

🇬🇧
1. Open `android_davx5_caldav.jpg` in Paint — cover the IP with a white rectangle, label it "VPS_IP"
2. Open `nextcloud_talk.png` — assess the message content. If OK, leave it; if not, retake the screenshot.
3. Open `immich_web.png` — if faces are visible, crop to statistics only or blur the grid
4. Open `nas_jetson_nano_api_swagger.png` — check the address bar, blur it if it shows a real IP
5. Remaining screenshots — quick review, 5 minutes
