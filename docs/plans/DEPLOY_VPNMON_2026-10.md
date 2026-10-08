# VPS/VPN Monitor — Deployment Runbook (VPS)

> Acceptance 2026-10-06: tasks 1–7 are ready locally; task 8 has not been executed. Commands below require a separately authorized deployment. Reading VPN counters requires explicit owner authorization for strictly read-only collection; the prohibition on changing Amnezia remains. The safety snapshot uses only `docker inspect` and `ss`; the peer count is recorded by a trial sample before the rollout (step 2) and checked after it (step 10) — it must not decrease; the owner may additionally cross-check in Amnezia Desktop. Historical examples with 21 peers are dated measurements, not today's guarantee.
>
> Token transfer uses `sudo -n`, never a Nextcloud password. If the operator lacks approved non-interactive sudo access to the source file, stop and arrange access with the owner. An incomplete stream does not replace the existing token on the VPS. Rollback stops only this monitor and preserves its database and configuration.
>
> Delivery persists acknowledged chunks across runs. Lost Telegram acknowledgements can cause duplicates; exactly-once is not guaranteed. The 240-second budget controls admission of attempts; systemd terminates the process after 300 seconds. `Persistent=true` catches up the latest report day, not every missed day.

> **Date:** 2026-10-07 · **Status:** ready to deploy; deployment happens only after the owner's word «деплой» (deploy)
> Preparation 07.10: outside variant of step 6 through the tunnel, peer count by measurement, no rollout.
> **Basis:** task 8 of the plan `docs/superpowers/plans/2026-10-04-vps-vpn-monitor.md` (EN — `…-monitor.en.md`);
> spec `docs/superpowers/specs/2026-10-04-vps-vpn-monitor-design.ru.md` §10–11 (EN — `…-design.md`).
> Russian pair — `DEPLOY_VPNMON_2026-10.ru.md`.

## 1. Status and rules

- The rollout is performed by the **lead only** (rule №16): the VPS is a critical zone; neither
  a subagent nor the DeepSeek executor takes this task.
- The commands in the steps are shown **for a future deployment with the owner's explicit
  permission**; this document itself is not that permission.
- Before the start and after the finish — rule №13 snapshots (before/after, command in step 2).
- Nothing irreversible: this runbook deletes no data. A full uninstall of the accounting
  (units, code, directories) is not part of it — see §8.

## 2. What the rollout does

It installs load accounting on the VPS — **observation only**, no rate limits and no blocks:

- `nasa-vpnmon-collect.timer` — every 60 s, samples `awg0` peer counters and host metrics
  (read-only) into the SQLite DB `/var/lib/nasa-vpnmon/vpnmon.db`;
- `nasa-vpnmon-report.timer` — at 10:00 MSK, sends the owner a daily summary in Telegram;
  the installer enables this timer only if `/etc/nasa-vpnmon/telegram.env` exists.

Not touched: Amnezia containers and configs, ufw, iptables, routes, sshd, nginx, Docker.
No new ports, packages or users; nothing new is exposed outward (spec §9).

## 3. Prerequisites

- The code of plan tasks 1–6 is merged into the deployment branch; the workstation is on this
  repository.
- Access from the workstation: `root@95.163.176.103`, key `~/.ssh/borovskoy_new_ed25519`.
- Step 6 (token transfer) has two variants (rule №17): **6a** — from the home network, direct
  ssh to the Jetson, `admin@192.168.0.50`, same key; **6b** — from outside, through the Jetson
  reverse tunnel (alias `jetson-via-vps`; rule №17 allows the VPS path only from outside).
- ISPs alternately block the two VPS addresses (CLAUDE.md «Грабли», 2026-10-05): if
  `95.163.176.103` times out, in every command replace `root@95.163.176.103` with
  `-o HostKeyAlias=95.163.176.103 root@193.8.215.130` (same host key; `accept-new` is forbidden),
  and use the alias `jetson-via-vps-alt` instead of `jetson-via-vps`. Alias reference —
  `docs/plans/VOSTRO_BASTION_HOME_ACCESS.md`.
- The file `/etc/nasa-monitor/telegram.env` is in place on the Jetson (the same bot and
  `chat_id` as the Jetson daily report).

## 4. Deployment steps (1–10)

- [ ] **Step 1: the code on the VPS, into a temporary directory**

```bash
cd "e:/Linux mint/virtual_VM/shared/NAS_Jetson_Nano"
tar -C services --exclude=__pycache__ -czf - vpn_monitor | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'umask 077; test ! -e /root/vpnmon-src && mkdir /root/vpnmon-src && tar -C /root/vpnmon-src -xzf - && ls /root/vpnmon-src/vpn_monitor'
```

- [ ] **Step 2: rule 13 snapshot "before"**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | tee /root/vpnmon-rule13-before.txt'
```
As a second command — record the peer count by measurement (a number only, no identifiers):
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'set -o pipefail; cd /root/vpnmon-src/vpn_monitor && python3 collect.py --dry-run --names /nonexistent | tail -1 > /root/vpnmon-peers-before.txt && grep -E "^peers=[1-9][0-9]*$" /root/vpnmon-peers-before.txt'
```
Expected: a single line `peers=N` (a number only, no identifiers); no output or `awg: недоступен`
(awg unavailable) means STOP.
Snapshot: `amnezia-awg2`/`amnezia-xray` running, peers=N recorded; among the listeners exposed
outward (`0.0.0.0`/`[::]`) only 22, 443, 40568/udp and the previous service ports.

- [ ] **Step 3: trial sample with no write, cross-checked against `wg`**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'cd /root/vpnmon-src/vpn_monitor && python3 collect.py --dry-run --names /nonexistent; echo ---; docker exec amnezia-awg2 wg show awg0 transfer | sort -k3 -n | tail -3 | cut -c1-8,44-'
```
Expected: the last line `peers=N` equals the value from step 2; for the top three by `tx` the values match `wg show` (allowing for the
seconds between the commands); `awg: rx=… tx=…`, `wan`, `xray` are not "нет".
⚠️ The `--dry-run` output prints key prefixes and names — do not copy it into chats or
documents (see §7).

- [ ] **Step 4: installation**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/install_vps.sh'
```
Expected: `nasa-vpnmon-collect.timer` appears in the timer list; the message
«таймер отчёта НЕ включён» (report timer NOT enabled) — no token yet.

- [ ] **Step 5: `names.conf` — six unnamed peers**

From the output of step 3, take the key prefixes for `10.8.1.17` (Vostro) and `10.8.1.18`–`.22`
(«запасной-1»…«запасной-5» in ascending address order) and write them on the VPS. The values
never get into git.

Phones were re-added to the VPN on 2026-10-07: if step 3 shows unnamed peers ("?") in a number
other than six, or addresses other than `.17`–`.22`, do not guess — ask the owner for the names
and write only what the owner says. Real names and key prefixes never go to git, chats or task
cards.
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'umask 077; cat > /etc/nasa-vpnmon/names.conf' <<'EOF'
<префикс .17> = Vostro
<префикс .18> = запасной-1
<префикс .19> = запасной-2
<префикс .20> = запасной-3
<префикс .21> = запасной-4
<префикс .22> = запасной-5
EOF
```
The lead replaces the `<префикс …>` placeholders with the real prefixes from step 3 at execution time.

- [ ] **Step 6: the token from the Jetson to the VPS without printing it**

**6a. From the home network** (rule №17). First check that the file is in place on the Jetson
and that sudo is available without a password:
```bash
ssh -o BatchMode=yes admin@192.168.0.50 'ls -l /etc/nasa-monitor/telegram.env && sudo -n true && echo sudo-ok'
```
Expected: the file is listed and `sudo-ok`; otherwise STOP, do not guess passwords.
Then transfer the two lines through a pipeline: the value goes from the Jetson's stdout to the
VPS's stdin and is never printed anywhere.
```bash
set -o pipefail
ssh -o BatchMode=yes admin@192.168.0.50 'sudo -n grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /etc/nasa-monitor/telegram.env' \
  | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'set -e; umask 077; tmp=$(mktemp /etc/nasa-vpnmon/telegram.env.XXXXXX); trap '\''rm -f "$tmp"'\'' EXIT; cat > "$tmp"; grep -q "^TELEGRAM_BOT_TOKEN=." "$tmp"; grep -q "^TELEGRAM_CHAT_ID=." "$tmp"; chmod 600 "$tmp"; mv "$tmp" /etc/nasa-vpnmon/telegram.env; echo 2'
```
Expected: `2`.

**6b. From outside, through the Jetson reverse tunnel** (rule №17 allows the VPS path only from outside). First the same pre-check through the alias `jetson-via-vps`:
```bash
ssh -o BatchMode=yes jetson-via-vps 'ls -l /etc/nasa-monitor/telegram.env && sudo -n true && echo sudo-ok'
```
Expected: the file is listed and `sudo-ok`; otherwise STOP, do not guess passwords.
Then the same transfer through a pipeline:
```bash
set -o pipefail
ssh -o BatchMode=yes jetson-via-vps 'sudo -n grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /etc/nasa-monitor/telegram.env' \
  | ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'set -e; umask 077; tmp=$(mktemp /etc/nasa-vpnmon/telegram.env.XXXXXX); trap '\''rm -f "$tmp"'\'' EXIT; cat > "$tmp"; grep -q "^TELEGRAM_BOT_TOKEN=." "$tmp"; grep -q "^TELEGRAM_CHAT_ID=." "$tmp"; chmod 600 "$tmp"; mv "$tmp" /etc/nasa-vpnmon/telegram.env; echo 2'
```
Expected: `2`.

- [ ] **Step 7: test message and enabling the report**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 /usr/local/lib/nasa-vpnmon/report.py --test && systemctl enable --now nasa-vpnmon-report.timer && systemctl list-timers --all "nasa-vpnmon-*" --no-pager'
```
Expected: `проверка: доставлено` (test delivery succeeded); the owner sees the 🧪 message;
the next report run — 10:00 MSK.

- [ ] **Step 8: after 5 minutes — data in the DB and resource usage**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 -c "import sqlite3; d=sqlite3.connect(\"/var/lib/nasa-vpnmon/vpnmon.db\"); print(\"host\", d.execute(\"select count(*), sum(samples) from host_hourly\").fetchone(), \"peers\", d.execute(\"select count(*) from peers where removed_at is null\").fetchone())"; systemctl show nasa-vpnmon-collect.service -p CPUUsageNSec -p MemoryPeak -p Result; journalctl -u nasa-vpnmon-collect -n 5 --no-pager; ls -l /var/lib/nasa-vpnmon /etc/nasa-vpnmon'
```
Expected: active peers >= N from step 2, `samples` ≥ 4; `Result=success`; `MemoryPeak` < 64 MB; files 0600,
directories 0700.

- [ ] **Step 9: the report for the current day to screen**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'python3 /usr/local/lib/nasa-vpnmon/report.py --stdout --day $(TZ=Europe/Moscow date +%F)'
```
Expected: all blocks of the §7 layout; the six peers named via `names.conf`; "Не подключались
с ДД.ММ" — today's date.

- [ ] **Step 10: rule 13 snapshot "after"**

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | diff /root/vpnmon-rule13-before.txt - && echo "правило 13: без изменений"'
```
As a second command — compare the active peer count with the step 2 measurement:
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'b=$(cut -d= -f2 /root/vpnmon-peers-before.txt); a=$(cd /root/vpnmon-src/vpn_monitor && python3 collect.py --dry-run --names /nonexistent | tail -1 | cut -d= -f2); echo "пиров: до=$b после=$a"; [ -n "$b" ] && [ -n "$a" ] && [ "$a" -ge "$b" ] && echo "пиры: не уменьшилось"'
```
Expected: both `правило 13: без изменений` (rule 13: unchanged) and `пиры: не уменьшилось`
(peers did not decrease); otherwise STOP, roll back (§8) and investigate.

⚠️ Difference from the plan (task 8): the cleanup command `rm -rf /root/vpnmon-src` is
deliberately not run here — the source copy on the VPS stays as a fallback path for recovery
and relaunch. Removing the temporary directory is a separate action, not part of the rollout.

## 5. After the rollout (11–12)

- [ ] **Step 11: documentation and publication**

- The monitor code is already in `main` (merged before 06.10). Merge the branch with this
  preparation into `main` if not yet merged (`git merge --ff-only`) and publish per the
  rule №15 procedure.
- `CLAUDE.md` + `CLAUDE.en.md`: a table row for VPN accounting (units, report time); the peer
  count is the measurement from step 2 (`peers=N`), not the historical 21; VPS downtime
  04.10 04:55–05:27 UTC; a new checkpoint.
- No family announcement is needed: only the owner sees the report (rule №18 concerns what
  the family can see).

- [ ] **Step 12: the next day at 10:00 MSK**

The real report has arrived; the owner confirms. If the owner wishes — a volume cross-check:
download 100 MB through the VPN on a known device, then `report.py --stdout --day <today>`
shows a growth of about 100 MB (±5 %) for that client.

## 6. Verification

| When | What we check | Expected |
|---|---|---|
| Step 2 | Rule №13 "before" and peer count | `amnezia-*` running, `peers=N` recorded (a number only), outward only 22/443/40568/udp and the previous service ports |
| Step 3 | Parsing matches `wg` | the last line `peers=N` equals step 2, the top by `tx` agree, `wan`/`xray`/`awg` are not "нет" |
| Step 4 | Installation | `nasa-vpnmon-collect.timer` listed; the report timer still disabled |
| Step 7 | Telegram channel | `проверка: доставлено`; the 🧪 message reaches the owner; next run 10:00 MSK |
| Step 8 | Writing and resources | active peers >= N from step 2, `samples` ≥ 4, `Result=success`, `MemoryPeak` < 64 MB, modes 0600/0700 |
| Step 9 | Report text | All §7 blocks; six peers named via `names.conf` |
| Step 10 | Rule №13 "after" and peer count | `правило 13: без изменений` and `пиры: не уменьшилось` — otherwise stop and roll back |
| +1 day | The real report | A message at 10:00 MSK; the owner confirms |
| On request | Volume cross-check | 100 MB through the VPN → ≈100 MB (±5 %) growth for the client |

## 7. Risks and privacy

- 🔴 **The telemetry contains peer names and public keys.** The DB `/var/lib/nasa-vpnmon/vpnmon.db`,
  the file `/etc/nasa-vpnmon/names.conf`, the `collect.py --dry-run` output and the report table
  contain people's names and their key prefixes. Rules: do not print real identifiers to stdout
  longer than necessary; do not copy them into chats, commits, documents or task cards; diagnose
  by counters (as in step 8) rather than by dumping the DB contents.
- **Token.** `/etc/nasa-vpnmon/telegram.env` — root, 0600; step 6 transfers it through a
  pipeline without printing the value. Check the mode with `ls -l`, not `cat`.
- **Rule №13.** Before and after the rollout: `amnezia-*` were not restarted, the peer count
  did not decrease, only the previous ports listen outward. Any discrepancy — stop and roll back.
- **Observation only.** No rate limits, no blocks; the collector calls `docker` only with
  `exec` (the constant read script) and `inspect`; `dump`/`showconf` are forbidden and checked
  by a test (spec §8).
- **`amnezia-awg2` being unavailable** does not distort accounting: the minute is flagged with
  an `awg_unavailable` event, host metrics keep being written, peers are not marked removed.
- **No secrets in git:** only `names.conf.example` and `telegram.env.example` without values
  enter the repository.
- The report goes only to the owner's personal chat; no family announcement is needed (step 11).

## 8. Safe rollback

The rollback **disables this monitor?s timers and stops its running services**. Data and configuration are kept: the hourly rows and
events in `/var/lib/nasa-vpnmon/vpnmon.db`, the names in `/etc/nasa-vpnmon/names.conf`.
Nothing is deleted: neither the DB, nor the config, nor the code, nor the units. The VPN is
not touched.

```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'systemctl disable --now nasa-vpnmon-collect.timer nasa-vpnmon-report.timer; systemctl stop nasa-vpnmon-collect.service nasa-vpnmon-report.service; systemctl list-timers --all "nasa-vpnmon-*" --no-pager; bash /root/vpnmon-src/vpn_monitor/rule13_snapshot.sh | diff /root/vpnmon-rule13-before.txt - && echo "правило 13: без изменений"'
```
Expected: the timers are disabled and both monitor services are inactive, `правило 13: без изменений`.

The same peer-count check as in step 10:
```bash
ssh -i ~/.ssh/borovskoy_new_ed25519 root@95.163.176.103 'b=$(cut -d= -f2 /root/vpnmon-peers-before.txt); a=$(cd /root/vpnmon-src/vpn_monitor && python3 collect.py --dry-run --names /nonexistent | tail -1 | cut -d= -f2); echo "пиров: до=$b после=$a"; [ -n "$b" ] && [ -n "$a" ] && [ "$a" -ge "$b" ] && echo "пиры: не уменьшилось"'
```

- Re-enabling when needed (no history is lost):
  `systemctl enable --now nasa-vpnmon-collect.timer nasa-vpnmon-report.timer`.
- A full uninstall (units `/etc/systemd/system/nasa-vpnmon-*`, code `/usr/local/lib/nasa-vpnmon`,
  config `/etc/nasa-vpnmon`, DB `/var/lib/nasa-vpnmon`) is **not performed** by this runbook —
  it is a separate owner decision, and even then keeping the DB and `names.conf` is recommended:
  without the DB all accounting history is lost irreversibly.
- ⚠️ The plan (task 8) contains a fuller rollback variant, up to deleting the directories.
  This runbook deliberately does not apply it: irreversible deletion of accounting data is not
  part of a rollback.
