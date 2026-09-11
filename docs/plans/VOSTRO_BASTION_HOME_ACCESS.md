# Vostro bastion: home / Jetson → corporate resources

> 2026-09-11 · reverse SSH already live · **Amnezia on VPS not modified**

## Goal

Use personal **Dell Vostro 15** (`192.168.75.153`, corp LAN) as the **only jump host**
into resources that this laptop can already reach (DNS/TCP from Vostro).

```
Home (Wi‑Fi or Ethernet) or Jetson  →  VPS 95.163.176.103:22  →  127.0.0.1:10222  →  Vostro:22  →  corp
```

## Home Wi‑Fi vs LAN — where you can connect from

| Where you are | Path to Vostro bastion | Need Amnezia? |
|---------------|------------------------|---------------|
| **Home Wi‑Fi** (`TP-Link_828C` / `_5G`, same router as Jetson) | Internet → VPS:22 → jump `:10222` | **No** for SSH bastion (only keys + `ssh vostro-bastion`) |
| **Home Ethernet** LAN `192.168.0.0/24` | Same as Wi‑Fi (egress via CGNAT to VPS) | **No** for bastion |
| **Mobile / any internet** | Same: VPS:22 → `:10222` | **No** for bastion |
| **Corp LAN** `192.168.75.0/24` | Direct `ssh alexey@192.168.75.153` | N/A |
| Family apps Nextcloud/Immich via VPS service ports | VPS ufw allows only VPN subnets | **Yes** Amnezia (separate from bastion) |

**Short answer:** family home Wi‑Fi is enough. Bastion does **not** require being on Jetson LAN cable and does **not** require Amnezia — it only needs reachability of `95.163.176.103:22` and the SSH keys.  
Home Wi‑Fi and home Ethernet are equivalent for this path (both leave via the same ISP/CGNAT).

**Does not work without the tunnel:** phone/PC on home Wi‑Fi cannot open `192.168.75.153` directly (different building/network).

## Already deployed (verified)

| Piece | State |
|-------|--------|
| Vostro `nas-offsite-tunnel.service` | **active** — `autossh -R 10222:localhost:22 root@95.163.176.103` |
| VPS listen | **`127.0.0.1:10222`** only (not public) |
| Jetson reverse | `10022` → Jetson SSH (unchanged) |
| Amnezia (`amnezia-awg2`, `amnezia-xray`) | **untouched** |
| Jump key | `id_ed25519_nas_vostro_admin` (operator + Jetson `admin`) |
| Tunnel key on Vostro | `~/.ssh/id_ed25519_nas_offsite` |

### Live test 2026-09-11

- Windows → ProxyJump VPS → Vostro: **OK** (`alexey-Vostro-15-3568`)
- Jetson → VPS:10222 → Vostro: **OK**
- From Vostro: `rserver3` → `192.168.57.1:22` open; local Belgorod gateways `:8772` / `:8774` open

## Operator SSH (Windows)

Keys (local, not in git):

- `~/.ssh/borovskoy_new_ed25519` — VPS root
- `~/.ssh/id_ed25519_nas_vostro_admin` — Vostro `alexey`

```sshconfig
Host vps-nas
  HostName 95.163.176.103
  User root
  IdentityFile ~/.ssh/borovskoy_new_ed25519

Host vostro-bastion
  HostName 127.0.0.1
  User alexey
  IdentityFile ~/.ssh/id_ed25519_nas_vostro_admin
  ProxyCommand ssh -i ~/.ssh/borovskoy_new_ed25519 -W 127.0.0.1:10222 vps-nas
```

```powershell
ssh vostro-bastion
# one corp TCP via local forward example:
ssh -L 18443:192.168.57.1:22 vostro-bastion
# SOCKS for browser/agent (traffic exits Vostro):
ssh -D 11080 vostro-bastion
```

## Jetson

`~/.ssh/config.d/vostro-bastion` + key `id_ed25519_nas_vostro_admin`:

```bash
ssh vostro-bastion 'hostname; getent hosts rserver3'
```

Script: `scripts/network/test_vostro_bastion_from_jetson.sh` (copy to device when needed).

## Safety

1. **Do not** restart/edit Amnezia containers or `wg set` on VPS.
2. **Do not** publish `10222` on `0.0.0.0` / open ufw to the world.
3. Only resources already reachable **from Vostro** (same rights as sitting at the laptop).
4. Do **not** push whole `192.168.75.0/24` into family Amnezia.
5. `HOST_CONTRACT.md` on Vostro is source of truth for ports — append only.

## Rollback

```bash
# on Vostro — stops bastion path (restic channel too)
sudo systemctl stop nas-offsite-tunnel.service
# optional: disable
# sudo systemctl disable nas-offsite-tunnel.service
```

VPS: nothing to uninstall if reverse drops; `10222` disappears when tunnel stops.

## Related

- ADR-0005 Jetson reverse tunnel
- `docs/plans/VOSTRO_ML_NODE_ONBOARDING.md` (historical ML; bastion is separate)
- Checkpoint 2026-08-24 (tunnel + restic bootstrap)
