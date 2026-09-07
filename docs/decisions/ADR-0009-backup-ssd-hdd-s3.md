# ADR-0009: Топология бэкапов — SSD live, HDD on-site, S3 off-site

## Статус / Status

🇷🇺 **Принято** (2026-09-04). / 🇬🇧 **Accepted** (2026-09-04).  
🇷🇺 Реализация: Волна 2 (HDD), Волна 3 (S3) — см. план развития.

## Контекст / Context

- P0 audit: Immich photos ~6–9 GB only on SSD (CRITICAL).
- Vostro off-site (WAVE_0 phase 1 DB dumps) excluded from NAS architecture (ADR-0007).
- Owner: second Immich copy on Jetson 2 TB HDD; true off-site via Cloud.ru when ready.

## Решение / Decision

| Layer | Content | Location |
|---|---|---|
| **L0 live** | Immich + Nextcloud data | SSD `/mnt/storage` |
| **L1 on-site** | Immich library second copy | HDD `/mnt/hdd2tb/backups/immich/` (dedicated dir, not mixed with personal archive tree root) |
| **L1b** | DB dumps | SSD (+ optional HDD) nightly |
| **L2 off-site** | restic **encrypted** dumps (DB first; bulk photos by separate decision) | Cloud.ru Object Storage `s3.cloud.ru` |
| **L3 code** | git | GitHub canon + GitVerse `NAS_HOME` mirror |

Vostro restic, if still running elsewhere, is **legacy** — not required by this ADR.

## Последствия / Consequences

- L1 does **not** protect against house-level loss; L2 does (with encryption).
- NTFS archive on HDD must not be wiped; only `backups/` subtree.
- Free-space preflight required before Immich copy jobs.

## Откат / Rollback

Stop timers; leave existing copies; do not delete without owner OK.
