# Checkpoint — 2026-10-19

[Русский](CHECKPOINT_2026-10-19.ru.md) · [Previous checkpoint](CHECKPOINT_2026-10-15.ru.md)

The owner accepted the work queue and requested small steps with DeepSeek.
This block covers live read-only diagnostics and deployment of the accepted HDD guard.

## Live diagnostics (13:42–13:46 UTC)

- Connected through the existing `jetson-via-vps` profile; direct LAN SSH timed out.
  No network, tunnel, or VPS configuration changes.
- HDD `/mnt/hdd2tb`: fuseblk, currently `/dev/sda1`, 381 GB available, 80% used.
  SSD `/mnt/storage`: ext4, currently `/dev/sdb1`, 176 GB available, 20% used.
  Both answered a bounded `stat -f`; SD root was 42% used.
- Active containers with healthchecks were healthy. An unrelated old stopped
  `bold_payne` container was left untouched.
- Immich microservices had **1432 restarts**, `OOMKilled=true`, last start
  03:37:26 UTC today. Kernel logs confirm repeated OOM around 03:34–03:37 UTC
  with the 1 GB container limit. No new kernel `Killed process` messages in the
  last eight hours; repeat measurement showed no increase in restarts.
  Current memory usage was about 336 MiB. Triggering jobs/files remain unknown.
- Today's database backup, configuration backup, and Immich HDD copy completed
  successfully at 03:01, 03:49, and 04:50 UTC. The two newest dumps were nonempty.
  Dump contents were not read; recoverability has not been demonstrated.
- Failed unit `nasa-hdd2tb-selftest.service`: exit 2, unsupported SMART opcode.
  Its hardcoded `/dev/sdb` currently identifies the SSD rather than the archive HDD.
  This does **not** establish HDD failure. Stable device identification and USB/SMART
  compatibility need a separate step. The unit was not modified or rerun.

## HDD guard deployment

Deployed from `main` (`d0245fd`), CRLF normalized to LF, under `/home/admin/nasa`:

| File | SHA-256 |
|---|---|
| `scripts/monitoring/hdd_guard.py` | `ae384fee6962dc78644ee2c5cf6830d2493039a82f426a4832a191ece0ed4fa7` |
| `scripts/monitoring/nas_jetson_nano-container-watchdog.py` | `cab3b0d66392297f432230be2ba198ea18b9b63b84d56202d775d169d3fd18a6` |
| `scripts/storage/hdd_hang_recover.sh` | `7b9b4b7c3901b49cb997fb8efe30beea2648836e77ff0bb5132c0a524bdf403d` |

The guard prevents start/restart of HDD holders when the mount is missing or hung
and issues an alert. Dependencies were installed before atomically replacing the
watchdog. Admin-owned files allowed deployment without sudo; noninteractive sudo
is unavailable. No container restarts or systemd/mount/backup configuration changes.
The recovery script was syntax-checked only; neither dry-run nor apply was executed.

Validation: remote SHA-256, host Python compilation, `bash -n`, and local
`python -m pytest tests/unit/test_hdd_guard.py tests/unit/test_container_watchdog.py -q`
— **19 passed**. The scheduled post-deployment run completed at **13:47:15 UTC**:
`Result=success`, `ExecMainStatus=0`; timer active. All three hashes matched again.
Immich microservices remained healthy with restart count 1432. No deliberate disk
hang was induced; failure behavior was exercised only with synthetic tests.

Rollback: restore the previous watchdog via a temporary sibling and atomic rename
from `.agent-work/archives/ops1-hdd-guard-20261019/watchdog.before.py` on Jetson,
SHA-256 `0c2761ce49b3a8f31eecc0563f986d8e044108b6c8d1d4dd85556691028d36cf`.
The old watchdog ignores the added module/recovery script. No Docker restart needed.

## Executors and next steps

Codex lead performed infrastructure diagnostics, safety review, deployment, and
independent verification. DeepSeek inventoried only two synthetic test files
(`data_class=project-own`), without code changes. Task
`nas-ops1-test-inventory-20261019` was manually accepted after checking its claims;
the report's `test_results` field had the wrong type. Cost **$0.01614**, one attempt,
zero retries, **67.74%** cache hits. NAS data/logs/configuration/secrets were not shared.

Next: stable SMART device addressing; bounded investigation of recurring Immich OOM;
SEC-3 password rotation with owner involvement; OBS-1 task 6. Do not resume bulk
thumbnail generation yet. No history rewrite, push, or publication. Existing owner
changes to `ds_worker.toml` were preserved. Local artifacts remain under
`.agent-work/` and `ds_board/`.

## Follow-up: stable SMART target prepared, privileged installation pending

Both the weekly unit and Talk SMART monitor used the unstable letter path
`/dev/sdb`. The unit now requires
`/etc/nas-smart-hdd.env` (`NAS_SMART_HDD_DEVICE`) and checks for a block device
before smartctl. The monitor uses the same setting and rejects letter paths and
partition targets before running smartctl. Configuration must contain a whole-disk
`/dev/disk/by-id/` path; actual identifiers remain on Jetson only.

Validation: eight focused tests, five existing self-test parser checks, eight
systemd 237 checks, two unit-test entrypoint checks, and the metrics ratchet pass
without exceptions. The lead extracted the path-format guard
to preserve the monitor's maximum complexity. Host Python 3.6 compilation, hashes,
and by-id mapping to the mounted archive's parent disk passed. Unprivileged
`systemd-analyze verify` was denied cgroup access; root installation runs it before
writing any system files.

Prepared host package: `/home/admin/nasa/.agent-work/tmp/smart-stable-20261019/`.

```sh
python3 /home/admin/nasa/.agent-work/tmp/smart-stable-20261019/install.py --check
sudo python3 /home/admin/nasa/.agent-work/tmp/smart-stable-20261019/install.py --apply
```

Installation archives the old unit, monitor, and existing config under
`.agent-work/archives/smart-stable-20261019/`, atomically installs the files and
runs daemon-reload. It does not start a self-test or change the schedule.
Rollback restores the archived unit/monitor and previous config (or removes only
the newly created config if none existed), then runs daemon-reload.

**Not deployed:** sudo rejected the supplied password. The owner explicitly
authorized local use of a recorded sudo password for SMART. No unambiguous working
record was found across 300 accessible administrative files (documentation,
configuration and shell history, excluding family disks); other service passwords
were not tried. The initial auto-review rejection of credential retrieval was
cleared for the bounded check after explicit authorization. No credential values
were printed, persisted in artifacts, or sent to DeepSeek. The installed unit
remains unchanged.

## Immich OOM investigation

The available kernel journal since October 16 contains **1310 cgroup OOM events**,
zero global OOM events: 1197 killed immich processes, 105 perl, eight others.
This event count differs from the container's 1432 restarts. Repeated overnight
series on October 17–19 start around midnight Moscow time (21:00 UTC) and continue
into the morning. Container timezone is MSK +0300; its memory limit is 1 GB.
It remained healthy with restart count 1432 during diagnostics.

Of 43,800 external images, **199 lack thumbhash**: 191 TIFF, six PSD, two JPG.
Thumbhash absence indicates unfinished processing; it is not a complete audit of
preview files. The largest TIFF metadata size is 1,824,035,156 bytes, with up to
approximately 63 MP in this group. No HDD traversal or image decoding was performed.

The thumbnail queue has **811 failed**, zero active/waiting/delayed/paused jobs.
810 failures are stalled AssetGenerateThumbnails jobs; one is a queue-all job.
They reference 221 distinct asset IDs. Matching database assets include 200 TIFF,
eight PSD, seven NEF and two DNG; 190 of those TIFF and six PSD still lack thumbhash.
These groups differ from the overall missing-thumbhash query.

Stored configuration overrides omit `nightlyTasks` and `job`, while library scan
is disabled and embedded preview extraction enabled. [Immich v2.7.5 defaults](https://github.com/immich-app/immich/blob/v2.7.5/server/src/config.ts)
enable nightly missing-thumbnail generation at midnight with thumbnail concurrency
three. Disabling library scanning does not disable this separate nightly job.

The strongest explanation is recurring nightly thumbnail work on heavy TIFF/PSD
under the 1 GB limit. Job-to-format correlation, nightly timing and cgroup OOM are
confirmed; the exact triggering file and per-job peak memory were not reproduced
on the live NAS. The [v2.7.5 decoder](https://github.com/immich-app/immich/blob/v2.7.5/server/src/repositories/media.repository.ts)
does not impose an input pixel limit; output thumbnail size does not establish
the memory required to decode the original.

Next mitigation: disable only `nightlyTasks.missingThumbnails`, retain the failed
queue, then use a controlled workstation pilot for heavy formats. Do not raise
Jetson memory limits without measurement. Immich settings, queues and originals
were not changed in this session.

DeepSeek prepared code/tests; the lead reviewed, tested and packaged them. Three
follow-up runs cost **$0.05511**, zero automatic network retries; two hit turn limits.
The first draft was cancelled in favor of compact tests; the monitor result was
accepted manually after verification. Total today including the earlier block:
**$0.07125**, 91.04% cache hits. No commits or pushes were made.
