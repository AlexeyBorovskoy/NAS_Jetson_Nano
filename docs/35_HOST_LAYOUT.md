# 35. Раскладка хоста / Host layout

> 🇷🇺 Где на Jetson живут проект, конфиги, логи и юниты — и почему скрипты больше не знают этого сами.
> 🇬🇧 Where the project, configs, logs and units live on the Jetson, and why scripts no longer hardcode it.

## 🇷🇺 Проблема (2026-09-08 → 2026-09-19)

Git переименован в `nas_jetson_nano-*`, устройство живёт по старым именам `nasa-*`. Скрипт
авто-восстановления SSD звал `/home/admin/nas_jetson_nano/...` — каталога нет, код 127,
механизм не работал 11 дней (аудит 2026-09-19, NAS-STO-001). Таких путей в git было ~30.

## 🇷🇺 Решение

Раскладка — **конфигурация хоста**. Единственный источник: `scripts/lib/layout.sh`
(Python-двойник `scripts/lib/nas_layout.py`, правила сверяет `tests/unit/test_layout.py`).

Порядок: явное окружение (`Environment=` юнита) → `/etc/nas-layout.env` → автоопределение
(есть только `nasa-monitor` → `nasa`) → целевые имена `nas_jetson_nano`.

| Переменная | Устройство сейчас (замер 2026-09-19) | Цель после Part B |
|---|---|---|
| `NAS_PREFIX` | `nasa` | `nas_jetson_nano` |
| `NAS_PROJECT_DIR` | `/home/admin/nasa` | `/home/admin/nas_jetson_nano` |
| `NAS_CONF_DIR` | `/etc/nasa-monitor` | `/etc/nas_jetson_nano-monitor` |
| `NAS_LOG_DIR` | `/var/log/nasa-monitor` | `/var/log/nas_jetson_nano-monitor` |
| `NAS_STATE_DIR` | `/var/lib/nasa-monitor` | `/var/lib/nas_jetson_nano-monitor` |
| `NAS_SBIN_PREFIX` | `/usr/local/sbin/nasa` | `/usr/local/sbin/nas_jetson_nano` |
| `NAS_UNIT_PREFIX` | `nasa` | `nas_jetson_nano` |
| `NAS_OPT_DIR` | `/opt/nasa` | `/opt/nas_jetson_nano` |
| `NAS_API_CONTAINER` | `homecloud_nasa_api` | не меняется (решение 2026-08-30) |

**Правило для кода:** скрипт, работающий на Jetson, не пишет путь хоста буквально —
подключает `layout.sh` (Python: `nas_layout.resolve()`). Тест `NoHardcodedHostPaths` падает иначе.
Скрипты в `/usr/local/sbin` находят библиотеку в `/usr/local/lib/nas_jetson_nano/`
(ставит `scripts/lib/install_layout.sh`, только в окне деплоя).

**Part B (переезд)** = перенести каталоги и юниты + поправить `/etc/nas-layout.env`. Скрипты не меняются.

**Не покрыто:** systemd-юниты в `systemd/` остаются шаблонами под целевые имена (юниты не умеют
`source`); скрипты для VPS (`ddns`, `amnezia monitor`, `install_*_vps`) — другой хост.

## 🇬🇧 Summary

Host paths are configuration, not code. `scripts/lib/layout.sh` and its Python twin
`nas_layout.py` resolve them in this order: explicit env, `/etc/nas-layout.env`, auto-detect
(legacy `nasa-*` dirs), then target names. The live Jetson resolves to the legacy layout, verified
on 2026-09-19. Device-run scripts must not hardcode host paths, and a unit test enforces this.
The Part B migration then becomes a data move plus an edit of `/etc/nas-layout.env`.
