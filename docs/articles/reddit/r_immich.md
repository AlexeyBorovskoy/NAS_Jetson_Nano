# r/Immich — Post

**Subreddit:** r/Immich  
**Type:** Text post  
**Attach image:** `07_immich_web_redacted.png` or `06_android_clients_card_redacted.png`

---

## Title

> Running Immich on Jetson Nano 4GB (ARM64, no swap) — 6,700 photos, Android auto-backup working, ML disabled

---

## Post body

Sharing my setup in case it helps others running Immich on constrained hardware.

**Hardware:** NVIDIA Jetson Nano 4GB, ARM64, no swap (eMMC wear concern). USB SSD 229GB via JMS583 enclosure.

**The key flag:**

```yaml
IMMICH_DISABLE_MACHINE_LEARNING=true
```

Without this, Immich tries to load face/object recognition models at startup. On 4GB without swap it OOMs and crashes. With it: everything else works perfectly.

**Current numbers:**
- 6,697 photos and videos uploaded from family phones (5 people)
- 6,484 photos + 210 videos in the library (3 files rejected — corrupted/duplicates)
- 4.24 GB library size
- Android auto-backup active and stable

**Android (Xiaomi MIUI/HyperOS quirks):**

MIUI aggressively kills background processes. Without these steps, backup silently stops:
1. Battery → App power usage → Immich → No restrictions
2. Security → Auto-start → enable for Immich
3. Lock Immich in recent apps (swipe-hold to pin)

**HTTPS for Android auto-backup:**

Immich Android requires HTTPS for auto-backup. No domain = self-signed cert with IP in SAN:

```bash
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -subj "/CN=nas-jetson-nano" \
  -addext "subjectAltName=IP:YOUR_VPS_IP,IP:192.168.x.x" \
  -out nas_jetson_nano.crt -keyout nas_jetson_nano.key
```

Accept the cert once in the app → auto-backup works normally.

**mem_limit:**

```yaml
immich_server:         mem_limit: 1024m
immich_microservices:  mem_limit: 512m
immich_db:             mem_limit: 384m
immich_redis:          mem_limit: 64m
```

Stable for weeks with these limits.

**Access:** reverse SSH tunnel through VPS (CGNAT, no port forwarding). LAN URL configured separately in Immich Android settings for faster local backup when on WiFi.

Full setup: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano

---

## Comments to prepare

**If asked about ML in the future:**
> Planning to test enabling ML selectively — run a job overnight when the system is idle and nothing else is writing to SSD. Haven't tried yet. If anyone has done this on 4GB ARM64, I'd love to know the mem usage.

**If asked about performance:**
> Upload speed is fine — limited by WiFi, not Jetson. Browsing the library is responsive. Video thumbnails take a second to generate (no ML = no GPU acceleration for that either). Acceptable for a home setup.
