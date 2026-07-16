# r/selfhosted — Post

**Subreddit:** r/selfhosted  
**Type:** Text post  
**Attach image:** `01_beszel_systems_overview.png` (optional, or post as image post separately)

---

## Title (pick one)

**Option A** (story-driven):
> I replaced Google Photos, Google Drive and Google Contacts for my whole family — running on a Jetson Nano I found in a drawer

**Option B** (stats-driven):
> Self-hosted family cloud on Jetson Nano: Nextcloud + Immich + DAVx⁵, 6,700 photos backed up, zero subscriptions

**Option C** (curiosity):
> Gave an old Jetson Nano a second life. 13 Docker containers, 3 USB SSD failures, one working family server.

---

## Post body

**TL;DR:** Jetson Nano 4GB → Nextcloud (files/contacts/calendar) + Immich (photos) + Samba + monitoring. Family of 5 using it daily. No domain, no Tailscale, no subscriptions. Everything open on GitHub.

---

Had an NVIDIA Jetson Nano sitting in a drawer since 2021. My son brought a 232 GB USB SSD — "dad, you'll need this." He was right.

Instead of paying for Synology (~$200+) or cloud subscriptions, I spent a few evenings turning it into a proper family home server.

**What it replaced:**

| Before | After |
|---|---|
| Google Photos | Immich — auto-backup from all phones |
| Google Drive + Yandex.Disk | Nextcloud — files, WebDAV sync |
| Google Contacts | DAVx⁵ + Nextcloud CardDAV — 2,151 contacts |
| Telegram family groups | Nextcloud Talk — 5 members, history on our SSD |

**Current state:**
- 13 Docker containers — all up/healthy
- 6,697 photos and videos backed up (Immich)
- goss 40/40 infrastructure tests passing
- USB SSD: Write 250 MB/s (JMS583, after fixing UAS quirk)
- Telegram daily health report every morning at 09:00

**The hard part — no swap, no domain, CGNAT:**

Jetson Nano has no swap. That killed Zabbix (needs 500+ MB for PostgreSQL alone), OpenMediaVault, and several other candidates. Had to build a lightweight stack with strict `mem_limit` per container.

External access without port forwarding: reverse SSH tunnel through a cheap VPS. `autossh` with `Restart=always`. Works through CGNAT, no WireGuard (incompatible with Tegra kernel 4.9), no Tailscale (conflicts with existing VPN on phones).

HTTPS without a domain: self-signed TLS on alt-ports (:8443/:2443) with IP in SAN. DAVx⁵ and Immich Android accept it after a one-time "trust" click.

**Three USB SSD incidents that almost killed the project:**

1. RTL9210B-CG chip + Tegra kernel 4.9 = USB autosuspend disconnect, `error -71` in dmesg. `usbcore.autosuspend=-1` helped partially, but write speed degraded to 40 MB/s. Solution: replace enclosure → JMS583.
2. USB port 4 on Jetson is physically unstable. Moved to port 2. Now watchdog is hardcoded to PORT=2.
3. Scripts created on Windows had `\r\n` line endings. Bash on Jetson saw `#!/bin/bash\r` — "No such file or directory". Fixed with `.gitattributes eol=lf`.

**Everything is documented and open:**

Full Docker Compose files, systemd units, scripts, architecture decisions, and even the agent prompts used during development:

👉 https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano

Happy to answer questions about the Jetson Nano constraints, the USB quirk, or the reverse tunnel setup.

---

## Comments to prepare (post as replies)

**If asked about the VPS:**
> The VPS only runs nginx as a reverse proxy + autossh for the tunnel. No data is stored there. It's a $3/month VPS in Vienna. The tunnel is initiated by Jetson outbound, so nothing is exposed directly.

**If asked about Immich without ML:**
> `IMMICH_DISABLE_MACHINE_LEARNING=true` — without this flag Immich tries to load face/object recognition models on startup and OOMs on 4GB without swap. Photos, albums, sharing and Android auto-backup all work fine without ML.

**If asked about why not Raspberry Pi:**
> Already had the Jetson. Same approach would work on RPi 4/5 — actually easier since you can add swap on RPi. The Jetson constraints made it more interesting to document.
