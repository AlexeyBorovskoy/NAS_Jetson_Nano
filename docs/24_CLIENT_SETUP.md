# 24. Подключение устройств / Client Setup

> 🇷🇺 Как подключить телефон, ноутбук и десктоп к NAS_Jetson_Nano.
> Охватывает Android, Windows и Linux — для каждой платформы и каждого сервиса.
>
> 🇬🇧 How to connect your phone, laptop, or desktop to NAS_Jetson_Nano.
> Covers Android, Windows, and Linux — for each platform and each service.
>
> Статус / Status 2026-06-27: Nextcloud, Immich и LLM Gateway доступны через VPS / accessible via VPS.
> SSD смонтирован в `/mnt/storage` / SSD mounted at `/mnt/storage`.

---

## Адреса доступа / Access URLs

| Режим / Mode | Где работает / Where | Адрес / Address |
|---|---|---|
| **LAN (домашняя сеть / home network)** | Дома / At home | `192.168.0.50` |
| **Внешний / External (через VPS / via VPS)** | Везде: 4G, другая сеть / Anywhere | `95.163.176.103` |

| Сервис / Service | LAN | Внешний / External (VPS) |
|---|---|---|
| Nextcloud | `http://192.168.0.50:8080` | `http://95.163.176.103:8080` |
| Immich | `http://192.168.0.50:2283` | `http://95.163.176.103:2283` |
| LLM Gateway | `http://192.168.0.50:8090` | `http://95.163.176.103:8090` |
| Samba NAS | `\\192.168.0.50` (SMB) | ❌ только LAN / LAN only |
| nas_jetson_nano-api / Swagger | `http://192.168.0.50:8099/docs` | ❌ только LAN / LAN only |
| Netdata | `http://192.168.0.50:19999` | ❌ только LAN / LAN only |
| Uptime Kuma | `http://192.168.0.50:3001` | ❌ только LAN / LAN only |
| Portainer | `http://192.168.0.50:9000` | ❌ только LAN / LAN only |

> 🇷🇺 **Примечание:** Samba и мониторинг — только LAN. Текущий внешний доступ для
> пользовательских сервисов идёт через VPS reverse tunnel (ADR-0005).
>
> 🇬🇧 **Note:** Samba and monitoring tools are LAN-only. External access for user services
> goes through the VPS reverse tunnel (ADR-0005).

---

## Android

### Nextcloud — файлы, контакты, календарь / Files, Contacts, Calendar

🇷🇺 **Файлы:** Настраивать синхронизацию только после проверки storage preflight:

1. Установить [Nextcloud](https://play.google.com/store/apps/details?id=com.nextcloud.client) из Play Store или F-Droid
2. Открыть приложение → "Войти" → ввести адрес сервера:
   - Дома: `http://192.168.0.50:8080`
   - Везде: `https://95.163.176.103:8443` (HTTPS)
3. Логин/пароль Nextcloud admin (или создать отдельного пользователя)
4. Включить автозагрузку фото: Профиль → Автозагрузка → выбрать папки

🇬🇧 **Files:** Set up sync only after verifying the storage preflight is clean:

1. Install [Nextcloud](https://play.google.com/store/apps/details?id=com.nextcloud.client) from Play Store or F-Droid
2. Open app → "Login" → enter server address:
   - At home: `http://192.168.0.50:8080`
   - Anywhere: `https://95.163.176.103:8443` (HTTPS, accept self-signed cert)
3. Nextcloud admin credentials (or create a separate user)
4. Enable photo auto-upload: Profile → Auto Upload → select folders

🇷🇺 **Контакты и календарь через DAVx⁵:**
1. Установить [DAVx⁵](https://play.google.com/store/apps/details?id=at.bitfire.davdroid) (APK v4.5.14 или Play Store)
2. Добавить аккаунт → "Войти с URL и именем пользователя"
3. URL: `https://95.163.176.103:8443/remote.php/dav` (HTTPS)
4. Логин/пароль — те же, что для Nextcloud
5. DAVx⁵ синхронизирует контакты и календарь с системным аккаунтом Android

🇬🇧 **Contacts and calendar via DAVx⁵:**
1. Install [DAVx⁵](https://play.google.com/store/apps/details?id=at.bitfire.davdroid) (APK v4.5.14 or Play Store)
2. Add account → "Login with URL and username"
3. URL: `https://95.163.176.103:8443/remote.php/dav` (HTTPS)
4. Same login/password as Nextcloud
5. DAVx⁵ syncs contacts and calendar with the Android system account

### Immich — резервная копия фотографий / Photo backup

🇷🇺
1. Установить [Immich](https://play.google.com/store/apps/details?id=app.alextran.immich)
2. Открыть → ввести адрес сервера:
   - Дома: `http://192.168.0.50:2283`
   - Везде: `http://95.163.176.103:2283`
3. Войти с логином/паролем Immich
4. Профиль → Настройки резервного копирования → включить
5. Immich будет автоматически загружать новые фото и видео на сервер

🇬🇧
1. Install [Immich](https://play.google.com/store/apps/details?id=app.alextran.immich)
2. Open → enter server address:
   - At home: `http://192.168.0.50:2283`
   - Anywhere: `http://95.163.176.103:2283`
3. Login with Immich credentials
4. Profile → Backup Settings → enable
5. Immich will automatically upload new photos and videos to the server

> 🇷🇺 Immich — полноценная замена Google Фото. Поддерживает альбомы, совместный доступ, временну́ю шкалу.
> 🇬🇧 Immich is a full Google Photos replacement. Supports albums, sharing, and timeline view.

### Samba NAS — доступ к сетевым папкам / Network shares

🇷🇺 Для доступа к общим папкам Samba нужен файловый менеджер с поддержкой SMB:

**Вариант 1 — ES File Explorer:**
1. Установить [ES File Explorer](https://play.google.com/store/apps/details?id=com.estrongs.android.pop)
2. Сеть → LAN → Новый → `192.168.0.50`
3. Войти как guest или с логином Samba

**Вариант 2 — Solid Explorer:**
1. Установить [Solid Explorer](https://play.google.com/store/apps/details?id=pl.solidexplorer2)
2. "+" → Network → SMB/CIFS → Хост: `192.168.0.50`

🇬🇧 To access Samba shares, use a file manager with SMB support:

**Option 1 — ES File Explorer:**
1. Install [ES File Explorer](https://play.google.com/store/apps/details?id=com.estrongs.android.pop)
2. Network → LAN → New → `192.168.0.50`
3. Login as guest or with Samba credentials

**Option 2 — Solid Explorer:**
1. Install [Solid Explorer](https://play.google.com/store/apps/details?id=pl.solidexplorer2)
2. "+" → Network → SMB/CIFS → Host: `192.168.0.50`

> 🇷🇺 Samba работает только в домашней сети (LAN). Вне дома доступ к Samba не публикуется.
> 🇬🇧 Samba is LAN-only. No external Samba access is published.

---

## Windows

### Nextcloud Desktop — синхронизация файлов / File sync

🇷🇺
1. Скачать [Nextcloud Desktop](https://nextcloud.com/install/#install-clients) для Windows
2. Установить → "Войти" → сервер:
   - Дома: `http://192.168.0.50:8080`
   - Везде: `https://95.163.176.103:8443`
3. Выбрать папку для синхронизации (например `C:\Users\<имя>\Nextcloud`)
4. Отметить папки для синхронизации → ОК
5. Значок в трее — статус синхронизации

🇬🇧
1. Download [Nextcloud Desktop](https://nextcloud.com/install/#install-clients) for Windows
2. Install → "Login" → server:
   - At home: `http://192.168.0.50:8080`
   - Anywhere: `https://95.163.176.103:8443`
3. Choose sync folder (e.g. `C:\Users\<name>\Nextcloud`)
4. Select folders to sync → OK
5. Tray icon shows sync status

🇷🇺 **Дополнительно — монтировать как диск (WebDAV):**
1. Открыть "Этот компьютер" → ПКМ → "Подключить сетевой диск"
2. Папка: `http://192.168.0.50:8080/remote.php/dav/files/<логин>/`
3. Отметить "Подключать при входе в систему"
4. Ввести логин/пароль Nextcloud

🇬🇧 **Optional — mount as drive (WebDAV):**
1. Open "This PC" → right-click → "Map network drive"
2. Folder: `http://192.168.0.50:8080/remote.php/dav/files/<login>/`
3. Check "Reconnect at sign-in"
4. Enter Nextcloud credentials

### Samba NAS — сетевые папки / Network shares

🇷🇺 Самый простой способ — через Проводник:

1. Открыть Проводник → в адресной строке ввести: `\\192.168.0.50`
2. Windows найдёт Jetson и покажет доступные папки (public, family, exchange)
3. ПКМ на нужной папке → "Подключить сетевой диск" → выбрать букву диска

🇬🇧 Easiest via File Explorer:

1. Open File Explorer → type in address bar: `\\192.168.0.50`
2. Windows will show available shares (public, family, exchange)
3. Right-click the share → "Map network drive" → assign a drive letter

```powershell
# Map drive N: / Подключить как диск N:
net use N: \\192.168.0.50\public /persistent:yes

# With credentials / С логином:
net use N: \\192.168.0.50\family /user:samba_user password /persistent:yes

# Verify / Проверка:
net use
```

### Immich — веб-интерфейс / Web UI

🇷🇺 Immich на Windows открывается в браузере:
- Дома: `http://192.168.0.50:2283`
- Везде: `http://95.163.176.103:2283`

🇬🇧 Immich on Windows opens in a browser:
- At home: `http://192.168.0.50:2283`
- Anywhere: `http://95.163.176.103:2283`

### Outlook / Thunderbird — контакты и календарь / Contacts & Calendar (CalDAV/CardDAV)

🇷🇺 **Thunderbird:**
1. Аккаунт → Параметры → Синхронизация → CalDAV
2. URL: `http://192.168.0.50:8080/remote.php/dav/calendars/<логин>/personal/`
3. CardDAV (контакты): `http://192.168.0.50:8080/remote.php/dav/addressbooks/<логин>/default/`

🇬🇧 **Thunderbird:**
1. Account → Settings → Sync → CalDAV
2. URL: `http://192.168.0.50:8080/remote.php/dav/calendars/<login>/personal/`
3. CardDAV (contacts): `http://192.168.0.50:8080/remote.php/dav/addressbooks/<login>/default/`

### Веб-интерфейсы / Web UIs (LAN)

| Сервис / Service | URL | Назначение / Purpose |
|---|---|---|
| Nextcloud | `http://192.168.0.50:8080` | Файлы, контакты, календарь / Files, contacts, calendar |
| Immich | `http://192.168.0.50:2283` | Семейный фотоархив / Family photo archive |
| LLM Gateway | `http://192.168.0.50:8090` | Локальный AI / Local AI assistant |
| nas_jetson_nano-api Swagger | `http://192.168.0.50:8099/docs` | API сервера / Server API |
| Netdata | `http://192.168.0.50:19999` | Мониторинг / Real-time monitoring |
| Uptime Kuma | `http://192.168.0.50:3001` | Статус сервисов / Service status |
| Portainer | `http://192.168.0.50:9000` | Управление Docker / Docker management |

---

## Linux

### Nextcloud Desktop — синхронизация файлов / File sync

```bash
# Ubuntu/Debian — установить / install
sudo apt install nextcloud-desktop

# Или через flatpak / Or via flatpak:
flatpak install flathub com.nextcloud.desktopclient.nextcloud
```

🇷🇺 Запустить → ввести сервер `http://192.168.0.50:8080` → логин/пароль → выбрать папку.
🇬🇧 Launch → enter server `http://192.168.0.50:8080` → credentials → choose sync folder.

```bash
# CLI sync / CLI-синхронизация:
sudo apt install nextcloud-desktop-cmd
nextcloudcmd -u admin -p <password> ~/nextcloud http://192.168.0.50:8080
```

### Samba — монтирование / Mount

```bash
# One-time mount / Разовое монтирование:
sudo apt install cifs-utils
sudo mkdir -p /mnt/nas
sudo mount -t cifs //192.168.0.50/public /mnt/nas -o guest,vers=2.0

# Persistent (fstab) / Постоянное монтирование:
echo "username=samba_user" | sudo tee /etc/samba-credentials
echo "password=<password>"  | sudo tee -a /etc/samba-credentials
sudo chmod 600 /etc/samba-credentials

# Add to /etc/fstab / Добавить в /etc/fstab:
//192.168.0.50/public /mnt/nas cifs credentials=/etc/samba-credentials,vers=2.0,nofail,_netdev 0 0
sudo mount -a
df -h /mnt/nas
```

🇷🇺 **Через Nautilus (GNOME Files) — без монтирования:**
1. Открыть Файлы → "Другие места" → ввести в адресную строку: `smb://192.168.0.50/public`

🇬🇧 **Via Nautilus (GNOME Files) — no mount needed:**
1. Open Files → "Other Locations" → type in address bar: `smb://192.168.0.50/public`

### Immich CLI

```bash
# Install / Установить
npm install -g @immich/cli

# Login / Войти
immich login http://192.168.0.50:2283 <API-key>

# Upload photos / Загрузить фото
immich upload ~/Pictures --recursive
```

🇷🇺 API-ключ: Immich → Профиль → API-ключи → Создать.
🇬🇧 API key: Immich → Profile → API Keys → Create.

### CalDAV/CardDAV (Linux)

🇷🇺 **GNOME Online Accounts:**
1. Настройки → Онлайн-аккаунты → "Другой аккаунт"
2. CalDAV / CardDAV
3. URL: `http://192.168.0.50:8080/remote.php/dav/`
4. Логин/пароль Nextcloud

🇬🇧 **GNOME Online Accounts:**
1. Settings → Online Accounts → "Other account"
2. CalDAV / CardDAV
3. URL: `http://192.168.0.50:8080/remote.php/dav/`
4. Nextcloud credentials

---

## Tailscale — архивный план / Archive Plan

> 🇷🇺 Текущая реализация — VPS reverse SSH tunnel (ADR-0005). Tailscale описан как
> возможный отдельный admin-сценарий, но не является текущей реализацией.
>
> 🇬🇧 Current implementation is the VPS reverse SSH tunnel (ADR-0005). Tailscale is
> documented as a possible separate admin scenario but is not the current implementation.

🇷🇺 После установки Tailscale на все устройства и входа в один аккаунт:
- Android/Windows/Linux видят Jetson по адресу Tailscale (100.x.x.x)
- Все порты доступны, как в LAN
- Работает через CGNAT, мобильный интернет, любую сеть

🇬🇧 After installing Tailscale on all devices and signing into one account:
- Android/Windows/Linux see Jetson via Tailscale address (100.x.x.x)
- All ports available as on LAN
- Works via CGNAT, mobile data, any network

Details / Инструкция: [docs/plans/TAILSCALE_ACCESS_PLAN.md](plans/TAILSCALE_ACCESS_PLAN.md)

---

## Быстрая проверка подключения / Quick Connectivity Check

```bash
# Check from client machine / Проверить с клиентской машины:
curl -sf http://192.168.0.50:8080/status.php | python3 -m json.tool  # Nextcloud
curl -sf http://192.168.0.50:2283/api/server/ping                     # Immich
curl -sf http://192.168.0.50:8099/healthcheck                         # nas_jetson_nano-api
ping 192.168.0.50                                                      # basic connectivity
```

🇷🇺 Если Nextcloud возвращает `503`, сначала проверить storage и состояние контейнера:
🇬🇧 If Nextcloud returns `503`, first check storage and container state:

```bash
docker ps -a --filter name=homecloud_nextcloud
sudo bash scripts/storage/storage_preflight.sh
```
