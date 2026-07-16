---
layout: default
title: Architecture
---

# Architecture

## Overview

```
[Smartphone / browser / app]
        |
        | HTTPS / HTTP
        v
   [VPS — Europe]
   nginx (Docker)
   :8443 Nextcloud
   :2443 Immich
   :9443 LLM
   :8099 NAS_Jetson_Nano API
        |
        | reverse SSH tunnel (autossh, Restart=always)
        v
[Jetson Nano — LAN]
   Nextcloud    :8080
   Immich       :2283
   LLM Gateway  :8090
   NAS_Jetson_Nano API     :8099
   Samba        :445  (LAN only)
   Netdata      :19999
   Uptime Kuma  :3001
   Portainer    :9000
        |
        | USB 3.0, 5 Gbps
        v
[JMS583 SSD 229 GB — /mnt/storage]
```

## Key decisions

### Reverse SSH instead of WireGuard

WireGuard requires DKMS — incompatible with Tegra kernel 4.9.  
Tailscale conflicts with an existing VPN on Android devices.  
`autossh` with `Restart=always` works through CGNAT with no external dependencies and no kernel modules.

### Self-signed TLS instead of Let's Encrypt

Let's Encrypt requires a domain name. Current workaround: self-signed TLS on alt-ports (:8443, :2443, :9443) with 10-year validity and the server IP in SAN.  
Planned migration: add a domain, switch to Caddy + Let's Encrypt automatic certs.

### USB SSD with quirk mode

JMS583 (chip 152d:a583) works reliably only in BOT (Bulk-Only Transport) mode, not UAS.  
Kernel parameter: `usb-storage.quirks=152d:a583:u`  
Without quirk: write 8 MB/s. With quirk: Write **250 MB/s**, Read **172 MB/s**, zero USB errors.

### No swap

Jetson Nano 4 GB LPDDR4 — no swap configured (eMMC wear concern).  
This eliminates some Docker images: Zabbix needs 500+ MB just for PostgreSQL.  
Chosen stack: lightweight images with explicit `mem_limit` per container.

## Docker Compose files

| File | Services |
|---|---|
| `docker-compose.nextcloud.yml` | Nextcloud, MariaDB, Redis |
| `docker-compose.immich.yml` | Immich server, microservices, Redis, PostgreSQL |
| `docker-compose.monitoring.yml` | Netdata, Uptime Kuma, Portainer, Beszel Agent |
| `docker-compose.nas_jetson_nano-api.yml` | NAS_Jetson_Nano API (FastAPI) |
| `docker-compose.llm.yml` | LLM Gateway |

All services write to `/mnt/storage` (USB SSD).  
Startup is blocked until storage preflight passes (`scripts/storage/storage_preflight.sh`).

## Storage layout

```
/mnt/storage/
├── nextcloud/data/      — user files, contacts, calendars
├── immich/library/      — photo/video archive
├── mariadb/             — Nextcloud database
├── immich-postgres/     — Immich database
└── backups/             — local backup snapshots
```

## VPS role

The VPS only runs nginx as a reverse proxy and autossh for the tunnel.  
It does not store data. It does not run Nextcloud or Immich.  
Amnezia VPN containers on the VPS serve ~25 family VPN clients — they must not be touched.

---

[← Back to index](../index.md) | [Reliability →](reliability.md)
