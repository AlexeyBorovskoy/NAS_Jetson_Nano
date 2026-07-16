---
layout: default
title: Evidence Package
---

# Evidence package

Screenshots and artifacts confirming the system is live and working.

## Screenshots

All screenshots are redacted: IPs replaced with placeholders, personal names blurred.

| # | Screenshot | What it shows |
|---|---|---|
| 01 | [Beszel Hub overview](../assets/screenshots/article/redacted/01_beszel_systems_overview.png) | Jetson Nano and VPS — both online, uptime, agent versions |
| 02 | [Beszel Jetson metrics](../assets/screenshots/article/redacted/02_beszel_jetson_metrics.png) | CPU ~15%, RAM 2.3 GB, disk, network — live data |
| 03 | [NAS_Jetson_Nano API Swagger](../assets/screenshots/article/redacted/03_nas_jetson_nano_api_swagger_redacted.png) | All 5 endpoint groups (System, Talk, Users, Photos, Actions) |
| 04 | [Nextcloud dashboard](../assets/screenshots/article/redacted/04_nextcloud_dashboard_redacted.png) | Files, contacts, activity — family account |
| 05 | [Nextcloud Talk](../assets/screenshots/article/redacted/05_nextcloud_talk_redacted.png) | Family group chat, messages |
| 06 | [Android clients](../assets/screenshots/article/redacted/06_android_clients_card_redacted.png) | Immich backup stats + DAVx⁵ sync status |
| 07 | [Immich web](../assets/screenshots/article/redacted/07_immich_web_redacted.png) | Photo archive, 6.1 GiB, 228 GB free |

## Validation results

**goss 40/40** — all infrastructure tests pass.

Run on Jetson Nano:
```bash
cd ~/nas_jetson_nano && goss -g tests/goss/goss.yaml validate
```

Test matrix: [docs/quality/test_matrix.md](../quality/test_matrix.md)

## Repository artifacts

| Path | Contents |
|---|---|
| `artifacts/` | Audit reports, JSON exports |
| `docs/quality/` | Test plan, test matrix, baseline reports |
| `docs/ADR/` | Architecture Decision Records |
| `CHANGELOG.md` | Full version history |

## Links

- GitHub repository: [AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)
- Habr article: [habr.com/ru/sandbox/291694/](https://habr.com/ru/sandbox/291694/)

---

[← Android client](android.md) | [↑ Back to index](../index.md)
