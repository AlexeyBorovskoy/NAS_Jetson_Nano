# Checkpoint 2026-09-12 — домашняя сеть: перестройка mesh / home network rebuild

> 🇷🇺 День работы по домашней сети. Устройство Jetson и VPS **не менялись**, Amnezia не
> трогали. Все числа замерены 12.09.2026.
>
> 🇬🇧 A home-network day. The Jetson and the VPS were **not modified**, Amnezia untouched.
> Every number was measured on 2026-09-12.

Предыдущая точка: [`CHECKPOINT_2026-09-11.md`](CHECKPOINT_2026-09-11.md).
Слепок сети: [`../34_NETWORK_SNAPSHOT_2026-09-12.md`](../34_NETWORK_SNAPSHOT_2026-09-12.md).

---

## 1. Повод и главный результат

Жалоба владельца: «на телефоне медленно работает интернет через Deco».

Аудит показал, что канал провайдера и проводная часть здоровы, а узким местом было
**размещение второго узла mesh**. После переноса узла ближе к главному:

| Второй узел, один и тот же тест | До | После |
|---|---|---|
| HTTP-обращений успешно из 10 | 6 | **10** |
| Среднее время ответа | 746 мс | **53 мс** |
| Худшее | 4023 мс | **63 мс** |
| ICMP | 1 из 10 | **20 из 20** |

Рабочая станция, переехавшая на этот узел: сигнал 36–42 % → **85 %**, скорость
радиоканала 40–175 → **866.7 Мбит/с**.

---

## 2. Состояние сети на конец дня (замер 12.09)

| Точка | Значение |
|---|---|
| Станция | 5 ГГц, канал 40, 866.7 Мбит/с, сигнал 85 % |
| Скорость наружу по Wi-Fi | **80 Мбит/с** |
| Скорость наружу по проводу (Jetson) | **87–92 Мбит/с**, 3 прогона |
| Через AmneziaVPN | 46–53 Мбит/с, **1 прогон из 4 сорвался** до 0.8 |
| Пинг: hallway / living_room / Jetson | 1.5 / 0.4 / 2.3 мс |
| DNS: Deco / EC220 | 73 мс (выбросы 353) / **4 мс** |

Jetson не трогали: 13 контейнеров, аптайм 4 суток, бэкапы 12.09 03:04, вторая копия
Immich 12.09 04:20 (12.8 ГБ).

---

## 3. Прошивки Deco — сделано наполовину

Модель по наклейке: **Deco E4, EU/4.0** (веб-интерфейс пишет `E4R(4.0)`).

| Узел | Было | Стало |
|---|---|---|
| `hallway` (главный) | 1.0.0 Build 20230307 | **1.2.0 Build 20250728** |
| `living_room` | 1.0.0 Build 20230307 | 1.0.0 — **не обновился** |

🔴 **Веб-интерфейс не обновляет дочерний узел.** Дважды при выбранном
`E4R(living_room)` окно показывало `Upgrading…` и `Rebooting…`, но опрос всех адресов
каждые 4 с **не зафиксировал ни одного пропадания узла из сети**, и версия не
изменилась. Обновляется только главный узел, что бы ни стояло в `Device Model`.

**Цепочка версий** (прямой прыжок отвергается, `RSA2048_up`):
`1.0.0 → 1.2.0 → 1.2.2 → 1.3.1`. Файлы скачаны в
`C:\Users\Alexey\Downloads\deco-e4-fw\` (вне git).

**Все пути обновления дочернего узла проверены и закрыты, кроме одного:**

| Путь | Результат |
|---|---|
| Облако через приложение | `Невозможно проверить наличие обновлений`, их FAQ отдаёт 404 |
| Облако через веб-интерфейс | `Downloading… 0 %` |
| Локальный файл | Уходит на главный узел независимо от выбора узла |
| **Переподключение узла в приложении** | **Не пробовали** — прошивка передаётся с главного локально |

Канал до облака исправен: пять хостов TP-Link отвечают на 443 с провода, файлы качаются.

**Что дал апгрейд главного узла:** DNS через Deco 73 → **7 мс**, скорость наружу
64–80 → **100 Мбит/с**, веб-интерфейс переехал на HTTPS.

---

## 4. Отозванные гипотезы (важнее сделанного)

1. **«Расхождение версий прошивки уронило радио».** Неверно. При просадке до
   6–12 Мбит/с версии были разными — но и после возврата к 80 Мбит/с они остались
   разными. Настоящая причина: станцию сбросило на **2.4 ГГц, канал 9**. Правило:
   при внезапном падении сначала смотреть диапазон клиента.
2. **«Для V4 прошивок нет нигде»** (проверено 7 регионов). Проверялся не тот каталог:
   `deco-e4r` вместо `deco-e4`, и страница `v4-40` вместо `v4`. Утверждение было шире
   проверенного.
3. **«Wi-Fi даёт 10 Мбит/с»** — артефакт `Invoke-WebRequest`; `curl` на том же канале
   в ту же секунду показал 53–80.
4. **«Путь до TP-Link заблокирован»** — `getent hosts` отдал AAAA, IPv6 в доме нет
   вовсе; по IPv4 всё открыто.

Полный разбор семи ловушек — в слепке `docs/34_NETWORK_SNAPSHOT_2026-09-12.md`.

---

## 4а. Доступ к архиву на HDD и выдача материалов владельцу

- 🔴 **Шара `hdd2tb` была недоступна из LAN** — рудиментный хостовой `smbd` вне проекта
  перехватывал порт 445 у контейнера (гонка при загрузке 08.09, разрыв 24 с). Владелец
  остановил его и снял с автозапуска; откат `systemctl enable --now smbd nmbd`.
  Разбор — слепок 34 §5г.
- ✅ Диск подключён на станции как `Z:` → `\\192.168.0.50\hdd2tb`. ⚠️ `net use` падает
  с `ошибкой 67`; работает только `New-SmbMapping`.
- ✅ **Собран архив** `Diplom_MO_2026-09-12.zip` на самом устройстве: 7.06 ГБ исходных
  → **4.21 ГБ**, **28 421 запись** (25 173 файла + 3 248 папок — сходится точно),
  сборка ~16 минут. Целостность проверена полностью (`unzip -t`): **ошибок нет**.
  Лежит в корне шары.
- ⛔ **Автоматическая выгрузка наружу не выполнена.** SwissTransfer требует настоящий
  токен recaptcha (`Captcha not valid`), обходить защиту сервиса не стали; последующие
  попытки подобрать сервис с curl-API заблокированы политикой сессии как выгрузка
  данных. Владельцу передан ручной порядок: браузер, VPN выключен, файл берётся прямо
  с `Z:`.
- Замер отдачи канала: **84 Мбит/с** — архив уходит наружу примерно за 7 минут, но
  только мимо туннеля.

## 4б. Пилот Immich ML на ROG — начат, упёрся в гипервизор

Владелец выбрал этот блок развития. Подготовка выполнена, запуск отложен.

| Шаг | Состояние |
|---|---|
| Версия образа привязана к серверу | ✅ Immich на Jetson **2.7.5** → ML `…:v2.7.5-cuda` |
| `config/immich-ml-rog.env` | ✅ создан, вне git (правило `config/*.env` в `.gitignore`) |
| Порт ML | ✅ привязан к `127.0.0.1`, в LAN не открыт |
| Видеокарта | ✅ RTX 3050 Ti Laptop, 4 ГБ, драйвер 596.36 |
| Docker Desktop | ⛔ `Virtualization support not detected` |
| Запуск обработчика | ⛔ отложен |

🔴 **Блокер:** на станции выключен гипервизор Windows — `HypervisorPresent = False`
при `VirtualizationFirmwareEnabled = True`. Служба `com.docker.service` была
остановлена (владелец запустил), но без гипервизора движок не поднимается. Нужны права
администратора и **перезагрузка**; рядом стоит VMware Workstation 25, которая после
включения гипервизора продолжит работать, но немного медленнее. **Владелец отложил
решение на завтра.**

🔴 **Runbook пилота устарел в части топологии.** Он предполагает ROG и Jetson в одной
подсети, но станция за Deco в `192.168.68.0/22`, и Jetson её не достаёт (ping 100 %
потерь). Рабочий путь — обратный туннель со станции с привязкой к `172.17.0.1`
(`GatewayPorts clientspecified` на Jetson уже включён). Документ пилота исправлен.

## 5. Доска

| Сообщение | Что |
|---|---|
| `m0130` → `work` | факт: замеры до/после, скорости дома, изменившиеся адреса, семь ловушек |
| `m0131` ← `work` | запрос: длинные сессии наружу не доживают, `getaddrinfo failed` |
| `m0132` → `work` | ответ: DNS-замеры, срывы только через туннель, адрес узла плавает, отзыв своей гипотезы |
| `m0133` ← `work` | подтверждение: DNS уходит в туннель Amnezia (1.1.1.1/1.0.0.1 на VPN-интерфейсе, метрика 5 против 95) |
| `m0134` → `work` | факт: замер удержания, обе сессии по 19.5 минут выжили; класс их отказа не воспроизведён, названо ограничение теста |

Соседи отдельно заметили: часть их обрывов SSH в 09:50 МСК совпала с переассоциацией
Wi-Fi при переносе узла, а не с туннелем.

---

## 6. Не закончено

- ✅ **Тест удержания выполнен, результат отрицательный.** Обе сессии по 19.5 минут
  дожили до конца: через AmneziaVPN 1172.4 с и 60 МБ, мимо туннеля 1171.9 с и 60 МБ,
  обрывов нет. Длительность сессию не убивает. Ограничение: поток шёл на 50 КБ/с,
  нагрузка и паттерн трафика не проверены. Отдано соседям (`m0134`).
- 🟠 **`living_room` на старой прошивке** — остался единственный путь: удалить узел в
  приложении и добавить заново. До этого **не менять имя сети и пароль Wi-Fi**:
  конфигурация может до узла не дойти, и он отвалится.
- 🟠 **Скан эфира не сделан**: Windows требует разрешённой геолокации (прав в сессии
  нет), телефон в `adb` не появился. Не подтверждено, на каком диапазоне держится
  транзит между узлами и насколько забит канал соседями.
- 🟠 **EC220 продолжает раздавать свой Wi-Fi** и конкурирует с mesh за эфир. Решение
  (погасить и перевести клиентов либо развести каналы) не принято.
- Кабельный backhaul между узлами исключён владельцем: только радио.

---

## 7. English summary

The owner reported slow phone internet over the Deco mesh. The wired path proved healthy
(87–92 Mbit/s, 0.45 ms to the gateway); the bottleneck was **node placement**. After
moving the second node closer, its response went from 746 ms with 4 failures in 10 to
**53 ms with none**, and the workstation went from 36 % signal / 175 Mbit/s to
**85 % / 866.7 Mbit/s**.

Firmware is half done: `hallway` is on 1.2.0, `living_room` is still on 1.0.0 because
**the web UI only ever updates the main node** — polling every 4 s recorded no reboot of
the child node despite the progress dialog. Use the Deco app or re-add the node.

Four of my own hypotheses were withdrawn, including "mismatched firmware broke the
radio" (the real cause was the client falling back to 2.4 GHz channel 9) and "no V4
firmware exists anywhere" (wrong catalogue).

**Session-hold test finished — negative.** Two 20-minute sessions, through AmneziaVPN and
bypassing it over the same Wi-Fi, both completed without a drop. Duration alone does not
kill a session; the test was rate-limited to 50 KB/s, so load was not tested.

**Samba was broken and is fixed.** An out-of-project host `smbd` had hijacked port 445
from the project container in a boot race, serving three empty shares; the `hdd2tb`
archive share was unreachable from the LAN. The owner disabled the host units. A 4.21 GB
archive of the diploma folder was then built on the device (7.06 GB in, 28 421 entries,
integrity verified) and handed over on the share. Uploading it to an external service was
**not** performed: the chosen service requires a real captcha and the session policy
blocks outbound data transfer.

**Immich ML pilot started and is blocked.** The image is pinned to server version 2.7.5
and the local env sits outside git, but Docker Desktop will not start: the Windows
hypervisor is off (`HypervisorPresent = False`). Enabling it needs admin rights and a
reboot; the owner postponed it. The pilot runbook was also corrected: the station now
lives behind the Deco in another subnet, so a reverse SSH tunnel bound to `172.17.0.1`
replaces the LAN URL.

Open: firmware on the child Deco node; no RF scan was possible; the EC220 still
broadcasts a competing Wi-Fi; off-site for photos still waits on the Cloud.ru console.
