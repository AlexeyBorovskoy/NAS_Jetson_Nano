# 01. Аппаратный аудит / Hardware Audit

> 🇷🇺 До развёртывания сервисов необходимо зафиксировать фактическое состояние Jetson Nano, HDD, сети и ОС.
> 🇬🇧 Before deploying services, document the actual state of Jetson Nano, HDD, network, and OS.

## 1. Цель / Purpose

🇷🇺 До развёртывания сервисов необходимо зафиксировать фактическое состояние Jetson Nano, HDD, сети и ОС.
🇬🇧 Before deploying services, document the actual state of Jetson Nano, HDD, network, and OS.

## 2. Исходное оборудование

| Компонент | Предварительно определено |
|---|---|
| SBC | NVIDIA Jetson Nano Developer Kit |
| Роутер | домашний роутер (модель уточняется на месте) |
| HDD | USB HDD, питание предусмотрено отдельно |
| Системный носитель | microSD 64 GB |
| Сеть | Ethernet для Jetson; на Stage 0 допустим временный direct-link через USB-Ethernet адаптер |
| Кандидат home-helper (2026-09-11) | **Dell Inspiron N5110** ST `6M60JR1` / `5110-8477` RED — пока неисправен; см. `docs/plans/INSPIRON_N5110_HOME_NODE.md` |

## 2.1. Текущий Stage 0 стенд

На 2026-05-31 Jetson подключён к компьютеру через USB и через USB-LAN адаптер.
На компьютере виден адаптер `ICS Advent 10/100M LAN`, интерфейс `ens37` с адресом
`192.168.1.2/24`.

Это не домашняя LAN-схема. На первом шаге Jetson настраивается напрямую с
ноутбука (первичный first-boot — через serial console по Micro-USB, см.
`docs/05_NETWORKING_VPN.md` §1.1 и официальную документацию NVIDIA в
`external_docs/jetson/`). Домашний роутер подключается позже, после завершения
bootstrap и проверки SSH.

Проверка с компьютера перед SSH:

```bash
ip -br addr
lsusb
ip neigh show dev ens37
nmap -sn 192.168.1.0/24
```

Текущий контрольный результат: в подсети `192.168.1.0/24` обнаружен только
компьютер `192.168.1.2`. Jetson ещё нужно довести до состояния, когда он
получает адрес именно в direct-link сегменте.

## 3. Команды аудита

```bash
uname -a
cat /etc/os-release
free -h
df -h
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL
lsusb
ip a
ip route
sudo dmesg | grep -i -E "usb|sd|error|reset|fail|i/o" | tail -n 200
```

## 4. Проверка Jetson

```bash
sudo nvpmodel -q || true
sudo tegrastats --interval 1000 || true
```

Если `tegrastats` отсутствует, установить или зафиксировать как отсутствие инструмента.

## 5. Проверка HDD

```bash
sudo apt update
sudo apt install -y smartmontools
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL
sudo smartctl -a /dev/sda || sudo smartctl -a -d sat /dev/sda || true
```

Если HDD уже содержит нужные данные, аудит выполняется как intake существующего
диска:

```bash
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,TRAN,RO
mountpoint /mnt/storage || echo "/mnt/storage is not mounted"
command -v ntfs-3g || sudo apt install -y ntfs-3g
sudo mkdir -p /mnt/hdd-check
sudo mount -t ntfs-3g -o ro /dev/sdXN /mnt/hdd-check
findmnt /mnt/hdd-check
df -hT /mnt/hdd-check
find /mnt/hdd-check -mindepth 1 -maxdepth 1 | wc -l
```

Не запускать `scripts/storage/setup_disk.sh` для такого диска до отдельного
плана миграции. Скрипт предназначен для подготовки рабочего storage и может
добавить постоянное монтирование в `/etc/fstab`.

## 6. Критерии допуска к следующему этапу

| Критерий | Норма |
|---|---|
| HDD виден в `lsblk` | Да |
| HDD с существующими данными проверен read-only | Да, через отдельный mountpoint, например `/mnt/hdd-check` |
| В `dmesg` нет повторяющихся USB reset/I/O error | Да |
| RAM свободна после старта | Не менее 1 GB желательно |
| Температура Jetson без нагрузки | Стабильная, без throttling |
| Jetson доступен по SSH | Да, через direct-link с ноутбука |
| IP закреплён на роутере | Не требуется на Stage 0; выполняется позже при переносе в домашнюю LAN |

## 7. Результат

Результаты аудита сохраняются в:

```text
runtime/audit/HARDWARE_AUDIT_REPORT.md
```

Этот каталог не коммитится в публичный репозиторий, если содержит серийные номера или внутренние IP.
