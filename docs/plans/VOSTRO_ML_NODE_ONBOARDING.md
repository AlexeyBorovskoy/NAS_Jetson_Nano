# Ввод в эксплуатацию: Dell Vostro 15 как ML-узел / Onboarding: Dell Vostro 15 as an ML node

> 🇷🇺 Включение старого ноутбука Dell Vostro 15 (2018) в проект NAS_Jetson_Nano
> в роли **выделенного always-on узла машинного обучения Immich** и вспомогательного сервера.
> Решение принято: 2026-08-01. Проект ZTN временно закрыт → ноутбук свободен.
>
> 🇬🇧 Bringing the old Dell Vostro 15 (2018) laptop into the NAS_Jetson_Nano project
> as a **dedicated always-on Immich machine-learning node** and auxiliary server.
> Decision made: 2026-08-01. The ZTN project is on hold → the laptop is free.

## Зачем / Why
- 🇷🇺 **Immich ML** (распознавание лиц + smart search/CLIP) — главный запрос читателей Habr. Jetson Nano её не тянет (CUDA 10.2, 4 ГБ); Vostro (x86-64, 4C/8T) — тянет. Разгрузка Jetson по RAM. Без покупок.
- 🇬🇧 **Immich ML** (face recognition + smart search/CLIP) — the top request from Habr readers. The Jetson Nano can't handle it (CUDA 10.2, 4 GB); the Vostro (x86-64, 4C/8T) can. It also relieves the Jetson's RAM. No purchases.
- 🇷🇺/🇬🇧 См. / See [POST_HABR_FEEDBACK_2026-08.md](POST_HABR_FEEDBACK_2026-08.md).

## Железо / Hardware

| Параметр / Parameter | Значение / Value | Статус / Status |
|---|---|---|
| Модель / Model | Dell **Vostro 15** (5000-серия / series), MFG 2018 | с таблички / from label |
| Service Tag | `H7YB9L2` | с таблички / from label |
| CPU / RAM / GPU / диск / disk | **уточнить на сайте Dell по service tag** / **confirm via Dell site by service tag**; ожидаемо / expected i5-8250U класс, 8 ГБ, iGPU или NVIDIA MX | TBD |
| Прежняя роль / Prior role | ZTN: QEMU/KVM-хост Континента (192.168.75.177) | освобождён / freed |

## Сетевой план / Network plan

| Параметр / Parameter | Значение / Value |
|---|---|
| Подключение / Connection | LAN-кабель в домашний роутер / LAN cable to home router (`192.168.0.0/24`, gw `192.168.0.1`) |
| Статический IP / Static IP | **`192.168.0.60`** (Jetson = .50) — netplan или / or DHCP-reservation |
| Имя / Hostname | `vostro-ml` |
| Доступ / Access | SSH-ключ с Windows-dev и Jetson / SSH key from Windows-dev and Jetson |
| ML-порт / ML port | `3003/tcp` (immich-machine-learning), только LAN / LAN only |

## Фазы ввода / Onboarding phases

### L0 — Снять реальные спеки / Capture real specs (перед всем / before everything)
🇷🇺 На ноуте / 🇬🇧 On the laptop:
```bash
lscpu | grep -E 'Model name|^CPU\(s\)|Thread'; free -h | head -2; \
lspci | grep -iE 'vga|3d|nvidia'; lsblk -d -o NAME,SIZE,MODEL | grep -v loop
```
🇷🇺 От результата зависит: CPU-путь или GPU-ускорение ML; хватит ли RAM (нужно ≥8 ГБ комфортно).
🇬🇧 The result decides: CPU path vs GPU-accelerated ML; whether RAM is enough (≥8 GB comfortable).

### L1 — ОС, сеть, работа 24/7 с закрытой крышкой / OS, network, 24/7 lid-closed
- 🇷🇺 **ОС:** рекомендуется чистая **Ubuntu 24.04 Server** (headless — крышка закрыта, экран не нужен); заодно уходят ZTN-артефакты (QEMU, br0/tap0). Альтернатива — upgrade 20.04→22.04/24.04 (20.04 уже EOL).
- 🇬🇧 **OS:** recommend a clean **Ubuntu 24.04 Server** (headless — lid closed, no screen needed); this also removes ZTN leftovers (QEMU, br0/tap0). Alternative — upgrade 20.04→22.04/24.04 (20.04 is already EOL).
- 🇷🇺/🇬🇧 **Статический IP / Static IP** (netplan, интерфейс / interface вероятно / likely `enp3s0`):
  ```yaml
  # /etc/netplan/01-nas.yaml
  network:
    version: 2
    ethernets:
      enp3s0:
        addresses: [192.168.0.60/24]
        routes: [{to: default, via: 192.168.0.1}]
        nameservers: {addresses: [192.168.0.1, 1.1.1.1]}
  ```
  `sudo netplan apply`
- 🇷🇺/🇬🇧 **Работа с закрытой крышкой / Lid-closed operation** (`/etc/systemd/logind.conf`):
  ```ini
  HandleLidSwitch=ignore
  HandleLidSwitchDocked=ignore
  HandleLidSwitchExternalPower=ignore
  ```
  `sudo systemctl restart systemd-logind`
- 🇷🇺/🇬🇧 **Запрет сна / Disable sleep:**
  `sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`
- 🇷🇺 **Питание:** держать в сети; (опц.) ограничить заряд батареи. 🇬🇧 **Power:** keep plugged in; (opt.) cap battery charge.

### L2 — База сервера / Server base
- 🇷🇺/🇬🇧 SSH-ключи / SSH keys (Windows-dev + Jetson), отключить пароль-логин / disable password login.
- `sudo apt install docker.io docker-compose-plugin`
- 🇷🇺/🇬🇧 UFW: SSH + `3003/tcp` только из LAN / LAN only. Добавить в мониторинг / add to monitoring (Beszel / Uptime Kuma).

### L3 — Immich ML remote-сервер / Immich ML remote server
- 🇷🇺 Узнать версию Immich на Jetson (`docker inspect homecloud_immich_server | grep -i image`) — образ ML **должен совпадать по версии**. 🇬🇧 Get the Immich version on the Jetson — the ML image **must match the version**.
- 🇷🇺/🇬🇧 Поднять / run `ghcr.io/immich-app/immich-machine-learning:<версия/version>` (порт/port 3003, том кэша моделей / model cache volume).
  - 🇷🇺 Если есть **NVIDIA GPU**: драйвер + `nvidia-container-toolkit`, образ `:...-cuda`. Иначе — CPU-образ. 🇬🇧 If an **NVIDIA GPU** is present: driver + `nvidia-container-toolkit`, `:...-cuda` image. Otherwise — CPU image.
- 🇷🇺/🇬🇧 На Jetson / on the Jetson: `IMMICH_MACHINE_LEARNING_URL=http://192.168.0.60:3003`, перезапуск / restart `immich-server` + `immich-microservices`.
- 🇷🇺/🇬🇧 Запустить Job'ы / run jobs: Smart Search + Face Detection → обработать бэклог / process backlog (~6710 фото / photos).

### L4 — Дополнительные роли / Extra roles (опционально / optional)
- 🇷🇺/🇬🇧 restic backup target; разгрузка мониторинга с Jetson / offload monitoring from the Jetson.

## Открытые вопросы / Open questions
- 🇷🇺/🇬🇧 ОС / OS: чистая / clean Ubuntu 24.04 Server (по умолчанию / default) vs upgrade 20.04.
- 🇷🇺/🇬🇧 IP `192.168.0.60` — если занят, выбрать другой / pick another if taken.
- 🇷🇺/🇬🇧 GPU-ускорение / GPU acceleration — зависит от L0 / depends on L0.

## Что дальше / Next
🇷🇺 После подключения к домашней LAN и назначения IP `192.168.0.60` узел доступен по SSH — настройку L2–L3 выполняем удалённо.
🇬🇧 Once connected to the home LAN with IP `192.168.0.60`, the node is reachable over SSH — L2–L3 setup proceeds remotely.
