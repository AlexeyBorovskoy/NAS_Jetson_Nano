# GitHub Pages — Image Audit

**Date:** 2026-06-29  
**Source:** `docs/articles/publication/images_ready/`  
**Target:** `docs/assets/screenshots/article/redacted/`

## Screenshot inventory

| # | Filename | Content | Redacted |
|---|---|---|---|
| 01 | `01_beszel_systems_overview.png` | Beszel Hub: Jetson + VPS status overview | ✅ IP blurred |
| 02 | `02_beszel_jetson_metrics.png` | Jetson metrics: CPU, RAM, disk, network | ✅ IP blurred |
| 03 | `03_nas_jetson_nano_api_swagger_redacted.png` | NAS_Jetson_Nano API Swagger UI, all endpoint groups | ✅ URL blurred |
| 04 | `04_nextcloud_dashboard_redacted.png` | Nextcloud dashboard: files, contacts, chat | ✅ Names blurred |
| 05 | `05_nextcloud_talk_redacted.png` | Nextcloud Talk: family group chat | ✅ Names + messages blurred |
| 06 | `06_android_clients_card_redacted.png` | Android: Immich backup + DAVx⁵ sync card | ✅ Names blurred |
| 07 | `07_immich_web_redacted.png` | Immich web: photo archive, storage stats | ✅ Names blurred |

## What was redacted (method: solid fill 185,185,185)

- All server IP addresses (192.168.x.x, VPS IP)
- Personal names of family members in Nextcloud, Talk, Immich
- Chat message content in Nextcloud Talk
- Nextcloud card #5 "Recent activity" (personal file names)
- NAS_Jetson_Nano API external access URL

## Article image references (habr_article_ru.md)

All 8 image tags in the article now reference the numbered filenames above.  
The two Android screenshot tags both point to `06_android_clients_card_redacted.png` (single combined card).

## Verification command

```bash
grep "assets/screenshots" docs/articles/habr_article_ru.md
ls -1 docs/assets/screenshots/article/redacted/0*.png
```
