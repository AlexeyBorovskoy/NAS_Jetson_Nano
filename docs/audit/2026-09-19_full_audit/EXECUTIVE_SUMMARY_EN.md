# NAS_Jetson_Nano — Full Technical Audit 2026-09-19 (English summary)

> Full report in Russian: [`NAS_FULL_AUDIT_2026-09-19.md`](NAS_FULL_AUDIT_2026-09-19.md).
> Mode: read-only. Nothing was changed on the Jetson or the VPS. Code was executed only in isolated
> copies (HEAD, staged index, working tree). Measurements: 2026-09-19 03:33–03:45 UTC.

## What the system is
A family private cloud on a Jetson Nano 4 GB (L4T R32.7.1, Ubuntu 18.04): 13 containers
(Nextcloud 33.0.4, Immich 2.7.5 with ML disabled, Samba, two Postgres, two Redis, an LLM gateway,
a NAS API with the `@бобик` Talk bot, Netdata, Uptime Kuma, Portainer). SSD holds databases and
photos (13 GB), a 2 TB NTFS HDD holds the family archive (1.4 TB) and a photo copy, and the SD card
holds the OS and all of Docker. External access is VPN-only through a VPS reverse tunnel.
All containers healthy, 0 restarts, 0 OOM, 0 USB errors, clean HDD SMART, fresh DB dumps.

## Strengths
USB storage hardening; fail-closed DB dumps; a minimal public surface on the VPS (only 22/443/40568);
one redacting, budgeted egress to external LLMs; memory limits everywhere; ADRs and a culture of
withdrawing wrong diagnoses.

## Top problems
1. **P0 (deploy blocker, CONFIRMED by execution):** the gateway change — committed and pushed to
   `main` as `d52c11b` while this audit ran — breaks every GigaChat chat with HTTP 500 (`full` used
   before assignment) and removes `_IMG_TAG_RE` still in use; two existing tests fail. The pre-commit
   gate missed it because it only runs `tests/unit`. Not deployed.
2. **P1:** SSD auto-recovery has been broken since 2026-09-08 — the device pulled 98 renamed commits
   and the script calls a path that does not exist (exit 127). Docs say it is active.
3. **P1:** two confirmed power-loss resets (17.08, 18.09 ~3.5 h), no UPS.
4. **P1:** Nextcloud files, Nextcloud `config.php`, `.env` secrets and SD-card volumes have no backup;
   photos have no off-site copy; the HDD copy is writable by every family user via SMB/Nextcloud.
5. **P1:** NAS API serves room lists with participants, logs and containers without auth and with
   `CORS *` — any web page in a household browser can read them. The LLM gateway has no auth,
   honours an arbitrary `save_path`, trusts a client-supplied `user` for quotas and resets its budget
   when the usage file is unreadable.
6. **P2:** ~8 GB/day written to the SD card (unrotated Docker logs, Netdata, Redis, Kuma); CI has been
   red for 35 consecutive runs since 2026-08-30 because of two genuinely broken shell scripts;
   floating image tags; documentation claims hardening that is not in the code.

## Not a hardware problem
No CPU, RAM or I/O saturation was found (1.5 GB available, load < 2, no OOM). The only justified
purchase now is a UPS. Board replacement is a lifecycle question (EOL OS), not a performance one.

## First steps
Fix and fully test the gateway change before committing; fix the recovery script path; require auth
on NAS API endpoints and drop `CORS *`; add a service token to the gateway; back up configuration and
Nextcloud files; isolate the HDD copy; rotate Docker logs and move writers off the SD card; make CI
green and gate deployments on it; buy a UPS.

Details: [`FINDINGS_2026-09-19.md`](FINDINGS_2026-09-19.md) · [`ROADMAP_2026-09-19.md`](ROADMAP_2026-09-19.md) · [`EVIDENCE_2026-09-19.md`](EVIDENCE_2026-09-19.md).
