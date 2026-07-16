# Миграция с Google — NAS_Jetson_Nano
# Google Migration — NAS_Jetson_Nano

> 🇷🇺 Пошаговая замена Google-сервисов самохостингом. Всё делается постепенно — Google не отключается до подтверждения, что данные перенесены.
>
> 🇬🇧 Step-by-step replacement of Google services with self-hosted alternatives. Everything is gradual — don't disable Google until data is confirmed migrated.

---

## Обзор миграции / Migration overview

```
Google Photos ──────────────────────→ Immich
Google Drive  ──────────────────────→ Nextcloud Files
Google Контакты / Contacts ─────────→ Nextcloud Contacts (CardDAV)
Google Календарь / Calendar ────────→ Nextcloud Calendar (CalDAV)
Gmail ──────────────────────────────→ не мигрируем / not migrated (Stage 5)
Google Maps offline ────────────────→ не мигрируем / not migrated
```

---

## Фаза 0 / Phase 0. Экспорт из Google / Export from Google (Google Takeout)

> 🇷🇺 Делается ДО настройки приложений. Без экспорта нет данных для импорта.
> 🇬🇧 Done BEFORE configuring apps. Without export there is no data to import.

### 0.1 Скачать Google Takeout / Download Google Takeout

🇷🇺
1. Открыть [takeout.google.com](https://takeout.google.com)
2. **Снять выбор со всего** → выбрать только нужное:
   - ✅ **Google Фото** → Все фото альбомы
   - ✅ **Контакты** → формат vCard (.vcf)
   - ✅ **Календарь** → формат iCal (.ics)
   - ✅ **Диск** → все файлы (опционально, большой объём)
3. Формат: zip, максимальный размер архива 50 GB
4. Нажать **Создать экспорт** → придёт email со ссылкой (от нескольких часов до 2 дней)
5. Скачать архивы

🇬🇧
1. Open [takeout.google.com](https://takeout.google.com)
2. **Deselect all** → select only what you need:
   - ✅ **Google Photos** → All photo albums
   - ✅ **Contacts** → vCard (.vcf) format
   - ✅ **Google Calendar** → iCal (.ics) format
   - ✅ **Google Drive** → all files (optional, can be large)
3. Format: zip, max archive size 50 GB
4. Click **Create export** → you will receive an email link (few hours to 2 days)
5. Download the archives

### 0.2 Структура Takeout / Takeout structure

```
Takeout/
├── Google Фото / Google Photos/
│   ├── Фото со мной / Photos with me/
│   ├── Photos from 2023/
│   │   ├── IMG_20230115.jpg
│   │   ├── IMG_20230115.jpg.json  ← metadata (date, GPS)
│   │   └── ...
│   └── ...
├── Контакты / Contacts/
│   └── Контакты.vcf               ← all contacts in one file
└── Календарь / Calendar/
    ├── Личный / Personal.ics
    └── Праздники в России.ics
```

---

## Фаза 1 / Phase 1. Миграция фотографий / Migrate photos → Immich

### Метод A / Method A: Через веб-интерфейс / Via web (small collections, < 5 GB)

🇷🇺
1. Открыть `http://192.168.0.50:2283` (или HTTPS-адрес)
2. Войти в Immich
3. **+** → **Загрузить** → перетащить папки из Takeout
4. Immich читает метаданные из `.json` файлов Google (дата, GPS)

🇬🇧
1. Open `http://192.168.0.50:2283` (or HTTPS address)
2. Log into Immich
3. **+** → **Upload** → drag folders from Takeout
4. Immich reads metadata from Google's `.json` files (date, GPS)

### Метод B / Method B: Через CLI (большие коллекции, рекомендуется / large collections, recommended)

🇷🇺 Immich включает инструмент `immich-go` для массового импорта с сохранением метаданных.
🇬🇧 Immich's companion tool `immich-go` enables bulk import with metadata preservation.

```bash
# На машине с архивом Takeout (Windows/Linux) / On the machine with the Takeout archive:

# 1. Скачать / Download immich-go:
# https://github.com/simulot/immich-go/releases
# Windows: immich-go_Windows_x86_64.zip

# 2. Запустить импорт / Run import:
./immich-go upload \
  --server http://192.168.0.50:2283 \
  --api-key YOUR_IMMICH_API_KEY \
  --google-photos \
  "E:/Takeout/Google Фото/"
```

**Получить API ключ Immich / Get Immich API key:**
🇷🇺 Immich Web → Аватар → Настройки аккаунта → API ключи → Новый ключ
🇬🇧 Immich Web → Avatar → Account Settings → API Keys → New Key

### Что происходит при импорте / What happens during import

- 🇷🇺 Immich читает `.json` метаданные Google → восстанавливает **оригинальные даты** фото
- 🇬🇧 Immich reads Google `.json` metadata → restores **original photo dates**
- 🇷🇺 Дубликаты определяются по хешу файла — повторно не загружаются
- 🇬🇧 Duplicates detected by file hash — not uploaded twice
- 🇷🇺 GPS-координаты сохраняются (карта в Immich работает)
- 🇬🇧 GPS coordinates preserved (Immich map view works)
- 🇷🇺 Live Photos (MOV + JPG) объединяются автоматически
- 🇬🇧 Live Photos (MOV + JPG) paired automatically

### Проверка импорта / Verify import

```
Immich → Explore → По дате / By date — хронология / timeline should restore
Immich → Map — GPS точки / GPS points should appear
```

---

## Фаза 2 / Phase 2. Миграция контактов / Migrate contacts → Nextcloud Contacts

### 2.1 Импорт в Nextcloud / Import into Nextcloud

🇷🇺
1. Открыть `http://192.168.0.50:8080` → Nextcloud
2. **Контакты** (значок в верхнем меню)
3. ⚙️ → **Импортировать** → выбрать `Контакты.vcf` из Takeout
4. Дождаться импорта

🇬🇧
1. Open `http://192.168.0.50:8080` → Nextcloud
2. **Contacts** (top menu icon)
3. ⚙️ → **Import** → select `Contacts.vcf` from Takeout
4. Wait for import to complete

### 2.2 Настроить синхронизацию / Set up phone sync

🇷🇺 После установки DAVx⁵ ([ANDROID_SETUP.md → Шаг 4](ANDROID_SETUP.md)):
- DAVx⁵ синхронизирует Nextcloud Contacts → стандартное приложение Контакты Xiaomi
- Контакты появятся через 1–2 минуты после первой синхронизации

🇬🇧 After installing DAVx⁵ ([ANDROID_SETUP.md → Step 4](ANDROID_SETUP.md)):
- DAVx⁵ syncs Nextcloud Contacts → standard Xiaomi Contacts app
- Contacts appear within 1–2 minutes after first sync

### 2.3 Отключить Google Contacts sync / Disable Google Contacts sync

🇷🇺 После проверки (все контакты на месте):
Настройки → Аккаунты → Google → выключить **Контакты**

🇬🇧 After verifying (all contacts present):
Settings → Accounts → Google → disable **Contacts**

> ⚠️ 🇷🇺 Не удалять аккаунт Google целиком — только синхронизацию контактов.
> ⚠️ 🇬🇧 Do not remove the Google account entirely — only disable contact sync.

---

## Фаза 3 / Phase 3. Миграция календарей / Migrate calendars → Nextcloud Calendar

### 3.1 Импорт в Nextcloud / Import into Nextcloud

🇷🇺
1. Nextcloud → **Календарь**
2. ← (левое меню) → **Импорт календаря** → выбрать `.ics` файл из Takeout
3. Повторить для каждого календаря

🇬🇧
1. Nextcloud → **Calendar**
2. ← (left menu) → **Import Calendar** → select `.ics` file from Takeout
3. Repeat for each calendar (Personal, Holidays, etc.)

### 3.2 Синхронизация / Phone sync

🇷🇺 DAVx⁵ автоматически найдёт новые календари после синхронизации.
Проверить: DAVx⁵ → Аккаунт NAS_Jetson_Nano → CalDAV → список календарей ✅

🇬🇧 DAVx⁵ will automatically find new calendars after sync.
Check: DAVx⁵ → NAS_Jetson_Nano Account → CalDAV → calendar list ✅

### 3.3 Отключить Google Calendar sync / Disable Google Calendar sync

🇷🇺 Настройки → Аккаунты → Google → выключить **Календарь**
🇬🇧 Settings → Accounts → Google → disable **Calendar**

---

## Фаза 4 / Phase 4. Миграция файлов / Migrate files → Nextcloud

### 4.1 Загрузить через веб / Upload via web

🇷🇺 Nextcloud Web → **Файлы** → **Загрузить** → выбрать папки из `Takeout/Диск/`
Для больших объёмов использовать WebDAV-клиент (Cyberduck, RaiDrive)

🇬🇧 Nextcloud Web → **Files** → **Upload** → select folders from `Takeout/Drive/`
For large volumes use a WebDAV client (Cyberduck, RaiDrive)

### 4.2 WebDAV адрес / WebDAV address

```
http://192.168.0.50:8080/remote.php/dav/files/USERNAME/
или / or
https://193.8.215.130:8443/remote.php/dav/files/USERNAME/
```

### 4.3 Настроить авто-синхронизацию / Configure auto-upload

🇷🇺 Nextcloud Android → **⋮** → **Автозагрузка**: `Documents` → `Documents/`, `Download` → `Downloads/`
🇬🇧 Nextcloud Android → **⋮** → **Auto Upload**: `Documents` → `Documents/`, `Download` → `Downloads/`

---

## Фаза 5 / Phase 5. Отключение Google Photos / Disable Google Photos

🇷🇺 После проверки что ВСЕ фото в Immich (сравнить количество):
1. Убедиться что в Google Фото есть резервные копии
2. Отключить резервное копирование Google Фото на телефоне:
   Google Фото → Профиль → Настройки Фото → Резервное копирование → Выкл.
3. Через месяц (после проверки) — очистить Google Photos
4. Immich → включить авто-загрузку новых фото

🇬🇧 After confirming ALL photos are in Immich (compare counts):
1. Confirm Google Photos shows backups exist
2. Disable Google Photos backup on phone:
   Google Photos → Profile → Photo Settings → Backup → Off
3. After one month (after verification) — clear Google Photos
4. Immich → enable auto-upload of new photos

---

## Чеклист миграции / Migration checklist

### Подготовка / Preparation
- ⬜ Google Takeout создан и скачан / created and downloaded
- ⬜ nginx на VPS установлен / installed (`scripts/setup/install_nginx_vps.sh`)

### Фото / Photos
- ⬜ Импортировано через immich-go / imported (verify count vs Google Photos)
- ⬜ Даты, GPS в Immich корректны / dates and GPS correct in Immich
- ⬜ Immich авто-загрузка включена / auto-upload enabled on phone
- ⬜ Google Photos backup **отключён / disabled**

### Контакты / Contacts
- ⬜ .vcf импортирован в Nextcloud Contacts / imported
- ⬜ DAVx⁵ настроен, контакты синхронизированы / configured, contacts synced
- ⬜ Google Contacts sync **отключён / disabled** (not the account — only sync)
- ⬜ Контакты видны в приложении Xiaomi / visible in Xiaomi Contacts app

### Календарь / Calendar
- ⬜ .ics импортирован в Nextcloud Calendar / imported
- ⬜ DAVx⁵ синхронизировал CalDAV / synced CalDAV
- ⬜ Google Calendar sync **отключён / disabled**
- ⬜ События видны в MIUI Calendar / events visible in MIUI Calendar

### Файлы / Files
- ⬜ Drive файлы загружены в Nextcloud / uploaded
- ⬜ Nextcloud авто-загрузка настроена / auto-upload configured
- ⬜ Google Drive sync **отключён / disabled** (or keep as secondary)

---

## Что остаётся в Google / What stays in Google (not migrated)

| Сервис / Service | Причина / Reason |
|---|---|
| Gmail | Сложная инфраструктура / complex infrastructure, client everywhere |
| Google Maps (история / history) | Нет аналога / No equivalent |
| YouTube | Нет аналога / No equivalent |
| Google Authenticator | Перенести в Aegis / Move to Aegis (F-Droid) separately |
| Google Play | Системная зависимость Xiaomi / System dependency on Xiaomi |

---

## Инструменты / Tools

| Инструмент / Tool | Назначение / Purpose | Ссылка / Link |
|---|---|---|
| immich-go | Импорт Google Takeout → Immich / Import | github.com/simulot/immich-go |
| DAVx⁵ | CardDAV/CalDAV клиент / client for Android | bitfire.at/davdroid |
| Nextcloud | Файлы + Контакты + Календарь / Files + Contacts + Calendar | nextcloud.com |
| Aegis | TOTP (2FA) замена / replaces Google Authenticator | getaegis.app |
| F-Droid | Альтернативный маркет / Alternative app store | f-droid.org |
