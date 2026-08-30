# 26. TP-Link Deco E4 AC1200 — перестройка домашней сети

> RU: Карточка устройства, анализ выигрыша и потерь для NAS, рекомендованная
> топология и пошаговый регламент настройки.
>
> EN: Device inventory, gain/loss analysis for the NAS, recommended topology,
> and a step-by-step configuration runbook.
>
> Создано / Created: 2026-08-09.
>
> ## ⛔ Документ заменён / Superseded
>
> **Статус: разведочный анализ, ЗАМЕНЁН документом [`27_HOME_NETWORK_MESH.md`](27_HOME_NETWORK_MESH.md) (2026-08-10).**
> Оставлен как история рассуждения; для работ использовать документ 27.
>
> **Что здесь оказалось неверно:** этот документ утверждал, что режим роутера обязательно
> сменит подсеть на `192.168.68.0/24` и потому неприемлем. Проверка спецификации TP-Link
> показала, что **LAN IP меняется** (`More → Advanced → LAN IP`), то есть подсеть
> `192.168.0.0/24` при замене роутера сохраняется. Кроме того, **Address Reservation
> недоступен в режиме AP** — а именно он нужен для проекта. Поэтому рекомендация
> изменилась на противоположную: выбран **режим Router**.
>
> **Что здесь осталось верным и перенесено в документ 27:** порты 100 Мбит/с как жёсткое
> ограничение, замеры «до», выигрыш от бесшовного роуминга для Immich, ценность гостевой
> сети, предложение закрыть план по Keenetic.

---

## 1. Главное в одном абзаце / Summary in one paragraph

🇷🇺 Deco E4 — это апгрейд **покрытия**, а не **скорости**. У него порты **100 Мбит/с**
(на коробке: «2 fast Ethernet ports per Deco unit»), тогда как Jetson сейчас подключён
на **1000 Мбит/с**. Любой клиент, чей трафик к NAS проходит через порт Deco, упирается
в потолок ≈ 94 Мбит/с (11 МБ/с). Поэтому **Jetson нельзя переносить на Deco** — он должен
остаться в гигабитном порту EC220-G5. При такой схеме проект выигрывает много и не теряет ничего.

🇬🇧 The Deco E4 is a **coverage** upgrade, not a **speed** upgrade. Its ports are **100 Mbps**
(box label: "2 fast Ethernet ports per Deco unit"), while the Jetson is currently connected
at **1000 Mbps**. Any client whose traffic to the NAS passes through a Deco port hits a
ceiling of ≈ 94 Mbps (11 MB/s). That is why **the Jetson must not be moved to a Deco port** —
it has to stay in the gigabit port on the EC220-G5. Under this scheme the project gains a lot
and loses nothing.

---

## 2. Идентификация устройства / Device identification

| Поле / Field | Значение / Value | Источник / Source |
|---|---|---|
| Производитель / Manufacturer | TP-Link | Коробка / Box |
| Модель / Model | Deco E4, AC1200, комплект 2 шт. / kit of 2 | Коробка / Box |
| Wi-Fi | 300 Мбит/с @ 2.4 ГГц + 867 Мбит/с @ 5 ГГц / 300 Mbps @ 2.4 GHz + 867 Mbps @ 5 GHz | Коробка / Box |
| Ethernet | **2 × Fast Ethernet (100 Мбит/с)** на модуль / **2 × Fast Ethernet (100 Mbps)** per unit | Коробка / Box |
| MU-MIMO | Есть, 2×2 / Yes, 2×2 | Коробка / Box |
| Покрытие / Coverage | до 260 м² комплектом / up to 260 m² per kit | Коробка / Box |
| Клиентов / Clients | до 100 / up to 100 | Коробка / Box |
| Режимы / Modes | Router **и Access Point** / Router **and Access Point** | Коробка / Box |
| Гостевая сеть / Guest network | Есть / Yes | Коробка / Box |
| IPv6 | Совместим / Compatible | Коробка / Box |
| QoS | Есть / Yes | Коробка / Box |
| Backhaul | Беспроводной или Ethernet (100 Мбит/с) / Wireless or Ethernet (100 Mbps) | Коробка / Box |
| Управление / Management | Только приложение Deco + аккаунт TP-Link / Deco app + TP-Link account only | Коробка / Box |
| Гарантия / Warranty | 3 года / 3 years | Коробка / Box |

---

## 3. Что есть сейчас (замерено 2026-08-09) / Current state (measured 2026-08-09)

| Параметр / Parameter | Значение / Value | Как получено / How obtained |
|---|---|---|
| Шлюз / Gateway | TP-Link / Aginet **EC220-G5**, `192.168.0.1` | `docs/19`, `docs/25` |
| Подсеть / Subnet | `192.168.0.0/24` | `ip route` на Jetson / on the Jetson |
| Jetson eth0 | **1000 Мбит/с, Full duplex**, 0 ошибок RX/TX / **1000 Mbps, Full duplex**, 0 RX/TX errors | `ethtool eth0` |
| SSID | `TP-Link_828C` / `TP-Link_828C_5G` (разные имена для диапазонов / different names per band) | `netsh wlan` |
| Рабочая станция / Workstation | 802.11ac, 5 ГГц, канал/channel 48, **сигнал/signal 48 %** | `netsh wlan` |
| Реальная скорость Wi-Fi → NAS / Actual Wi-Fi → NAS throughput | **17.6 МБ/с (141 Мбит/с) / 17.6 MB/s (141 Mbps)**, 400 МБ за 23.8 с / 400 MB in 23.8 s | HTTP-загрузка с Jetson / HTTP download from the Jetson |
| Диски NAS / NAS disks | SSD 250 МБ/с запись / write; HDD 2 ТБ 106 МБ/с чтение / read, 92 МБ/с запись / write | `dd`, 2026-08-09 |

🇷🇺 **Вывод из замеров.** Узкое место сегодня — Wi-Fi, а не диски и не Ethernet: 141 Мбит/с
против 800+ Мбит/с, которые способны отдать диски. Сигнал 48 % у рабочей станции
означает, что одна точка не покрывает квартиру — это и есть та боль, которую лечит mesh.

🇬🇧 **Conclusion from the measurements.** Today's bottleneck is Wi-Fi, not the disks or
Ethernet: 141 Mbps versus the 800+ Mbps the disks are capable of delivering. A 48 % signal
at the workstation means a single access point does not cover the apartment — that is exactly
the pain a mesh network fixes.

---

## 4. Что проект значительно выиграет / What the project gains significantly

### 4.1. Immich перестанет ронять автозагрузку с телефонов / Immich stops dropping phone auto-uploads
🇷🇺 Сейчас телефон при уходе в дальнюю комнату теряет 5 ГГц, прыгает на 2.4 ГГц или рвёт
сессию — автобэкап 6710 фото прерывается и начинается заново. Mesh с **единым SSID** и
бесшовным роумингом убирает это как класс. Это прямое попадание в главную функцию проекта.

🇬🇧 Right now, when a phone moves to a far room it loses the 5 GHz band, jumps to 2.4 GHz,
or drops the session — the auto-backup of 6,710 photos gets interrupted and restarts from
scratch. A mesh with a **single SSID** and seamless roaming removes this entirely. This is
a direct hit on the project's core function.

### 4.2. Единое имя сети вместо двух / One network name instead of two
🇷🇺 Сегодня `TP-Link_828C` и `TP-Link_828C_5G` — разные сети, и телефоны залипают на 2.4 ГГц,
получая 3–5 МБ/с вместо 17. Deco отдаёт **один SSID** на оба диапазона и сам уводит клиента
на 5 ГГц, где это выгодно.

🇬🇧 Today `TP-Link_828C` and `TP-Link_828C_5G` are separate networks, and phones stick to
2.4 GHz, getting 3–5 MB/s instead of 17. The Deco serves **a single SSID** for both bands
and steers the client to 5 GHz whenever it is advantageous.

### 4.3. Гостевая сеть = выполнение правила №4 внутри дома / Guest network enforces rule #4 inside the home
🇷🇺 Правило проекта «не открывать сервисы наружу» сейчас защищает только периметр интернета.
Внутри LAN Nextcloud, Immich, Portainer, **admin-API :8099** и Samba открыты **любому**,
кто знает пароль от Wi-Fi. Гостевая сеть Deco изолирует гостей, телевизор и IoT от подсети
NAS — это заметное усиление модели безопасности, которого сейчас нет вовсе.

🇬🇧 The project's "don't expose services outward" rule currently only protects the internet
perimeter. Inside the LAN, Nextcloud, Immich, Portainer, the **admin API on :8099**, and Samba
are open to **anyone** who knows the Wi-Fi password. The Deco guest network isolates guests,
the TV, and IoT devices from the NAS subnet — a real security improvement that does not
exist today at all.

### 4.4. Фиксированные адреса под план развития / Fixed addresses for the roadmap
🇷🇺 DHCP-резервирование в Deco закрепит `192.168.0.50` за Jetson и `192.168.0.60` за будущим
ML-узлом Vostro 15 (`docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`) — без правки статики на самих
устройствах.

🇬🇧 DHCP reservation in the Deco will pin `192.168.0.50` to the Jetson and `192.168.0.60` to
the future Vostro 15 ML node (`docs/plans/VOSTRO_ML_NODE_ONBOARDING.md`) — without touching
static settings on the devices themselves.

### 4.5. Keenetic Omni KN-1410 становится не нужен / Keenetic Omni KN-1410 becomes unnecessary
🇷🇺 `docs/25` планировал его как усилитель. Deco решает ту же задачу лучше (бесшовный роуминг
против простого репитера) и на том же классе портов. **Рекомендация: план по Keenetic закрыть,**
устройство оставить как холодный резерв.

🇬🇧 `docs/25` planned it as a range extender. The Deco solves the same problem better
(seamless roaming versus a plain repeater) with the same class of ports. **Recommendation:
close the Keenetic plan** and keep the device as a cold spare.

### 4.6. Стабильный фундамент под реверс-туннель / A stable foundation for the reverse tunnel
🇷🇺 Туннель на VPS не требует проброса портов, поэтому скудность NAT-функций Deco роли не играет.
Зато меньше разрывов Wi-Fi → меньше поводов для `autossh` пересоздавать сессию.

🇬🇧 The VPS tunnel does not need port forwarding, so the Deco's limited NAT features do not
matter. Fewer Wi-Fi disconnects also means fewer reasons for `autossh` to re-establish the
session.

---

## 5. Что можно потерять (и как не потерять) / What could be lost (and how to avoid it)

| Риск / Risk | Суть / Substance | Митигация / Mitigation |
|---|---|---|
| 🔴 **Потолок 100 Мбит/с / 100 Mbps ceiling** | Любой трафик через порт Deco ≤ 94 Мбит/с. Jetson сейчас в гигабите / Any traffic through a Deco port is capped at ≤ 94 Mbps. The Jetson is currently on gigabit | **Jetson оставить в порту EC220-G5.** Deco — только Wi-Fi / **Keep the Jetson on the EC220-G5 port.** The Deco is Wi-Fi only |
| 🔴 **Смена подсети / Subnet change** | В режиме роутера Deco по умолчанию поднимает `192.168.68.1/24`. В проекте `192.168.0.50` зашит в CLAUDE.md, мобильных приложениях, Samba, доках / In router mode the Deco defaults to `192.168.68.1/24`. `192.168.0.50` is hard-coded across CLAUDE.md, mobile apps, Samba, and docs | Использовать **режим Access Point** — подсеть не меняется вовсе / Use **Access Point mode** — the subnet does not change at all |
| 🟠 **Мало портов / Few ports** | На главном модуле 1 порт уйдёт под WAN → останется 1 LAN. Jetson + Vostro не поместятся / On the main unit 1 port goes to WAN → only 1 LAN port remains. The Jetson + Vostro will not both fit | Гигабитный свитч, либо режим AP (все порты EC220-G5 свободны) / A gigabit switch, or AP mode (all EC220-G5 ports stay free) |
| 🟠 **Облачная зависимость / Cloud dependency** | Настройка только через приложение и аккаунт TP-Link; веб-интерфейса нет / Configuration only via the app and a TP-Link account; no web UI | Осознанный компромисс. Для проекта «уход от облаков» — отметить в README / A conscious trade-off. Note it in the README for a project about "leaving the cloud" |
| 🟠 **Двойной NAT / Double NAT** | Deco в режиме роутера за EC220-G5 = два NAT, ломает Samba-обнаружение и mDNS / Deco in router mode behind the EC220-G5 = two NATs, breaks Samba discovery and mDNS | Только режим AP / AP mode only |
| 🟡 **Нет VLAN / No VLAN** | Полноценно изолировать IoT нельзя, только гостевая сеть / IoT cannot be fully isolated, only via the guest network | Достаточно гостевой сети / The guest network is sufficient |
| 🟡 **Ethernet-backhaul тоже 100 Мбит/с / Ethernet backhaul is also 100 Mbps** | Проводной backhaul между модулями не быстрее беспроводного / Wired backhaul between units is no faster than wireless | При хорошем сигнале **беспроводной backhaul на 5 ГГц может быть быстрее** / With a good signal, **5 GHz wireless backhaul may be faster** |

---

## 6. Рекомендованная топология / Recommended topology

### ✅ Вариант A — Deco в режиме Access Point (рекомендуется) / Option A — Deco in Access Point mode (recommended)

```
Интернет / Internet
   │
   ▼
EC220-G5  (шлюз, DHCP, гигабит / gateway, DHCP, gigabit)  192.168.0.1
   ├── LAN gigabit ──► Jetson Nano   192.168.0.50   ← 1000 Мбит/с, НЕ трогать / 1000 Mbps, DO NOT touch
   ├── LAN gigabit ──► Vostro 15     192.168.0.60   ← план / planned
   ├── LAN ─────────► Deco #1 (AP)   192.168.0.2
   └── LAN ─────────► Deco #2 (AP)   192.168.0.3   ← или беспроводной backhaul / or wireless backhaul
```

🇷🇺
- Wi-Fi EC220-G5 **выключить**, чтобы остался один SSID от Deco.
- Подсеть, шлюз, DHCP, статика Jetson — **не меняются**. Правило №3 CLAUDE.md соблюдено.
- Скорость Wi-Fi → NAS: ≈ 94 Мбит/с (потолок порта Deco), покрытие — по всей квартире.

🇬🇧
- **Turn off** Wi-Fi on the EC220-G5 so only the Deco's single SSID remains.
- The subnet, gateway, DHCP, and the Jetson's static config **do not change**. CLAUDE.md rule #3 is respected.
- Wi-Fi → NAS speed: ≈ 94 Mbps (Deco port ceiling), with coverage across the whole apartment.

### ⚠️ Вариант B — Deco как основной роутер / Option B — Deco as the primary router

🇷🇺 EC220-G5 убирается. Требует смены LAN-подсети Deco на `192.168.0.0/24`, иначе рвётся всё:
статика Jetson, URL в мобильных приложениях, Samba, документация. Jetson падает до 100 Мбит/с,
свободный порт остаётся один. **Не рекомендуется.**

🇬🇧 The EC220-G5 is removed. Requires changing the Deco's LAN subnet to `192.168.0.0/24`,
otherwise everything breaks: the Jetson's static config, URLs in mobile apps, Samba, the
documentation. The Jetson drops to 100 Mbps, and only one free port remains. **Not recommended.**

### 🔵 Вариант C — гибрид, если нужен максимум скорости на рабочем месте / Option C — hybrid, for maximum workstation speed

🇷🇺 Как A, но Wi-Fi EC220-G5 **оставить включённым** под отдельным SSID (например `NASA_FAST_5G`)
для рабочей станции: её трафик идёт гигабитным путём и сохраняет текущие 141 Мбит/с и выше.
Минус — две сети вместо одной, роуминг между ними не бесшовный.

🇬🇧 Same as A, but **keep** the EC220-G5's Wi-Fi **on** under a separate SSID (e.g. `NASA_FAST_5G`)
for the workstation: its traffic takes the gigabit path and keeps the current 141 Mbps or higher.
Downside: two networks instead of one, and roaming between them is not seamless.

---

## 7. Регламент настройки (Вариант A) / Configuration runbook (Option A)

### Шаг 0. Подготовка — до включения Deco / Step 0. Preparation — before powering on the Deco

🇷🇺
- [ ] Зафиксировать текущее: скриншот DHCP-таблицы EC220-G5, список резерваций.
- [ ] Убедиться, что доступ к Jetson есть **и по LAN, и через VPS-jump** (`ssh -p 10022`
      на `95.163.176.103`) — второй путь спасёт, если Wi-Fi ляжет посреди настройки.
- [ ] Свежий бэкап БД: `sudo systemctl start nasa-backup.service`, затем проверить, что в
      `/mnt/storage/backups/database-dumps/` появились файлы с сегодняшней датой.
- [ ] Заранее поставить приложение Deco и создать аккаунт TP-Link (без интернета не настроится).

🇬🇧
- [ ] Record the current state: a screenshot of the EC220-G5 DHCP table and reservation list.
- [ ] Make sure the Jetson is reachable **both over the LAN and via the VPS jump** (`ssh -p 10022`
      to `95.163.176.103`) — the second path is the fallback if Wi-Fi drops mid-setup.
- [ ] Fresh DB backup: `sudo systemctl start nasa-backup.service`, then verify that
      `/mnt/storage/backups/database-dumps/` has files with today's date.
- [ ] Install the Deco app and create a TP-Link account ahead of time (setup is impossible without internet).

### Шаг 1. Первый модуль / Step 1. First unit

🇷🇺
1. Deco #1 подключить в **свободный LAN-порт EC220-G5** (не в WAN).
2. В приложении пройти мастер. Когда спросит тип подключения — выбрать любой, режим сменим следом.
3. Сразу после мастера: **More → Advanced → Operation Mode → Access Point**. Модуль перезагрузится.
4. Проверить, что Deco получил адрес из `192.168.0.0/24`, а не поднял свой `192.168.68.x`.

🇬🇧
1. Connect Deco #1 to a **free LAN port on the EC220-G5** (not WAN).
2. Run the app wizard. When asked for the connection type — pick anything, the mode is changed next.
3. Right after the wizard: **More → Advanced → Operation Mode → Access Point**. The unit reboots.
4. Verify the Deco got an address from `192.168.0.0/24`, rather than raising its own `192.168.68.x`.

### Шаг 2. Параметры Wi-Fi / Step 2. Wi-Fi parameters

| Параметр / Parameter | Значение / Value | Почему / Why |
|---|---|---|
| SSID | Единый, например `NASA_HOME` / A single one, e.g. `NASA_HOME` | Бесшовный роуминг, конец залипанию на 2.4 ГГц / Seamless roaming, ends sticking to 2.4 GHz |
| Пароль / Password | WPA2/WPA3, новый, ≥ 16 символов / new, ≥ 16 characters | Внутри LAN сервисы не защищены — пароль Wi-Fi де-факто главный периметр / LAN services aren't otherwise protected — the Wi-Fi password is effectively the main perimeter |
| Smart Connect | Включить / Enable | Автовыбор диапазона / Automatic band selection |
| Fast Roaming | Включить / Enable | Ради Immich на телефонах / For Immich on phones |
| Гостевая сеть / Guest network | Включить, отдельный пароль / Enable, separate password | Изоляция гостей/IoT от NAS / Isolates guests/IoT from the NAS |

### Шаг 3. Второй модуль / Step 3. Second unit

🇷🇺
1. Разместить примерно на середине между Deco #1 и дальней комнатой — **не в самой дальней точке**.
2. Добавить через приложение. Дождаться индикации хорошего сигнала backhaul.
3. Если между комнатами есть кабель — можно завести Ethernet-backhaul, но помнить: он тоже
   100 Мбит/с и при сильном сигнале беспроводной может оказаться быстрее. **Сравнить замером.**

🇬🇧
1. Place it roughly halfway between Deco #1 and the far room — **not at the far point itself**.
2. Add it through the app. Wait for a good backhaul signal indication.
3. If there is a cable between the rooms, Ethernet backhaul is an option, but remember: it is
   also 100 Mbps, and with a strong signal wireless may turn out faster. **Compare by measuring.**

### Шаг 4. Отключить старый Wi-Fi / Step 4. Turn off the old Wi-Fi

🇷🇺 В веб-интерфейсе EC220-G5 (`192.168.0.1`) выключить Wi-Fi 2.4 ГГц и 5 ГГц.
DHCP и маршрутизация на EC220-G5 **остаются**.

🇬🇧 In the EC220-G5 web UI (`192.168.0.1`), turn off Wi-Fi on both 2.4 GHz and 5 GHz.
DHCP and routing on the EC220-G5 **stay in place**.

### Шаг 5. Резервирование адресов / Step 5. Address reservation

🇷🇺 DHCP остаётся на EC220-G5 → резервации делаются **там**, не в Deco:

🇬🇧 DHCP stays on the EC220-G5 → reservations are made **there**, not on the Deco:

| Устройство / Device | MAC | Адрес / Address |
|---|---|---|
| Jetson Nano | `00:04:4b:e6:88:dc` | `192.168.0.50` |
| Vostro 15 (план / planned) | — | `192.168.0.60` |
| Deco #1 | — | `192.168.0.2` |
| Deco #2 | — | `192.168.0.3` |

---

## 8. Проверка после перестройки / Verification after the rebuild

🇷🇺 Прогнать целиком; всё должно пройти.

🇬🇧 Run the whole sequence; everything must pass.

```bash
# 1. Jetson на месте и всё ещё в гигабите
ssh admin@192.168.0.50 "ip -4 -br addr show eth0; ethtool eth0 | grep Speed"
#    ожидаем: 192.168.0.50/24 и Speed: 1000Mb/s

# 2. Все контейнеры живы
ssh admin@192.168.0.50 "docker ps --format '{{.Names}} {{.Status}}' | wc -l"   # 13

# 3. Сервисы отвечают по LAN
for p in 8080 2283 8090 8099 3001 19999 9000; do
  curl -s -o /dev/null -w "$p: %{http_code}\n" --max-time 10 http://192.168.0.50:$p
done

# 4. Реверс-туннель не порвался
ssh admin@192.168.0.50 "systemctl is-active nasa-tunnel; ss -tn | grep 95.163.176.103"

# 5. Samba и HDD
#    из проводника Windows: \\192.168.0.50\hdd2tb  и  \\192.168.0.50\public

# 6. Скорость Wi-Fi → NAS (ожидаем ~11 МБ/с в варианте A)
ssh -f admin@192.168.0.50 "cd /dev/shm && dd if=/dev/zero of=spd.bin bs=1M count=400 2>/dev/null && timeout 100 python3 -m http.server 8123 >/dev/null 2>&1 </dev/null"
curl -s -o /dev/null -w "%{speed_download} B/s\n" http://192.168.0.50:8123/spd.bin
ssh admin@192.168.0.50 "rm -f /dev/shm/spd.bin"
```

🇷🇺 Отдельно проверить на телефоне: Immich делает автозагрузку, пройдя по всей квартире без разрывов.

🇬🇧 Separately verify on a phone: Immich auto-upload keeps working while walking through the
whole apartment without interruptions.

---

## 9. Откат / Rollback

🇷🇺 Deco в режиме AP ничего не меняет в адресации, поэтому откат тривиален:

1. Выдернуть оба модуля Deco из сети.
2. Включить обратно Wi-Fi на EC220-G5 (`192.168.0.1`).
3. Всё возвращается к текущему состоянию: подсеть, DHCP и статика Jetson не менялись.

Если случайно был выбран Вариант B и Deco сменил подсеть — Jetson станет недоступен по LAN.
**Резервный путь входа сохраняется:** VPS-jump
`ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103` → `ssh -p 10022 admin@127.0.0.1`.

🇬🇧 The Deco in AP mode does not change addressing at all, so rollback is trivial:

1. Unplug both Deco units from the network.
2. Turn Wi-Fi back on on the EC220-G5 (`192.168.0.1`).
3. Everything returns to the current state: the subnet, DHCP, and the Jetson's static config
   never changed.

If Option B was chosen by mistake and the Deco changed the subnet, the Jetson becomes
unreachable over the LAN. **The fallback entry path still works:** VPS jump
`ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103` → `ssh -p 10022 admin@127.0.0.1`.

---

## 10. Чего категорически нельзя / What is strictly forbidden

🇷🇺
1. **Не переносить Jetson в порт Deco** — падение 1000 → 100 Мбит/с.
2. **Не менять подсеть** `192.168.0.0/24` и адрес `192.168.0.50` (правило №3 CLAUDE.md).
3. **Не включать Deco в режиме роутера за EC220-G5** — двойной NAT ломает Samba и mDNS.
4. **Не выносить сервисы NAS в гостевую сеть** и не открывать их из неё.
5. Смена пароля Wi-Fi = повторный вход всех клиентов; делать не в момент автобэкапа Immich.

🇬🇧
1. **Do not move the Jetson to a Deco port** — a drop from 1000 to 100 Mbps.
2. **Do not change the subnet** `192.168.0.0/24` or the address `192.168.0.50` (CLAUDE.md rule #3).
3. **Do not put the Deco in router mode behind the EC220-G5** — double NAT breaks Samba and mDNS.
4. **Do not put NAS services on the guest network** or open them from it.
5. Changing the Wi-Fi password forces every client to reconnect; do not do it during an Immich
   auto-backup.

---

## 11. Открытые вопросы / Open questions

🇷🇺
- Есть ли между комнатами витая пара под Ethernet-backhaul? От этого зависит Шаг 3.
- Нужен ли гигабитный свитч сейчас или после подключения Vostro 15.
- Оставлять ли отдельный «быстрый» SSID (Вариант C) для рабочей станции.

🇬🇧
- Is there Ethernet cable between the rooms for backhaul? Step 3 depends on this.
- Is a gigabit switch needed now, or only after the Vostro 15 is connected.
- Whether to keep a separate "fast" SSID (Option C) for the workstation.

## 12. Связанные документы / Related documents

- `docs/19_NETWORK_INVENTORY.md` — инвентаризация сети / network inventory
- `docs/25_KEENETIC_OMNI_KN1410.md` — предшествующий план усилителя (предлагается закрыть) / earlier range-extender plan (proposed to close)
- `docs/24_CLIENT_SETUP.md` — настройка клиентов / client setup
- `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md` — будущий узел `192.168.0.60` / future node `192.168.0.60`
