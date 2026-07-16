# r/JetsonNano — Post

**Subreddit:** r/JetsonNano  
**Type:** Text post  
**Attach image:** `02_beszel_jetson_metrics.png`

---

## Title

> Jetson Nano 4GB as a home server — JMS583 UAS quirk, 13 Docker containers, 40 goss tests, everything documented

---

## Post body

Turned my Jetson Nano into a family home cloud server. Sharing the Jetson-specific lessons since most of the pain was platform-specific.

**The stack:**
- Nextcloud + Immich + Samba + LLM Gateway + custom REST API
- 13 Docker containers, all up/healthy
- Access via reverse SSH tunnel through VPS (CGNAT, no WireGuard — incompatible with Tegra kernel 4.9)

**Jetson-specific constraints that shaped every decision:**

**1. No swap.** This is the hard one. Eliminated Zabbix (PostgreSQL alone needs 500+ MB), OpenMediaVault, and several monitoring stacks. Solution: `mem_limit` on every container + `restart: always`.

**2. Docker 20.10.7 locked by JetPack.** Can't upgrade without breaking NVIDIA runtime. Old but functional for home use.

**3. ARM64 image availability.** Some images don't have ARM64 builds. Switched to `crazymax/samba` for Samba, used `pgvecto-rs:pg16` for Immich's PostgreSQL. Check `docker pull` before planning your stack.

**4. Tegra kernel 4.9.** WireGuard requires DKMS — not available. DKMS modules in general are risky. Stick to userspace solutions.

**USB SSD — the JMS583 fix:**

First enclosure used RTL9210B-CG. USB autosuspend + Tegra kernel 4.9 = disconnect every few days, `error -71` in dmesg. Even with `usbcore.autosuspend=-1` it eventually degraded to 40 MB/s.

Replaced with **JMS583 (chip 152d:a583)**. Critical kernel parameter:

```
# /boot/extlinux/extlinux.conf — add to APPEND line:
usb-storage.quirks=152d:a583:u usbcore.autosuspend=-1
```

Flag `u` = disable UAS, use BOT (Bulk-Only Transport) instead.  
Without quirk: **8 MB/s write** (UAS broken on Tegra 4.9).  
With quirk: **250 MB/s write, 172 MB/s read**. Zero errors in dmesg for weeks.

Also add udev rule to raise SCSI timeout:

```bash
# /etc/udev/rules.d/99-usb-storage-timeout.rules
ACTION=="add", SUBSYSTEMS=="usb", DRIVERS=="usb-storage", \
  ATTR{../../../bInterfaceProtocol}=="50", \
  RUN+="/bin/sh -c 'echo 120 > /sys$$devpath/../../../timeout'"
```

**Monitoring on ARM64:**

- **goss v0.4.9** — ARM64 binary available, 40 tests, runs in 4 seconds
- **Netdata** — has ARM64 image, works great, shows Jetson CPU/GPU temp
- **Beszel agent** — ARM64, reports to Hub on VPS
- **Uptime Kuma** — ARM64 OK

**Temperature:** sitting at 47°C under normal load (13 containers). Passive cooling fine.

**RAM:** 2.0GB used / 3.9GB total at steady state with everything running.

Full repo with Docker Compose, systemd units, goss tests, scripts:  
👉 https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano

---

## Comments to prepare

**If asked about GPU usage:**
> Maxwell GPU is not used by the stack — no CUDA workloads. Immich ML is disabled (`IMMICH_DISABLE_MACHINE_LEARNING=true`) because it would OOM without swap. LLM Gateway routes to DeepSeek API, not local inference.

**If asked about the USB quirk applying to other chips:**
> The `u` flag disables UAS for that specific VID:PID. For other chips: RTL9210B-CG is `0bda:9210`, ASM1153E is `174c:55aa`. Check `lsusb` for your chip's ID and try the same flag if you're seeing UAS issues on Tegra kernel.
