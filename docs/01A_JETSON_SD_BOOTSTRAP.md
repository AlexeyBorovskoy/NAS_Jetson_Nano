# 01A. Jetson SD Bootstrap

> 🇷🇺 Подготовить Jetson Nano к первому запуску, если готовой загрузочной microSD карты ещё нет, а USB HDD пока недоступен.
> 🇬🇧 Prepare Jetson Nano for first boot when a bootable microSD is not yet ready and USB HDD is not yet available.

## 1. Цель / Purpose

🇷🇺 Подготовить Jetson Nano к первому запуску, если готовой загрузочной microSD карты ещё нет.
🇬🇧 Prepare Jetson Nano for first boot when no bootable microSD is ready yet.

Этот шаг предшествует `docs/01_HARDWARE_AUDIT.md`: сначала нужно получить
загружаемый Jetson, настроить первый вход и сеть, и только потом выполнять
полный аппаратный аудит.

## 2. Что меняется

На ноутбуке:

- выбирается официальный образ Jetson Nano Developer Kit SD Card Image;
- скачивается архив образа;
- проверяется наличие microSD-карты и кардридера;
- подготавливается безопасный порядок записи образа.

На Jetson:

- вставляется подготовленная microSD;
- выполняется первый boot;
- настраивается пользователь, пароль, hostname и сеть;
- проверяется доступ по SSH.

HDD на этом шаге не нужен и не подключается.

## 3. Почему меняется

Проект нельзя начинать с Docker, Nextcloud или storage-аудита, пока Jetson не
имеет рабочей ОС. Для Jetson Nano Developer Kit базовый путь старта — записать
официальный SD Card Image на microSD и загрузиться с неё.

## 4. Какие файлы затрагиваются

В репозитории меняется только документация:

- `docs/01A_JETSON_SD_BOOTSTRAP.md`

Runtime-артефакты не коммитятся:

- скачанный `.zip` образ;
- распакованный `.img`;
- логи первого запуска;
- серийные номера;
- локальные IP.

Рекомендуемое локальное место для образов:

```text
/home/alexey/downloads/jetson/
```

или любой внешний каталог вне Git-репозитория.

## 5. Исходные вводные

| Пункт | Текущее состояние |
|---|---|
| Готовая стартовая microSD | нет |
| HDD | пока недоступен |
| Цель первого этапа | загрузить Jetson и получить SSH |
| Основной источник образа | официальная страница NVIDIA Jetson Nano Developer Kit |
| Метод записи | balenaEtcher или Linux CLI после ручного выбора устройства |

## 6. Что нужно физически

Минимум:

- Jetson Nano Developer Kit;
- microSD 64 GB или больше, UHS-I, желательно High Endurance;
- кардридер microSD для ноутбука;
- стабильное питание Jetson;
- Ethernet-кабель или USB-Ethernet адаптер для direct-link к ноутбуку;
- ноутбук с интернетом.

Доступ к домашнему роутеру на Stage 0 не требуется. Static DHCP lease
настраивается позже, после успешного bootstrap и SSH через ноутбук.

Для headless setup:

- micro-USB кабель data-capable, не только зарядный;
- питание Jetson через DC barrel jack, если micro-USB занят под serial/device mode.

Для setup через монитор:

- HDMI или DisplayPort монитор;
- USB-клавиатура;
- USB-мышь.

## 7. Официальные источники

Использовать только официальные NVIDIA-страницы:

- Jetson Nano Developer Kit Getting Started:
  `https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit`
- JetPack 4.x installation documentation:
  `https://docs.nvidia.com/jetson/jetpack/4.6/install-jetpack/index.html`

Важное уточнение: Jetson Nano относится к JetPack 4.x / L4T r32-линейке.
Нельзя брать образ для Jetson Orin Nano или других Jetson-плат без явного
подтверждения модели.

## 7.1. Локальные материалы в проекте

В проект перенесён локальный каталог внешних материалов:

```text
/home/alexey/work/NAS_Jetson_Nano/external_docs/jatson
```

Он не коммитится в GitHub, потому что содержит большие сторонние бинарные
файлы. Состав, размеры и checksums зафиксированы в:

```text
docs/references/JETSON_LOCAL_ASSETS.md
```

Для текущего Stage 0 уже есть локальный SD-образ:

```text
external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
```

и локальный Etcher:

```text
external_docs/jatson/balenaEtcher-linux-x64-2.1.6.zip
```

Если checksum совпадает с manifest, повторно скачивать образ не нужно.

## 8. Команды инвентаризации на ноутбуке

До скачивания образа:

```bash
mkdir -p /home/alexey/downloads/jetson
df -h /home/alexey/downloads/jetson
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL
```

После вставки microSD:

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL
dmesg | tail -n 50
```

Нужно вручную определить устройство microSD, например `/dev/sdX` или
`/dev/mmcblkX`. Нельзя угадывать имя устройства.

## 9. Скачивание образа

Безопасный порядок:

1. Открыть официальный NVIDIA Getting Started для Jetson Nano Developer Kit.
2. Скачать `Jetson Nano Developer Kit SD Card Image`.
3. Сохранить архив вне репозитория.
4. Зафиксировать имя файла, размер и checksum, если NVIDIA публикует checksum.

Для текущего проекта этот шаг уже частично выполнен: локальный архив находится
в `external_docs/jatson/`. Перед записью карты нужно только повторно проверить
checksum по `docs/references/JETSON_LOCAL_ASSETS.md`.

Пример проверки локального файла:

```bash
cd /home/alexey/downloads/jetson
ls -lh
sha256sum *.zip
```

Checksum нужно сравнить с официальным значением, если оно доступно на странице
загрузки или в NVIDIA Download Center.

## 10. Запись microSD

Рекомендуемый безопасный способ — balenaEtcher:

1. Select image: официальный `.zip` образ Jetson Nano.
2. Select target: только microSD.
3. Flash.
4. Дождаться validation.
5. Извлечь карту штатно.

CLI-способ допустим только после ручного подтверждения устройства:

```bash
# Пример. НЕ запускать без проверки /dev/sdX.
unzip -p jetson_nano_devkit_sd_card.zip | sudo dd of=/dev/sdX bs=1M status=progress conv=fsync
sudo eject /dev/sdX
```

`/dev/sdX` в примере должен быть заменён на реальное устройство microSD.
Неверный выбор устройства уничтожит данные на другом диске.

## 11. Первый boot

1. Вставить microSD в слот Jetson Nano.
2. Подключить Ethernet.
3. Выбрать режим первого запуска:
   - монитор + клавиатура + мышь;
   - headless через micro-USB serial/device mode;
   - офлайн-настройка rootfs на ноутбуке без монитора и консоли — см. §11.2
     (так Jetson и был реально настроен 2026-05-31).
4. Подключить питание.
5. Пройти первичную настройку Ubuntu/L4T:
   - принять license;
   - создать пользователя;
   - задать пароль;
   - выбрать hostname;
   - настроить timezone.

Рекомендуемый hostname:

```text
nas_jetson_nano-jetson
```

## 11.1. Текущий стенд: USB + USB-Ethernet direct-link

На 2026-05-31 Jetson подключён к компьютеру двумя путями:

- micro-USB/data USB для первичной настройки или serial/device mode;
- USB-LAN адаптер для временного Ethernet-сегмента без изменения роутера.

На этом этапе Jetson намеренно подключён именно к ноутбуку, а не к домашней
сети. Домашний роутер не используется для Stage 0: его настройки понадобятся
позже, когда Jetson уже будет загружен, настроен и доступен по SSH.

На рабочей машине обнаружен USB-Ethernet адаптер:

```text
ICS Advent 10/100M LAN
```

Текущий интерфейс direct-link:

```text
ens37  192.168.1.2/24
```

Эта схема является основной рабочей схемой Stage 0. Она используется для
bootstrap, первого SSH и аппаратного аудита. Целевая LAN/VPN-схема через роутер
и static DHCP lease включается только после завершения настройки Jetson.

Проверка с компьютера:

```bash
ip -br addr
lsusb
ip route
ip neigh show dev ens37
nmap -sn 192.168.1.0/24
```

Важно: если Jetson настроен как DHCP-клиент, ноутбук должен либо раздавать DHCP
на direct-link интерфейсе, либо на Jetson должен быть задан статический адрес
из этой же подсети. Профиль direct-link на ноутбуке задаёт только адрес
ноутбука `192.168.1.2/24`; DHCP-сервер на `ens37` сам по себе не включён.

Варианты для Stage 0:

1. На Jetson вручную задать временный IP, например `192.168.1.50/24`, без
   gateway.
2. На ноутбуке временно включить DHCP только для `ens37`, затем найти Jetson
   через `nmap -sn 192.168.1.0/24`.
3. Использовать monitor/keyboard или serial console, если сеть ещё не поднята.

Ожидаемый результат перед SSH:

- компьютер видит USB-Ethernet адаптер;
- direct-link интерфейс имеет IP;
- Jetson появляется как отдельный host в той же подсети;
- после настройки SSH доступен `ssh <user>@<jetson-direct-link-ip>`.

Если `nmap` видит только компьютер, значит Jetson ещё не получил адрес в этом
сегменте или USB/device/network mode не проброшен в текущую ОС/VM. В этом случае
нужно завершить первичную настройку Jetson локально через монитор/клавиатуру
или serial console, затем повторить сетевую проверку.

Переход к домашнему роутеру разрешён только после контрольных условий:

- Jetson успешно загружается с microSD;
- создан пользователь и задан hostname `nas_jetson_nano-jetson`;
- SSH работает в direct-link схеме;
- выполнен минимальный hardware audit без HDD;
- нет необходимости менять firewall или port forwarding на роутере.

## 11.2. Headless offline-настройка rootfs (без монитора и serial-консоли)

Применено **2026-05-31** — основной путь, которым Jetson был реально настроен.

Подходит, когда первичную настройку (oem-config) нельзя пройти интерактивно:
монитора нет, а USB-serial на стоковом образе Jetson Nano консоли **не даёт**
(kernel console и getty висят на 40-пиновом UART `ttyTHS0`, а не на USB-гаджете
`ttyGS0`). При этом по Micro-USB в device mode Jetson всё равно поднимает сеть
`192.168.55.1` (хост получает `192.168.55.100`), но до завершения oem-config
`sshd` не стартует, поэтому зайти некуда. Решение — сделать офлайн на ноутбуке
то же, что делает мастер: завести пользователя, переключить загрузку в
`multi-user`, включить ssh.

1. Выключить Jetson, вынуть microSD, вставить в **USB-картридер** ноутбука (в
   VMware пробросить ридер в VM). Rootfs — раздел APP (ext4, `*p1`),
   автомонтируется в `/media/<user>/<UUID>`.

2. Проверить состояние (read-only):

```bash
R=/media/<user>/<UUID>
head -1 "$R/etc/nv_tegra_release"                  # подтвердить, что это Jetson rootfs
awk -F: '$3>=1000 && $3<65534' "$R/etc/passwd"     # есть ли пользователь (uid>=1000)
readlink "$R/etc/systemd/system/default.target"    # nv-oem-config.target => мастер не пройден
```

3. От root (chroot не нужен и невозможен без `qemu-aarch64-static` — правим файлы
   напрямую; `useradd --root` спотыкается об отсутствие `$R/dev/null`). Бэкап
   исходных файлов сохранить рядом как `*.nas_jetson_nanobak`:

```bash
U=admin; HOSTN=nas_jetson_nano-jetson
HASH=$(openssl passwd -6)                 # введёт пароль интерактивно
for f in passwd shadow group; do sudo cp -a "$R/etc/$f" "$R/etc/$f.nas_jetson_nanobak"; done
# /etc/passwd:  admin:x:1000:1000:admin,,,:/home/admin:/bin/bash
# /etc/shadow:  admin:$HASH:19500:0:99999:7:::
# /etc/group:   создать admin:x:1000: и добавить admin в
#               sudo,adm,dialout,audio,video,plugdev,netdev,i2c,gpio
# /home/admin:  cp -a "$R/etc/skel" "$R/home/admin"; chown -R 1000:1000 "$R/home/admin"

# загрузка в multi-user вместо oem-config:
sudo ln -sf /lib/systemd/system/multi-user.target "$R/etc/systemd/system/default.target"
sudo ln -sf /dev/null "$R/etc/systemd/system/nv-oem-config.service"
# ssh host-ключи (иначе sshd не стартует) + hostname:
for t in rsa ecdsa ed25519; do sudo ssh-keygen -q -t "$t" -f "$R/etc/ssh/ssh_host_${t}_key" -N ''; done
echo "$HOSTN" | sudo tee "$R/etc/hostname"
```

> Числовой владелец `/home/admin` должен быть `1000:1000` (на хосте отобразится
> как локальный uid 1000 — это нормально; на Jetson uid 1000 = `admin`).

4. `sync && sudo umount "$R"`, вернуть microSD в Jetson, подать питание.

5. Зайти по SSH через device mode (поставить свой ключ для входа без пароля):

```bash
ssh admin@192.168.55.1
ssh-copy-id admin@192.168.55.1     # опционально
```

6. Расширить rootfs на всю карту. На стоковом образе APP-раздел физически
   последний (наибольший start-сектор), поэтому штатный resize работает онлайн:

```bash
/usr/lib/nvidia/resizefs/nvresizefs.sh --check     # должно быть true
sudo /usr/lib/nvidia/resizefs/nvresizefs.sh        # без аргументов = вся карта
df -h /                                            # ~13G -> ~59G
```

Реквизиты доступа — в `config/.env` (`JETSON_*`, gitignored) и `.master.env`
(`NAS_JETSON_NANO_JETSON_*`). Откат — восстановить `/etc/*.nas_jetson_nanobak` на карте.

## 12. Проверка первого запуска

На Jetson:

```bash
uname -a
cat /etc/os-release
df -h
free -h
ip a
```

Проверка Jetson-инструментов:

```bash
sudo nvpmodel -q || true
sudo tegrastats --interval 1000 || true
```

Проверка SSH:

```bash
sudo systemctl status ssh || true
hostname -I
```

С ноутбука:

```bash
ssh <user>@<jetson-lan-ip>
```

## 13. Критерии допуска к аппаратному аудиту

| Критерий | Норма |
|---|---|
| Jetson загружается с microSD | да |
| Первый пользователь создан | да |
| Direct-link интерфейс получил временный IP | да |
| SSH работает с ноутбука напрямую | да |
| `df -h` видит root filesystem на microSD | да |
| Нет циклических boot errors | да |
| HDD не требуется | да |

После этого можно выполнять:

```bash
./scripts/diagnostics/hardware_audit.sh
```

## 14. Rollback

Если Jetson не загружается:

1. Не форматировать HDD и не менять роутер/firewall.
2. Проверить, что образ соответствует именно Jetson Nano Developer Kit.
3. Перезаписать microSD через balenaEtcher с validation.
4. Проверить питание.
5. Проверить другой кардридер или другую microSD.
6. Повторить первый boot.

Если была выбрана не та SD-карта при записи CLI-способом, автоматического
rollback нет. Поэтому CLI-запись разрешена только после ручного подтверждения
устройства.
