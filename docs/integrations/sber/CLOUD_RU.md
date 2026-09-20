# Cloud.ru Evolution — NAS notes

## Auth (docs)

```text
POST https://auth.iam.cloud.ru/auth/system/openid/token
grant_type=access_key&client_id=<Key ID>&client_secret=<Key Secret>
→ Authorization: Bearer <token>
```

FM chat/list: `https://foundation-models.api.cloud.ru/v1` + Bearer (SA API key scoped to Foundation Models).  
S3: `https://s3.cloud.ru`, SigV4, Access Key ID format `tenant_id:key_id`.

## Inventory

See [`../../plans/CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md`](../../plans/CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md).

- `GET /v1/models` **public** catalog (~98 models) ≠ free inference.
- VM/PG/CA/AR/RAG: auth required; do not probe API roots `/`.

## NAS use (plan waves)

| Wave | Use |
|---|---|
| W3 | FM adapter behind gateway — **`provider=cloudru`** in code (2026-09-07); needs `CLOUDRU_FM_API_KEY` on device |
| W3 | S3 restic encrypted dumps (L2 off-site, ADR-0009) |
| later | optional Container Apps watchdog / free_tier VM |

### Gateway env

```env
CLOUDRU_FM_API_KEY=          # FM static SA key (Bearer), not IAM pair alone
CLOUDRU_FM_BASE_URL=https://foundation-models.api.cloud.ru/v1
CLOUDRU_FM_MODEL=ai-sage/GigaChat3-10B-A1.8B
```

```bash
curl -s http://127.0.0.1:8090/v1/chat -H 'Content-Type: application/json' \
  -d '{"prompt":"ping","provider":"cloudru","user":"admin"}'
```

## Live status (2026-09-08)

| Item | State |
|---|---|
| Org / customer | `d7322872-213e-4331-a522-8ac88ae15282` |
| Project | `10dd738e-6389-4b75-9570-852df04c0165` («Новый Проект» / home-nas) |
| SA | `home-nas-api` (`8f07c1f7-202a-4bfa-a66d-2550f2b2fa11`) |
| SA role on project | `platform.project.admin` (bound) |
| IAM access_key → token | OK |
| FM API key | issued; **`Authorization: Bearer`** (not `Api-Key`) |
| FM chat | **OK** (200) — Bearer key; `ai-sage/GigaChat3-10B-A1.8B` + `GigaChat/GigaChat-2-Max` after balance top-up |
| S3 buckets | **0** — 2026-09-08 re-probe: Bearer ListBuckets empty; CreateBucket `nas-home-restic` → `AccessDenied`; SigV4 tenant prefixes → `NoSuchTenant`. **Blocker:** console **tenant_id** + Object Storage service + S3 keys `tenant_id:key_id`. restic L2 **not** run. See `S3_AND_BUDGET_CHECKLIST.md` |

Probe notes: `docs/plans/AUTH_PROBE_*.md`, `AUTH_PROBE_FM_KEY_SMOKE_2026-09-07.md`.

## Access keys (2026-09-20)

IAM access key pair for SA `home-nas-api` received from the owner: **no expiry** (владелец сделал бессрочными).
Verified 2026-09-20: `grant_type=access_key` → HTTP 200, `token_len=1295`, `expires_in=3600`.
Stored **only** in Windows Credential Manager (`nas-cloudru-iam`, user = Key ID) and in the owner's local file
outside git (`kaggle/` is git-ignored). Never in the repository, never in argv, never printed.
Unblocks: D3 watchdog job in Container Apps, E5 spend alert, E6 Immich ML spike.

## Do not

- Primary host Nextcloud/Immich in Cloud.ru.
- Managed RAG over family photos.
- Put Key ID/Secret / FM key in git.
