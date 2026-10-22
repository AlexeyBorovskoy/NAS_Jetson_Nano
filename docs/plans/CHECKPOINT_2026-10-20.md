# Checkpoint — 2026-10-20

[Русский](CHECKPOINT_2026-10-20.ru.md) · [Previous checkpoint](CHECKPOINT_2026-10-19.md)

## OBS-1 two-hour acceptance — October 22

The two-hour observer completed with `accepted=true`, Result=success / exit 0:
121 samples / 7,200.053 s, CPU 2.5665%, VmHWM peak 22.3008 MiB, cgroup peak
35.9883 MiB, heartbeat age max 11 s. It added 6,984 fast, 119 minute, and 158
process snapshots; PID/restarts stayed unchanged, with `failcnt` delta 0. The
process `write_bytes` delta was 59,826,176 B; the SSD partition counter delta was
181,403,648 B and includes other writers. Neither delta establishes the ≤60 MB/day
target or measures NAND writes; do not extrapolate the two-hour window. The separate
24-hour observer began October 22 08:48:22 UTC and is expected to end October 23
around 08:48:22 UTC. Its result and UTC-midnight transition are pending.

## OBS-1 resource fix — October 22, 10:35 MSK

Verified commit **`b21b81c13e61d5254d7f73c724c6c8ab3e8be307`** is installed:
`store.py` uses low-memory XZ preset 0 and skips an unchanged SQLite cursor.
Heartbeat and metric-flush intervals remain 10 seconds; the database schema is
unchanged. The previous 32 smoke assertions and a separate lossless 8 MiB
round-trip under `RLIMIT_AS=64 MiB` passed on Python 3.6.9. Source, installer
state and manifest are preserved in `.agent-work/archives/obs1-resource-before-20261022/`;
only the collector changed. SMART, VPS/VPN and family containers were untouched.

The two-hour observer `nas-obs1-resources-20261022T073511.service` ran from
**07:35:16 to 09:35:16 UTC** and completed successfully: 121 samples / 7,200.053 s,
`accepted=true`, observer Result=success / exit 0. CPU averaged **2.5665% of one
core**; VmHWM peak was **22.3008 MiB**, cgroup peak **35.9883 MiB**, and maximum
heartbeat age **11 s**. It added **6,984 fast**, **119 minute**, and **158 process
snapshots**; PID 1200 and restart count 0 stayed unchanged, with cgroup `failcnt`
delta 0.

Over those two hours, process `write_bytes` increased **59,826,176 B** and the SSD
partition counter **181,403,648 B**. The partition counter includes other writers
and is not NAND wear. Neither two-hour delta establishes the **≤60 MB/day** target;
do not extrapolate it to a day.

At October 22 07:18 UTC, pre-fix `memory.stat` showed **32.046875 MiB cache**
and **15.734375 MiB anonymous RSS**. Separate reads gave `memory.failcnt=2106`
and `under_oom=0` from `memory.oom_control`; the latter describes that moment only.
This is a current snapshot, not a breakdown of the historical maximum. A 64 MiB
cgroup peak does not establish a Python leak or OOM: file cache is accounted too,
and failcnt records limit hits followed by reclaim
([kernel documentation](https://www.kernel.org/doc/Documentation/cgroup-v1/memory.txt)).
XZ memory cost is reproducible, but the earlier VmHWM timestamp was not recorded.

The SSD filesystem block and SQLite page are both **4096 bytes**; heartbeat
size is **141 logical / 4096 allocated bytes**. Assuming one WAL page per
nonempty metric flush plus one new heartbeat block every 10 seconds gives a
conditional lower estimate of **70,778,880 bytes/day** (70.8 MB), before
checkpoints, other tables, metadata or NAND amplification. This is a calculation
under stated assumptions, not a measured day. Repeated cursor writes were not
the only cause. Keeping the ≤60 MB/day target needs separate storage work while
preserving the agreed ten-second unsynced-data-loss window.

The additional read-only observer `nas-obs1-soak24-20261022.service` started
**October 22 08:48:22 UTC / 11:48:22 MSK**: 289 samples every 300 seconds,
at least 86,400 seconds, expected to finish **October 23 around 08:48 UTC / 11:48 MSK**.
It crosses UTC midnight without subtracting counters from different daily DBs.
PID/boot identity and counter monotonicity are checked. Whole SSD partition writes
include other writers and are not NAND bytes. The run is in progress; no result is assumed. Observer
limits: Nice19, CPUQuota5%, MemoryMax64M, RuntimeMaxSec87000; only a temporary
diagnostic unit was added.

Before deployment, isolated process measurements showed:

- Synthetic 8 MiB journal: default LZMA reached **106,676,224 bytes RSS peak**;
  preset 0 reached **18,759,680 bytes**. Compression took 4.244 → 0.856 s;
  archive size was 703,404 → 806,804 bytes; both round-trip SHA checks matched.
- A saved prior-day journal was read only on the Jetson: decoded size 397,589
  bytes; separate-process peaks **34,775,040 → 16,023,552 bytes**; archive
  size 28,784 → 35,896 bytes; round-trip matched. Raw lines and hashes were
  neither printed nor transferred. This reproduces encoder cost, not the exact
  whole-collector peak at the earlier moment.
- An accelerated synthetic workload equivalent to one scheduled hour, using
  temporary databases inside the project, changed `write_bytes` from
  **25,694,208 → 14,688,256 bytes**. Most cursor saves repeated in this scenario,
  so its saving must not be generalized to live traffic. After the change, the
  main remaining component is metric flush, about **10.6 MB per virtual hour**;
  the **≤60 MB/day** SSD target remains open. No larger unsynced-data-loss window
  was introduced.

Local runtime pre-commit passed; blackbox Windows reported **317 passed / 6
skipped**. The bounded-memory Linux regression failed on the original code with
`MemoryError` and passed on the fix. An extended WSL run reported **366 passed**;
one unrelated watchdog SSH-key-mode check failed because POSIX `chmod` is
unavailable on DrvFs, while the corresponding Windows suite passed. This
environment failure is recorded, not hidden or fixed by changing the app.

DeepSeek received only a synthetic API contract in an isolated `--bare`,
Write-only call; it returned DSML text instead of executing Write. The draft was
extracted and independently checked red/green by the lead, then manually
accepted. Cost: **$0.0346**, one attempt, zero retries, 0% cache hit; earlier
costs are excluded. The worker copy/branch was removed after cleanliness checks;
the card and trace remain in the local `ds_board`.

The article prototype and editorial materials are being updated through October
22; dated Word copies are maintained separately from the October 10 sources.
Live observer results will be added after the full interval completes.


## Verified state — October 22, 2026, 09:48 MSK

Checked through the existing `jetson-via-vps-alt` tunnel; VPS/VPN, family
containers, originals and SMART were unchanged. Earlier entries retain history.

- The October 21 **14:11:59–15:11:59 UTC** OBS hour completed: 61 measurements,
  3600.058 s, `accepted=true`, observer Result=success / exit 0. Mean CPU
  **2.604% of one core**, VmHWM **20.875 MiB**, cgroup peak **28.0195 MiB**,
  maximum heartbeat age **11 s**; **3491 fast**, **59 minute**, **82 distinct
  process snapshots** added; PID 4991 and restart count 0 unchanged.
- **Longer-term OBS acceptance remains open.** At October 22 06:48 UTC PID 4991
  was still running without restarts, heartbeat age 4 s, current RSS 24.06 MiB,
  but cumulative VmHWM **43.89 MiB** exceeded the 40 MiB target. Cgroup current
  51.61 MiB, peak **64 MiB**. These values establish neither OOM nor its cause.
- Process `write_bytes`: **632,123,392 bytes** over about 16 h 37 min since
  startup; OBS file tree **45,500,462 bytes**, fallback 0. Process write count,
  occupied space and physical NAND writes differ. The accepted-hour write delta
  was **37,408,768 bytes**, versus **10,992,557 bytes** of file-tree growth.
  The specification's **SSD ≤60 MB/day** budget is unverified; examine WAL,
  flush/retention and memory peaks. An extrapolation is not a measured day.
- All 39 runtime files plus `nas_layout.py` matched `2f4edaa`; four installed
  units and current boot/snapshot matched; three SQLite quick checks passed.
  Last 600 s: 575 fast samples with all checked sensor fields present,
  10 minute rows and 197 process rows.
- Scheduled archive service completed October 22 05:30 UTC with success / exit 0;
  next trigger **October 23 05:30 UTC / 08:30 MSK**. A successful invocation
  does not prove creation of an archive if no week was eligible. Isolated
  synthetic SSD→HDD acceptance had passed. `nas-why --boot -1 --short` exits 0
  with expected unknown; heartbeat fresh; synthetic stale/cooldown checks passed
  without sending messages.
- Immich at **October 22 06:47:50 UTC / 09:47 MSK**: no new cgroup/global OOM
  over the window starting **October 20 21:00 UTC / October 21 midnight MSK**;
  restart count **1820, delta 0**, healthy; nightly missing-thumbnail generation
  remains false. Three backup jobs successful, copies **2.25–3.65 hours** old.
  Two quiet overnight windows do not prove a permanent fix or complete DR.
- General read-only check October 22 09:55 MSK: **16 containers** running,
  all with healthchecks healthy. The sole failed unit is the historical
  `nasa-hdd2tb-selftest.service`, deliberately not reset. MemAvailable 1680 MiB;
  SD root 43% used, SSD 20%. This is a state snapshot, not a load test.

Next: (1) review the 24-hour observer after it completes; the ≤60 MB/day SSD
target remains open until separately confirmed over a full day; (2) separate
copied TIFF/PSD and one-asset family ML pilots on direct home LAN; (3) targeted
commits for outstanding SMART/docs and preparation for linear OBS integration;
(4) author revision using current facts.
Isolated DR and rotation of formerly published family passwords remain open:
completion evidence was not found. No merge/push was performed.

OBS RU/EN runbooks and implementation plan were locally committed as **`f4b9ed7`**
on `feat/obs1-blackbox`; its worktree is clean. The real pre-commit passed:
36 regression checks, all service suites (blackbox 314 passed / 5 skipped),
metrics ratchet without exceptions. Two quick-mode warnings: local ShellCheck
unavailable and Compose config skipped. Runtime remains `2f4edaa`; main is still
`c8c151f`, with outstanding uncommitted SMART/documentation changes.

Evidence is local-only under `.agent-work/tmp/obs1-deploy-20261021/`:
`observe-result-host.json`, `status-host.json`, `runtime-details-host.json`,
`hooks-check-host.json`, `immich-after-observation.json`, `hour-observation.png/.svg`.
General state snapshot: `project-health-20261022.json`.
These are field data, not a public package or DeepSeek input. Read-only checks:
`systemctl show nas_jetson_nano-blackbox.service -p ActiveState -p MainPID
-p NRestarts -p Result`; `sudo nas-why --boot -1 --short`. Runtime configuration
was unchanged by this audit; the existing OBS rollback procedure is retained.
Root `ds_worker.toml` was not modified.

## Completed block

The owner requested continuation of the accepted queue. SMART installation still
required working sudo. Overnight, Immich restarts increased **1432 → 1820 (+388)**.
At 08:59 Moscow time it was healthy, last started at 06:32:59 Moscow time.

**At 09:10:52 Moscow time (06:10:52 UTC), changed only
`nightlyTasks.missingThumbnails` from true to false via the official API.**

Before the change, the API confirmed missingThumbnails=true, midnight start,
thumbnail concurrency=3, library scanning=false. The existing configured API key
was used locally on Jetson, never printed or sent externally.

The utility rereads configuration before PUT and refuses to overwrite a detected
concurrent change. Full configuration after PUT matched the original with only
the intended flag changed. This is a double-read check, not an atomic server-side
lock; a concurrent admin write between GET and PUT remains theoretically possible.
An independent GET confirmed false; the database stores the false override.
Repeating --disable performed no PUT.

All **1007 failed** thumbnail jobs were preserved (811 yesterday); active, waiting,
delayed and paused counts were zero before/after. Other inspected queues were empty.
Immich remained healthy at 1820 restarts; the container watchdog succeeded with
exit status zero. No container restarts or archive modifications were performed.
Both disks responded. Today's database backup, configuration backup and Immich
HDD copy succeeded at 06:13, 06:46 and 07:38 Moscow time respectively.

**Overnight effectiveness remains unverified.** Check after midnight on October 21
Moscow time for new cgroup OOM events, restart count, service health and backup
freshness. Manually started heavy jobs can still exceed the 1 GB limit. No TIFF/PSD
processing was retried and no memory limit was raised.

## Files, validation and rollback

- `scripts/immich/nightly_thumbnails.py`: default read-only display; --disable
  changes one flag; --restore restores only that flag while preserving unrelated
  newer configuration. HTTP stays on localhost without proxies/redirects. Keys
  and error response bodies are not printed. Host Python 3.6 and installed SHA-256
  verified: `d00d431b5062592e11608099875c39caef0943123bddf5c28b351da2bbea40ea`.
- `tests/unit/test_immich_nightly_thumbnails.py`: seven synthetic tests cover
  read-only default, narrow mutation, input preservation/validation, idempotence,
  concurrent modification, narrow rollback and failed post-write verification.

```sh
python tests/unit/test_immich_nightly_thumbnails.py
python scripts/quality/code_metrics.py --check docs/audit/2026-10-02_code_audit/baseline.json --summary
python scripts/quality/repo_hygiene.py --staged
```

All passed. New files were added individually to the index before the metrics
check; hygiene reported 665 entries and zero violations. Eight focused SMART tests
also passed again. Utility/tests are staged, with **no commits or pushes**. Existing
owner edits to `ds_worker.toml` and yesterday's changes were preserved.

The rollback record contains only the prior boolean and timestamp, no credentials
or full configuration; permissions 0600, owner admin:
`.agent-work/archives/immich-nightly/nightly-thumbnails-20261020T061052Z-32136.json`.

A local wrapper reads the configured API key only into process memory:

```sh
python3 /home/admin/nasa/.agent-work/tmp/immich-nightly-session-20261020.py --inspect
# Restores the problematic nightly task; not executed automatically:
python3 /home/admin/nasa/.agent-work/tmp/immich-nightly-session-20261020.py --restore /home/admin/nasa/.agent-work/archives/immich-nightly/nightly-thumbnails-20261020T061052Z-32136.json
```

## Remaining work and executors

SMART remains undeployed: the running unit still targets `/dev/sdb`, its previous
failure remains recorded, and sudo requires a password. The prepared October 19
package is intact. No new credential search/guessing, sudo bypass or installation
was attempted. Working sudo/root access is required.

Next: observe the next night, then a controlled workstation pilot for heavy formats;
retain failed jobs and avoid bulk thumbnail recovery on Jetson. Subsequently resume
OBS-1 task 6 and SEC-3 with owner involvement.

DeepSeek prepared the utility/tests (`data_class=project-own`), task
`nas-immich-nightly-toggle-20261020`. No actual host configuration, logs, family data
or API key was shared. Codex lead reviewed the diff, corrected two fixtures missing
the third GET, disabled proxy/redirect behavior, added the rollback record path,
and performed deployment/verification. The worker hit its turn limit; independently
checked files were manually accepted. Cost **$0.082457**, one attempt, zero automatic
retries, **97.04%** cache hits.

## Continuation of items 1–5: monitoring, workstation and OBS-1

The read-only night observer and synthetic tests are prepared. A daytime probe
at 06:42 UTC found a healthy container, 1,820 restarts (zero delta), and no new
OOM after the flag change; this is **not next-night evidence**. Review findings
were fixed: default six-hour minimum window, a retained current-boot kernel
record before the window, StartedAt validation and a final repeated inspect.
Twelve synthetic tests, metrics and hygiene pass. Host Python validation and a
07:00:26 UTC daytime probe found the same 1,820 restarts, zero delta/OOM, flag
false and three fresh backups. That daytime run explicitly disabled the minimum
window; the scheduled night check requires six hours. A retained lower-bound
journal record cannot exclude every possible internal journal gap.

Windows one-shot task `NAS-Immich-NightCheck-20261021` is registered for October 21,
08:15 MSK / 05:15 UTC. Its window starts October 20 at 21:00 UTC, baseline 1,820.
It uses the interactive owner's token without storing a password and requires an
available workstation, Windows login and SSH. StartWhenAvailable permits delayed
execution but cannot guarantee evidence. Runner:
`.agent-work/tmp/run-immich-night-probe-20261021.ps1`; JSON output:
`.agent-work/tmp/immich-night-20261021.json`. Existing `not_due` is a daytime
mechanism check only. Rollback: unregister that task with
`Unregister-ScheduledTask -TaskName NAS-Immich-NightCheck-20261021 -Confirm:$false`.

Docker Desktop and the pinned CUDA ML image now work locally. `immich_ml_rog`
is healthy and bound to localhost. Synthetic `buffalo_l` detection/recognition
with CUDA returned zero faces: 21.434 seconds cold, 0.269 seconds warm. No family
quality or TIFF/PSD performance claim follows. No tunnel or NAS ML configuration
change was made; direct home LAN remains unavailable. See the updated bilingual
station runbook for evidence and local rollback. SMART still requires working sudo.

OBS-1 task 6 was implemented by DeepSeek and independently verified: 15 targeted
tests, 122 Linux tests across tasks 1–6 in isolated read-only/no-network Docker.
Working branch `feat/obs1-blackbox` was rebased onto current main; commit `13ab315`
passed the normal commit hooks after providing the missing SDK in a temporary
environment. No merge or push. Task 7 is being implemented by DeepSeek; OBS-1 is
not deployed. Its initial draft passed 16 tests but was rejected after review
found SQLite/WAL cap, resumable migration, deep-redaction and disk-delta defects.
DeepSeek is revising it; no draft or unverified revision was installed on NAS.
New task costs will be recorded after acceptance.

Article evidence and article plan now distinguish the outage causes, deployed
HDD guard, unverified overnight effectiveness, synthetic ML readiness and pending
SMART/photo-library/OBS-1 work. No publication. An independent subagent reviewed
station safety, code and article wording.

### Correction of executor input classification

The lead incorrectly included the original OBS-1 plan/specification in tasks
classified as project-own. Those documents mix interfaces with actual device
measurements and incident descriptions, contrary to the owner's field/proprietary
boundary. Local transcript audit confirms the collector read the plan and the
boot-snapshot task read both documents. That completed reading cannot be undone;
the blanket claim that these tasks received only code/synthetic inputs is invalid.

The collector, bootsnap and rules DeepSeek processes were stopped and their
cards marked CANCELLED. Native subagents now continue the work. Mixed original
documents must not be resent; future external delegation requires a separately
sanitized contract and a fresh session. Local path-only audit:
`.agent-work/tmp/ds-input-audit-20261020.json`. It does not establish the absence
of other data from automatically loaded CLI context.

The night observer was accepted after 12 tests and live read-only validation:
three attempts cost $0.244203, 98.62% cache hits. At interruption, the October 20
worker report recorded $0.624065 including prior tasks. Interrupted unfinished
runs may not be accounted for, so this is not a final billing total. Native
subagent dollar usage is not separately available here. The lead reviews all work.

### October 21 continuation: tunnel and local OBS-1 integration

The owner authorized OBS-1 and diagnostics over the existing tunnel; working
sudo/root and home LAN will be provided later. Attempts around 10:36–10:39 MSK
timed out connecting to the VPS SSH proxy before reaching Jetson. No VPS shell,
Amnezia/VPN changes or remote writes occurred. The 08:15 scheduled night check
produced no new report; a bounded retry saved `unavailable` at 07:38:57 UTC,
SSH exit 255. This does not demonstrate an OOM-free night. The runner now also
limits connection time in the inner SSH proxy.

OBS-1 tasks 7–13 are locally integrated in `feat/obs1-blackbox`: collector,
fallback ring, boot/heartbeat association, supervised archive, evidence/rules
CLI, D2/OPS-1, units and rollback installer. Native subagents implemented/reviewed
components; the lead verified integration. Isolated offline Linux: **301 passed**;
Windows: **296 passed, 5 skipped**. Six isolated installer/rollback scenarios passed.
After refinements the metrics ratchet reports no violations or exceptions.
SMART/night utility recheck: **27 passed**. Full preflight **passed** October 21:
36 unit files; gateway 56, nas_api 283, watchdog 44, backup_api 24 (1 skip),
stt 17, vpn_monitor 101, blackbox 296 (5 skips). Log:
`.agent-work/tmp/obs1-preflight-accepted-20261021.log`. The only warning is local
ShellCheck absence. Refinements included the new unit entrypoint, an explicit
mock placeholder and a Windows TCP-reset fix in the STT 404 test (empty POST,
same status assertion; no service change). All 27 OBS-1 modules passed Python
3.6 grammar validation. Local tests do not constitute target acceptance.
No new DeepSeek calls were made during this October 21 run ($0).

OBS-1 is **not installed or running on Jetson**; SMART still needs sudo. The
feature branch contains `docs/plans/DEPLOY_OBS1_BLACKBOX{,.ru}.md`, including
source backups before package transfer. Once SSH works, obtain night evidence,
check sudo/mount state, then install only an accepted package and measure one
hour of operation before alert acceptance.

Remote diagnostic retry around 12:43 MSK October 21 again failed before reaching
Jetson. Explicit Windows OpenSSH/configuration did not change the outcome;
an independent TCP check of proxy port 22 returned `False`. Current OOM,
restarts, backups and services remain unknown. Evidence is saved under
`.agent-work/tmp/remote-diagnostics-20261021.json`; this check does not establish
why the port is unreachable. No remote commands were executed.

### Route correction and night result — October 21, 12:48 MSK

Rechecking `docs/handoff/CODEX_START_2026-10-08.md` revealed the existing alternate
address of the same VPS, which the lead had missed. **`jetson-via-vps-alt` works**;
the primary address is unreachable from this workstation. VPS SSH uses port 22;
`127.0.0.1:10022` is the Jetson reverse tunnel. The earlier blanket remote-access
block is withdrawn. Existing host-key verification was preserved; no SSH, network
or VPN configuration was changed.

Docker is active, uptime approximately 8 days 13 hours. The observer returned
`ok` for **October 20 21:00 UTC–October 21 09:48:25 UTC**: restart count **1820,
delta 0**, healthy, container started before the window, **0 cgroup/global OOM**,
and missing-thumbnail generation remains disabled. All three backup jobs
succeeded; ages are **6.60 / 5.97 / 5.17 hours**. This confirms one stable night,
not a definitive root-cause or permanent resolution. A native subagent reviewed
the interpretation independently.

The canonical night JSON was updated; the previous unavailable result was saved
separately. Summary: `.agent-work/tmp/remote-diagnostics-20261021.json`.
The local runner now uses alt and passed syntax validation; persistent SSH and
schedule configuration were not changed. OBS-1 is not installed. Watchdog timer
is active. Actual SMART unit `nasa-hdd2tb-selftest.service` remains failed, its
timer active; the prepared installer returned `CHECK_OK` without applying changes.
Passwordless sudo is unavailable; the documented sudo source was located in the
handoff, but the credential was not read. No service restart or SMART test was
performed. No new DeepSeek calls ($0).

### SMART installed — October 21

This supersedes the previous prepared / sudo-blocked status. The stable-target
fix was installed through `jetson-via-vps-alt`. The owner-authorized saved sudo
credential was used only locally on Jetson, never copied into reports, the
repository or external models.

**Change and reason:** the unit and monitor now share `NAS_SMART_HDD_DEVICE`
from `/etc/nas-smart-hdd.env` (root:root, 0600), replacing erroneous `/dev/sdb`.
The whole-disk by-id was checked against `/mnt/hdd2tb` and the canonical HDD
model/serial. At deployment the HDD was `/dev/sda`, archive `/dev/sda1`.
Changed targets: `/etc/systemd/system/nasa-hdd2tb-selftest.service`,
`/usr/local/sbin/nasa-talk-alert.py`, and the environment file. The monitor was
built on the actual live version; unrelated prepared Cloud.ru changes were excluded.

**Commands and checks:** staged `invoke_local_sudo.py --check` and `--apply`
were run from `/home/admin/nasa/.agent-work/tmp/smart-stable-20261019/`.
Staged/live SHA-256, config permissions, archive mapping, Python 3.6 compatibility,
`systemd-analyze --man=no verify`, and the installed monitor's targeted SMART
check (`quiet=true`) passed. `--man=no` skips only man-page availability checks;
syntax and dependency verification remain. A prior verification failure was
caused by the man-page check, not a rejected sudo password.
**14 local tests passed:** 8 target/unit tests, 4 installer cases including
replacement/reload/post-check rollback, and 2 local credential-stdin/redaction
tests. Evidence: `.agent-work/tmp/smart-apply-20261021.json`, status
`installed_with_smart_warning`.

**Limits:** read-only `smartctl -i -H -A -d sat` confirmed the correct HDD,
attributes 5/197/198 **0/0/0**, **43 °C**, **3991 hours**. Exit code **4** and
`Incomplete response, ATA output registers missing` remain; PASSED is based
on attribute checks. This is not a successful full SMART test or an established
USB/SAT root cause. No self-test started; historical failed state retained.
The timer is active, its file unchanged (`OnCalendar=Mon 04:30`, randomized
delay 15 minutes). Reload recalculated the next run to October 26,
**04:40:03 UTC / 07:40:03 MSK**; the exact second can change again.

**Rollback:** preserved on Jetson under
`/home/admin/nasa/.agent-work/archives/smart-stable-20261019/`:
`unit.before.service`, `monitor.before.py`, previous config or `config-was-absent`,
and original mode/uid/gid in `metadata.json`. Apply/post-check failure restores
all three targets automatically. For manual rollback, restore these files with
original metadata; if config was absent, remove only the newly-created config
after checking its contents. Run `sudo systemctl daemon-reload`, verify hashes,
unit and timer without starting a self-test. Manual rollback was not executed;
it would also restore the previous incorrect disk-letter selection.

A native subagent hardened the installer and reviewed evidence limits; the lead
checked diffs/tests and live deployment. No new DeepSeek calls: **0, $0**;
closed host data were not sent externally. Next SMART step: investigate the
incomplete ATA Status and verify a subsequent controlled short self-test.
OBS-1 is still not deployed.

### Incomplete ATA Status diagnosis — October 21

The archive HDD was verified through its deployed by-id. Host: smartctl **6.6
r4324**, kernel **4.9.253-tegra**, USB **Realtek RTL9201 0bda:9201**,
`bcdDevice=f200`, `usb-storage` driver. bcdDevice is a USB device-version
descriptor, not an independently established firmware version.

Read-only `smartctl -r ioctl,2 -H -d sat[,12|,16] <by-id>` returned **4** in
all three modes. SMART RETURN STATUS requests **CK_COND** (CDB byte 2 `0x2c`),
but returns SCSI/host/driver **0/0/0**, without sense data or ATA output
registers. CDB length changes do not help. Separate `-A -l selftest -d sat`
succeeds with **exit 0**: attribute blocks and the log are readable. Attributes
5/197/198/199 are **0/0/0/0**, **41 °C**, **3992 hours**; the most recent logged
short test succeeded at **3770 hours**, not during this diagnostic session.

The mechanism matches the [smartmontools developer's explanation](https://sourceforge.net/p/smartmontools/mailman/smartmontools-support/thread/56E32872.8070409@t-online.de/):
some USB SAT implementations ignore the request to return ATA registers in
SCSI sense. Attribute reads work while SMART RETURN STATUS is unavailable,
so smartctl falls back to attribute-based health. Bridge SAT implementation
is the leading explanation for this path. Separating bridge firmware from
kernel/driver conclusively requires another bridge or direct SATA comparison,
which was not performed. No firmware, USB quirk/driver or system-package changes
were made. Neither this error nor readable attributes establishes full HDD health.

**Independent check:** the same fixed CDB12/CDB16 SMART RETURN STATUS requests
were sent directly through Linux `SG_IO`, bypassing smartctl, with `O_RDONLY`,
no data transfer and a 5-second timeout. Both returned ioctl/errno/status/
host/driver/info **0**, `sb_len_wr=0`, empty sense. Thus the smartctl 6.6 parser
does not cause the missing registers: the kernel API already returns no sense.
Native `sg_io_hdr` size is 88 bytes; the lead reviewed its layout and fixed CDBs
after subagent implementation. Unit, monitor, env and timer hashes remained
unchanged. Evidence: `.agent-work/tmp/smart-ata-raw-20261021.json` (12:01 UTC).

The bounded recent kernel sample (10 minutes, at most 300 entries) contained
no matching USB/SCSI/reset/I/O messages; this is not a full historical audit.
Service state did not change; no self-tests, media writes or disk-setting
changes occurred. Local evidence: `.agent-work/tmp/smart-ata-status-20261021.json`.
A cheap native subagent reviewed request safety; the lead checked upstream code
and actual responses. DeepSeek: **0 calls, $0**, no host data sent externally.

### OBS-1 installation and failed initial acceptance — October 21

The owner authorized sudo for OBS-1. **39 runtime files** from `621c21f` were
installed through `jetson-via-vps-alt`, without pulling/checking out the remote
repository or overwriting its 47 existing unrelated changes. Source bytes and
metadata, HEAD/status and scoped diff were backed up on Jetson under
`.agent-work/archives/obs1-source-before-20261021/`; installer system-file backups
and absence markers are under `blackbox-install-20261021T124419Z-11452`.
The 250 GB ext4 SSD was verified as a separate mount with about 188 GB free.
Target: Python **3.6.9**, SQLite **3.22.0**, systemd **237**, three INA3221 channels.
SMART unit/monitor/env hashes are preserved and checked after deployment actions.

Boot snapshot succeeded and collector started, but **initial hour acceptance
failed**: active/PID did not prove useful work. Fast rows and heartbeat stopped
during the first minute's processing, with CPU reaching its 10% quota. Only
OBS-1 collector was stopped; family containers were not restarted. A temporary
faulthandler launcher captured function stacks without locals or log rows,
showing `tick_logs → persist_logs → mask_secrets/_scrub_line`; its override was removed.

The lead fixed quadratic scans of token prefixes, URL schemes and non-Cyrillic
word edges; a native subagent reviewed privacy preservation. **322 passed,
5 skipped** on Windows before new regression tests. All three new synthetic
timeout cases fail on the baseline and pass after the fix. On target, **16
smoke assertions** passed: SQLite WAL/insert/replace/query, heartbeat, privacy,
and honest unknown verdicts. Regex fixes alone were insufficient: the initial
log pass reads up to 4 MiB per container, across as many as 200 containers.
Repeat acceptance also found heartbeat delay. As of **13:23 UTC**, collector
was stopped for bounded log processing; successful hour acceptance remains pending.
Evidence: `.agent-work/tmp/obs1-deploy-20261021/`.

**13:37 UTC continuation:** two native subagents implemented and cross-reviewed
bounded logging: at most one container / 16 KiB read per iteration; an unfinished
queue of up to 200 containers is not reset on the next due time. Initial backlog
and oversized records are omitted with explicit gap markers/byte counters, never
partial record fragments. Original Docker logs are unchanged. The existing
first-200-container selection remains; larger farms need separate fairness work.
Windows blackbox/container-watchdog: **323 passed, 5 skipped**. Three additional
runtime files were deployed with before/after SHA-256 guards and the
`obs1-log-budget-before-20261021` backup; two redaction files form the earlier
patch layer. Actual Python 3.6.9 / SQLite 3.22 passed **29 synthetic assertions**,
including bounded tails and oversized-record privacy. Collector started at
13:36:41 UTC, PID 1660; a new hour observer started at 13:37:13 UTC. Initial
heartbeat age was 6 s, RSS about 18 MiB, fast rows grew and restarts were zero.
This is **not yet successful hour acceptance**. Further observation identified
the fixed sleep-after-work loop reducing the nominal one-second cadence;
compensation is being prepared before the final uninterrupted hour.

Isolated synthetic archive acceptance passed real cp/sync/SHA-256, tar contents,
catalog commit, source removal after verification, immutable conflict rejection,
and injected copy-failure source retention/no archive commit. Archive: 288 bytes,
payload: 27 bytes. Only then was the persistent archive timer enabled; next
schedule **October 22 05:30 UTC / 08:30 MSK**. Family originals/production hot days
were not part of the test.

**14:24 UTC continuation:** monotonic iteration-time compensation fixed the
sleep-after-work sampling drift. Live completeness checks then found a separate
integration defect: `snapshot(prev_raw=None, ...)` raised a guarded TypeError
and the process baseline never progressed. A native subagent fixed the missing
first baseline and added coverage of first RSS/CPU-zero rows and subsequent
CPU deltas. Linux: 16 targeted process tests after the one-line fix; before it,
the full blackbox/container-watchdog set passed **329 tests without skips**.
Final full preflight passes; Windows blackbox **314 passed, 5 skipped**, metrics
ratchet has no exceptions. Only full-run warning: local ShellCheck unavailable.
Local commit **`2f4edaa`** was created with the real pre-commit hook; main remains
an ancestor. No merge/push.

Actual Python 3.6.9 / SQLite 3.22 passed **32 synthetic assertions**. All **39
runtime files + nas_layout.py** match commit
`2f4edaa5d86ef0ba0cfbc8b045ca35c417e8cba5`; accepted manifest SHA-256:
`a028cc15ef10da9048c6bf7115352eaa7a694529dbcc38eaca931f31937a8193`.
Device Git HEAD is unchanged. All three databases passed read-only quick checks;
current boot/snapshot linkage and four installed units match. All **574** recent
ten-minute samples had voltage, memory, frequency and temperature data, and
**299 process rows** were present. Collector started **14:10:49 UTC**, PID 4991;
final uninterrupted observation started **14:11:55 UTC**. Acceptance now also
requires at least 55 distinct process snapshots per hour alongside fast/minute
growth, heartbeat, CPU, VmHWM/cgroup peaks and unchanged PID/restarts. A successful
hour is not yet claimed. Failed-run evidence and patch-layer backups are retained.

Two cheap native subagents handled reviews/checks and bounded helper code;
the lead handled access, deployment, diagnosis and security. DeepSeek received
only public API descriptions and synthetic test inputs, with bare CLI/custom
system prompt and only Write (no Read/Bash/ambient CLAUDE.md discovery). No
implementation, host measurements, logs or credentials were supplied. Its reply
contained textual DSML rather than executed tool calls, so the lead extracted,
shortened and independently tested the draft. Recorded cost: **$0.0192**, one
attempt, no automatic retries, **0%** cache hits. This is the new step's expense,
separate from the incomplete October 20 accounting.
