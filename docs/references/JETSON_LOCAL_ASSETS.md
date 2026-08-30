# Jetson Local Assets

## 1. Назначение / Purpose

🇷🇺 Этот документ фиксирует локальные внешние материалы Jetson, перенесённые в
проект из:

🇬🇧 This document records the local external Jetson materials moved into the
project from:

```text
/home/alexey/shared_vm/jatson
```

Текущий локальный путь после переноса: / Current local path after the move:

```text
/home/alexey/work/NAS_Jetson_Nano/external_docs/jatson
```

🇷🇺 Каталог `external_docs/` намеренно добавлен в `.gitignore`: в нём лежат большие
сторонние бинарные файлы, которые нельзя отправлять в GitHub.

🇬🇧 The `external_docs/` directory is deliberately added to `.gitignore`: it holds
large third-party binary files that must not be pushed to GitHub.

## 2. Состав папки / Directory contents

| Файл / File | Размер / Size | Назначение / Purpose | Git |
|---|---:|---|---|
| `jetson-nano-jp461-sd-card-image.zip` | 6.2 GB | загрузочный SD Card Image для Jetson Nano / JetPack 4.6.1 / bootable SD Card Image for Jetson Nano / JetPack 4.6.1 | не коммитить / do not commit |
| `balenaEtcher-linux-x64-2.1.6.zip` | 156 MB | локальный архив balenaEtcher для записи microSD / local balenaEtcher archive for flashing the microSD | не коммитить / do not commit |
| `NV_Jetson_Nano_Developer_Kit_User_Guide.pdf` | 1.7 MB | NVIDIA Jetson Nano Developer Kit User Guide | не коммитить, ссылка/описание в docs / do not commit, link/description lives in docs |
| `PROJECT_EXTERNAL_DOCUMENTATION_REFERENCE.md` | 39 KB | локальный список внешних ссылок и рекомендаций / local list of external links and recommendations | не коммитить как external copy; важное перенести в docs / do not commit as an external copy; move anything important into docs |

## 3. Checksums / Checksums

```text
b469c726bd9a0cdf6b0c83f70e74f0763bb4a71b90fea56a9622fbb6c39e37b4  PROJECT_EXTERNAL_DOCUMENTATION_REFERENCE.md
96e07c785c55969e35b0a69fc58fdea0542b2c3ce8f565a659240e53c6ce3f34  NV_Jetson_Nano_Developer_Kit_User_Guide.pdf
31755fc7992058738297ab633bc60f75999f34db94680cd6ca4c9da222bd4f75  balenaEtcher-linux-x64-2.1.6.zip
735fea3df2509436ce43e480f2e70d633f0adfe84007ed9ce7f43910e3814168  jetson-nano-jp461-sd-card-image.zip
```

🇷🇺 Перед записью microSD checksum локального файла нужно сверить повторно:

🇬🇧 Before flashing the microSD, the checksum of the local file must be re-verified:

```bash
cd /home/alexey/work/NAS_Jetson_Nano
sha256sum external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
sha256sum external_docs/jatson/balenaEtcher-linux-x64-2.1.6.zip
```

## 4. SD Card Image / SD Card Image

🇷🇺 Локальный архив: / 🇬🇧 Local archive:

```text
external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
```

🇷🇺 Содержимое архива: / 🇬🇧 Archive contents:

```text
sd-blob-b01.img
```

🇷🇺 Размер распакованного образа: / 🇬🇧 Unpacked image size:

```text
13,816,037,376 bytes
```

🇷🇺 Вывод `unzip -l`: / 🇬🇧 `unzip -l` output:

```text
Archive:  external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
  Length      Date    Time    Name
---------  ---------- -----   ----
13816037376  2022-02-22 23:37   sd-blob-b01.img
---------                     -------
13816037376                     1 file
```

🇷🇺 Практический вывод: microSD должна быть больше 13.8 GB. Для проекта всё равно
рекомендуется microSD 64 GB или больше.

🇬🇧 Practical takeaway: the microSD must be larger than 13.8 GB. For this project,
64 GB or larger is still recommended.

## 5. balenaEtcher / balenaEtcher

🇷🇺 Локальный архив: / 🇬🇧 Local archive:

```text
external_docs/jatson/balenaEtcher-linux-x64-2.1.6.zip
```

🇷🇺 Назначение: графическая запись Jetson SD Card Image на microSD с validation.

🇬🇧 Purpose: graphical flashing of the Jetson SD Card Image onto the microSD with validation.

🇷🇺 Рекомендация: для первого запуска использовать Etcher вместо `dd`, потому что
он снижает риск выбрать не тот диск.

🇬🇧 Recommendation: use Etcher instead of `dd` for the first flash, since it
reduces the risk of selecting the wrong disk.

## 6. NVIDIA User Guide / NVIDIA User Guide

🇷🇺 Локальный PDF: / 🇬🇧 Local PDF:

```text
external_docs/jatson/NV_Jetson_Nano_Developer_Kit_User_Guide.pdf
```

🇷🇺 Метаданные PDF: / 🇬🇧 PDF metadata:

| Поле / Field | Значение / Value |
|---|---|
| Title | Jetson Nano Developer Kit |
| Date | January 15, 2020 |
| Pages | 26 |
| PDF version | 1.6 |
| File size | 1,680,990 bytes |

🇷🇺 Ключевые практические выводы из User Guide:

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

🇬🇧 Key practical takeaways from the User Guide:

- Before first use, the Jetson Nano Developer Kit requires a prepared microSD
  with the OS and JetPack components.
- The simplest path is to download the microSD card image and flash it onto the card.
- The User Guide states a minimum of 16 GB UHS-I microSD; for this project a
  recommendation of 64 GB or larger has been adopted.
- The first boot through a monitor needs an HDMI/DP monitor, a USB keyboard,
  a mouse, Ethernet, and power.
- The guide specifies 5V/2A power over Micro-USB for the basic setup, but for
  a server scenario with peripherals it is more practical to use a more stable
  power supply for the Jetson and a separate power supply for the HDD.
- The microSD slot is underneath the Jetson Nano module.
- The Jetson Nano Developer Kit powers on automatically once power is connected.

## 7. External Documentation Reference / External Documentation Reference

🇷🇺 Локальный файл: / 🇬🇧 Local file:

```text
external_docs/jatson/PROJECT_EXTERNAL_DOCUMENTATION_REFERENCE.md
```

🇷🇺 Что из него уже учтено в проекте:

- внешние бинарные материалы не коммитятся;
- `external_docs/` добавлен в `.gitignore`;
- Jetson Nano SD Card Image хранится локально, а в Git фиксируются только
  ссылки, checksums и инструкции;
- Stage 0 описан в `docs/01A_JETSON_SD_BOOTSTRAP.md`;
- для публичного проекта предпочтительны ссылки на официальные источники, а не
  копии сторонней документации.

🇬🇧 What has already been accounted for in the project:

- external binary materials are not committed;
- `external_docs/` is added to `.gitignore`;
- the Jetson Nano SD Card Image is stored locally, and only links, checksums,
  and instructions are recorded in Git;
- Stage 0 is described in `docs/01A_JETSON_SD_BOOTSTRAP.md`;
- for a public project, links to official sources are preferred over copies
  of third-party documentation.

🇷🇺 Полезные ссылки из локального reference-файла: / 🇬🇧 Useful links from the local reference file:

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

## 8. Как использовать на Stage 0 / How to use at Stage 0

🇷🇺 1. Проверить, что локальные файлы на месте: / 🇬🇧 1. Verify the local files are in place:

```bash
cd /home/alexey/work/NAS_Jetson_Nano
ls -lh external_docs/jatson
```

🇷🇺 2. Проверить checksum SD-образа: / 🇬🇧 2. Verify the SD image checksum:

```bash
sha256sum external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
```

🇷🇺 3. Записать microSD через Etcher: / 🇬🇧 3. Flash the microSD with Etcher:

```text
Image:  external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
Target: microSD card, selected manually
Mode:   Flash + validate
```

🇷🇺 4. После записи выполнить первый boot по `docs/01A_JETSON_SD_BOOTSTRAP.md`.

🇬🇧 4. After flashing, perform the first boot following `docs/01A_JETSON_SD_BOOTSTRAP.md`.

## 9. Ограничения / Constraints

🇷🇺

- Не добавлять `external_docs/` в Git.
- Не распаковывать SD image внутрь репозитория.
- Не использовать CLI-запись через `dd` без ручного подтверждения устройства.
- Не подключать HDD на Stage 0: сначала boot, LAN IP и SSH.
- Не скачивать повторно образы, пока локальный файл проходит checksum и
  соответствует Jetson Nano Developer Kit.

🇬🇧

- Do not add `external_docs/` to Git.
- Do not unpack the SD image inside the repository.
- Do not use CLI flashing via `dd` without manually confirming the target device.
- Do not connect the HDD at Stage 0: boot, LAN IP, and SSH come first.
- Do not re-download the images while the local file passes its checksum and
  matches the Jetson Nano Developer Kit.
