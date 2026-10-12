# Vostro bastion: home / Jetson → corporate resources

> 2026-09-11 · reverse SSH already live · **Amnezia on VPS not modified**

## Goal

Уточнение владельца 2026-10-10: Vostro — общий стенд для различных тестовых
решений в корпоративной сети, а не рабочий компьютер пользователя.
Существующие службы соседних проектов и HOST_CONTRACT сохраняют силу.

### Проверка и исправление — 2026-10-10

Из домашней Deco-сети проверены Windows→VPS→Vostro и Windows→VPS→Jetson.
На Jetson основной VPS `95.163.176.103` не отвечал, резервный `193.8.215.130`
работал. Для `vostro-bastion` установлен ProxyCommand
`/home/admin/.ssh/nas-vostro-proxy.sh` из `scripts/network/ssh_vostro_proxy.sh`:
TCP-проба каждого адреса ограничена 6 с; затем SSH проверяет существующий ключ
VPS под `HostKeyAlias=95.163.176.103`, `StrictHostKeyChecking=yes`.
Добавлен явный `vps-nas-alt`. Jetson→Vostro успешно проверен командой hostname.
Пробы TCP не гарантируют успешного SSH handshake; при обрыве установленного
соединения требуется новое подключение. Обратные туннели и Amnezia не менялись.
Откат: вернуть `~/.ssh/config.d/vostro-bastion.before-fallback-20261010` на Jetson;
копию сохранить, пока исправление используется.

На Vostro восстановлена `systemd-backlight@leds:dell::kbd_backlight.service`
(Result=success после записи допустимой яркости и restart). Драйвер после этого
снова показывает 3 при max=2: устранение причины в драйвере не доказано, повторение
после перезагрузки остаётся риском. Для casper-md5check добавлен drop-in
`10-installed-system.conf` с ConditionPathExists=/cdrom/md5sum.txt: без ISO
проверка корректно пропускается. Изменения записаны в HOST_CONTRACT с откатом.

**Уточнённое решение владельца 2026-10-10: Mac исключён только из NAS.** Соседний
проект вправе его использовать. NAS ошибочно остановил и отключил его
belgorod-mac-ollama-tunnel.service и belgorod-local-llm-warm.timer; после уточнения
обоим возвращены enabled и запуск. Исправление записано в HOST_CONTRACT.
Владелец подтвердил, что Mac выключен или вне рабочей сети: URLError и ошибки
mDNS ожидаются до его возвращения. Запущенный туннель не доказывает доступность
модели. Новый провайдер не подключался; конфигурация моделей, ключи и алиас сохранены.
Все четыре боевых gateway/bot службы и nas-offsite-tunnel после исправления active.

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
| Vostro `nas-offsite-tunnel.service` | **active** — since 2026-10-05 via drop-in `10-pick-address.conf` → `/usr/local/sbin/nas-offsite-tunnel.sh`: `ssh -R 10222:localhost:22` to the first reachable VPS address (see below) |
| VPS listen | **`127.0.0.1:10222`** only (not public) |
| Jetson reverse | `10022` → Jetson SSH (unchanged) |
| Amnezia (`amnezia-awg2`, `amnezia-xray`) | **untouched** |
| Jump key | `id_ed25519_nas_vostro_admin` (operator + Jetson `admin`) |
| Tunnel key on Vostro | `~/.ssh/id_ed25519_nas_offsite` |

### Outage 2026-09-26 → 10-05 and the address picker

The office ISP drops new flows to **one** of the two VPS addresses, and which one flips:
on 02.09 it was the old `193.8.215.130`, from 26.09 the new `95.163.176.103`. The unit ran
`autossh` with the fixed new address and retried it ~8390 times; `10222` was gone and with it
the bastion (the nightly backup was not affected: it uses `VPS_HOST`). The same flip hit the
Jetson from the home ISP on 18–26.09.

Fix (2026-10-05, base unit untouched): `systemd/nas-offsite-tunnel.service.d/10-pick-address.conf`
points `ExecStart` at `scripts/setup/nas-offsite-tunnel.sh`, which probes `95.163.176.103:22`,
then `193.8.215.130:22` (TCP, 6 s) and `exec`s plain `ssh -N -R 10222:localhost:22` to the
first one that answers; `Restart=always`, `RestartSec=30` re-probe on every restart. The VPS
host key (the same on both addresses) is pinned as `nas-vps` in Vostro's `known_hosts`, and
the wrapper connects with `HostKeyAlias=nas-vps`, `StrictHostKeyChecking=yes`.

Verified 05.10: `193.8.215.130` picked, `127.0.0.1:10222` listening on the VPS,
`ssh vostro-bastion hostname` → `alexey-Vostro-15-3568`; ssh killed at 09:07:07, back at
09:07:43. Rollback: delete the drop-in, `daemon-reload`, restart (record in Vostro
`HOST_CONTRACT.md`, section of 05.10).

The client leg has the same exposure: the `vps-nas` alias is pinned to `95.163.176.103`.
Under AmneziaVPN that address is routed inside the tunnel and works regardless; without VPN
a flip on the client's ISP breaks it. Since 2026-10-05 the operator config has `-alt` twins on
`193.8.215.130` (see «Operator SSH»): if `vps-nas` times out, use the same command with `-alt`.

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

# 2026-10-05: fallback on the other address of the same VPS. The host key is the
# same, so it is verified against the 95.163.176.103 record (HostKeyAlias).
Host vps-nas-alt
  HostName 193.8.215.130
  User root
  HostKeyAlias 95.163.176.103
  IdentityFile ~/.ssh/borovskoy_new_ed25519

Host vostro-bastion-alt
  HostName 127.0.0.1
  User alexey
  HostKeyAlias vostro-bastion
  IdentityFile ~/.ssh/id_ed25519_nas_vostro_admin
  ProxyCommand ssh -i ~/.ssh/borovskoy_new_ed25519 -W 127.0.0.1:10222 vps-nas-alt
# jetson-via-vps-alt: the same pattern with -W 127.0.0.1:10022
```

Verified 2026-10-05 from the office workstation over the direct (non-VPN) route, with both
Git Bash ssh and Windows OpenSSH: `vps-nas-alt`, `vostro-bastion-alt`, `jetson-via-vps-alt` → OK.

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
