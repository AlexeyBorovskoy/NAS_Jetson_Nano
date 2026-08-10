# Nextcloud Talk — Plan & Setup

> Семейный мессенджер и видеозвонки внутри NAS_Jetson_Nano.

## Что даёт Nextcloud Talk

| Функция | Работает без TURN | Работает с TURN |
|---|---|---|
| Текстовый чат | ✅ везде | ✅ везде |
| Голосовой/видеозвонок дома (LAN) | ✅ | ✅ |
| Голосовой/видеозвонок вне дома | ❌ | ✅ |
| Групповой чат | ✅ | ✅ |
| Уведомления push | ✅ (через Android app) | ✅ |
| Совместный доступ к файлам | ✅ | ✅ |

**TURN-сервер (coturn)** — нужен только для звонков вне домашней сети.  
Для текстового чата и звонков по LAN TURN не нужен.

---

## Шаг 1 — Установить Talk на Jetson (после подключения SSD)

```bash
ssh admin@192.168.0.50
cd ~/nas_jetson_nano && git pull --ff-only
bash scripts/setup/install_nextcloud_talk.sh
```

Скрипт:
- Устанавливает приложение `spreed` (Talk) через `occ`
- Настраивает STUN: `stun.l.google.com:19302` (работает из LAN и VPN)
- Если в `/etc/nas_jetson_nano-monitor/talk.env` есть TURN — настраивает его тоже

---

## Шаг 2 — Установить котурн на VPS (для звонков вне дома)

### 2a. Сгенерировать секрет

```bash
# На VPS или локально:
openssl rand -hex 32
# Скопировать результат → TURN_SECRET
```

### 2b. Заполнить конфиг

Файл: `configs/coturn/turnserver.conf` — заменить `CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32`  
на сгенерированный секрет.

Добавить в `config/secrets.json`:
```json
"coturn": {
  "static_auth_secret": "сюда_секрет"
}
```

### 2c. Открыть порты на VPS

```bash
# На VPS:
ufw allow 3478/udp comment "TURN/STUN"
ufw allow 3478/tcp comment "TURN/STUN"
ufw allow 5349/udp comment "TURNS TLS"
ufw allow 5349/tcp comment "TURNS TLS"
ufw allow 49152:65535/udp comment "TURN media relay"
ufw reload
```

⚠️ **Порты 49152-65535/udp** — это большой диапазон. На VPS с Amnezia он не конфликтует  
(Amnezia использует другие порты). Проверить: `ufw status numbered`.

### 2d. Задеплоить coturn на VPS

```bash
# На VPS:
cd ~/nas_jetson_nano
git pull --ff-only
docker compose -f docker/compose/docker-compose.coturn.yml \
  --env-file config/.env up -d
docker logs homecloud_coturn
```

### 2e. Настроить Talk на использование TURN

Создать `/etc/nas_jetson_nano-monitor/talk.env` на Jetson:
```bash
TURN_SERVER=95.163.176.103:3478
TURN_SECRET=твой_секрет_из_шага_2a
```

Перезапустить install-скрипт:
```bash
bash ~/nas_jetson_nano/scripts/setup/install_nextcloud_talk.sh
```

Или настроить вручную:  
Nextcloud → Настройки → Talk → TURN-серверы:
- URL: `turn:95.163.176.103:3478`
- Секрет: твой секрет
- Протоколы: UDP и TCP

---

## Шаг 3 — Android-приложение

**Скачать:** Play Store → **"Nextcloud Talk"**

**Настройка:**
1. Открыть → вход через Nextcloud
2. Адрес: `https://95.163.176.103:8443`
3. Логин / пароль: те же что в Nextcloud
4. Принять сертификат

**Уведомления (важно для Xiaomi/MIUI):**
- Батарея → Нет ограничений для Nextcloud Talk
- Автозапуск → Вкл

---

## Шаг 4 — Проверка

```bash
# Проверить установку:
docker exec homecloud_nextcloud php occ app:list | grep spreed

# Проверить STUN (с Jetson):
nc -uzv stun.l.google.com 19302

# Проверить TURN (с любого хоста, если установлен turnutils):
turnutils_stunclient 95.163.176.103
```

---

## Пользователи

Talk автоматически доступен всем пользователям Nextcloud:
`admin`, `olga`, `ivan`, `ulyana`

Создать групповой чат «Семья»:
- Nextcloud → Talk → Новый разговор → Выбрать всех участников

---

## Известные ограничения

- Без TURN: видеозвонки только по LAN или через Amnezia VPN
- VPS 1 vCPU — coturn лёгкий (~10 MB RAM), не влияет на другие сервисы
- Self-signed сертификат: Talk app нужно один раз принять его при входе
- Push-уведомления работают через сервер уведомлений Nextcloud (не через Google FCM)
