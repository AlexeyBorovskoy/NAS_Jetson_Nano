# Android Mobile Setup — NAS_Jetson_Nano

> 🇷🇺 Практическое руководство по настройке Xiaomi (MIUI / HyperOS) для синхронизации с самохостинговыми сервисами: Immich, Nextcloud, CardDAV/CalDAV.
>
> 🇬🇧 Practical guide for setting up Xiaomi (MIUI / HyperOS) to sync with self-hosted services: Immich, Nextcloud, CardDAV/CalDAV.

---

## Архитектура доступа / Access Architecture

```
Xiaomi (дома / at home)
  └── Wi-Fi → 192.168.0.50 (Jetson LAN, прямое подключение / direct)

Xiaomi (вне дома / away from home)
  └── VPN → VPS 193.8.215.130
        └── nginx reverse proxy → SSH tunnel → Jetson 192.168.0.50
```

🇷🇺 Оба сценария используют одинаковые URL — приложения умеют работать с двумя серверами (home/away) или с постоянным VPN-адресом.

🇬🇧 Both scenarios use the same URLs — apps can work with two server addresses (home/away) or a permanent VPN address.

---

## Требования (серверная сторона) / Server-side prerequisites

| Компонент / Component | Статус / Status |
|---|---|
| Jetson Nano запущен / running | ✅ |
| Immich работает на / running at :2283 | ✅ |
| Nextcloud работает на / running at :8080 | ✅ |
| Beszel мониторинг / monitoring | ✅ |
| nginx на VPS (HTTPS) | ✅ (`:8443`, `:2443`, `:9443`) |

---

## Шаг 1 / Step 1. nginx на VPS / Install nginx on VPS

> 🇷🇺 Выполняется один раз. Без этого шага удалённый доступ не работает.
> 🇬🇧 Run once. Without this step, remote access does not work.

```bash
# На Windows (Git Bash) / From Windows (Git Bash):
ssh -i ~/.ssh/borovskoy_new_ed25519 root@193.8.215.130 \
  "bash -s" < scripts/setup/install_nginx_vps.sh
```

🇷🇺 После установки сервисы доступны по адресам:
🇬🇧 After installation, services are available at:

| Сервис / Service | HTTP | HTTPS |
|---|---|---|
| Nextcloud | `http://193.8.215.130:8080` | `https://193.8.215.130:8443` |
| Immich | `http://193.8.215.130:2283` | `https://193.8.215.130:2443` |
| LLM Gateway | `http://193.8.215.130:8090` | `https://193.8.215.130:9443` |

> 🇷🇺 Самоподписанный сертификат — принять предупреждение один раз в браузере/приложении.
> 🇬🇧 Self-signed certificate — accept the warning once in browser/app.

---

## Шаг 2 / Step 2. Immich — синхронизация фото / Photo sync

### Установить приложение / Install app

**[Immich](https://play.google.com/store/apps/details?id=app.alextran.immich)** — Google Play
or APK from [github.com/immich-app/immich/releases](https://github.com/immich-app/immich/releases)

### Настройка / Setup

🇷🇺
1. Открыть Immich → **Войти** → ввести адрес сервера
2. **Дома (Wi-Fi):** `http://192.168.0.50:2283`
   **Вне дома:** `https://193.8.215.130:2443`
3. Создать пользователя в Immich или использовать существующего

🇬🇧
1. Open Immich → **Login** → enter server address
2. **At home (Wi-Fi):** `http://192.168.0.50:2283`
   **Away from home:** `https://193.8.215.130:2443`
3. Create an Immich user or use an existing one

### Настройка автозагрузки / Configure auto-backup

🇷🇺 Immich → **Профиль** → **Резервное копирование** → ✅ Включить фоновое резервное копирование

🇬🇧 Immich → **Profile** → **Backup** → ✅ Enable background backup

Рекомендуемые настройки / Recommended settings:
- ✅ Резервное копирование при Wi-Fi / Backup on Wi-Fi only (saves data)
- ✅ Исключить скриншоты / Exclude screenshots (Settings → Excluded Albums)
- ✅ Видео тоже копировать / Also backup videos
- 🇷🇺 Начать с Wi-Fi, потом включить мобильный интернет / 🇬🇧 Start Wi-Fi only, then enable mobile data

### Важно для Xiaomi MIUI/HyperOS / Important for Xiaomi

> 🇷🇺 Без этих настроек Immich не будет грузить фото в фоне!
> 🇬🇧 Without these settings Immich will not upload photos in the background!
> Details: [XIAOMI_MIUI_QUIRKS.md](XIAOMI_MIUI_QUIRKS.md)

---

## Шаг 3 / Step 3. Nextcloud — файловое облако / File cloud

### Установить приложение / Install app

**[Nextcloud](https://play.google.com/store/apps/details?id=com.nextcloud.client)** — Google Play

### Настройка / Setup

🇷🇺
1. Nextcloud → **Войти** → ввести адрес сервера:
   - Дома: `http://192.168.0.50:8080`
   - Вне дома: `https://193.8.215.130:8443`
2. Ввести логин/пароль Nextcloud
3. Разрешить доступ к файлам

🇬🇧
1. Nextcloud → **Login** → enter server address:
   - At home: `http://192.168.0.50:8080`
   - Away: `https://193.8.215.130:8443`
2. Enter Nextcloud login/password
3. Allow file access

### Автозагрузка файлов / Auto-upload (replaces Google Drive)

🇷🇺 Nextcloud → **⋮** → **Автозагрузка** → выбрать папки:
🇬🇧 Nextcloud → **⋮** → **Auto Upload** → select folders:

- `DCIM/Camera` → optional alternative to Immich
- `Documents` → документы / documents
- `Download` → загрузки / downloads

---

## Шаг 4 / Step 4. Контакты и Календарь / Contacts & Calendar (DAVx⁵)

🇷🇺 DAVx⁵ — мост между стандартными контактами/календарями Android и Nextcloud (CardDAV/CalDAV).
🇬🇧 DAVx⁵ is the bridge between standard Android contacts/calendars and Nextcloud (CardDAV/CalDAV).

### Установить DAVx⁵ / Install DAVx⁵

**[DAVx⁵](https://play.google.com/store/apps/details?id=at.bitfire.davdroid)** — Google Play (paid)
or free via **[F-Droid](https://f-droid.org/packages/at.bitfire.davdroid/)**

### Настройка / Setup

🇷🇺
1. DAVx⁵ → **+** → **Войти с URL**
2. **Base URL:**
   - Дома: `http://192.168.0.50:8080/remote.php/dav`
   - Вне дома: `https://193.8.215.130:8443/remote.php/dav`
3. Логин/пароль Nextcloud → **Далее**
4. DAVx⁵ найдёт: адресную книгу (CardDAV) и календари (CalDAV)
5. ✅ Включить синхронизацию нужных коллекций

🇬🇧
1. DAVx⁵ → **+** → **Login with URL**
2. **Base URL:**
   - At home: `http://192.168.0.50:8080/remote.php/dav`
   - Away: `https://193.8.215.130:8443/remote.php/dav`
3. Nextcloud login/password → **Next**
4. DAVx⁵ will find: address book (CardDAV) and calendars (CalDAV)
5. ✅ Enable sync for needed collections

🇷🇺 DAVx⁵ → Аккаунт → ⚙️ → **Интервал синхронизации**: 15 минут (рекомендуется)
🇬🇧 DAVx⁵ → Account → ⚙️ → **Sync interval**: 15 minutes (recommended)

---

## Шаг 5 / Step 5. Настройки Xiaomi / Xiaomi Background Settings

> 🇷🇺 Это критически важно — MIUI/HyperOS агрессивно убивает фоновые приложения.
> 🇬🇧 This is critical — MIUI/HyperOS aggressively kills background apps.

Краткий чеклист / Quick checklist:
- ⬜ Immich: снять ограничения батареи + разрешить автозапуск / remove battery restrictions + allow autostart
- ⬜ DAVx⁵: снять ограничения батареи + разрешить автозапуск / remove battery restrictions + allow autostart
- ⬜ Nextcloud: снять ограничения батареи + разрешить автозапуск / remove battery restrictions + allow autostart
- ⬜ VPN app: снять ограничения батареи / remove battery restrictions (otherwise VPN disconnects)

Details / Подробно: **[XIAOMI_MIUI_QUIRKS.md](XIAOMI_MIUI_QUIRKS.md)**

---

## Сетевые профили / Network profiles in apps

🇷🇺 Immich и Nextcloud поддерживают разные адреса для LAN и WAN.
🇬🇧 Immich and Nextcloud support separate addresses for LAN and WAN.

🇷🇺 **Рекомендация:** использовать постоянный HTTPS-адрес через VPS как основной — работает и дома, и вне дома.
🇬🇧 **Recommendation:** use the permanent HTTPS address via VPS as the main one — works both at home and away.

---

## Что НЕ синхронизируется без root / What does NOT sync without root

| Данные / Data | Статус / Status |
|---|---|
| SMS / MMS | ❌ requires root (Stage 4) |
| Журнал звонков / Call log | ❌ requires root |
| Wi-Fi пароли / Wi-Fi passwords | ❌ system backup only |
| Данные приложений / App data | ❌ requires root |
| Настройки системы / System settings | ❌ requires root |
| APK (список / list) | ✅ can export list |

---

## Ссылки / Links

- [GOOGLE_MIGRATION.md](GOOGLE_MIGRATION.md) — пошаговая миграция с Google / step-by-step Google migration
- [XIAOMI_MIUI_QUIRKS.md](XIAOMI_MIUI_QUIRKS.md) — специфика MIUI / MIUI specifics
- [install_nginx_vps.sh](../../scripts/setup/install_nginx_vps.sh) — nginx setup script
- [09_ANDROID_STAGE2_ARCHITECTURE.md](../09_ANDROID_STAGE2_ARCHITECTURE.md) — план кастомного приложения / custom app plan
