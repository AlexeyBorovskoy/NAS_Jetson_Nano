# External Docs Local Cache

## 1. Назначение / Purpose

🇷🇺 Этот manifest описывает локально скачанные внешние материалы для автономной
работы с проектом NAS_Jetson_Nano.

🇬🇧 This manifest describes externally downloaded materials cached locally for
offline work on the NAS_Jetson_Nano project.

Локальный cache: / Local cache:

```text
docs/references/external_docs/
```

🇷🇺 Каталог `docs/references/external_docs/` исключён из Git через `.gitignore`. В публичный
репозиторий попадает только этот manifest и список ссылок.

🇬🇧 The `docs/references/external_docs/` directory is excluded from Git via `.gitignore`.
Only this manifest and the list of links make it into the public repository.

## 2. Что скачано / What was downloaded

Дата cache-среза: 2026-05-31. / Cache snapshot date: 2026-05-31.

| Каталог / Directory | Содержание / Contents | Назначение / Purpose |
|---|---|---|
| `docs/references/external_docs/jatson/` | локальный SD image, Etcher, NVIDIA User Guide PDF, исходный reference-файл / local SD image, Etcher, NVIDIA User Guide PDF, original reference file | Stage 0: microSD и первый boot / Stage 0: microSD and first boot |
| `docs/references/external_docs/jetson/` | NVIDIA Getting Started, L4T index, Jetson reference links | Stage 0: официальная HTML-документация / Stage 0: official HTML documentation |
| `docs/references/external_docs/docker/` | Docker Engine Ubuntu, Compose plugin, Compose file reference, post-install | установка Docker/Compose на Jetson / installing Docker/Compose on Jetson |
| `docs/references/external_docs/nextcloud/` | Nextcloud admin/system/WebDAV pages, link manifest | Nextcloud Stage 1B |
| `docs/references/external_docs/nextcloud/groupware/` | Contacts, Calendar, DAVx5 pages, link manifest | DAVx5/CalDAV/CardDAV сценарии / DAVx5/CalDAV/CardDAV scenarios |
| `docs/references/external_docs/immich/` | Immich requirements, install, backup, mobile backup, latest compose/env | Immich Stage 1C |
| `docs/references/external_docs/deepseek/` | API quick start, pricing, chat completion, reasoning, JSON, tools, cache | LLM Gateway Stage 1D |
| `docs/references/external_docs/protocols/` | RFC 4918, 4791, 6352, 5545, 6350 | WebDAV/CalDAV/CardDAV/iCalendar/vCard |
| `docs/references/external_docs/nas/` | Samba smb.conf, OpenSSH manual, sshd_config | Samba/SFTP |
| `docs/references/external_docs/backup/` | restic index, repository, backup, restore, forget pages | Backup/restore Stage 1E |
| `docs/references/external_docs/alternatives/` | link manifest for alternatives | архитектурное сравнение / architectural comparison |

🇷🇺 После загрузки cache содержит 52 файла. Пустых файлов не найдено.

🇬🇧 After downloading, the cache contains 52 files. No empty files were found.

## 3. Что намеренно не скачано / What was intentionally not downloaded

Не скачивались: / Not downloaded:

- `nextcloud-documentation-master.zip`;
- `nextcloud-docker-master.zip`;
- `immich-main.zip`;
- `restic-master.zip`;
- 🇷🇺 ZIP-архивы альтернативных проектов.
- 🇬🇧 ZIP archives of alternative projects.

🇷🇺 Причина: это большие и быстро устаревающие копии репозиториев. Для текущего
этапа достаточно официальных HTML-страниц, RFC-файлов, ссылок и актуальных
Immich `docker-compose.yml` / `example.env`.

🇬🇧 Reason: these are large, quickly outdated copies of repositories. For the
current stage, official HTML pages, RFC files, links, and current Immich
`docker-compose.yml` / `example.env` are sufficient.

## 4. Полезные локальные файлы первого порядка / Useful first-order local files

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

🇷🇺 Для локального контроля создан ignored-файл:

🇬🇧 An ignored file was created for local verification:

```text
docs/references/external_docs/SHA256SUMS.local
```

Его можно пересоздать командой: / It can be regenerated with the command:

```bash
cd /home/alexey/work/NAS_Jetson_Nano
sha256sum $(find external_docs -type f | sort) > docs/references/external_docs/SHA256SUMS.local
```

🇷🇺 Jetson SD image и Etcher checksums отдельно зафиксированы в
`docs/references/JETSON_LOCAL_ASSETS.md`.

🇬🇧 The Jetson SD image and Etcher checksums are recorded separately in
`docs/references/JETSON_LOCAL_ASSETS.md`.

## 6. Обновление cache / Refreshing the cache

Для повторной загрузки облегчённого набора используется: / To re-download the lightweight set, run:

```bash
./scripts/fetch_external_docs.sh
```

🇷🇺 Скрипт не скачивает тяжёлые repo ZIP и не скачивает Jetson SD Card Image. SD
image уже лежит локально в `docs/references/external_docs/jatson/` и должен обновляться только
вручную, если это действительно нужно.

🇬🇧 The script does not download heavy repo ZIP files and does not download the
Jetson SD Card Image. The SD image already sits locally in
`docs/references/external_docs/jatson/` and should only be refreshed manually,
if genuinely necessary.

## 7. Правила безопасности / Security rules

- 🇷🇺 Не добавлять `docs/references/external_docs/` в Git.
- 🇬🇧 Do not add `docs/references/external_docs/` to Git.
- 🇷🇺 Не хранить в `docs/references/external_docs/` реальные `.env`, ключи, токены, дампы или
  персональные файлы.
- 🇬🇧 Do not store real `.env` files, keys, tokens, dumps, or personal files in
  `docs/references/external_docs/`.
- 🇷🇺 Не публиковать локальные копии сторонних бинарников.
- 🇬🇧 Do not publish local copies of third-party binaries.
- 🇷🇺 Перед использованием скачанных HTML-страниц для решений, которые могли
  измениться, сверять критичные детали с официальным сайтом.
- 🇬🇧 Before using downloaded HTML pages for decisions that may have changed,
  cross-check critical details against the official site.
