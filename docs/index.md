# NAS_Jetson_Nano

_Old Hardware Must Live._

A family self-hosted cloud built on Jetson Nano, USB SSD, Docker Compose,
Nextcloud, Immich, Android clients, monitoring and AI-assisted reliability engineering.

## Highlights

> **Статус данных / Data status:** приведённые ниже эксплуатационные числа являются историческими снимками из материалов проекта, а не текущими показателями. / The runtime figures below are historical snapshots from project records, not current measurements.

- **Jetson Nano 4GB** as home server (ARM64, no swap — real constraints)
- **Nextcloud** for files, contacts and calendar (CardDAV/CalDAV)
- **Immich** for family photo archive (6 697 photos backed up)
- **Android clients** with DAVx5 / Nextcloud / Immich auto-backup
- **Reverse SSH tunnel** through VPS for CGNAT bypass (no port forwarding needed)
- **Monitoring** with Beszel / Uptime Kuma / Telegram daily reports
- **Reliability story** around USB SSD failures and automated recovery
- **NAS_Jetson_Nano API** — custom REST API over the full stack (FastAPI, 20 endpoints, JWT)
- Open-source documentation, agent prompts and evidence

## Read

- [🇷🇺 Черновик статьи для Habr / Habr article draft](articles/habr_article_ru.md)
- [🇬🇧 Hackaday.io project draft (EN)](articles/hackaday_project_en.md)
- [Architecture](pages/architecture.md)
- [Reliability and validation](pages/reliability.md)
- [Android client](pages/android.md)
- [Evidence package](pages/evidence.md)
- [Keenetic Omni KN-1410 extender inventory](25_KEENETIC_OMNI_KN1410.md) — plan cancelled, cold spare
- [TP-Link Deco E4 scouting analysis](26_DECO_E4_NETWORK.md) — superseded by document 27
- [Home network on Deco E4 — full router replacement runbook](27_HOME_NETWORK_MESH.md)
- [Remote Immich ML node on a Dell Vostro 15](plans/VOSTRO_ML_NODE_ONBOARDING.md)

## Where the project is going / Куда движется проект

- **[Step 2 roadmap — six waves](plans/ROADMAP_STEP2_2026-08.md)** — safety net → network →
  ML node → offloading the Jetson → GPU experiment → conversational bot → article
- [Health audit 2026-08-10](plans/SYSTEM_AUDIT_2026-08-10.md) — the state we start from
- [Habr feedback and phase status](plans/POST_HABR_FEEDBACK_2026-08.md)

## Historical status snapshot / Исторический снимок состояния

| Component | Status |
|---|---|
| Docker containers | 13/13 up, healthy |
| Photos backed up | 6 697 files (Immich) |
| SSD | JMS583, 229 GB, Write 250 MB/s |
| goss tests | 40/40 passing |
| HTTPS (self-signed) | Live on alt-ports |
| Off-site backup | Planned (restic + 2 TB HDD) |

## Repository

GitHub: [AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)
