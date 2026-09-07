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

Console → **Object Storage** → create bucket, e.g. `nas-home-restic` (name unique).

Record offline (not secret):

```text
bucket_name = ____________________
region      = ru-central-1
endpoint    = https://s3.cloud.ru
```

S3 credentials (password manager only):

- Access Key ID format often `tenant_id:key_id`  
- Secret = Key Secret  
- Docs: https://cloud.ru/docs/s3e/ug/topics/api__getting-started?source-platform=Evolution  

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
