# Nextcloud Talk — Plan & Setup / План и настройка

> 🇷🇺 Семейный мессенджер и видеозвонки внутри NAS_Jetson_Nano.
>
> 🇬🇧 A family messenger and video calls inside NAS_Jetson_Nano.

## Что даёт Nextcloud Talk / What Nextcloud Talk provides

| Функция / Feature | Работает без TURN / Works without TURN | Работает с TURN / Works with TURN |
|---|---|---|
| Текстовый чат / Text chat | ✅ везде / everywhere | ✅ везде / everywhere |
| Голосовой/видеозвонок дома (LAN) / Voice/video call at home (LAN) | ✅ | ✅ |
| Голосовой/видеозвонок вне дома / Voice/video call away from home | ❌ | ✅ |
| Групповой чат / Group chat | ✅ | ✅ |
| Уведомления push / Push notifications | ✅ (через Android app / via Android app) | ✅ |
| Совместный доступ к файлам / Shared file access | ✅ | ✅ |

🇷🇺 **TURN-сервер (coturn)** — нужен только для звонков вне домашней сети.
Для текстового чата и звонков по LAN TURN не нужен.

🇬🇧 **TURN server (coturn)** is needed only for calls made outside the home network.
TURN is not required for text chat or for calls over the LAN.

---

## Шаг 1 — Установить Talk на Jetson (после подключения SSD) / Step 1 — Install Talk on Jetson (after the SSD is attached)

```bash
ssh admin@192.168.0.50
cd ~/nas_jetson_nano && git pull --ff-only
bash scripts/setup/install_nextcloud_talk.sh
```

🇷🇺 Скрипт:
- Устанавливает приложение `spreed` (Talk) через `occ`
- Настраивает STUN: `stun.l.google.com:19302` (работает из LAN и VPN)
- Если в `/etc/nas_jetson_nano-monitor/talk.env` есть TURN — настраивает его тоже

🇬🇧 The script:
- Installs the `spreed` (Talk) app via `occ`
- Configures STUN: `stun.l.google.com:19302` (works from LAN and VPN)
- If TURN is present in `/etc/nas_jetson_nano-monitor/talk.env` — configures it too

---

## Шаг 2 — Установить котурн на VPS (для звонков вне дома) / Step 2 — Install coturn on the VPS (for calls away from home)

### 2a. Сгенерировать секрет / Generate the secret

```bash
# На VPS или локально: / On the VPS or locally:
openssl rand -hex 32
# Скопировать результат → TURN_SECRET / Copy the result → TURN_SECRET
```

### 2b. Заполнить конфиг / Fill in the config

🇷🇺 Файл: `configs/coturn/turnserver.conf` — заменить `CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32`
на сгенерированный секрет.

🇬🇧 File: `configs/coturn/turnserver.conf` — replace `CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32`
with the generated secret.

🇷🇺 Добавить в `config/secrets.json`:

🇬🇧 Add to `config/secrets.json`:
```json
"coturn": {
  "static_auth_secret": "сюда_секрет"
}
```

### 2c. Открыть порты на VPS / Open ports on the VPS

```bash
# На VPS: / On the VPS:
ufw allow 3478/udp comment "TURN/STUN"
ufw allow 3478/tcp comment "TURN/STUN"
ufw allow 5349/udp comment "TURNS TLS"
ufw allow 5349/tcp comment "TURNS TLS"
ufw allow 49152:65535/udp comment "TURN media relay"
ufw reload
```

🇷🇺 ⚠️ **Порты 49152-65535/udp** — это большой диапазон. На VPS с Amnezia он не конфликтует
(Amnezia использует другие порты). Проверить: `ufw status numbered`.

🇬🇧 ⚠️ **Ports 49152-65535/udp** are a wide range. On a VPS running Amnezia it does not conflict
(Amnezia uses different ports). Verify with: `ufw status numbered`.

### 2d. Задеплоить coturn на VPS / Deploy coturn on the VPS

```bash
# На VPS: / On the VPS:
cd ~/nas_jetson_nano
git pull --ff-only
docker compose -f docker/compose/docker-compose.coturn.yml \
  --env-file config/.env up -d
docker logs homecloud_coturn
```

### 2e. Настроить Talk на использование TURN / Configure Talk to use TURN

🇷🇺 Создать `/etc/nas_jetson_nano-monitor/talk.env` на Jetson:

🇬🇧 Create `/etc/nas_jetson_nano-monitor/talk.env` on the Jetson:
```bash
TURN_SERVER=95.163.176.103:3478
TURN_SECRET=твой_секрет_из_шага_2a
```

🇷🇺 Перезапустить install-скрипт:

🇬🇧 Restart the install script:
```bash
bash ~/nas_jetson_nano/scripts/setup/install_nextcloud_talk.sh
```

🇷🇺 Или настроить вручную:
Nextcloud → Настройки → Talk → TURN-серверы:
- URL: `turn:95.163.176.103:3478`
- Секрет: твой секрет
- Протоколы: UDP и TCP

🇬🇧 Or configure manually:
Nextcloud → Settings → Talk → TURN servers:
- URL: `turn:95.163.176.103:3478`
- Secret: your secret
- Protocols: UDP and TCP

---

## Шаг 3 — Android-приложение / Step 3 — Android app

🇷🇺 **Скачать:** Play Store → **"Nextcloud Talk"**

🇬🇧 **Download:** Play Store → **"Nextcloud Talk"**

🇷🇺 **Настройка:**
1. Открыть → вход через Nextcloud
2. Адрес: `https://95.163.176.103:8443`
3. Логин / пароль: те же что в Nextcloud
4. Принять сертификат

🇬🇧 **Setup:**
1. Open → sign in via Nextcloud
2. Address: `https://95.163.176.103:8443`
3. Login / password: same as Nextcloud
4. Accept the certificate

🇷🇺 **Уведомления (важно для Xiaomi/MIUI):**
- Батарея → Нет ограничений для Nextcloud Talk
- Автозапуск → Вкл

🇬🇧 **Notifications (important for Xiaomi/MIUI):**
- Battery → No restrictions for Nextcloud Talk
- Autostart → On

---

## Шаг 4 — Проверка / Step 4 — Verification

```bash
# Проверить установку: / Check the install:
docker exec homecloud_nextcloud php occ app:list | grep spreed

# Проверить STUN (с Jetson): / Check STUN (from the Jetson):
nc -uzv stun.l.google.com 19302

# Проверить TURN (с любого хоста, если установлен turnutils): / Check TURN (from any host, if turnutils is installed):
turnutils_stunclient 95.163.176.103
```

---

## Пользователи / Users

🇷🇺 Talk автоматически доступен всем пользователям Nextcloud:
`admin`, `olga`, `ivan`, `ulyana`

🇬🇧 Talk is automatically available to all Nextcloud users:
`admin`, `olga`, `ivan`, `ulyana`

🇷🇺 Создать групповой чат «Семья»:
- Nextcloud → Talk → Новый разговор → Выбрать всех участников

🇬🇧 Create the "Семья" (Family) group chat:
- Nextcloud → Talk → New conversation → Select all participants

---

## Известные ограничения / Known limitations

🇷🇺
- Без TURN: видеозвонки только по LAN или через Amnezia VPN
- VPS 1 vCPU — coturn лёгкий (~10 MB RAM), не влияет на другие сервисы
- Self-signed сертификат: Talk app нужно один раз принять его при входе
- Push-уведомления работают через сервер уведомлений Nextcloud (не через Google FCM)

🇬🇧
- Without TURN: video calls work only over LAN or through the Amnezia VPN
- VPS 1 vCPU — coturn is light (~10 MB RAM), does not affect other services
- Self-signed certificate: the Talk app needs to accept it once at login
- Push notifications work through the Nextcloud notification server (not through Google FCM)
