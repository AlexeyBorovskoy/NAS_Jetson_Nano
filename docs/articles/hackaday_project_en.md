# Old Hardware Must Live: Jetson Nano Home Cloud

**Platform:** NVIDIA Jetson Nano 4GB (ARM64)  
**Repository:** [github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)

---

## What is this?

A family self-hosted cloud server built from hardware that was already sitting in a drawer.
Replaced Google Photos, Google Drive, Yandex.Disk, and Google Contacts with open-source
alternatives running on a Jetson Nano and a USB SSD — with zero monthly subscription cost.

This is not a tutorial. It is a documented engineering story, including the failures.

---

## Why old hardware?

The Jetson Nano was bought for robotics experiments, used for a week, and forgotten.
My son brought a 232 GB DEXP board — "dad, you'll need this." He was right.

Instead of buying a Synology (≈$200+) — used what was already there.

The constraint was real: 4 GB RAM, no swap, ARM64, Docker 20.10.7 (locked by JetPack).
Not every image has an ARM64 build. Zabbix was out (needs 500+ MB just for PostgreSQL).
The solution had to be minimal and composable.

---

## Hardware

| Component | Details |
|---|---|
| NVIDIA Jetson Nano Dev Kit | 4 GB LPDDR4, ARM64, Maxwell GPU |
| System disk | microSD 64 GB |
| Storage | USB SSD 232 GB → 229 GB (ext4) |
| USB enclosure | JMS583 (chip 152d:a583), USB 3.0, 5 Gbps |
| VPS | Ubuntu 24.04, 2 GB RAM, Europe |
| Router | Static LAN IP for Jetson |

The USB enclosure story is the most interesting part — see **Reliability story** below.

---

## Architecture

```
[Smartphone / browser / app]
        |
        | HTTPS / HTTP
        v
   [VPS in Europe]
   nginx (Docker)
   :8443 Nextcloud
   :2443 Immich
   :9443 LLM
   :8099 NAS_Jetson_Nano API
        |
        | reverse SSH tunnel (autossh, initiated by Jetson)
        v
[Jetson Nano — LAN JETSON_LAN_IP]
   Nextcloud    :8080
   Immich       :2283
   LLM Gateway  :8090
   NAS_Jetson_Nano API     :8099
   Samba        :445 (LAN only)
   Netdata      :19999
   Uptime Kuma  :3001
   Portainer    :9000
        |
        | USB 3.0, 5 Gbps
        v
[JMS583 SSD 229 GB — /mnt/storage]
```

**Why reverse SSH and not WireGuard?**  
WireGuard requires DKMS — incompatible with Tegra kernel 4.9.
Tailscale conflicts with an existing VPN on the Android devices.
`autossh` with `Restart=always` works through CGNAT without external dependencies.

**HTTPS without a domain?**  
Let's Encrypt requires a domain. Temporary workaround: self-signed TLS on alt-ports (:8443, :2443, :9443), 10-year cert, IP in SAN.
Browser warns once — accept certificate. Next step: add a domain, switch to Caddy + Let's Encrypt.

---

## Current status

- 13 Docker containers — all up, healthy
- 6 697 photos and videos backed up from family phones (Immich)
- 2 151 contacts synced via DAVx⁵
- 5 family members in Nextcloud Talk group chat
- goss 40/40 — infrastructure validation tests
- SSD: Write 250 MB/s, Read 172 MB/s (JMS583, BOT mode after UAS quirk)
- Telegram daily report every morning at 09:00

---

## Android client

Connecting family phones (Xiaomi with MIUI/HyperOS) required:

1. **Immich** — auto-backup enabled, 6 697 files uploaded. MIUI requires battery whitelist and auto-start permission or backup stops in background.
2. **Nextcloud** — file sync and WebDAV.
3. **DAVx⁵** — CalDAV and CardDAV sync (contacts + calendar). Requires HTTPS — that's why the self-signed cert was needed.

---

## Reliability story: USB storage failures

Three separate incidents around the USB SSD, each of which could have ended the project.

### Incident 1 — error -71 (RTL9210B-CG + autosuspend)

First enclosure (RTL9210B-CG chip): worked for days, then dmesg started showing:

```
usb 2-1.3: USB disconnect, device number X
sd 0:0:0:0: [sda] tag#0 FAILED Result: hostbyte=DID_ERROR
```

Root cause: RTL9210B-CG enters USB autosuspend at idle, and Tegra kernel 4.9 does not wake it correctly. Docker dropped, data unavailable.

`usbcore.autosuspend=-1` in the bootloader helped partially, but write speed gradually degraded to 40 MB/s and stream errors started.

**Solution: replace the enclosure.** New one: JMS583 (chip 152d:a583).

### Incident 2 — broken USB port 4

After connecting JMS583 to port 4 — same symptoms. The port was physically unstable.
Moved to **port 2** — everything worked. Now documented in the watchdog config (PORT=2).

### Incident 3 — CRLF in bash scripts

Scripts created on Windows had `\r\n` line endings. Bash on Jetson saw `#!/bin/bash\r` — unrecognized interpreter.

**Solution:** `.gitattributes` with `* text=auto eol=lf`. All scripts are auto-converted on Linux checkout.

### What's running now

```bash
# /boot/extlinux/extlinux.conf, add to APPEND line:
usb-storage.quirks=152d:a583:u usbcore.autosuspend=-1
```

Flag `u` switches JMS583 to BOT mode instead of UAS.
Without it: write 8 MB/s. With it: Write **250 MB/s**, Read **172 MB/s**, zero USB errors in dmesg.

Additional: SCSI timeout raised to 120s (udev rule), watchdog service does power cycle on boot,
udev trigger auto-mounts the disk and brings all containers up if SSD is hot-reconnected.

---

## AI-assisted engineering

The implementation used Claude Code — an AI agent with filesystem and SSH access.

**What worked well:**
- Generating sets of similar files in parallel (systemd units, Docker Compose files, nginx configs)
- Analyzing tool options (why Zabbix won't fit: needs 500+ MB RAM for PostgreSQL alone)
- Documentation that would normally be skipped (ADR, CHANGELOG, bilingual family guides)

**What required a human:**
- Hardware-specific context: broken USB port 4, RTL9210B-CG instability with kernel 4.9, existing VPN on VPS that must not be touched
- Security review: firewall rules, fstab, secrets — read and verify yourself
- Final decisions about architecture trade-offs

`AGENTS.md` (now `CLAUDE.md`) is read at every session start. It stores hard constraints, hardware quirks, and decisions — so the agent doesn't repeat known mistakes.

---

## Monitoring and validation

**Beszel Hub** (VPS) — historical CPU/RAM/Disk/Network graphs for both servers.

**Telegram daily report** at 09:00:

```
NAS_JETSON_NANO — Daily Report
SYSTEM: Uptime 18h | RAM 2.3/3.9G | Disk 7G/229G | Temp 41°C
CONTAINERS: ✅ all 13 running (restarts: 0)
LOCAL HTTP: ✅ Nextcloud 302 ✅ Immich 200
EXTERNAL: ✅ Nextcloud VPS ✅ Immich VPS
```

**goss** (ARM64) — 40 infrastructure tests: ports, services, files, HTTP endpoints.

---

## NAS_Jetson_Nano API

Custom REST API (FastAPI) over the full stack — 20 endpoints, JWT auth via Nextcloud:

| Group | What it does |
|---|---|
| System | RAM, CPU, temperature, containers |
| Talk | List chats, participants, send messages |
| Users | Family accounts, personal DMs |
| Photos | Immich stats: 6 484 photos, 210 videos |
| Actions | Restart container, trigger backup |

Swagger UI: `VPS_IP:8099/docs`

---

## Known limitations

- Docker 20.10.7 — outdated, locked by JetPack. Contains old CVEs. Upgrade is non-trivial.
- Off-site backup not yet configured — restic scripts ready, deployment planned after 2 TB HDD is connected. Data is on one disk only — this is a known risk.
- ML in Immich disabled — Jetson 4 GB without swap cannot run face/object recognition.
- Self-signed TLS — temporary until a domain is added.

---

## GitHub repository

Full documentation, Docker Compose files, systemd units, scripts, agent prompts, ADRs, family guides:

**[github.com/AlexeyBorovskoy/NAS_Jetson_Nano](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano)**

---

## Project logs plan

- [x] Hardware setup and Docker Compose stack
- [x] Reverse SSH tunnel through VPS
- [x] HTTPS with self-signed TLS
- [x] Android clients (Immich, Nextcloud, DAVx⁵)
- [x] USB SSD incidents and recovery automation
- [x] NAS_Jetson_Nano API v0.6.0 (Talk, Photos, Users, Actions)
- [x] Monitoring (Beszel, Uptime Kuma, Telegram)
- [ ] Off-site backup (restic + 2 TB HDD)
- [ ] Domain + Caddy + Let's Encrypt
- [ ] Docker upgrade path (post-JetPack)
