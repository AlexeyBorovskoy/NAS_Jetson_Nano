# CPP-1, step 1: where the Jetson spends its resources — measurement of 2026-10-12

[Русский](CPP1_BOTTLENECKS_2026-10-12.ru.md) · [Owner goals plan](../plans/DEVELOPMENT_PLAN_2026-10_OWNER_GOALS.md) ·
[CPP-1 statement](../../WORK_PLAN.md#planned-c-experiment--cpp-1)

The owner's question: are there bottlenecks in the project that would justify rewriting the code in C++.
Step 1 of plan CPP-1 is to measure CPU, memory and latencies on the Jetson itself, separating computation
from waiting for the disk, the network and external APIs, and, if there is no computational bottleneck, to record that without porting code.

**Answer: there is no computational bottleneck in our code.** All of our Python takes 1.7% of one core,
API responses are a few milliseconds. The resources go to the surrounding infrastructure: `dockerd`, Nextcloud under Talk polling and
the monitoring itself. C++ will not reduce any of these items.

## How we measured

- 2026-10-12, around 13:00 UTC, a 300 s window, the live Jetson via the VPS tunnel. Uptime 17 h, an ordinary weekday,
  no one in the family was uploading photos or asking the bot at that time.
- Read-only, without sudo and without load: `/proc/stat`, `/proc/<pid>/stat` and `status`, CPU accounting by
  cgroup (`cpuacct.usage` of containers and units), `/proc/diskstats`, `systemctl show`, local `curl`
  (20–30 requests per address), timing of «что сломалось?» ("what broke?") inside the API container (5 runs).
- Probe: [`scripts/quality/cpp1_probe.py`](../../scripts/quality/cpp1_probe.py). Repeat:
  `ssh jetson-via-vps "WINDOW=300 python3 -" < scripts/quality/cpp1_probe.py > out.json`.
  Raw data — outside git (`.agent-work/tmp/cpp1/`): they contain process command lines.

## Results

**The system as a whole** (shares of 4 cores): idle 69.1%, user 19.8%, system 9.2%, disk wait
(iowait) 0.2%. On average ≈ 1.2 of the 4 cores are busy. GPU 0%. Memory: 2.4 of 3.96 GB used, 1.4 GB
available, ZRAM swap 508 of 1 982 MB. Disks over 5 minutes: the SD card — 27 MB of writes (2 064 operations,
1.7% busy), the SSD — 0.6 MB, the HDD — not a single operation.

**Who takes the CPU** (% of one core over the window, cgroup accounting):

| Who | CPU | What it is |
|---|---:|---|
| `dockerd` (unit `docker.service`) | 35.9 | the Docker daemon |
| Nextcloud | 30.0 | apache + PHP, dozens of processes at ≈ 2.2% each |
| netdata | 20.7 | the monitoring itself (`netdata` 10.4 + `apps.plugin` 7.9) |
| Immich redis / Nextcloud redis | 3.8 / 3.6 | |
| `containerd` | 3.5 | |
| Samba | 3.4 | |
| Nextcloud DB | 2.8 | |
| **our API** (`homecloud_nasa_api`) | **2.3** | the bot, «что сломалось?», downloads |
| **our LLM gateway** | **1.4** | |
| Uptime Kuma | 1.2 | |
| Immich (server, microservices, DB) | 0.8 + 0.6 + 0.6 | |
| **our speech recognition** | **0.5** | |

**Our Python separately:** 6 processes, in total **1.73% of one core**, **383 MB** of memory. The largest —
speech recognition, 176 MB: it is the Vosk model, and the recognizer itself is already native (Kaldi, C++). The API and
the gateway — 80 MB each, the Docker status proxy — 21 MB. Python 3.12 in the containers.

**Latencies** (locally on the Jetson, without the network):

| Address | p50, ms | p95, ms |
|---|---:|---:|
| API `/healthcheck` | 2.5 | 3.4 |
| LLM gateway `/health` | 3.4 | 9.8 |
| Immich `/api/server/ping` | 3.3 | 3.8 |
| Nextcloud `/status.php` | 49.6 | 62.7 |

**«Что сломалось?»** (the bot's whole answer, without sending to Telegram): 90–112 ms. Of these, 75–107 ms — polling
the containers through the Docker status proxy, that is waiting for the Docker API. Disks, the HDD and systemd — 1–7 ms each.
The first run — 315 ms for the container poll (warm-up).

**Timers** (the last run): the Immich copy to the HDD — 176 s (`rsync`), USB preparation at boot —
57.6 s, SSD recovery — 42.7 s, DB dumps — 16.6 s, the daily report — 15.5 s, the rest — less than
5 s. All of them are bash and external programs waiting for the disk or the network.

## Where the third of a core at `dockerd` and Nextcloud comes from

Verified, but causality is not proven: that would need a before/after experiment in a maintenance window.

- **Health checks.** 13 of the 16 containers have them: 9 — every 30 s, 3 — once a minute, Immich's
  microservices — by default. That is ≈ 22 process launches in containers per minute, each through
  `runc`. A probable cause of the load on `dockerd` and `containerd`.
- **Talk polling.** Over the same 5 minutes Nextcloud served 73 requests: 60 — the phase A bot polling the Talk chat,
  15 — `status.php` (health checks and Uptime Kuma). The family does not use Talk (the owner's scaffold,
  2026-10-11), and the polling continues.
- **Monitoring** itself costs a fifth of a core (netdata).

## Conclusion

1. **There is no point in rewriting our code in C++ for speed.** Our Python — 1.7% of a core, responses — milliseconds,
   «что сломалось?» waits for Docker rather than computing. Under plan CPP-1 this is a negative result, and it is
   recorded without porting code.
2. **The resources can be won back without C++** — with three changes, each with a before/after measurement: fewer health
   checks, stop or make Talk polling rare, increase netdata's collection interval. Candidates for
   REL-5 and ARCH-1.
3. **The Jetson's main constraint is memory, not the processor:** 1.4 GB available, half a gigabyte in swap.
   Our largest process (speech, 176 MB) is already native inside; the only win is loading the model
   on demand, not rewriting.

## What this measurement does not cover

- Five quiet minutes: no photo uploads, no questions to the bot, no downloads, no voice messages. The peaks — Immich indexing and ML,
  uploads from phones, `pg_dump`, the Samba stream — will be measured by load test REL-5.
- One sample, without repeats at another time of day.
- Model responses (seconds) were not measured: that is waiting for external APIs and the network, not computation on the Jetson.

## CPP-1 next step (the owner's decision)

Step 2 — comparing Python and C++ on one component — after this measurement makes sense only as
a demonstrative experiment for the article, on synthetic data. Candidates: the gateway's redaction filter
(regular expressions over the request text) or the bot's intent classifier. The expected gain against
the background of network latencies of seconds is invisible to the family; that is what the numbers will have to show.
