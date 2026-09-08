# ADR-0009: Backup topology — SSD live, HDD on-site, S3 off-site  
# ADR-0009: Топология бэкапов — SSD live, HDD on-site, S3 off-site

## Status / Статус

🇬🇧 **Accepted** (2026-09-04).  
🇷🇺 **Принято** (2026-09-04).

🇬🇧 Implementation: L1 Immich→HDD **done on device 2026-09-08**; L2 S3 **blocked** (no tenant_id / AccessDenied).  
🇷🇺 Реализация: L1 Immich→HDD **на устройстве 2026-09-08**; L2 S3 **блокер** (tenant_id / AccessDenied).

Emergency T0 DB dumps may still land on Vostro restic (legacy path, snapshot `3922949b` 2026-09-08).

## Context / Контекст

🇬🇧 Audit P0: Immich photos were a single copy on SSD.  
🇷🇺 Аудит P0: фото Immich — одна копия на SSD.

🇬🇧 Vostro off-site is out of architecture as a required node (ADR-0007); owner may still use it for emergency dumps.  
🇷🇺 Vostro не обязательный узел (ADR-0007); emergency-дампы допустимы.

## Decision / Решение

| Layer / Слой | Content / Содержимое | Location / Место |
|---|---|---|
| **L0 live** | Immich + Nextcloud data | SSD `/mnt/storage` |
| **L1 on-site** | Immich library second copy | HDD `/mnt/hdd2tb/backups/immich/` |
| **L1b** | DB dumps | SSD (+ optional pull) |
| **L2 off-site** | restic encrypted dumps | Cloud.ru S3 (when unlocked) |
| **L3 code** | git | GitHub + GitVerse `NAS_HOME` |

## Consequences / Последствия

🇬🇧 L1 does **not** protect house-level loss; L2 does (with encryption).  
🇷🇺 L1 не спасает от потери дома; L2 — да (с шифрованием).

🇬🇧 NTFS archive on HDD must not be wiped; only `backups/` subtree.  
🇷🇺 Архив NTFS на HDD не трогать; только `backups/`.

## Rollback / Откат

🇬🇧 Stop timers; leave existing copies; no delete without owner OK.  
🇷🇺 Остановить таймеры; копии не удалять без OK владельца.
