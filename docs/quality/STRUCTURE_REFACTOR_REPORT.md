# Отчёт рефакторинга структуры / Structure Refactor Report

**Date:** 2026-06-27
**Performed by:** Claude Sonnet 4.6 + AlexeyBorovskoy
**Prompt:** `docs/prompts/structura_dif.md`

## Summary

Repository root had 4 loose `.md` files and 8 directories that didn't follow
open-source conventions. All misplaced files were moved (not deleted) to logical
locations. No scripts, systemd units, or Docker Compose files were touched.

## File moves

| Old path | New path | Method | Reason |
|---|---|---|---|
| `AUDIT_2026-05-31.md` | `artifacts/reports/AUDIT_2026-05-31.md` | git mv | audit output → artifacts |
| `PROJECT_CONTEXT.md` | `docs/PROJECT_CONTEXT.md` | git mv | documentation → docs |
| `PROJECT_TREE.txt` | `archive/legacy/PROJECT_TREE.txt` | git mv | stale snapshot → archive |
| `archtectura_nas_jetson_nano.md` | `docs/architecture_nas_jetson_nano.md` | git mv | fix typo + move to docs |
| `configs/samba/smb.conf` | `config/samba/smb.conf` | git mv | merge duplicate configs/ → config/ |
| `configs/samba/config.yml` | `config/samba/config.yml` | git mv | merge duplicate configs/ → config/ |
| `photo/test_sys.jpg` | `assets/photos/test_sys.jpg` | git mv | image → assets |
| `prompts/CODEX_*.md` (14 files) | `docs/prompts/` | git mv | prompts are docs |
| `prodaction/audit prodaction.md` | `artifacts/reports/` | git mv | audit report → artifacts |
| `prodaction/audit_report_2026-06-25.md` | `artifacts/reports/` | git mv | audit report → artifacts |
| `prodaction/stat.md` | `artifacts/reports/` | git mv | stats → artifacts |
| `ethernet_home/` (3 files, untracked) | `assets/photos/ethernet_home/` | mv | hardware photos → assets |
| `external_docs/` (53 files, untracked) | `docs/references/external_docs/` | mv | ref docs stay gitignored at new path |
| `runtime/audit/HARDWARE_AUDIT_REPORT.md` | `artifacts/reports/` | mv | audit → artifacts |
| `runtime/audit/hdd_*.json` (2 files) | `artifacts/reports/` | mv | audit data → artifacts |
| `runtime/wg-nas_jetson_nano-client.conf` | `archive/legacy/` | mv | VPN config (gitignored, has private key) |
| `runtime/wg-nas_jetson_nano-client.png` | `archive/legacy/` | mv | VPN QR code (gitignored) |
| `test_systems/*.md` (3 files, untracked) | `docs/prompts/` | mv | prompts → docs |
| `prodaction/android audit .md` (untracked) | `artifacts/reports/` | mv | audit → artifacts |

## New directories created

| Directory | Purpose |
|---|---|
| `assets/photos/` | hardware photos, screenshots of physical setup |
| `assets/screenshots/` | UI screenshots for documentation |
| `assets/diagrams/` | architecture diagrams |
| `artifacts/reports/` | generated audit reports, JSON exports |
| `archive/legacy/` | deprecated files, preserved for history |
| `docs/prompts/` | agent prompts (Codex, Claude, ChatGPT) |

## .gitignore changes

- Removed: `ethernet_home/` (now `assets/photos/ethernet_home/`, safe to track)
- Removed: `external_docs/` (moved; new location added below)
- Removed: `runtime/` (moved; no longer needed)
- Added: `docs/references/external_docs/` (large HTML cache, not for git)
- Added: `archive/legacy/wg-*.conf` and `archive/legacy/wg-*.png` (VPN private keys)
- Added: `prodaction/` and `test_systems/` (now consolidated into docs/prompts/)

## Files intentionally NOT moved

| Path | Reason |
|---|---|
| `docker/` | All scripts and systemd units reference `docker/compose/` — moving would break deployments |
| `systemd/` | Deployed to `/etc/systemd/system/` by install scripts — path is hardcoded |
| `scripts/` | Already well-structured; many cross-references |
| `tests/` | Already correct structure |
| `services/` | Microservice source — correct location |
| `docs/00-24_*.md` | Already in correct location |
| `config/` | Correct location, now extended with `config/samba/` |
| `.agents/`, `.codex/` | Agent tool config, should stay at root |

## References updated

| File | Change |
|---|---|
| `README.md` | Updated links for `PROJECT_CONTEXT.md` and `archtectura_nas_jetson_nano.md` |
| `docs/references/EXTERNAL_DOCS_CACHE.md` | Updated all `external_docs/` → `docs/references/external_docs/` |

## Remaining manual actions

1. Run `bash -n` on all scripts after any future moves to verify nothing broke.
2. The `photo/Эскорт_настройка_сети.docx` (untracked) left in place — personal document, add to `.gitignore` if not needed.
3. The `proton доступ.odt` (untracked, root level) — personal doc, add to `.gitignore`.
4. Empty dirs (`runtime/audit/`, `prodaction/`, `test_systems/`, `configs/samba/`) can be cleaned up after confirming nothing references them.
