# Project checkpoint 2026-10-05 — Vostro bastion restored

> Russian original — `CHECKPOINT_2026-10-05.ru.md`. Previous checkpoint — `CHECKPOINT_2026-10-02.md`.
> The owner's workstation was in the office that day (`192.168.75.126`; CLAUDE.md still says `.137`).

## 1. Repository state

| Branch | Commit | Where | State |
|---|---|---|---|
| `main` | `668734e` | GitHub | unchanged since 04.10 |
| `fix/vostro-tunnel-pick-address` | this checkpoint on top of `ffa1794` | worktree `E:/nas-fix-vostro-tunnel`, GitHub | deployed on Vostro, **not merged into `main`**, not published to GitVerse |
| `feat/vpn-monitor-2026-10` | `f3c19a0` | main checkout, GitHub (first pushed 05.10) | VPS/VPN monitor: tasks 1–3 of 8 in git |

**Not in git** (on disk in the main checkout, branch `feat/vpn-monitor-2026-10`) — task 4 in progress:
- `services/vpn_monitor/vpnmon_query.py` (73 lines) and `tests/vpn_monitor/test_report_text.py` (141 lines).
  The test imports the not-yet-written `vpnmon_render` and **fails at collection**, so a commit on this
  branch will not pass the hook until task 4 is finished;
- edits to the plan `docs/superpowers/plans/2026-10-04-vps-vpn-monitor.md` (+12/−5) and to both specs (one line each);
- `artifacts/nas-dp1-socket-proxy-arm64.tar` (20 MB, DP-1 image) — not to be committed.

## 2. Done on 05.10

| What | How verified |
|---|---|
| **The Vostro→VPS tunnel (`10222`) had been down since 26.09 19:48 MSK.** The office ISP drops new flows to `95.163.176.103` (:22 and :443 time out) while `193.8.215.130` passes; the host key is the same (`SHA256:u+rTLGiv…`). `autossh` with the hard-coded new address made ≈8390 attempts while the unit stayed `active (running)`. Diagnosed by `work` (m0228), confirmed by my own measurement | `bash </dev/tcp` from Vostro; `ssh-keyscan` of the old address matched `known_hosts` |
| **Fix:** drop-in `10-pick-address.conf` → `/usr/local/sbin/nas-offsite-tunnel.sh`. On every start it probes both addresses and `exec`s `ssh -R 10222` to the first that answers; `Restart=always`, `RestartSec=30`; the VPS key is pinned as `HostKeyAlias=nas-vps` instead of `accept-new`. Base unit untouched. Commit `436508e` | journal: `95.163.176.103 unreachable → 193.8.215.130 reachable`; VPS `127.0.0.1:10222` LISTEN; `ssh vostro-bastion hostname` → `alexey-Vostro-15-3568`; SOCKS via the bastion to `192.168.75.120:8080` → `401`; ssh killed at 09:07:07, back at 09:07:43 |
| **Rule 13:** VPS unchanged | `amnezia-*` StartedAt `2026-10-04T05:27:49Z` and `restarts=0` before and after, **21** peers before and after, identical set of listening sockets |
| **HOST_CONTRACT.md on Vostro:** appended section "Изменено 05.10.2026" with rollback | sections 44 → 45, append only, backup `HOST_CONTRACT.md.bak-20261005-tunnel` |
| **Fallback aliases on the workstation:** `vps-nas-alt`, `vostro-bastion-alt`, `jetson-via-vps-alt` on `193.8.215.130` (`HostKeyAlias 95.163.176.103`). Backup `~/.ssh/config.bak-20261005-alt`. Commit `ffa1794` (bastion doc) | all three connect from Git Bash and Windows OpenSSH over the direct route (Ethernet, bypassing the VPN) |
| **Board:** m0229 (answer to m0228 + notes on §3 of the `work` package), m0230 (correction), m0231 (fact for `atc`); m0217, m0223 resolved | `coord.py` returned `OK` |

**Retracted the same day:**
- "restic holds only snapshot `ab975984` from 24.08" — a misreading: I looked at the tail of the `forget`
  output. Snapshots are made daily, the latest is `8dd7cee7` on 05.10 04:02.
- in m0229 I wrote "SOCKS chain verified" when only the SSH login had been checked. Checked right after
  (`401`) and corrected in m0230.

## 3. Found and not fixed

- 🟠 **The nightly backup on Vostro depends on a single `VPS_HOST`.** It works now (05.10 04:02 OK while the
  new address is blocked, so `/opt/nasa/config/.env` on Vostro holds the old one). The next flip of the block
  will break it. Fix: the same address picking as the tunnel.
- 🟠 **Vostro has `PasswordAuthentication yes`.** With the tunnel up, any local process on the VPS can
  brute-force the `alexey` password via `127.0.0.1:10222`. This is `work`'s zone, change only on the owner's
  word; proposed (m0229): `Match Address 127.0.0.1,::1` → `PasswordAuthentication no` + `KbdInteractiveAuthentication no`.
- 🟡 **`restic forget` on Vostro never deletes anything.** Each run stages dumps in a random
  `/tmp/nas-offsite-pull.XXXX`; restic groups by paths, so every group holds one snapshot. About 10 MB/day.
  Fix: `--group-by host,tags` or a fixed staging directory.
- 🟡 The VPS has `ClientAliveInterval 0`: after a hard client drop the `10222` listener may linger ~2 h and
  block reconnection. The owner has ruled out VPS changes for now — record only.
- ℹ️ `amnezia-*` on the VPS restarted on **2026-10-04 05:27 UTC** — not by us, cause not investigated.
  21 peers (CLAUDE.md says 19).
- ℹ️ Detector tunnels `18765/18766` are not listening on the VPS — likely the same block; the detector
  project's zone, `work` is aware.

## 4. Next

1. Owner's decision: merge `fix/vostro-tunnel-pick-address` into `main` and publish to GitVerse.
2. VPS/VPN monitor: finish task 4 (`vpnmon_render`), then 5–7; rollout (task 8) only on "deploy".
3. Vostro backup — VPS address picking like the tunnel (section 3, first item).
4. Board: `m0158` (Vostro shared-use rules) still unanswered.
5. Unchanged since 02.10: rollout of the audit stages on the Jetson waits for "deploy".
