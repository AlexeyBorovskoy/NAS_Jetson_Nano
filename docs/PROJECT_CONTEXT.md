# PROJECT_CONTEXT / Контекст проекта

> 🇷🇺 Проект предназначен для создания домашней семейной облачной платформы на доступном оборудовании.
> 🇬🇧 The project aims to build a home family cloud platform on affordable hardware.

## 1. Назначение / Purpose

🇷🇺 Проект предназначен для создания домашней семейной облачной платформы на доступном оборудовании.
🇬🇧 The project aims to build a home family cloud platform on affordable hardware.

Базовый сценарий:

```text
Android-телефоны семьи
  ├── Nextcloud Android: файлы, документы
  ├── Immich Android: фото/видео
  └── DAVx5: контакты/календарь
        ↓
Jetson Nano + USB storage
        ↓
Nextcloud + Immich + Backup + DeepSeek Gateway
```

Текущее состояние на 2026-06-23: Jetson доступен через реализованный VPS
reverse SSH tunnel; SSD снова виден как Realtek RTL9210B-CG `/dev/sda1`,
смонтирован в `/mnt/storage` и прошёл `e2fsck -f -n` + `storage_preflight.sh`.
Immich, LLM Gateway, nas_jetson_nano-api, Samba, мониторинг, DB backup и Nextcloud
отвечают. Nextcloud прошёл data/app review и controlled start; прежний HTTP 503
был следствием read-only remount `/mnt/storage` во время USB-инцидента.
Reboot/autorecovery test прошёл: reverse tunnel, `/mnt/storage`, Docker
containers, HTTP endpoints и `jetson-nas-health.timer` восстановились
автоматически после перезагрузки.

## 2. Зафиксированные решения

| Направление | Решение |
|---|---|
| Файловое облако | Nextcloud |
| Контакты/календарь | Nextcloud Contacts/Calendar + DAVx5 |
| Фото/видео | Immich |
| Локальный NAS | Samba + SFTP |
| Внешний доступ | Реализованный VPS reverse SSH tunnel (ADR-0005), без port forwarding на домашнем роутере |
| AI/LLM | DeepSeek API через LLM Gateway |
| Локальная LLM | Не используется на первом этапе |
| Android-приложение | Архитектура закладывается, реализация Stage 2 |
| USB storage | Целевой `/mnt/storage`; перед запуском storage-backed сервисов обязателен preflight |

## 3. Ограничения Jetson Nano

Jetson Nano подходит для домашнего облака, но не должен использоваться для тяжёлых задач:

- локальный inference LLM;
- массовый ML-анализ фото;
- тяжёлое видеотранскодирование;
- одновременная обработка больших архивов без лимитов.

## 4. Публичная ценность проекта

Проект может быть полезен пользователям, которые хотят:

- собрать домашнее облако без покупки NAS;
- использовать старое SBC-оборудование;
- заменить часть функций Google/Xiaomi Cloud;
- получить инженерную документацию и автоматизируемые сценарии для Codex/агентов;
- иметь privacy-first подход при подключении внешней LLM.
