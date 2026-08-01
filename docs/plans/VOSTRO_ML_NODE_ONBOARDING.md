# Ввод в эксплуатацию: Dell Vostro 15 как ML/compute-узел

> Включение старого ноутбука Dell Vostro 15 (2018) в проект NAS_Jetson_Nano
> в роли **выделенного always-on узла машинного обучения Immich** и вспомогательного сервера.
> Решение принято: 2026-08-01. Проект ZTN временно закрыт → ноутбук свободен.

## Зачем
- **Immich ML** (распознавание лиц + smart search/CLIP) — главная претензия читателей Хабра
  (см. [POST_HABR_FEEDBACK_2026-08.md](POST_HABR_FEEDBACK_2026-08.md), комментарии vvzvlad/dE1l/falcon4fun).
  Jetson Nano её не тянет (CUDA 10.2, 4 ГБ). Vostro (x86-64, 4C/8T) — тянет.
- **Разгрузка Jetson:** ML уходит с перегруженного по RAM Nano (свободно ~520 МБ) на отдельную машину.
- **Без покупок** — используем уже имеющееся железо (то, что советовал falcon4fun, но своё).

## Железо

| Параметр | Значение | Статус |
|---|---|---|
| Модель | Dell **Vostro 15** (5000-серия), MFG 2018 | с таблички |
| Service Tag | `H7YB9L2` | с таблички |
| CPU / RAM / GPU / диск | **уточнить на месте** (Фаза L0); ожидаемо i5-8250U класс, 8 ГБ, iGPU или NVIDIA MX | TBD |
| Прежняя роль | ZTN: QEMU/KVM-хост Континента (192.168.75.177) | освобождён |

## Сетевой план

| Параметр | Значение |
|---|---|
| Подключение | LAN-кабель в домашний роутер (сеть `192.168.0.0/24`, gw `192.168.0.1`) |
| Статический IP | **`192.168.0.60`** (Jetson = .50) — через netplan или DHCP-reservation |
| Имя | `vostro-ml` |
| Доступ | SSH-ключ с Windows-dev и с Jetson |
| ML-порт | `3003/tcp` (immich-machine-learning), только в LAN |

## Фазы ввода

### L0 — Снять реальные спеки (перед всем)
На ноуте:
```bash
lscpu | grep -E 'Model name|^CPU\(s\)|Thread'; free -h | head -2; \
lspci | grep -iE 'vga|3d|nvidia'; lsblk -d -o NAME,SIZE,MODEL | grep -v loop
```
От результата зависит: CPU-путь или GPU-ускорение ML; хватит ли RAM (нужно ≥8 ГБ комфортно).

### L1 — ОС, сеть, работа 24/7 с закрытой крышкой
- **ОС:** рекомендуется чистая **Ubuntu 24.04 Server** (headless, без GUI — крышка закрыта, экран не нужен).
  Заодно убираются ZTN-артефакты (QEMU, br0/tap0). Альтернатива — upgrade 20.04→22.04/24.04 (20.04 уже EOL).
- **Статический IP** (netplan, интерфейс уточнить — вероятно `enp3s0`):
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
- **Работа с закрытой крышкой** (`/etc/systemd/logind.conf`):
  ```ini
  HandleLidSwitch=ignore
  HandleLidSwitchDocked=ignore
  HandleLidSwitchExternalPower=ignore
  ```
  `sudo systemctl restart systemd-logind`
- **Запрет сна/гибернации:**
  `sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`
- **Питание:** держать в сети постоянно; (опц.) ограничить заряд батареи, если поддерживается, чтобы не деградировала.

### L2 — База сервера
- SSH-ключи (доступ с Windows-dev и Jetson), отключить пароль-логин.
- `sudo apt install docker.io docker-compose-plugin` (или официальный docker-ce).
- UFW: разрешить SSH + `3003/tcp` только из LAN.
- Добавить узел в мониторинг (Beszel agent / Uptime Kuma).

### L3 — Immich ML remote-сервер
- Узнать версию Immich на Jetson (`docker inspect homecloud_immich_server | grep -i image`) — образ ML **должен совпадать по версии**.
- Поднять контейнер `ghcr.io/immich-app/immich-machine-learning:<версия>` (порт 3003, том для кэша моделей).
  - Если есть **NVIDIA GPU**: установить драйвер + `nvidia-container-toolkit`, взять `:...-cuda` образ.
  - Если нет: CPU-образ (i5-8250U тянет пакетно).
- На Jetson в Immich `.env`: `IMMICH_MACHINE_LEARNING_URL=http://192.168.0.60:3003`, перезапустить `immich-server` + `immich-microservices`.
- Запустить Job'ы: Smart Search + Face Detection → обработать бэклог (в CLAUDE.md было ~6710 фото).

### L4 — Дополнительные роли (опционально, после L3)
- **restic backup target** — второй адресат бэкапа (диск ноута / подключённый HDD).
- **Разгрузка мониторинга** — перенести netdata/uptime-kuma/portainer с Jetson сюда (освободит RAM Nano).

## Открытые вопросы / решения по умолчанию
- ОС: **чистая Ubuntu 24.04 Server** (по умолчанию) vs upgrade 20.04. → подтвердить.
- IP `192.168.0.60` — если занят, выбрать другой из свободных.
- GPU-ускорение — зависит от L0 (наличие и модель NVIDIA).

## Что дальше
После физического подключения к домашнему роутеру и назначения IP `192.168.0.60`
узел станет доступен по SSH — дальнейшую настройку (L2–L3) выполняем удалённо.
