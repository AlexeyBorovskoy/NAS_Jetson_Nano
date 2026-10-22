# Cloud.ru Object Storage + budget (synthetic validation)

> No secrets in this file. Create resources in https://console.cloud.ru/  
> Project (2026-09-07): `10dd738e-6389-4b75-9570-852df04c0165`  
> SA: `home-nas-api` (`8f07c1f7-202a-4bfa-a66d-2550f2b2fa11`)

## October 22 synthetic test execution

The earlier read-only inspection below is historical. The owner subsequently
authorized synthetic tests on the existing Cloud VM. An isolated virtualenv and
Restic 0.19.1 were installed only inside the task's own directory. No sudo,
services, ports, new cloud resources, or Object Storage uploads were used. The
existing VM was reused; this does not verify actual grant spending or balance.
The previously reported forecast of about 3,100 credits for the VM and 900
remaining for other consumption is unchanged and is still a forecast, not a
verified account balance. No family files were used.

| Trial | Observed result | Scope limit |
|---|---|---|
| OBS blackbox on Ubuntu 24.04 x86_64 / Python 3.12.3 | 323 passed, 0 skipped; pytest time 17.12 s | Separate Linux Cloud run; not target Jetson ARM acceptance |
| Local Restic 0.19.1 restore fixture | 36 generated files / 2,098,538 bytes; init, backup, `check --read-data`, full restore all exit 0; names, sizes, SHA-256 and file modes matched. Partial restore selected one file and was detected as incomplete; full restore took 0.721 s | Tiny local-only fixture, not production RTO/DR and not an S3 test |
| TIFF/PSD decoder matrix | 10 fixtures: 6 valid TIFF (raw, deflate, LZW, 16-bit, multipage, 2048-sized), 2 valid PSD (raw/RLE), 2 truncated negatives. Pillow 12.0.0 passed 10/10. libvips 8.18.7 passed 6 valid TIFF and 2 malformed rejections; its binary build does not support the 2 valid PSD inputs | Do not report this as 20/20 or as a fix for family PSD compatibility |

Image child limits: 768 MiB address space, 15 CPU seconds, 25 seconds wall time,
two libvips threads; cgroup limit 2 CPU / 4 GiB. No timeout or crash occurred,
inputs remained unchanged, and an independent 16-bit pixel value 257 was confirmed.
This synthetic matrix does not establish compatibility with private family images.

### Repeat on the prepared Linux VM

Use a fresh private output directory for every run; the harnesses refuse to reuse
existing output paths. Python 3.10+ is required. The prepared environment contains
pytest 8.4.2, Pillow 12.0.0, pyvips 3.0.0, pyvips-binary 8.18.7 and Restic 0.19.1.
The optional binary package supplies the tested libvips build. The Ubuntu image
has no ensurepip; setup used a venv without pip and a SHA-256-verified PyPI pip
wheel to bootstrap inside that venv, without sudo or system package changes.
Run the following after the three harnesses have been copied into the exported
source package. No private keys or cloud credentials belong in that package.

```bash
TEST_ROOT="$HOME/nasa/.agent-work/tmp/cloud-ci-20261022"
TASK_DIR="$(mktemp -d "$TEST_ROOT/recheck.XXXXXX")"
mkdir -p "$TASK_DIR/tmp"
export TMPDIR="$TASK_DIR/tmp" NAS_TEST_TMP="$TASK_DIR/tmp" VIPS_CONCURRENCY=2
cd "$TEST_ROOT/src"
"$TEST_ROOT/bin/restic" version
nice -n 15 "$TEST_ROOT/venv/bin/python" -m pytest tests/blackbox --basetemp="$TASK_DIR/pytest"
nice -n 15 "$TEST_ROOT/venv/bin/python" tests/cloud/generate_images.py "$TASK_DIR/images"
"$TEST_ROOT/venv/bin/python" tests/cloud/probe_image_decoders.py "$TASK_DIR/images" "$TASK_DIR/image-results"
nice -n 15 "$TEST_ROOT/venv/bin/python" tests/cloud/restic_restore_trial.py "$TASK_DIR/restic-trial" "$TEST_ROOT/bin/restic"
```

These commands create synthetic outputs only beneath `TASK_DIR`; they do not
upload data or access production repositories. With the recorded libvips binary,
the decoder probe is expected to exit **2** for the two known valid-PSD compatibility
gaps. Treat that as the expected result only when the JSON reports no hard failures,
no timeout/crash/MemoryError, and unchanged inputs; negative fixtures count as passed
only when rejected normally. Exit 0 means every decoder case passed; exit 1 means
a hard failure. Check package availability for the selected platform before relying
on the optional libvips wheel.

## A. Budget / grant

### October 22 update: reuse the owner's existing shared VM

The owner again reports 4,000 Test Evolution credits expiring November 6. The
neighboring `atc` project confirms an existing CPU VM and plans its deletion on
**November 5**. Its operator estimates about **3,100 credits** for the VM's
remaining lifetime, leaving roughly **900 for all other consumption**. These
are a forecast and an operator report, not a fresh account balance or proof of
bonus debits. The earlier 500/3,500 split below is historical.

The following records the historical read-only inspection performed before
the authorized synthetic run. NAS access was verified read-only on October 22 using a dedicated key and a
pinned ED25519 host key. The non-root `nas` account runs on Ubuntu 24.04.4 LTS
x86_64; effective parent-cgroup limits are **2 vCPU / 4 GiB RAM**. Podman is
available; no container was started. The agreed scope is
a separate user without sudo and **15 GiB disk by policy, without an enforced filesystem quota**, rootless
containers and loopback-only services. The neighboring project's applications,
network, nginx, SSH and firewall must remain untouched. No family data,
production NAS backups, field logs or other projects' closed code may be copied
there. User lingering is off according to the operator, so persistent user
services require a separate agreement. No software, service or remote file was
installed or changed during inspection.

| Priority | Project work | Concrete outcome before November 5 |
|---|---|---|
| 1 | OBS-1, REL-4/REL-5: Linux CI and isolated failure scenarios | Reproducible tests of log rotation, bounded memory, interrupted writes, recovery and diagnostics using synthetic data |
| 2 | REL-6 / ADR-0009: backup/restore rehearsal | Restore a synthetic dataset from a separate encrypted test prefix, verify hashes and record recovery time; this is not full ARM64/hardware or family-data DR |
| 3 | D3: external monitoring prototype | Outbound probes of approved endpoints, bounded timeouts and synthetic alert tests; no new inbound ports or permanent dependency on the expiring VM |
| 4 | FAM-4: decoder preparation | Public or generated TIFF/PSD fixtures with time/RSS limits; the real family-file pilot remains on home LAN |

Using idle capacity within this fixed-size VM adds no additional VM SKU hours.
A proposed **NAS incremental envelope of at most 100 credits**, taken from the
remaining shared reserve, is a planning proposal, not authorization for new
resources or object uploads. Most synthetic CI can run without creating another
billable cloud resource. Object Storage free allowances are shared and must be
checked; do not assume a fresh allowance for a new prefix.

For comparison only, the published Compute tariff (version 261014, 22% VAT)
prices a standard 4 vCPU / 16 GB VM at 7.9788 RUB/hour, a 50 GB SSD at
0.793 RUB/hour and one public IP at 0.2074 RUB/hour. Their sum is
**8.9792 RUB/hour**, or about **3,017 RUB for 336 hours**. This supports the
operator's approximate reservation; it is not an account-specific quote.
[Current Compute tariff](https://cdn.cloud.ru/docs/legal/tariffs/evolution/current-version/evolution-compute.pdf).

Current billing supports a budget with optional **resource suspension**, in
addition to notifications. Its scope and calendar-month periods need checking
against other projects and both October/November consumption; it is not an
automatic grant-expiry deadline. No billing setting was changed.
[Create a budget](https://cloud.ru/docs/billing/ug/topics/guides__budget_add).
Stopping a VM alone leaves disks and IP billable; export NAS results by November
3, remove its own workloads by November 4, and coordinate the operator's November
5 cleanup. Never delete another project's VM or data without its authorization.
[VM billing](https://cloud.ru/docs/virtual-machines/ug/topics/pricing).

GPU, Foundation Models, ML Inference, Container Apps and Marketplace remain
excluded from this grant. No new paid resources, payment changes or production
uploads were made in this assessment. The transfer of the owner's local family
folder is separately deferred until home LAN and is not an S3/cloud experiment.

- **Owner decision 2026-10-09:** 4,000 Cloud.ru bonus credits through 6 November are owner-confirmed. This is not independent cabinet verification. Confirm this project's eligibility for the exact SKU in the calculator before creating resources. Official exclusions include Foundation Models, Container Apps, GPU/ML Inference, and Marketplace ([grant terms](https://cloud.ru/docs/billing/ug/topics/concepts__start_grant)); do not propose FM/RAG or Container Apps as grant-funded experiments.
- **Original experiment proposal:** backup/restore of a minimal encrypted configuration set in Object Storage, with a proposed 500-credit ceiling and 3,500 reserved. The owner subsequently authorized the tiny synthetic trial documented below; this is not authorization to spend 500 credits. The old S3 tenant/key blocker was resolved on 2026-09-20 (see `CLOUD_RU.md`); the old Jetson restic HTTP 400 did not reproduce in the 2026-10-09 trial. Secondary option: isolated CPU-only watchdog VM, only after calculator confirmation. No production off-site backup of family data is authorized.
- No automatic paid fallback and no ruble top-up. Do not incur charges until covered SKU, budget behavior, and explicit experiment authorization are confirmed.

### SKU verification — 2026-10-09

### Authorized tiny restore trial — 2026-10-09

The owner reported **90 RUB** on the ruble balance and authorized trying the
experiment. Existing S3 credentials and restic were found on Jetson; their values
were neither printed nor copied to this workstation. The console remains
unavailable, so grant coverage and actual bonus/ruble charges are not verified.

- Client: **restic 0.19.1**, Linux/arm64; path-style lookup, `ru-central-1`,
  endpoint `https://s3.cloud.ru`, existing configured bucket.
- Separate repository prefix: `cloudru-trial-20261009-5de8d5e9`.
- Dataset: **2 synthetic files / 6,547 bytes**, no real configuration or family data.
  This is a connectivity/encryption/restore fixture, not a production backup.
- `init`, `backup`, `check --read-data`, `restore latest`: **exit 0** each.
- Restore ran **on Jetson**; both SHA-256 checks matched the source.
- The historical HTTP 400 did **not** reproduce with this client/options/prefix;
  this does not establish the cause of the earlier failure or validate old snapshots.
- Remote artifacts: `~/nasa/.agent-work/tmp/cloudru-trial-20261009-5de8d5e9/`;
  local report: `.agent-work/tmp/cloudru-trial-20261009-REPORT.json`.
- The tiny encrypted repository remains in its separate cloud prefix. No existing
  objects were deleted, no schedules/production services were installed, and no
  payment, top-up, balance activation, or VPN setting was changed.
- The earlier 1 GB estimate is a planning envelope, not this test's measured usage.
  Do not report zero cost, a grant debit, or the remaining 90 RUB without billing data.

### Public tariff and account verification

### Real configuration restore — owner-approved, 2026-10-09

The owner explicitly approved the exact four-file payload and destination after
automatic approval review initially rejected uploading real configuration without
that specific confirmation. Selected files were checked for known secrets and
literal secret assignments; their bytes and modes were frozen by hash before upload.

| Live source | Restored sample path | Bytes | Mode |
|---|---|---:|---|
| `~/nasa/docker/compose/docker-compose.nas_jetson_nano-api.yml` | `compose/nas-api.yml` | 5800 | 0664 |
| `~/nasa/docker/compose/docker-compose.nextcloud.yml` | `compose/nextcloud.yml` | 2892 | 0664 |
| `/etc/systemd/system/nas_jetson_nano-container-watchdog.service` | `systemd/watchdog.service` | 823 | 0644 |
| `/etc/systemd/system/nas_jetson_nano-container-watchdog.timer` | `systemd/watchdog.timer` | 195 | 0644 |

- Total: **4 files / 9,710 bytes**. Compose source was corroborated by the running
  API container's label; the installed watchdog timer was active.
- Destination: existing bucket `nas-immich-offsite`, unique encrypted restic
  repository prefix `cloudru-real-config-20261009-f3dffe07`.
- On Jetson, restic 0.19.1 with path-style: `init`, `backup`, `check --read-data`,
  `restore latest` all exited **0**. Restored into a separate test directory.
- **SHA-256 4/4 matched; permission modes 4/4 matched; original source hashes
  remained unchanged.** No restored file was applied to a running service.
- Local evidence: `.agent-work/tmp/cloudru-real-config-20261009-REPORT.json`;
  remote sample/report: `~/nasa/.agent-work/tmp/cloudru-real-config-20261009-f3dffe07/`.
- This verifies a small configuration sample, not full disaster recovery:
  `.env`, secrets, database dumps, photos, and other live configuration were excluded.
  Actual billing and grant debit remain unverified while the console is unavailable.
- The encrypted test repository remains in its isolated prefix; cleanup or
  scheduling automatic backups was not performed. Lead Codex handled the real
  configuration and credentials; none were sent to DeepSeek.

### Public eligibility and tariff details

**Selected service:** Evolution Object Storage, **standard** class, matching the
class of the bucket recorded on 2026-09-20. The initial eligibility check was
read-only; the subsequent authorized tiny trial is documented separately above.

**Public eligibility:** Object Storage is absent from the published exclusions
for the 4,000-credit Test Evolution grant. Coverage is therefore supported by
the public rules, subject to this account's grant scope and matching agreement.
Sources: [start grant](https://cloud.ru/docs/billing/ug/topics/concepts__start_grant),
[excluded services/SKUs](https://cloud.ru/documents/promotions/exceptions-list).

**Account verification remains pending:** the console again displayed “No Internet
connection”; the documented Windows credential `nas-cloudru-iam` was not found
(Windows error 1168), and `config/.env` contains no CLOUDRU credential variables.
No account API response or calculator quote was obtained. The owner's earlier
confirmation of 4,000 credits through 6 November remains the source for the balance
and deadline. No internal SKU UUID has been established.
The owner also confirmed on 2026-10-09 that the console is currently unavailable;
account-specific verification remains pending rather than assumed successful.

Public tariff names and prices, including **22% VAT**, from the current
[tariff PDF](https://cdn.cloud.ru/docs/legal/tariffs/evolution/current-version/object-storage.pdf),
version **260918** (checked 2026-10-09):

| Tariff service name | Billing unit | RUB including VAT |
|---|---|---:|
| Объектное хранилище Стандартное от 15 ГБ | GB/month | 1.83915 |
| Объектное хранилище Стандартное операции GET от 1000 тыс. шт | 1,000 operations | 0.03294 |
| Объектное хранилище Стандартное операции HEAD от 1000 тыс. шт | 1,000 operations | 0.03294 |
| Объектное хранилище Стандартное операции PUT от 100 тыс. шт | 1,000 operations | 0.1098 |
| Объектное хранилище Стандартное операции POST от 100 тыс. шт | 1,000 operations | 0.1098 |
| Объектное хранилище Стандартное операции LIST от 100 тыс. шт | 1,000 operations | 0.1098 |
| Объектное хранилище Исходящий трафик от 10000 ГБ | GB | 1.1712 |

**Small experiment estimate:** up to 1 GB stored for one full month, up to 1,000
of each operation above, and up to 1 GB downloaded. Conservatively applying all
paid rates even if free allowances are available gives
`1.83915 + 2 * 0.03294 + 3 * 0.1098 + 1.1712 = 3.40563 RUB` (about **3.41 credits**;
[1 credit = 1 RUB](https://cloud.ru/docs/billing/ug/topics/concepts__billing_bonus)).
This is an illustrative estimate, not a calculator quote or a spending cap enforced
by the cloud. It excludes consumption by other services/projects and any volume
outside the stated limits. The proposed 500-credit ceiling is substantially larger
than this experiment needs, and is not authorization to spend it.

**Free Tier is separate:** the published [rules](https://cloud.ru/documents/promotions/active/evolution-free-tier)
provide standard storage 15 GB, GET/HEAD 1 million operations, PUT/POST/LIST
100,000 operations, and egress 10 TB monthly. If participation is active and the
remaining shared allowances cover the experiment, its bill may be zero; account
activation and available quota have not been checked. Such a result would test S3
backup/restore, but would not demonstrate spending the grant.

Remaining read-only checks before experiment approval:

- [ ] The grant details permit this service and refer to the NAS project's agreement.
- [ ] The console/calculator confirms exact selected SKU identifiers, standard class,
      tariff, and remaining Free Tier allowances for this account.
- [ ] Balance activation/threshold/top-up behavior is understood; no setting is changed.
- [x] A synthetic dataset and restore client are specified; restore on Jetson
      passed for restic 0.19.1 with path-style. The original 400 cause is unproven.

- [ ] Balance / bonuses visible on **this** project  
- [ ] FM chat returns 200 (verified after top-up 2026-09-07)  
- [ ] Soft monthly cap in mind (FM burns money faster than PERS freemium)  
- [ ] Prefer family traffic on **GigaChat PERS**; FM for overflow/admin  

## B. Object Storage bucket (L2 off-site later)

### Live attempt 2026-09-07 (agent, owner-authorized)

| Step | Result |
|---|---|
| IAM token `access_key` / `auth/token` | ✅ OK |
| SigV4 ListBuckets with `customer_id` / `project_id` / `user_id` as tenant prefix | ❌ `NoSuchTenant` |
| Bare Key ID as AWS access key | ❌ `InvalidAccessKeyId` |
| CreateBucket Bearer IAM | ❌ `AccessDenied` |
| New S3/IAM keys via API | ❌ not created (key-create paths 415/404) |
| Preferred name | `nas-home-restic` (not created) |

### Live attempt 2026-09-08 (agent, owner-authorized)

| Step | Result |
|---|---|
| IAM token | ✅ OK |
| Bearer `GET https://s3.cloud.ru/` | ✅ 200 empty `<Buckets></Buckets>` (no tenant-scoped keys) |
| CreateBucket `nas-home-restic` Bearer / path-style / virtual-host | ❌ `AccessDenied` |
| SigV4 with customer/project/SA/user as tenant prefix | ❌ `NoSuchTenant` / bare key `InvalidAccessKeyId` |
| JWT claims | no `tenant_id` (sub = personal IAM user) |
| S3 access keys via API | ❌ not created |
| restic L2 on Jetson | ⏭ **skipped** — no bucket / no S3 keys |

**Historical blocker (2026-09-08; resolved 2026-09-20):** Object Storage
**tenant_id** is not customer/project/user id. `CLOUD_RU.md` records the working
`tenant_id:key_id` form and a successful write/read/hash/delete round trip on
2026-09-20. The instructions below describe the earlier setup attempt; do not
recreate keys or buckets merely because this historical record says “pending”.

**Owner console (one-time):**

1. Evolution project → ensure **Object Storage** is in the service list (support if missing).  
2. Copy **tenant_id** from «Параметры работы с API».  
3. Create bucket `nas-home-restic` **or** give agent tenant_id only (not a secret) and re-run SigV4 `create_bucket`.  
4. Access Key ID for tools = `tenant_id:key_id` (personal or SA access key); Secret = Key Secret → password manager only.

Record offline (not secret):

```text
bucket_name = (pending — not created 2026-09-07 / 2026-09-08)
region      = ru-central-1
endpoint    = https://s3.cloud.ru
tenant_id   = ____________________   # from console API params only
created     = —
restic_L2   = skipped 2026-09-08 (blocker tenant_id / CreateBucket AccessDenied)
```

S3 credentials (password manager only):

- Access Key ID format: `tenant_id:key_id` or `tenant_id.key_id`  
- Secret = Key Secret  
- Docs: https://cloud.ru/docs/s3e/ug/topics/api__getting-started?source-platform=Evolution  
- **S3 keys created this session:** no

## C. restic (on Jetson when ready)

See `scripts/backup/restic_s3_cloudru_example.sh`.

```text
RESTIC_REPOSITORY=s3:https://s3.cloud.ru/<bucket>/nas-restic
RESTIC_PASSWORD_FILE=/root/.config/homecloud/restic-s3-password   # device only
# first: dumps only — not full Immich until explicit OK
# 2026-09-08: not run — S3 bucket/keys blocked
```

## D. Do not

- Put S3 secrets in git  
- Upload raw family photo library unencrypted  
- Open bucket public  
