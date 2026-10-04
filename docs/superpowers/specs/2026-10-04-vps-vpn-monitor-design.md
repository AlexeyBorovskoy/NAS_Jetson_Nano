# VPS Load and VPN User Traffic Accounting — Specification

> **Date:** 2026-10-04 · **Status:** approved by the owner in full on 2026-10-04
> **Basis:** the owner's request of 04.10 ("summary information on VPS load and the network activity
> of each user"), the prompt `claude_amnezia_vps_monitoring_prompt.md` (outside git), a read-only
> VPS audit 2026-10-04 16:38 UTC.
> Russian version — `2026-10-04-vps-vpn-monitor-design.ru.md`.

## 1. Why

Once a day the owner receives a summary in their personal Telegram: how the VPS lived (CPU, memory,
disk, network, downtime) and how much traffic passed through the VPN for each user over the day, 7 and
30 days, who is online now and who has been silent for a long time. Observation only: no rate limits,
no blocks.

## 2. Owner's decisions (2026-10-04)

| Question | Decision |
|---|---|
| Where to look | **Telegram only, one report a day.** No web panel, no Grafana, no on-demand report, no real-time alerts |
| Who sends | **Option B — the VPS sends it itself**, independent of the Jetson. A permanent file with the bot token appears on the VPS |
| Design and accounting | Parts 1–2 below were approved in chat: "plan accepted" |

Rejected, with the reason: the Prometheus + Grafana + cAdvisor + node_exporter stack from the prompt.
On a VPS with 1 vCPU and 1.9 GB without swap it would have taken, by estimate (not measurement),
350–500 MB, duplicates Beszel and is not needed for one text message a day. Option C (Prometheus
without Grafana) — 150–250 MB for the same thing.

## 3. Initial state (measured 2026-10-04 16:38 UTC, read-only)

- VPS: Ubuntu 24.04.4, kernel 6.8, KVM (Aeza), **1 vCPU, 1967 MB RAM, no swap**, 30 GB disk (27 %),
  time zone `Etc/UTC`, Python 3 present, Docker 29.1.3. Load is almost zero (id 92–98 %).
- `amnezia-awg2`: interface `awg0`, subnet `10.8.1.0/24`, UDP 40568, **21 peers**; inside the container
  there are `wg` and `awg`; `clientsTable` gives a name for 15 peers. The six unnamed ones are the
  manual peers of 25.08: `.17` (Vostro) and `.18–.22` (spares).
- `amnezia-xray`: VLESS/Reality on 443, 11 clients. **The config has no `stats`, `api`, `policy`, and
  the clients have no `email`** → per-user xray accounting is impossible without editing the config and
  restarting. In 11 h ~18 MB passed through the container versus ~24 GB through `awg0`.
- Amnezia containers: `privileged`, `LogDriver=none`, `bridge` network.
- Monitoring already exists: Beszel hub (:8091) and the VPS agent (:45877) — a snapshot of the host and
  the containers.
- WireGuard counters live in kernel memory and are reset when the container or the VPS restarts.
- **2026-10-04 04:55:49–05:27:38 UTC the VPS was shut down by the hypervisor**
  (`qemu-ga: guest-shutdown`, `hypervisor initiated shutdown`): the VPN was down for 32 min. These data
  do not distinguish the initiator (the owner's panel or provider maintenance).

## 4. Boundaries

Not doing: per-user xray accounting (only the container's total traffic); connection counts and
destinations per client (conntrack in the container namespace is not readable, and this is a privacy
question); a web interface; real-time alerts; any traffic limits.
Not touching: Amnezia containers and configs, firewall, routes, sshd, Docker. No new ports.

## 5. Design (part 1, approved)

```
VPS
├─ nasa-vpnmon-collect.timer   every 60 s → /usr/local/sbin/nasa-vpnmon-collect.py  (root)
│     unit limits: CPUQuota=20 %, MemoryMax=64M, Nice=10, TimeoutStartSec=30
│     ├─ docker exec amnezia-awg2 <permanent read script>      — one exec per run
│     ├─ docker inspect amnezia-awg2 / amnezia-xray            — StartedAt, RestartCount, Pid
│     ├─ /proc/<pid awg2>/net/dev                              — awg0 counters, no exec
│     ├─ /proc/<pid xray>/net/dev                              — xray container traffic, no exec
│     ├─ /proc/stat, /proc/meminfo, /proc/loadavg, statvfs("/"),
│     │  /proc/net/dev (WAN), nf_conntrack_count, /proc/sys/kernel/random/boot_id
│     └─ SQLite /var/lib/nasa-vpnmon/vpnmon.db  (0600, WAL)
└─ nasa-vpnmon-report.timer    10:00 Europe/Moscow, Persistent=true
      → /usr/local/sbin/nasa-vpnmon-report.py → Telegram sendMessage to the owner
        unit: TimeoutStartSec=300 (> 3 attempts × 10 s + pauses 30/60 s = 120 s)
        token and chat_id: /etc/nasa-vpnmon/telegram.env (root, 0600)
        names of unnamed peers: /etc/nasa-vpnmon/names.conf (root, 0600, outside git)
```

Code — `services/vpn_monitor/` (`collect.py`, `report.py`, a shared storage module, `install_vps.sh`,
units), tests — `tests/vpn_monitor/`. Python 3.12 standard library only (`sqlite3`, `zoneinfo`,
`urllib`); `apt`/`pip` are not needed.

**The permanent read script inside `amnezia-awg2`** — a constant string in the code, with no
substitutions: `wg show awg0 allowed-ips; echo @@; wg show awg0 transfer; echo @@; wg show awg0
latest-handshakes; echo @@; cat /opt/amnezia/awg/clientsTable`. 🔴 `wg show … dump` (prints preshared
keys) and `wg showconf` (prints the private key) are forbidden — this is checked by a test against the
source.

## 6. Accounting (part 2, approved)

- **Difference from the previous sample.** A reset is detected if the counter decreased, or `boot_id`
  or the container's `StartedAt` changed; then the difference is taken as the current value. There are
  no negative numbers or "petabytes" after a reboot.
- **Storage is by UTC hour** per user: received, sent, peak per-minute rate. The Moscow day (UTC+3, no
  daylight saving time) is assembled from whole hours. Retention — 400 days (~10 MB per year by
  estimate); purging happens during the report run.
- **Rate** = difference / the actual interval between samples. If the interval is longer than 5 min
  (a collection gap), the bytes are counted but the rate for that interval is not.
- **"Last seen online"** — the maximum of all observed `latest-handshake` values; it survives resets.
  **"Online now"** — a handshake younger than 180 s.
- **"Never connected"** is written honestly: "has not connected since monitoring began DD.MM".
- **Silence:** > 7, > 30, > 90 days since the last handshake.
- **A removed peer** keeps its history under the last known name and is marked `removed_at`.
- **Name:** `clientsTable` → `names.conf` (key prefix = name) → "key abcd1234". If `clientsTable`
  cannot be parsed, the previous names are kept.
- **VPS by hour:** average and peak CPU (from the `/proc/stat` difference over a minute), peak used
  memory (`MemTotal − MemAvailable`), peak load1, disk usage, WAN traffic, `awg0` and xray container
  traffic, peak conntrack. WAN and xray container traffic includes both legs (client ↔ VPS and
  VPS ↔ internet), so it is roughly twice the user traffic; in the report it is labelled as container
  traffic, not user traffic. User traffic — only the `awg0` peer counters.
- **Events:** a `boot_id` change → "the VPS was down from … to …" (the last sample of the old boot →
  `btime` of the new one) and a reason line from `journalctl -b -1`, if there is one; a restart of the
  `amnezia-*` containers; collection gaps; an undelivered report.
- **Privacy:** client addresses (endpoint), connection destinations and DNS are neither read nor
  stored.

### DB schema

| Table | Contents |
|---|---|
| `peers` | `pubkey` PK, `name`, `vpn_ip`, `first_seen`, `last_handshake`, `removed_at` |
| `peer_state` | the latest raw `rx`, `tx`, `ts`, `boot_id`, `started_at` per peer |
| `peer_hourly` | (`pubkey`, `hour_utc`) PK, `rx`, `tx`, `peak_bps` |
| `host_state` | the latest raw host counters (CPU, WAN, xray, `boot_id`, `StartedAt`) |
| `host_hourly` | `hour_utc` PK, `samples`, `cpu_sum`, `cpu_max`, `mem_max`, `load_max`, `disk_pct`, `wan_rx`, `wan_tx`, `awg_rx`, `awg_tx`, `xray_rx`, `xray_tx`, `conntrack_max` |
| `events` | `ts`, `kind`, `detail` |
| `meta` | `schema_version`, `monitoring_start`, `last_report_ok` |

One collector run is one transaction: on error nothing is written.

## 7. Report (part 3 — for review)

Sent at 10:00 MSK for the Moscow day that has passed; the 7- and 30-day windows are the last full days,
ending with yesterday. The format is HTML (`<pre>` for the table), all names are escaped.
Mock-up (numbers are illustrative):

```
📡 VPN and VPS — 04.10 (MSK)

VPS ✅  CPU avg 3 % · peak 41 %  ·  RAM peak 610 / 1967 MB  ·  disk 27 %
VPS network: ↓ 24.6 GB  ↑ 25.9 GB  ·  conntrack peak 900
⚠️ Downtime 07:55–08:27 (32 min): hypervisor initiated shutdown
↻ amnezia-awg2, amnezia-xray — started 08:27 (together with the VPS)

AmneziaWG: 21 clients · were online 7 · now 5
Through the tunnel per day: ↓ 23.4 GB ↑ 0.9 GB · xray container: 18 MB

Client              day   7 d   30 d   peak
Name-1          15.3 GB  15.3   15.3   48 Mbit/s
Name-2           3.2 GB   3.2    3.2   21 Mbit/s
…
Silent: >7 d — 3 · >30 d — 2 · >90 d — 0
Never connected since 05.10: 10 — Name, Name, …
Collection: 1438 of 1440 min
```

- Client rows — everyone who had traffic during the day, in descending order; the rest as summary
  rows.
- The Telegram limit is 4096 characters: if exceeded, a second message rather than truncation.
- If yesterday's report did not arrive, the first line is: "⚠️ the report for DD.MM was not
  delivered".

## 8. Failures and self-checks (part 4 — for review)

| Failure | Behaviour |
|---|---|
| `amnezia-awg2` is not running or `docker exec` did not answer within 10 s | event "awg2 unavailable", peer accounting for that minute is skipped (not zeroes), host metrics are still written |
| `clientsTable` cannot be parsed | the previous names are kept |
| SQLite error | exit with code ≠ 0, in the systemd journal; the transaction is rolled back |
| Time went backwards / interval ≤ 0 | the difference is not counted, the sample becomes the new reference point |
| Telegram does not answer | 3 attempts (`timeout` 10 s, pause 30/60 s), then a `report_failed` event and a line in the next report |
| The VPS is off at 10:00 | `Persistent=true`: the report is sent after it powers on |
| The collector did not run | "Collection: N of 1440 min" in the report |

The collector **never** runs anything inside the containers except the permanent read script; `docker`
is invoked only with `exec` (that script) and `inspect`.

## 9. Security and rule #13 (part 5 — for review)

- Root is needed for `docker exec`; the unit limits keep the collector from taking CPU away from the
  VPN.
- The token is `/etc/nasa-vpnmon/telegram.env` (root, 0600). It is transferred from the Jetson over
  SSH in a single command without printing the value (the same bot and `chat_id` as the daily report).
  Only `*.example` goes into git. The script calls only `sendMessage` and does not affect `getUpdates`
  of the main bot.
- The DB and `names.conf` are 0600; people's names and keys never go into git.
- No new ports; `ss -tlnpu` before and after installation must match.
- **Rule #13 during installation and rollback:** before and after — `StartedAt`/`RestartCount` of
  `amnezia-*` unchanged, the number of peers in `wg show awg0 peers` has not decreased, and only the
  previous ports listen externally.

## 10. Testing (part 6 — for review)

**Unit tests, without a VPS** (`tests/vpn_monitor/`, in `preflight.sh` and CI like the other
services): parsing the output of `wg show` and `clientsTable` (fixtures without real keys); an ordinary
difference; a counter decrease; a `boot_id` change; a container restart; a peer appearing and
disappearing; the Moscow day boundary (21:00 UTC); the silence thresholds; "has not connected since
monitoring began"; escaping names (`Admin [Windows 11 …]`, `<b>`); splitting a long report; an empty
day; a static test: the source has no `dump`, `showconf`, `private`, and `docker` is invoked only with
`exec`/`inspect`.

**Live, on the VPS (the lead):** `collect.py --dry-run` (prints the parsed data, does not write to the
DB) matches `wg show awg0 transfer`; after 5 min there are rows in the DB; `report.py --stdout` for the
current day; `report.py --send --test` — one message delivered; `systemctl status` shows the CPU and
memory spent per run; after a day — the first real report. At the owner's discretion — a volume check:
download 100 MB over the VPN on a known device and find it in the hourly row (±5 %).

## 11. Deployment, rollback, executors

- **Deployment:** `install_vps.sh` installs the scripts and units, creates the directories, enables the
  timers; the token and `names.conf` are separate steps by the lead. Rule #13 checks before and after.
- **Rollback:** `systemctl disable --now nasa-vpnmon-collect.timer nasa-vpnmon-report.timer`, remove
  the units, `/usr/local/sbin/nasa-vpnmon-*`, `/etc/nasa-vpnmon`, `/var/lib/nasa-vpnmon`. The VPN is
  not affected.
- **Executors (rule #16):** implementation per the plan — a Sonnet subagent (TDD); the English pair of
  the specification and the runbook — DeepSeek; installation on the VPS, token transfer, live checks
  and acceptance — the lead only (the VPS is a critical zone).
- After deployment: update `CLAUDE.md` (21 peers, the 04.10 downtime, the new unit) in the RU/EN pair.

## 12. Owner's answers to the open questions (2026-10-04)

1. Peers `.18–.22` in `names.conf` — **"spare-1" … "spare-5"**; `.17` — "Vostro".
2. Report time — **10:00 MSK** (`OnCalendar=*-*-* 10:00:00 Europe/Moscow`).
3. Chat — **the same personal one** that receives the Jetson daily report (the same `TELEGRAM_CHAT_ID`).
