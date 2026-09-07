# Cloud.ru Object Storage + budget (offline prep)

> No secrets in this file. Create resources in https://console.cloud.ru/  
> Project (2026-09-07): `10dd738e-6389-4b75-9570-852df04c0165`  
> SA: `home-nas-api` (`8f07c1f7-202a-4bfa-a66d-2550f2b2fa11`)

## A. Budget / grant

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

**Blocker:** Object Storage **tenant_id** is not customer/project/user id. Docs: console → **Хранение данных → Object Storage → Параметры работы с API** (tenant id). Until that value exists (service opened in project), API cannot `mb` / ListBuckets for the tenant.

**Owner console (one-time):**

1. Evolution project → ensure **Object Storage** is in the service list (support if missing).  
2. Copy **tenant_id** from «Параметры работы с API».  
3. Create bucket `nas-home-restic` **or** give agent tenant_id only (not a secret) and re-run SigV4 `create_bucket`.  
4. Access Key ID for tools = `tenant_id:key_id` (personal or SA access key); Secret = Key Secret → password manager only.

Record offline (not secret):

```text
bucket_name = (pending — not created 2026-09-07)
region      = ru-central-1
endpoint    = https://s3.cloud.ru
tenant_id   = ____________________   # from console API params only
created     = —
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
```

## D. Do not

- Put S3 secrets in git  
- Upload raw family photo library unencrypted  
- Open bucket public  
