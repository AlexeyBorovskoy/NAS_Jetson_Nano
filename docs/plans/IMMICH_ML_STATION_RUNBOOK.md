# Immich ML on the ROG workstation — launch runbook (D4, option B)

> Date: 2026-09-26. Status: **kit ready, waiting on enabling the hypervisor on
> the workstation** (owner's admin step, see §2). Nothing on the device or the
> workstation was touched while preparing this — read-only checks and files in
> git only. Russian version — `IMMICH_ML_STATION_RUNBOOK.ru.md`. Decision and
> numbers — `D4_IMMICH_ML_DECISION.md`; original pilot plan —
> `IMMICH_ML_ROG_FREE_PILOT.md`.

## 1. What this is

Immich on the Jetson has never run `immich-machine-learning` — 0% ML
processing across 7646 assets (`smart_search`=0, `asset_face`=0, measured
2026-09-26). Option B (`D4_IMMICH_ML_DECISION.md`) runs semantic search and
face recognition as a one-off batch on the home workstation ROG (RTX 3050 Ti,
4 GiB VRAM, driver 596.36), over a reverse SSH tunnel — the same mechanism
already used for the local language model. Previews and embeddings never
leave the house (`AGENTS.md` §4, ADR-0010).

Kit files:

| File | Role |
|---|---|
| `docker/compose/docker-compose.immich-ml-rog.yml` | ML worker on the workstation, port bound to `127.0.0.1`, GPU via `deploy.resources.reservations.devices` |
| `config/immich-ml-rog.env.example` → `config/immich-ml-rog.env` (outside git) | version pinned to `v2.7.5` (matching the Jetson) |
| `scripts/workstation/immich_ml_station.ps1` | `start` / `stop` / `status` on the workstation |
| `scripts/immich/set_ml_url.sh` | `set` / `restore` / `show` — edits Immich `machineLearning` via the API |

## 2. Prerequisites

Nothing in this runbook runs until every item below is closed:

1. **Windows hypervisor is on** and the workstation has rebooted:
   ```powershell
   dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   bcdedit /set hypervisorlaunchtype auto
   # then reboot
   ```
   Check: `(Get-ComputerInfo).HyperVisorPresent` → `True`. This is the single
   administrative blocker the owner has deferred since 2026-09-12 (`D4` §4).
2. **Docker Desktop is running**, with GPU support enabled (WSL2 backend;
   the NVIDIA Container Toolkit ships with current Docker Desktop).
3. **NVIDIA driver ≥ 545** (for CUDA 12.3,
   `docs.immich.app/features/ml-hardware-acceleration`). Measured 2026-09:
   596.36 — comfortably above the floor.
4. **On AC power, sleep disabled** for the run — a Wi-Fi drop or sleep kills
   both the tunnel and Docker mid-indexing (risk noted in
   `IMMICH_ML_ROG_FREE_PILOT.md`).
5. **`config/immich-ml-rog.env` created on the workstation** (copy of
   `.example`, outside git). Its `IMMICH_VERSION` must match the Jetson's —
   verify with:
   ```bash
   ssh admin@192.168.0.50 "docker inspect homecloud_immich_server --format '{{.Config.Image}}'"
   ```
6. **An Immich API key with rights to `system-config`.** Create it inside
   Immich itself: Administration → Settings → API Keys → New API Key (admin
   role). Keep it outside git — same handling as the restic passwords
   (Windows Credential Manager), never printed to logs, never committed.
7. **Workstation → Jetson SSH key already working** — the same one
   `scripts/workstation/nas-tunnel.ps1` already uses for the local model.

## 3. Start

On the workstation:

```powershell
cd "E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano"
powershell -ExecutionPolicy Bypass -File scripts\workstation\immich_ml_station.ps1 -Command start
```

The script brings up `immich_ml_rog` (`docker compose up -d`), waits for
`/ping` on `127.0.0.1:3003`, then raises a reverse tunnel bound on the Jetson
to `172.17.0.1:3003` (`GatewayPorts clientspecified` is already enabled there
— containers only see the port at that address, not at `127.0.0.1`).

Next — once per pilot session — point Immich itself at the URL (not the
`.env` file, and not a container restart: since the Admin Settings UI shipped,
this lives in the database and overrides the environment variable):

```bash
export IMMICH_API_KEY='...'                         # never commit, never print
# run either on the Jetson (IMMICH_BASE_URL defaults to http://127.0.0.1:2283)
# or from any machine on the home LAN (IMMICH_BASE_URL=http://192.168.0.50:2283)
bash scripts/immich/set_ml_url.sh set http://172.17.0.1:3003
```

The script reads the current `system-config`, saves a copy to
`/mnt/storage/backups/immich-system-config/system-config.<UTC-timestamp>.json`
(on the Jetson; from the workstation — into `./immich-system-config-backups`),
then sends `PUT /api/system-config` with `machineLearning.enabled=true` and
the new `urls`.

Check status from the workstation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\workstation\immich_ml_station.ps1 -Command status
```

Shows: container status, `nvidia-smi`, whether the tunnel is alive, and a
`/ping` reply **from the Jetson itself** (a cross-check, not just from the
workstation's own side).

## 4. Trial run on one album

Honestly, per the Immich OpenAPI spec (pinned to tag `v2.7.5`, the same
version running on the Jetson):

- **Face Detection CAN be scoped to specific photos** — `POST
  /api/assets/jobs` accepts `{"assetIds": [...], "name": "refresh-faces"}`
  (`AssetJobName` includes `refresh-faces`). So you can pull one album's
  asset list and run face detection only on those:

  ```bash
  ALBUM_ID='...'   # Administration → Albums, or from the album's URL in the UI
  ASSET_IDS=$(curl -s -H "x-api-key: $IMMICH_API_KEY" \
      "$BASE/api/albums/$ALBUM_ID" | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps([a['id'] for a in d['assets']]))")
  curl -s -X POST -H "x-api-key: $IMMICH_API_KEY" -H "Content-Type: application/json" \
      -d "{\"assetIds\": $ASSET_IDS, \"name\": \"refresh-faces\"}" \
      "$BASE/api/assets/jobs"
  ```

- **Smart Search (CLIP) CANNOT be scoped to one album.** The spec has no
  per-asset/per-album endpoint for semantic search — only the whole library,
  via the `smartSearch` queue (Administration → Jobs → Smart Search →
  "Missing"/"All", or the same call via the API: `PUT /api/jobs/smartSearch`
  with body `{"command":"start","force":false}` — `force:false` matches the
  "Missing" button, `force:true` matches "All").

  The honest compromise for a trial: run Smart Search on the whole library
  right away (7646 assets), but **the first time, do it with `status` open**
  (GPU utilization, memory) and the SQL counter (§8) — not "fire and walk
  away." If after 10–15 minutes `smart_search` isn't growing and the GPU is
  idle, stop it (`docker compose ... down` on the workstation) and
  investigate instead of waiting for hours.

- Face clustering into named people (`facialRecognition` queue — distinct
  from `faceDetection`/`refresh-faces`, which only finds faces in a frame)
  also can't be scoped to an album — it's a separate library-wide queue.

## 5. Full run

Easiest via the UI: **Administration → Jobs → Smart Search / Face Detection /
Facial Recognition → Missing** (or "All" to reprocess everything from
scratch, including what's already done).

While it runs, watch:

```powershell
# on the workstation, repeat as needed
powershell -File scripts\workstation\immich_ml_station.ps1 -Command status
```

and keep `docker stats` open for `homecloud_immich_server` /
`homecloud_immich_microservices` on the Jetson — see the risk in §6.

## 6. What happens when the workstation is off

Two facts, both checked on the web on 2026-09-26, not contradictory but
carrying different confidence:

1. **Immich has a built-in safeguard** —
   `machineLearning.availabilityChecks` (`enabled`/`interval`/`timeout`,
   confirmed in the `MachineLearningAvailabilityChecksDto` OpenAPI schema) —
   a periodic ping of the ML URL, meant precisely to avoid dispatching jobs
   to a dead address.
2. 🔴 **But there is an open upstream issue** (not confirmed fixed as of
   2026-09-26) — [immich-app/immich#27617](https://github.com/immich-app/immich/issues/27617):
   on v2.6.2, an unreachable external ML URL didn't pause the queue but
   instead ran `immich-server`'s memory up to an OOM kill within seconds.
   Whether v2.7.5 (our version) is affected — **not verified**; the issue was
   filed against an older version and contains no confirmation of a fix.

**Practical conclusion:** don't rely on `availabilityChecks` alone. When the
workstation goes offline for a while, explicitly roll `machineLearning` back
(§7) instead of leaving `enabled=true` pointed at an address that's about to
go dark. Separately: jobs that fail because the ML endpoint was unreachable
are not retried automatically forever — per community reports
([immich-app/immich#17331](https://github.com/immich-app/immich/issues/17331))
you need to manually click **"Missing"** in Administration → Jobs for Smart
Search and Face Detection once the workstation is back, to pick up what
piled up while it was off.

## 7. Rollback

1. On the workstation:
   ```powershell
   powershell -File scripts\workstation\immich_ml_station.ps1 -Command stop
   ```
   Stops both the tunnel and the container.
2. On the Jetson — restore `machineLearning` to exactly its pre-pilot state,
   from the backup that `set_ml_url.sh set` saved before the change:
   ```bash
   ls -t /mnt/storage/backups/immich-system-config/*.json | head -1
   bash scripts/immich/set_ml_url.sh restore /mnt/storage/backups/immich-system-config/system-config.<TS>.json
   ```
3. Verify it rolled back to the right state:
   ```bash
   bash scripts/immich/set_ml_url.sh show
   ```

## 8. Post-run checks (numbers should grow)

```bash
ssh admin@192.168.0.50 \
  'docker exec homecloud_immich_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
   -c "select count(*) from smart_search;" \
   -c "select count(*) from asset_face;"'
```

Baseline (measured 2026-09-26): **0 and 0** out of 7646 assets (7014 photos +
609 videos + anything new since 2026-09-20). After the run both numbers
should climb toward the total asset count; whether videos are processed the
same way as photos or only via their preview frame was not benchmarked
separately (open question, `D4` §7).

## 9. Privacy

- The ML worker's port on the workstation is **`127.0.0.1` only**
  (compose file, audit CF-4). Not visible on the LAN.
- It's only reachable through the reverse SSH tunnel that the workstation
  itself raises toward the Jetson; on the Jetson the bind is `172.17.0.1`
  (docker bridge, `GatewayPorts clientspecified`) — not the LAN, not the WAN.
- Nothing is published to the WAN at any step — ADR-0010 holds.

## 10. Open questions

- Actual indexing time on the real workstation+tunnel+our library setup —
  not measured, only general GPU-inference practice (`D4` §7).
- Risk of `immich-server` OOM if the workstation connection drops mid-run
  (§6, issue #27617) — not specifically verified on v2.7.5.
- Video processing (609 files) was not benchmarked separately from photos.

## Sources

- The `machineLearning` field in `GET`/`PUT /api/system-config`, schema
  `SystemConfigMachineLearningDto` (`enabled`, `urls`, `availabilityChecks`) —
  Immich OpenAPI spec, tag `v2.7.5`:
  `https://raw.githubusercontent.com/immich-app/immich/v2.7.5/open-api/immich-openapi-specs.json`.
- Per-asset job `refresh-faces` (`AssetJobName`) and the absence of a
  per-asset job for semantic search — same spec, `paths./assets/jobs`,
  `paths./jobs/{name}`.
- `x-api-key` authentication — same spec, `components.securitySchemes`.
- GPU configuration via `deploy.resources.reservations.devices` (driver
  `nvidia`) — `https://docs.immich.app/features/ml-hardware-acceleration`
  (checked 2026-09-26).
- OOM risk when the external ML endpoint is unreachable —
  `https://github.com/immich-app/immich/issues/27617`.
- Manual retry of failed jobs —
  `https://github.com/immich-app/immich/issues/17331`.
