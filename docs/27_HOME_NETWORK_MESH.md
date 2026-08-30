# 27. Домашняя сеть на TP-Link Deco E4 — замена роутера / Home network on TP-Link Deco E4 — replacing the router

> RU: Рабочий документ по переводу домашней сети на mesh TP-Link Deco E4 с полной
> заменой роутера EC220-G5. Решение принято владельцем 2026-08-10.
>
> EN: Working document for migrating the home network to a TP-Link Deco E4 mesh,
> fully replacing the EC220-G5 router. Decision made by the owner on 2026-08-10.
>
> Создано / Created: 2026-08-10. Статус: **регламент готов, оборудование не введено.**
> Заменяет разведочный `docs/26_DECO_E4_NETWORK.md`.
>
> Status: **the procedure is ready, the equipment is not yet in service.**
> Supersedes the exploratory `docs/26_DECO_E4_NETWORK.md`.

---

## 1. Решение и его цена / The decision and its price

🇷🇺 **Решение владельца:** Deco E4 становится основным роутером сети. EC220-G5 выводится
из эксплуатации полностью.

**Что это даёт:** покрытие всей квартиры, единый SSID с бесшовным роумингом, гостевая
сеть для изоляции IoT, резервирование адресов, одно место управления вместо двух.

**Чем за это платим — честно и в цифрах:**

🇬🇧 **Owner's decision:** the Deco E4 becomes the network's primary router. The EC220-G5 is
fully decommissioned.

**What this brings:** coverage of the whole apartment, a single SSID with seamless roaming,
a guest network for IoT isolation, address reservation, one place to manage instead of two.

**The honest price, in numbers:**

| Параметр / Parameter | Сейчас / Now | После / After | Изменение / Change |
|---|---|---|---|
| Интернет / Internet | тариф ≤ 100 Мбит/с / plan ≤ 100 Mbps | 94 Мбит/с (потолок порта) / 94 Mbps (port ceiling) | ✅ **потерь нет / no loss** — тариф и так ниже потолка / the plan is already below the ceiling |
| Jetson ↔ сеть / Jetson ↔ network | **1000 Мбит/с / 1000 Mbps** | **100 Мбит/с / 100 Mbps** | 🔴 в 10 раз / 10× |
| Wi-Fi → NAS | 141 Мбит/с (17.6 МБ/с) / 141 Mbps (17.6 MB/s) | ≈ 94 Мбит/с (11 МБ/с) / ≈ 94 Mbps (11 MB/s) | 🟠 −33 % |
| Копирование с архива 2 ТБ по Samba / Copying from the 2 TB archive over Samba | упиралось в Wi-Fi / was Wi-Fi bound | **11 МБ/с / 11 MB/s** | 🟠 1.4 ТБ ≈ 36 часов / 1.4 TB ≈ 36 hours |
| Покрытие / Coverage | одна точка, сигнал 48 % / one access point, 48 % signal | вся квартира / whole apartment | ✅ ради этого всё и делается / this is the whole point |
| Роуминг Immich / Immich roaming | рвётся при переходе / drops on handoff | бесшовный / seamless | ✅ главный выигрыш / the main win |

🇷🇺 **Ключевое:** диски NAS отдают 250 МБ/с (SSD) и 106 МБ/с (HDD), а сеть после перехода
даст 11 МБ/с. Узким местом становится сеть, а не хранилище. Для просмотра фото,
автозагрузки с телефонов и работы с документами этого достаточно с запасом. Ощутимо
станет только на разовых массовых копированиях в архив.

🇬🇧 **Key point:** the NAS disks deliver 250 MB/s (SSD) and 106 MB/s (HDD), while the network
after the move will deliver 11 MB/s. The network becomes the bottleneck, not the storage. For
viewing photos, phone auto-uploads, and working with documents this is more than enough. It
will only be noticeable during one-off bulk copies into the archive.

> 🔧 🇷🇺 **Путь отхода, если 11 МБ/с начнёт мешать:** любой дешёвый гигабитный свитч между
> Deco и проводными устройствами вернёт гигабит **между ними** (см. раздел 10).
> Wi-Fi-клиенты при этом всё равно останутся на 94 Мбит/с — это потолок порта Deco.
>
> 🇬🇧 **Escape route if 11 MB/s becomes a problem:** any cheap gigabit switch between the
> Deco and wired devices restores gigabit **between them** (see section 10). Wi-Fi clients
> will still stay at 94 Mbps — that is the Deco port ceiling.

---

## 2. Оборудование / Equipment

### 2.1. TP-Link Deco E4 AC1200 (комплект 2 шт.) / TP-Link Deco E4 AC1200 (kit of 2)

🇷🇺 Проверено по спецификации производителя (2026-08-10):

🇬🇧 Verified against the manufacturer's spec sheet (2026-08-10):

| Параметр / Parameter | Значение / Value |
|---|---|
| Wi-Fi | AC1200: 300 Мбит/с @ 2.4 ГГц + 867 Мбит/с @ 5 ГГц / 300 Mbps @ 2.4 GHz + 867 Mbps @ 5 GHz |
| MU-MIMO | 2×2 |
| **Ethernet** | **2 × 10/100 Мбит/с** WAN/LAN на модуль — аппаратное ограничение / **2 × 10/100 Mbps** WAN/LAN per unit — a hardware limit |
| Покрытие / Coverage | до 260 м² комплектом / up to 260 m² per kit |
| Клиентов / Clients | до 100 / up to 100 |
| Режимы / Modes | Router и Access Point / Router and Access Point |
| Гостевая сеть / Guest network | есть / yes |
| IPv6 | совместим / compatible |
| Backhaul | беспроводной или Ethernet (тоже 100 Мбит/с) / wireless or Ethernet (also 100 Mbps) |
| Управление / Management | **только приложение Deco + аккаунт TP-Link**, веб-интерфейса нет / **Deco app + TP-Link account only**, no web UI |
| Гарантия / Warranty | 3 года / 3 years |

### 2.2. Что доступно в каком режиме / What is available in each mode

🇷🇺 Важное различие, определившее выбор режима:

🇬🇧 The key distinction that decided which mode to pick:

| Функция / Feature | Режим Router / Router mode | Режим Access Point / AP mode |
|---|---|---|
| Смена LAN IP / Changing the LAN IP (`More → Advanced → LAN IP`) | ✅ | — (адрес даёт вышестоящий роутер / address comes from the upstream router) |
| **Address Reservation** (резервирование по MAC / MAC-based reservation) | ✅ | ❌ **недоступно / unavailable** |
| Проброс портов / Port forwarding | ✅ | ❌ недоступно / unavailable |
| TP-Link DDNS | ✅ | ❌ недоступно / unavailable |
| Родительский контроль / Parental controls | ✅ | ❌ недоступно / unavailable |
| Гостевая сеть / Guest network | ✅ | ✅ |
| Ethernet backhaul | ✅ | ✅ |
| DHCP-сервер / DHCP server | ✅ (отключить нельзя / cannot be disabled) | — |

🇷🇺 Именно поэтому режим **Router** — правильный выбор для нашей цели: он единственный
даёт резервирование адресов и полное управление сетью из одного места.

🇬🇧 That is exactly why **Router** mode is the right choice for our goal: it is the only one
that offers address reservation and full network management from a single place.

### 2.3. Развенчанное опасение / A debunked concern

🇷🇺 Разведочный документ `docs/26` предполагал, что режим роутера сменит подсеть на
`192.168.68.0/24` и сломает всю адресацию проекта. **Это неверно:** LAN IP меняется в
приложении (`More → Advanced → LAN IP`). Подсеть `192.168.0.0/24` и адрес Jetson
`192.168.0.50` сохраняются полностью.

🇬🇧 The exploratory document `docs/26` assumed router mode would switch the subnet to
`192.168.68.0/24` and break all of the project's addressing. **This is wrong:** the LAN IP
is changed in the app (`More → Advanced → LAN IP`). The `192.168.0.0/24` subnet and the
Jetson's `192.168.0.50` address are fully preserved.

---

## 3. Состояние «до» (замерено 2026-08-09/10) / "Before" state (measured 2026-08-09/10)

| Параметр / Parameter | Значение / Value | Как получено / How obtained |
|---|---|---|
| Шлюз / Gateway | TP-Link / Aginet **EC220-G5**, `192.168.0.1`, гигабит / gigabit | web UI |
| Подсеть / Subnet | `192.168.0.0/24` | `ip route` на Jetson / on the Jetson |
| Jetson eth0 | `192.168.0.50`, **1000 Мбит/с Full / 1000 Mbps Full**, 0 ошибок / 0 errors | `ethtool eth0` |
| **Jetson MAC** | **`00:04:4b:e6:88:dc`** | `ip link` |
| Профиль сети Jetson / Jetson network profile | NetworkManager `nasa-lan`, **статический IP / static IP** | `nmcli` |
| SSID | `TP-Link_828C` (2.4) и/and `TP-Link_828C_5G` (5) — разные имена / different names | `netsh wlan` |
| Рабочая станция / Workstation | 802.11ac, 5 ГГц, канал/channel 48, сигнал/signal **48 %** | `netsh wlan` |
| Wi-Fi → NAS | **17.6 МБ/с (141 Мбит/с) / 17.6 MB/s (141 Mbps)**, 400 МБ за 23.8 с / 400 MB in 23.8 s | HTTP с Jetson / from the Jetson |
| Диски NAS / NAS disks | SSD 250 МБ/с запись / write; HDD 106 МБ/с чтение / read | `dd` |
| Тариф интернета / Internet plan | ≤ 100 Мбит/с / ≤ 100 Mbps | со слов владельца / owner's statement |

> ✅ 🇷🇺 **Важное свойство, которое спасает переход:** у Jetson **статический** IP, а не DHCP.
> Пока новый роутер стоит на том же `192.168.0.1` с той же маской, конфигурация Jetson
> продолжает работать **без единой правки на самом Jetson**.
>
> 🇬🇧 **A key property that makes the migration safe:** the Jetson has a **static** IP, not
> DHCP. As long as the new router sits on the same `192.168.0.1` with the same netmask, the
> Jetson's configuration keeps working **without a single edit on the Jetson itself**.

---

## 4. Целевая топология / Target topology

```
                    Интернет / Internet (провайдер / ISP, ≤ 100 Мбит/с / Mbps)
                              │
                              ▼  WAN-порт / WAN port
                    ┌─────────────────────┐
                    │  Deco #1  (Router)  │  192.168.0.1
                    │  шлюз · DHCP · DNS  │  единый SSID / single SSID
                    │  gateway · DHCP · DNS│
                    └─────────────────────┘
                       │ LAN-порт (свободный, 100 Мбит/с) / LAN port (free, 100 Mbps)
                       ▼
                 Jetson Nano  192.168.0.50   ← статический IP, не менять / static IP, do not change

                    ┌─────────────────────┐
                    │  Deco #2 (satellite)│  192.168.0.3
                    │  беспроводной       │  2 свободных LAN-порта / 2 free LAN ports
                    │  backhaul 5 ГГц     │  (резерв под проводные устройства / reserved for wired devices)
                    │  wireless 5 GHz     │
                    │  backhaul           │
                    └─────────────────────┘

    EC220-G5 — выведен из эксплуатации, убран в коробку как холодный резерв
    EC220-G5 — decommissioned, boxed up as a cold spare
```

🇷🇺 **Почему Jetson именно в Deco #1:** он ближе к вводу интернета, и путь
«Jetson → интернет» не проходит через беспроводной backhaul.

**Свободные порты после перехода:** Deco #1 — ноль (WAN + Jetson), Deco #2 — два.
Если понадобится подключить проводное устройство, оно идёт в Deco #2.

🇬🇧 **Why the Jetson goes specifically into Deco #1:** it is closer to the internet entry
point, and the "Jetson → internet" path does not cross the wireless backhaul.

**Free ports after the migration:** Deco #1 — zero (WAN + Jetson), Deco #2 — two. If a wired
device needs to be connected, it goes into Deco #2.

---

## 5. Адресный план / Address plan

| Устройство / Device | MAC | Адрес / Address | Способ / Method |
|---|---|---|---|
| Deco #1 (шлюз / gateway) | — | `192.168.0.1` | задаётся вручную в приложении / set manually in the app |
| Deco #2 (satellite) | — | `192.168.0.3` | резервирование / reservation |
| **Jetson Nano** | `00:04:4b:e6:88:dc` | **`192.168.0.50`** | **статика на самом Jetson** + резервирование в Deco как страховка / **static on the Jetson itself** + Deco reservation as a safety net |
| Vostro 15 (если приедет домой / if it comes home) | — | `192.168.0.60` | резервирование / reservation |
| Рабочая станция Windows / Windows workstation | — | DHCP | — |
| Телефоны, ТВ, IoT / Phones, TV, IoT | — | DHCP / гостевая сеть / guest network | — |

🇷🇺 **DHCP-пул:** задать так, чтобы `.1`–`.99` остались вне пула (например, пул
`192.168.0.100–192.168.0.199`). Тогда статические адреса и резервирования не пересекутся
с выдачей.

🇬🇧 **DHCP pool:** set it so that `.1`–`.99` stay outside the pool (for example, pool
`192.168.0.100–192.168.0.199`). This way static addresses and reservations never collide
with what the pool hands out.

---

## 6. Регламент настройки / Setup procedure

### Шаг 0. Подготовка — ОБЯЗАТЕЛЬНО до отключения старого роутера / Step 0. Preparation — MANDATORY before the old router is unplugged

🇷🇺 🔴 **Самый опасный шаг всей операции — потерять параметры подключения к провайдеру.**
Приложение Deco спросит тип подключения, а старого роутера уже не будет под рукой.

🇬🇧 🔴 **The most dangerous step of the whole operation is losing the ISP connection
parameters.** The Deco app will ask for the connection type, and the old router will no
longer be at hand.

🇷🇺
- [ ] Зайти в web-интерфейс EC220-G5 (`192.168.0.1`) и **записать**:
  - [ ] **тип WAN-подключения**: Dynamic IP / **PPPoE** / Static IP;
  - [ ] если PPPoE — **логин и пароль провайдера** (в git не класть!);
  - [ ] если Static IP — адрес, маску, шлюз, DNS;
  - [ ] **WAN MAC-адрес** роутера — понадобится, если провайдер привязывает сессию к MAC;
  - [ ] текущий DHCP-пул и список резерваций (скриншот).
- [ ] Скачать приложение **Deco** и **создать аккаунт TP-Link заранее**.
      ⚠️ Настройка Deco невозможна без интернета и без аккаунта — а интернета в момент
      перестановки не будет. **Держать телефон на мобильном интернете.**
- [ ] Свежий бэкап БД:
      ```bash
      ssh admin@192.168.0.50 "sudo systemctl start nasa-backup.service"
      ssh admin@192.168.0.50 "ls -lt /mnt/storage/backups/database-dumps/ | head -3"
      ```
      Убедиться, что появились файлы с сегодняшней датой.
- [ ] Проверить **запасной путь доступа** к Jetson на случай, если LAN ляжет посреди работ:
      ```bash
      ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 \
          "ssh -p 10022 admin@127.0.0.1 'hostname'"
      ```
      Этот путь не зависит от домашней сети вообще — он идёт через реверс-туннель.
- [ ] Предупредить домашних: Wi-Fi сменит имя и пароль, все устройства придётся
      переподключить.

🇬🇧
- [ ] Open the EC220-G5 web interface (`192.168.0.1`) and **write down**:
  - [ ] the **WAN connection type**: Dynamic IP / **PPPoE** / Static IP;
  - [ ] if PPPoE — the **ISP login and password** (do not put them in git!);
  - [ ] if Static IP — the address, netmask, gateway, DNS;
  - [ ] the router's **WAN MAC address** — needed if the ISP binds the session to a MAC;
  - [ ] the current DHCP pool and the reservation list (screenshot).
- [ ] Download the **Deco** app and **create a TP-Link account in advance**.
      ⚠️ Deco cannot be set up without internet and without an account — and there will be
      no internet at the moment of the swap. **Keep the phone on mobile data.**
- [ ] A fresh database backup:
      ```bash
      ssh admin@192.168.0.50 "sudo systemctl start nasa-backup.service"
      ssh admin@192.168.0.50 "ls -lt /mnt/storage/backups/database-dumps/ | head -3"
      ```
      Make sure files with today's date have appeared.
- [ ] Verify the **fallback access path** to the Jetson in case the LAN goes down mid-work:
      ```bash
      ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 \
          "ssh -p 10022 admin@127.0.0.1 'hostname'"
      ```
      This path does not depend on the home network at all — it goes through the reverse tunnel.
- [ ] Warn the family: the Wi-Fi will change its name and password, every device will have
      to be reconnected.

### Шаг 1. Deco #1 как роутер / Step 1. Deco #1 as the router

🇷🇺
1. Кабель провайдера — в **WAN-порт** Deco #1. Питание.
2. В приложении пройти мастер, выбрать **тип подключения из Шага 0**.
3. Если интернет не поднялся при типе Dynamic IP — провайдер привязан к MAC:
   `More → Advanced → MAC Clone` → ввести WAN MAC старого роутера из Шага 0.
4. Дождаться подтверждения выхода в интернет.

🇬🇧
1. Plug the ISP cable into the **WAN port** of Deco #1. Power it on.
2. Go through the wizard in the app, choose the **connection type from Step 0**.
3. If the internet does not come up with Dynamic IP, the ISP is bound to a MAC:
   `More → Advanced → MAC Clone` → enter the old router's WAN MAC from Step 0.
4. Wait for confirmation that internet access works.

### Шаг 2. Перевести сеть на 192.168.0.0/24 / Step 2. Move the network to 192.168.0.0/24

🇷🇺 🔴 **Критический шаг. До него Jetson недоступен, после — доступен.**

1. `More → Advanced → LAN IP`
2. IP-адрес: **`192.168.0.1`**, маска: `255.255.255.0`
3. Сохранить → Continue. Deco перезагрузится, телефон переподключится.
4. Проверить, что телефон получил адрес вида `192.168.0.x`.

🇬🇧 🔴 **A critical step. Before it the Jetson is unreachable, after it — reachable.**

1. `More → Advanced → LAN IP`
2. IP address: **`192.168.0.1`**, netmask: `255.255.255.0`
3. Save → Continue. The Deco reboots, the phone reconnects.
4. Verify that the phone received an address of the form `192.168.0.x`.

### Шаг 3. Подключить Jetson / Step 3. Connect the Jetson

🇷🇺
1. Кабель Jetson — в свободный LAN-порт Deco #1.
2. Проверить доступность (Jetson не перенастраиваем — у него статика):
   ```bash
   ping 192.168.0.50
   ssh admin@192.168.0.50 "hostname; ip -4 -br addr show eth0; ip route"
   ```
3. `More → Advanced → Address Reservation` → добавить `00:04:4b:e6:88:dc` → `192.168.0.50`.
   Это страховка: если кто-то однажды переведёт Jetson на DHCP, адрес не уедет.
4. DHCP-пул сузить до `192.168.0.100–192.168.0.199`.

🇬🇧
1. Plug the Jetson's cable into a free LAN port of Deco #1.
2. Check reachability (we do not reconfigure the Jetson — it has a static address):
   ```bash
   ping 192.168.0.50
   ssh admin@192.168.0.50 "hostname; ip -4 -br addr show eth0; ip route"
   ```
3. `More → Advanced → Address Reservation` → add `00:04:4b:e6:88:dc` → `192.168.0.50`.
   This is insurance: if someone ever switches the Jetson to DHCP, the address will not drift.
4. Narrow the DHCP pool to `192.168.0.100–192.168.0.199`.

### Шаг 4. Параметры Wi-Fi / Step 4. Wi-Fi parameters

| Параметр / Parameter | Значение / Value | Почему / Why |
|---|---|---|
| SSID | единый, например `NASA_HOME` / a single one, e.g. `NASA_HOME` | бесшовный роуминг, конец залипанию на 2.4 ГГц / seamless roaming, the end of sticking to 2.4 GHz |
| Пароль / Password | WPA2/WPA3, новый, ≥ 16 символов / WPA2/WPA3, new, ≥ 16 characters | внутри LAN сервисы не защищены — пароль Wi-Fi де-факто главный периметр / inside the LAN the services are unprotected — the Wi-Fi password is de facto the main perimeter |
| Smart Connect | включить / enable | автовыбор диапазона / automatic band selection |
| Fast Roaming | включить / enable | ради автозагрузки Immich на телефонах / for Immich auto-upload on the phones |
| Гостевая сеть / Guest network | включить, отдельный пароль / enable, separate password | изоляция гостей, ТВ и IoT от NAS / isolating guests, the TV and IoT from the NAS |

### Шаг 5. Deco #2 / Step 5. Deco #2

🇷🇺
1. Разместить примерно **на середине** между Deco #1 и дальней комнатой — не в самой
   дальней точке.
2. Добавить через приложение, дождаться индикации хорошего сигнала backhaul.
3. Зарезервировать за ним `192.168.0.3`.
4. Ethernet-backhaul использовать только если кабель уже проложен: он тоже 100 Мбит/с,
   и при хорошем сигнале беспроводной может оказаться быстрее. **Сравнить замером.**

🇬🇧
1. Place it roughly **halfway** between Deco #1 and the far room — not at the farthest point.
2. Add it through the app, wait for a good backhaul signal indication.
3. Reserve `192.168.0.3` for it.
4. Use Ethernet backhaul only if the cable is already laid: it is also 100 Mbit/s, and with a
   good signal the wireless one may turn out faster. **Compare by measurement.**

### Шаг 6. Вывод EC220-G5 / Step 6. Retiring the EC220-G5

🇷🇺
1. Отключить, убрать в коробку.
2. **Не сбрасывать к заводским** — сохранённая конфигурация пригодится при откате.
3. Подписать коробку датой вывода.

🇬🇧
1. Unplug it, put it in a box.
2. **Do not factory reset it** — the saved configuration will be useful for a rollback.
3. Label the box with the retirement date.

---

## 7. Приёмочные тесты / Acceptance tests

🇷🇺 Прогнать целиком. Всё должно пройти.

🇬🇧 Run the whole set. Everything must pass.

```bash
# 1. Jetson на месте, адрес и шлюз не изменились
#    Jetson is in place, address and gateway unchanged
ssh admin@192.168.0.50 "ip -4 -br addr show eth0; ip route | grep default"
#    ожидаем / expect: 192.168.0.50/24 и default via 192.168.0.1

# 2. Скорость линка — ожидаем ПАДЕНИЕ до 100 Мбит/с (это норма после перехода)
#    Link speed — expect a DROP to 100 Mbit/s (this is normal after the switch)
ssh admin@192.168.0.50 "ethtool eth0 | grep -E 'Speed|Duplex'"
#    ожидаем / expect: Speed: 100Mb/s, Duplex: Full

# 3. Все контейнеры живы / All containers are alive
ssh admin@192.168.0.50 "docker ps --format '{{.Names}}' | wc -l"     # 13

# 4. Сервисы отвечают по LAN / Services respond over the LAN
for p in 8080 2283 8090 8099 3001 19999 9000; do
  curl -s -o /dev/null -w "$p: %{http_code}\n" --max-time 10 http://192.168.0.50:$p
done

# 5. Реверс-туннель не порвался (важнее всего — это доступ извне)
#    The reverse tunnel did not break (most important — this is the external access path)
ssh admin@192.168.0.50 "systemctl is-active nasa-tunnel; ss -tn | grep 95.163.176.103"

# 6. DNS и интернет с самого Jetson / DNS and internet from the Jetson itself
ssh admin@192.168.0.50 "getent hosts github.com; ping -c 3 1.1.1.1"

# 7. Бэкап по-прежнему отрабатывает / Backups still run
ssh admin@192.168.0.50 "sudo systemctl start nasa-backup.service"
ssh admin@192.168.0.50 "ls -lt /mnt/storage/backups/database-dumps/ | head -3"

# 8. Samba и архив 2 ТБ — из проводника Windows:
#    Samba and the 2 TB archive — from Windows Explorer:
#    \\192.168.0.50\hdd2tb   и / and   \\192.168.0.50\public

# 9. Повторный замер Wi-Fi → NAS (ожидаем ~11 МБ/с)
#    Re-measure Wi-Fi → NAS (expect ~11 MB/s)
ssh admin@192.168.0.50 "cd /dev/shm && dd if=/dev/zero of=spd.bin bs=1M count=400 status=none && \
  (timeout 100 python3 -m http.server 8123 >/dev/null 2>&1 </dev/null &) "
curl -s -o /dev/null -w "%{speed_download} B/s\n" http://192.168.0.50:8123/spd.bin
ssh admin@192.168.0.50 "pkill -f 'http.server 8123'; rm -f /dev/shm/spd.bin"
```

> 🇷🇺 ⚠️ Шаг 9: **обязательно погасить** `http.server` после замера. При аудите 2026-08-10
> такой процесс нашли висящим 14 часов с открытым портом на всю LAN.
>
> 🇬🇧 ⚠️ Step 9: **be sure to kill** `http.server` after the measurement. During the
> 2026-08-10 audit such a process was found hanging for 14 hours with a port open to the
> whole LAN.

🇷🇺 **Отдельно на телефоне:** пройти по всей квартире с открытым Immich — автозагрузка
не должна прерываться при переходе между Deco #1 и #2.

🇬🇧 **Separately on the phone:** walk through the whole flat with Immich open — the
auto-upload must not be interrupted while moving between Deco #1 and #2.

---

## 8. Откат / Rollback

🇷🇺 Полный откат занимает минуты, потому что EC220-G5 сохранён с рабочей конфигурацией:

1. Отключить оба Deco.
2. Вернуть EC220-G5: кабель провайдера в WAN, Jetson — в LAN-порт.
3. Включить. Подсеть, DHCP и статика Jetson не менялись → всё поднимается само.
4. Проверить приёмочными тестами 1, 3, 5 из раздела 7.

🇬🇧 A full rollback takes minutes, because the EC220-G5 is kept with its working configuration:

1. Unplug both Decos.
2. Bring the EC220-G5 back: the ISP cable into WAN, the Jetson into a LAN port.
3. Power it on. The subnet, DHCP and the Jetson's static address were never changed → everything comes back on its own.
4. Verify with acceptance tests 1, 3 and 5 from section 7.

🇷🇺 **Если Jetson стал недоступен по LAN посреди работ** — вход остаётся через VPS:

🇬🇧 **If the Jetson becomes unreachable over the LAN mid-work** — the way in is still through the VPS:

```bash
ssh -o "ProxyCommand=ssh -i ~/.ssh/borovskoy_new_ed25519 -W %h:%p root@95.163.176.103" \
    -p 10022 admin@127.0.0.1
```

🇷🇺 Этот путь не зависит от домашней сети: Jetson сам держит исходящий туннель на VPS.

🇬🇧 This path does not depend on the home network: the Jetson itself keeps an outbound
tunnel to the VPS.

---

## 9. Чего категорически нельзя / What is strictly forbidden

🇷🇺
1. **Не менять подсеть** `192.168.0.0/24` и адрес `192.168.0.50` — они зашиты в CLAUDE.md,
   мобильных приложениях, Samba, документации и в статике самого Jetson (правило №3).
2. **Не сбрасывать EC220-G5** к заводским до успешной приёмки — это путь отката.
3. **Не начинать работы, не записав параметры WAN** — восстановить их будет неоткуда.
4. **Не выносить сервисы NAS в гостевую сеть** и не открывать их из неё.
5. **Не менять пароль Wi-Fi** в момент активной автозагрузки Immich — прервёт бэкап.
6. Не рассчитывать на проброс портов: Jetson за **CGNAT**, входящие соединения не приходят
   при любой топологии. Внешний доступ был и остаётся через реверс-туннель на VPS.

🇬🇧
1. **Do not change the subnet** `192.168.0.0/24` or the address `192.168.0.50` — they are
   baked into CLAUDE.md, the mobile apps, Samba, the documentation and the Jetson's own
   static configuration (rule #3).
2. **Do not factory reset the EC220-G5** before acceptance succeeds — it is the rollback path.
3. **Do not start the work without recording the WAN parameters** — there will be nowhere to recover them from.
4. **Do not move the NAS services into the guest network** and do not expose them from it.
5. **Do not change the Wi-Fi password** while an Immich auto-upload is running — it will interrupt the backup.
6. Do not count on port forwarding: the Jetson is behind **CGNAT**, inbound connections do
   not arrive under any topology. External access was and remains through the reverse tunnel to the VPS.

---

## 10. Что делать, если 11 МБ/с станет мешать / What to do if 11 MB/s becomes a problem

🇷🇺 Ограничение принципиальное — порты Deco аппаратно 100 Мбит/с. Обходится только выносом
проводного трафика за пределы Deco:

🇬🇧 The limit is fundamental — the Deco ports are 100 Mbit/s in hardware. The only way
around it is to move the wired traffic outside the Deco:

```
Deco #1 (роутер / router) ──100M── [гигабитный свитч / gigabit switch] ──1000M── Jetson
                                                                      ──1000M── прочие проводные / other wired devices
```

🇷🇺
- Трафик **между проводными устройствами** пойдёт мимо Deco на гигабите.
- Трафик **Wi-Fi → Jetson** всё равно пройдёт через порт Deco и останется 94 Мбит/с.
- Полезно, когда появится второе проводное устройство (например, Vostro дома) и между
  ними пойдёт объёмный обмен — резервные копии, перенос архива.
- Свитч подключается в LAN-порт Deco #1 вместо Jetson; Jetson и остальные — в свитч.

🇬🇧
- Traffic **between wired devices** bypasses the Deco at gigabit speed.
- Traffic **Wi-Fi → Jetson** still goes through a Deco port and stays at 94 Mbit/s.
- Useful once a second wired device appears (for example, the Vostro at home) and a bulk
  exchange starts between them — backups, moving the archive.
- The switch plugs into a LAN port of Deco #1 in place of the Jetson; the Jetson and the rest plug into the switch.

---

## 11. Судьба Keenetic Omni KN-1410 / The fate of the Keenetic Omni KN-1410

🇷🇺 `docs/25_KEENETIC_OMNI_KN1410.md` планировал Keenetic как усилитель Wi-Fi. Deco решает
ту же задачу лучше: бесшовный роуминг против простого репитера, единый SSID, гостевая сеть.

**Рекомендация: план по Keenetic закрыть, устройство оставить холодным резервом.**

🇬🇧 `docs/25_KEENETIC_OMNI_KN1410.md` planned the Keenetic as a Wi-Fi range extender. The
Deco solves the same problem better: seamless roaming instead of a plain repeater, a single
SSID, a guest network.

**Recommendation: close the Keenetic plan, keep the device as a cold spare.**

---

## 12. Открытые вопросы / Open questions

🇷🇺
- Тип WAN-подключения провайдера — заполнить в Шаге 0 до начала работ.
- Привязка провайдера к MAC — выяснится на Шаге 1.
- Есть ли между комнатами витая пара под Ethernet-backhaul.
- Имя единого SSID и новый пароль Wi-Fi.

🇬🇧
- The ISP's WAN connection type — fill it in at Step 0 before the work starts.
- Whether the ISP binds to a MAC — will become clear at Step 1.
- Whether there is twisted pair between the rooms for Ethernet backhaul.
- The name of the single SSID and the new Wi-Fi password.

## 13. Связанные документы / Related documents

- `docs/26_DECO_E4_NETWORK.md` — разведочный анализ, **заменён этим документом** / exploratory analysis, **superseded by this document**
- `docs/19_NETWORK_INVENTORY.md` — инвентаризация сети / network inventory
- `docs/25_KEENETIC_OMNI_KN1410.md` — план усилителя, предлагается закрыть / the range-extender plan, proposed to close
- `docs/24_CLIENT_SETUP.md` — настройка клиентов / client setup
- `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md` — узел Vostro (сейчас в корпоративной сети) / the Vostro node (currently in the corporate network)
- `docs/plans/POST_HABR_FEEDBACK_2026-08.md` — что новая сеть закрывает из отзывов / which feedback items the new network addresses

## 14. Источники / Sources

- [TP-Link Deco E4 — официальная страница продукта / official product page](https://www.tp-link.com/en/home-networking/deco/deco-e4/)
- [Deco Access Point Mode Setup — что недоступно в режиме AP](https://www.tp-link.com/us/support/faq/1842/)
- [Deco IP Address: How to Change Your Default LAN IP](https://www.tp-link.com/us/support/faq/2331/)
- [Deco DHCP Reservation | Set a Fixed IP Address](https://www.tp-link.com/us/support/faq/1795/)
- [Deco MAC Clone: Fix No Internet Connection](https://www.tp-link.com/us/support/faq/2925/)
- [Deco Setup Guide](https://www.tp-link.com/us/support/faq/1592/)
