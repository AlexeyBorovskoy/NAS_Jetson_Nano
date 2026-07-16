# External Docs Local Cache

## 1. Назначение

Этот manifest описывает локально скачанные внешние материалы для автономной
работы с проектом NAS_Jetson_Nano.

Локальный cache:

```text
docs/references/external_docs/
```

Каталог `docs/references/external_docs/` исключён из Git через `.gitignore`. В публичный
репозиторий попадает только этот manifest и список ссылок.

## 2. Что скачано

Дата cache-среза: 2026-05-31.

| Каталог | Содержание | Назначение |
|---|---|---|
| `docs/references/external_docs/jatson/` | локальный SD image, Etcher, NVIDIA User Guide PDF, исходный reference-файл | Stage 0: microSD и первый boot |
| `docs/references/external_docs/jetson/` | NVIDIA Getting Started, L4T index, Jetson reference links | Stage 0: официальная HTML-документация |
| `docs/references/external_docs/docker/` | Docker Engine Ubuntu, Compose plugin, Compose file reference, post-install | установка Docker/Compose на Jetson |
| `docs/references/external_docs/nextcloud/` | Nextcloud admin/system/WebDAV pages, link manifest | Nextcloud Stage 1B |
| `docs/references/external_docs/nextcloud/groupware/` | Contacts, Calendar, DAVx5 pages, link manifest | DAVx5/CalDAV/CardDAV сценарии |
| `docs/references/external_docs/immich/` | Immich requirements, install, backup, mobile backup, latest compose/env | Immich Stage 1C |
| `docs/references/external_docs/deepseek/` | API quick start, pricing, chat completion, reasoning, JSON, tools, cache | LLM Gateway Stage 1D |
| `docs/references/external_docs/protocols/` | RFC 4918, 4791, 6352, 5545, 6350 | WebDAV/CalDAV/CardDAV/iCalendar/vCard |
| `docs/references/external_docs/nas/` | Samba smb.conf, OpenSSH manual, sshd_config | Samba/SFTP |
| `docs/references/external_docs/backup/` | restic index, repository, backup, restore, forget pages | Backup/restore Stage 1E |
| `docs/references/external_docs/alternatives/` | link manifest for alternatives | архитектурное сравнение |

После загрузки cache содержит 52 файла. Пустых файлов не найдено.

## 3. Что намеренно не скачано

Не скачивались:

- `nextcloud-documentation-master.zip`;
- `nextcloud-docker-master.zip`;
- `immich-main.zip`;
- `restic-master.zip`;
- ZIP-архивы альтернативных проектов.

Причина: это большие и быстро устаревающие копии репозиториев. Для текущего
этапа достаточно официальных HTML-страниц, RFC-файлов, ссылок и актуальных
Immich `docker-compose.yml` / `example.env`.

## 4. Полезные локальные файлы первого порядка

Stage 0:

```text
docs/references/external_docs/jatson/jetson-nano-jp461-sd-card-image.zip
docs/references/external_docs/jatson/balenaEtcher-linux-x64-2.1.6.zip
docs/references/external_docs/jatson/NV_Jetson_Nano_Developer_Kit_User_Guide.pdf
docs/references/external_docs/jetson/get-started-jetson-nano-devkit.html
```

Docker:

```text
docs/references/external_docs/docker/docker-engine-ubuntu.html
docs/references/external_docs/docker/docker-compose-linux.html
docs/references/external_docs/docker/docker-linux-postinstall.html
```

Immich:

```text
docs/references/external_docs/immich/immich-docker-compose.yml
docs/references/external_docs/immich/immich-example.env
docs/references/external_docs/immich/requirements.html
docs/references/external_docs/immich/docker-compose-install.html
docs/references/external_docs/immich/backup-and-restore.html
```

Protocols:

```text
docs/references/external_docs/protocols/rfc4918-webdav.txt
docs/references/external_docs/protocols/rfc4791-caldav.txt
docs/references/external_docs/protocols/rfc6352-carddav.txt
docs/references/external_docs/protocols/rfc5545-icalendar.txt
docs/references/external_docs/protocols/rfc6350-vcard.txt
```

Backup:

```text
docs/references/external_docs/backup/restic-030-preparing-repo.html
docs/references/external_docs/backup/restic-040-backup.html
docs/references/external_docs/backup/restic-050-restore.html
docs/references/external_docs/backup/restic-060-forget.html
```

## 5. Checksums

Для локального контроля создан ignored-файл:

```text
docs/references/external_docs/SHA256SUMS.local
```

Его можно пересоздать командой:

```bash
cd /home/alexey/work/NAS_Jetson_Nano
sha256sum $(find external_docs -type f | sort) > docs/references/external_docs/SHA256SUMS.local
```

Jetson SD image и Etcher checksums отдельно зафиксированы в
`docs/references/JETSON_LOCAL_ASSETS.md`.

## 6. Обновление cache

Для повторной загрузки облегчённого набора используется:

```bash
./scripts/fetch_external_docs.sh
```

Скрипт не скачивает тяжёлые repo ZIP и не скачивает Jetson SD Card Image. SD
image уже лежит локально в `docs/references/external_docs/jatson/` и должен обновляться только
вручную, если это действительно нужно.

## 7. Правила безопасности

- Не добавлять `docs/references/external_docs/` в Git.
- Не хранить в `docs/references/external_docs/` реальные `.env`, ключи, токены, дампы или
  персональные файлы.
- Не публиковать локальные копии сторонних бинарников.
- Перед использованием скачанных HTML-страниц для решений, которые могли
  измениться, сверять критичные детали с официальным сайтом.
