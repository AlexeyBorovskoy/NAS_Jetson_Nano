# r/homelab — Post

**Subreddit:** r/homelab  
**Type:** Text post + image  
**Attach image:** `01_beszel_systems_overview.png` or `02_beszel_jetson_metrics.png`

---

## Title (pick one)

**Option A** (incident story):
> 3 USB SSD failures, 1 broken port, and CRLF line endings — building a home server on a Jetson Nano 4GB

**Option B** (hardware focus):
> Jetson Nano 4GB ARM64, no swap, 13 Docker containers, reverse SSH tunnel through CGNAT — lessons learned

**Option C** (outcome):
> Finally put my Jetson Nano to work: family cloud server, goss 40/40, everything documented on GitHub

---

## Post body

**TL;DR:** Jetson Nano 4GB ARM64 → 13 Docker containers (Nextcloud, Immich, Samba, monitoring). Biggest challenges: no swap, ARM64 image availability, USB SSD instability, CGNAT. All documented with Docker Compose files, systemd units and scripts on GitHub.

---

**Hardware:**

| Component | Details |
|---|---|
| Compute | NVIDIA Jetson Nano Dev Kit 4GB, ARM64, Maxwell GPU |
| System disk | microSD 64GB |
| Storage | USB SSD 232GB → 229GB ext4 |
| USB enclosure | JMS583 (152d:a583), USB 3.0, 5 Gbps |
| VPS | Ubuntu 24.04, 2GB RAM, Europe |

The Jetson was bought for robotics experiments in 2021, used for a week, forgotten. My son brought the USB SSD. Total new spend: zero.

**The constraint that shaped everything: no swap**

Jetson Nano 4GB has no swap (eMMC wear concern). This eliminated:
- Zabbix — needs PostgreSQL alone at 500+ MB
- OpenMediaVault — takes over the system
- Several monitoring stacks

Solution: strict `mem_limit` per container + `restart: always`. Current allocation:

```
immich_server      1024m
nextcloud           512m
nextcloud_db        512m
immich_db           384m
immich_microservices 512m
llm_gateway         256m
netdata             256m
... (7 more)
```

Total headroom: ~400MB. Has been stable for weeks.

**Networking: CGNAT bypass without WireGuard**

WireGuard requires DKMS — incompatible with Tegra kernel 4.9. Tailscale conflicts with existing VPN on Android devices.

Solution: reverse SSH tunnel through a cheap VPS. Jetson initiates outbound connection, VPS nginx proxies back.

```
Internet → VPS nginx (:8443/:2443/:9443)
              ↕ autossh reverse tunnel
         Jetson Nano LAN (192.168.x.x)
              ↕ USB 3.0
         JMS583 SSD 229GB /mnt/storage
```

`autossh` + `systemd Restart=always` = survived multiple network drops without manual intervention.

**The USB SSD story (the real engineering part)**

Three separate incidents, each of which could have ended the project:

**Incident 1** — RTL9210B-CG chip enters USB autosuspend at idle. Tegra kernel 4.9 can't wake it correctly. Docker dropped, `error -71` in dmesg. `usbcore.autosuspend=-1` helped partially but write speed degraded to 40 MB/s and stream errors started appearing. **Fix: replace enclosure.** New one: JMS583 (152d:a583).

**Incident 2** — JMS583 connected to USB port 4 showed the same disconnect symptoms. Port 4 is physically unstable. Moved to port 2. Watchdog and preboot service are now hardcoded to PORT=2.

**Incident 3** — Scripts written on Windows had `\r\n` line endings. Bash on Jetson saw `#!/bin/bash\r` — interpreter not found. **Fix:** `.gitattributes` with `* text=auto eol=lf`.

**Current JMS583 setup:**

```bash
# /boot/extlinux/extlinux.conf APPEND line:
usb-storage.quirks=152d:a583:u usbcore.autosuspend=-1
```

Flag `u` = BOT mode instead of UAS. Without it: write 8 MB/s. With it: **Write 250 MB/s, Read 172 MB/s**, zero errors in dmesg.

Plus: SCSI timeout raised to 120s (udev rule), preboot power cycle service, udev auto-recovery trigger.

**Validation: goss 40/40**

Using goss (ARM64 binary) for infrastructure testing — ports, services, files, HTTP endpoints. Runs in 4 seconds. 40/40 passing.

**Current state:**
- Uptime: stable, 1d 14h at last check
- All 13 containers up/healthy
- RAM: 2.0GB used / 3.9GB total
- Temp: 47°C
- SSD: 6.2GB / 229GB used

**Everything is open:**

Docker Compose files, systemd units, goss tests, monitoring scripts, architecture decisions (ADR), and the agent prompts used during development:

👉 https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano

The repo also has a GitHub Pages site with architecture docs:
👉 https://alexeyborovskoy.github.io/NAS_Jetson_Nano/

---

## Comments to prepare

**If asked about Docker version:**
> Docker 20.10.7 — locked by JetPack 4.x. It's outdated and contains known CVEs. Upgrading is non-trivial because of NVIDIA runtime dependencies. For a home lab I've accepted this risk; it's documented as a known limitation.

**If asked about monitoring:**
> Beszel Hub on the VPS for historical CPU/RAM/disk/network graphs on both servers. Uptime Kuma for HTTP uptime checks. Netdata for real-time. Daily Telegram report at 09:00. JMS583 hourly health monitor posts alerts on USB errors.

**If asked about backup:**
> pg_dump daily at 03:00 to /mnt/storage/backups with 7-day rotation. Off-site backup (restic to a 2TB HDD) is next on the list — scripts are ready, waiting for the HDD to arrive.
