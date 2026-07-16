# Jetson Local Assets

## 1. Назначение

Этот документ фиксирует локальные внешние материалы Jetson, перенесённые в
проект из:

```text
/home/alexey/shared_vm/jatson
```

Текущий локальный путь после переноса:

```text
/home/alexey/work/NAS_Jetson_Nano/external_docs/jatson
```

Каталог `external_docs/` намеренно добавлен в `.gitignore`: в нём лежат большие
сторонние бинарные файлы, которые нельзя отправлять в GitHub.

## 2. Состав папки

| Файл | Размер | Назначение | Git |
|---|---:|---|---|
| `jetson-nano-jp461-sd-card-image.zip` | 6.2 GB | загрузочный SD Card Image для Jetson Nano / JetPack 4.6.1 | не коммитить |
| `balenaEtcher-linux-x64-2.1.6.zip` | 156 MB | локальный архив balenaEtcher для записи microSD | не коммитить |
| `NV_Jetson_Nano_Developer_Kit_User_Guide.pdf` | 1.7 MB | NVIDIA Jetson Nano Developer Kit User Guide | не коммитить, ссылка/описание в docs |
| `PROJECT_EXTERNAL_DOCUMENTATION_REFERENCE.md` | 39 KB | локальный список внешних ссылок и рекомендаций | не коммитить как external copy; важное перенести в docs |

## 3. Checksums

```text
b469c726bd9a0cdf6b0c83f70e74f0763bb4a71b90fea56a9622fbb6c39e37b4  PROJECT_EXTERNAL_DOCUMENTATION_REFERENCE.md
96e07c785c55969e35b0a69fc58fdea0542b2c3ce8f565a659240e53c6ce3f34  NV_Jetson_Nano_Developer_Kit_User_Guide.pdf
31755fc7992058738297ab633bc60f75999f34db94680cd6ca4c9da222bd4f75  balenaEtcher-linux-x64-2.1.6.zip
735fea3df2509436ce43e480f2e70d633f0adfe84007ed9ce7f43910e3814168  jetson-nano-jp461-sd-card-image.zip
```

Перед записью microSD checksum локального файла нужно сверить повторно:

```bash
cd /home/alexey/work/NAS_Jetson_Nano
sha256sum external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
sha256sum external_docs/jatson/balenaEtcher-linux-x64-2.1.6.zip
```

## 4. SD Card Image

Локальный архив:

```text
external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
```

Содержимое архива:

```text
sd-blob-b01.img
```

Размер распакованного образа:

```text
13,816,037,376 bytes
```

Вывод `unzip -l`:

```text
Archive:  external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
13816037376  2022-02-22 23:37   sd-blob-b01.img
---------                     -------
13816037376                     1 file
```

Практический вывод: microSD должна быть больше 13.8 GB. Для проекта всё равно
рекомендуется microSD 64 GB или больше.

## 5. balenaEtcher

Локальный архив:

```text
external_docs/jatson/balenaEtcher-linux-x64-2.1.6.zip
```

Назначение: графическая запись Jetson SD Card Image на microSD с validation.

Рекомендация: для первого запуска использовать Etcher вместо `dd`, потому что
он снижает риск выбрать не тот диск.

## 6. NVIDIA User Guide

Локальный PDF:

```text
external_docs/jatson/NV_Jetson_Nano_Developer_Kit_User_Guide.pdf
```

Метаданные PDF:

| Поле | Значение |
|---|---|
| Title | Jetson Nano Developer Kit |
| Date | January 15, 2020 |
| Pages | 26 |
| PDF version | 1.6 |
| File size | 1,680,990 bytes |

Ключевые практические выводы из User Guide:

- Jetson Nano Developer Kit перед первым использованием требует подготовленную
  microSD с ОС и JetPack-компонентами.
- Самый простой путь — скачать microSD card image и записать его на карту.
- В User Guide указан минимум 16 GB UHS-I microSD; для нашего проекта принята
  рекомендация 64 GB или больше.
- Для первого запуска через монитор нужны HDMI/DP monitor, USB keyboard,
  mouse, Ethernet и питание.
- В guide для базового setup указано питание 5V/2A через Micro-USB, но для
  серверного сценария с периферией практичнее использовать более стабильное
  питание Jetson и отдельное питание HDD.
- microSD вставляется в слот под Jetson Nano module.
- Jetson Nano Developer Kit включается автоматически после подключения питания.

## 7. External Documentation Reference

Локальный файл:

```text
external_docs/jatson/PROJECT_EXTERNAL_DOCUMENTATION_REFERENCE.md
```

Что из него уже учтено в проекте:

- внешние бинарные материалы не коммитятся;
- `external_docs/` добавлен в `.gitignore`;
- Jetson Nano SD Card Image хранится локально, а в Git фиксируются только
  ссылки, checksums и инструкции;
- Stage 0 описан в `docs/01A_JETSON_SD_BOOTSTRAP.md`;
- для публичного проекта предпочтительны ссылки на официальные источники, а не
  копии сторонней документации.

Полезные ссылки из локального reference-файла:

| Назначение | Ссылка |
|---|---|
| Jetson Nano Getting Started | `https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit` |
| Jetson Nano Developer Kit SD Card Image | `https://developer.nvidia.com/jetson-nano-sd-card-image` |
| Jetson Download Center | `https://developer.nvidia.com/embedded/downloads` |
| Jetson Linux Archive | `https://developer.nvidia.com/embedded/jetson-linux-archive` |
| L4T 32.7.6 docs | `https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3276/index.html` |
| balenaEtcher | `https://etcher.balena.io/` |
| Docker Engine on Ubuntu | `https://docs.docker.com/engine/install/ubuntu/` |
| Docker Compose plugin on Linux | `https://docs.docker.com/compose/install/linux/` |
| Immich Docker Compose | `https://docs.immich.app/install/docker-compose/` |
| Nextcloud Admin Manual | `https://docs.nextcloud.com/server/latest/admin_manual/` |
| restic documentation | `https://restic.readthedocs.io/` |

## 8. Как использовать на Stage 0

1. Проверить, что локальные файлы на месте:

```bash
cd /home/alexey/work/NAS_Jetson_Nano
ls -lh external_docs/jatson
```

2. Проверить checksum SD-образа:

```bash
sha256sum external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
```

3. Записать microSD через Etcher:

```text
Image:  external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
Target: microSD card, selected manually
Mode:   Flash + validate
```

4. После записи выполнить первый boot по `docs/01A_JETSON_SD_BOOTSTRAP.md`.

## 9. Ограничения

- Не добавлять `external_docs/` в Git.
- Не распаковывать SD image внутрь репозитория.
- Не использовать CLI-запись через `dd` без ручного подтверждения устройства.
- Не подключать HDD на Stage 0: сначала boot, LAN IP и SSH.
- Не скачивать повторно образы, пока локальный файл проходит checksum и
  соответствует Jetson Nano Developer Kit.
