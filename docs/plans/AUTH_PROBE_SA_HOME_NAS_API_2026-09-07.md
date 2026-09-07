# Auth probe: SA `home-nas-api` + IAM keys (read-mostly)

**Date:** 2026-09-07  
**Scope:** Owner-authorized connectivity probe for Cloud.ru credentials tied to SA **home-nas-api**.  
**No secrets** in this file (no Key ID/Secret, no JWT, no GitVerse token, no FM API key material).  
**No role-bind WRITE** performed (list/bind endpoints not confirmed safe/exact; prefer console).  
**No cloud creates.**

**Credential source (host only):** `C:\Users\Alexey\Downloads\сбер\git.md`  
**Related prior probe:** `docs/plans/AUTH_PROBE_CLOUDRU_GITVERSE_2026-09-07.md`

---

## Known non-secret identifiers (OK to repeat)

| Field | Value |
|---|---|
| SA name | `home-nas-api` |
| SA ID | `8f07c1f7-202a-4bfa-a66d-2550f2b2fa11` |
| SA email | `home-nas-api@d7322872-213e-4331-a522-8ac88ae15282.iam.cloud.ru` |
| Namespace / org UUID (from SA email domain + API) | `d7322872-213e-4331-a522-8ac88ae15282` |
| SA enabled | `true` |
| SA created_at | `2026-09-07T06:46:14.941921Z` |

---

## Executive result

| Step | Result | Notes |
|---|---|---|
| IAM token `grant_type=access_key` (OpenID) | **OK** | HTTP **200**, `token_len=1295`, `expires_in=3600`, `token_type=Bearer` |
| IAM token JSON `POST iam.api…/auth/token` | **OK** | HTTP **200**, `token_len≈1287`, `expires_in=3600` (+ refresh fields present, values not stored) |
| JWT subject type | **`sub_type=user`** | Keys in note behave as **personal user access keys**, not SA-issued access keys |
| SA GET by id | **OK** | `GET /api/v1/service-accounts/{sa_id}` → 200; confirms SA metadata above |
| List projects | **Partial** | `GET https://organization.api.cloud.ru/v3/projects` → **200**, `projects=[]` (empty); pagination tokens advance but stay empty |
| FM `GET /v1/models` + IAM Bearer | **200** | 98 models (catalog; also public without auth) |
| FM tiny chat + IAM Bearer | **FAIL 400** | `InvalidArgument` — invalid API key / id not UUID (len 72) |
| Compute `GET /api/v1/flavors?limit=5` + IAM Bearer | **OK 200** | `items=5`, `total=75` (GPU-heavy sample names; catalog) |
| Compute `?project_id=<org uuid>` | **422** | empty body — org UUID ≠ project_id |
| Compute `?free_tier=true` | **422** | empty body |
| Role bind via API | **Not done** | No confirmed exact bind endpoint exercised; **do not assign blindly** |

---

## 1) IAM token

### A) OpenID access_key (documented quickstart)

- **POST** `https://auth.iam.cloud.ru/auth/system/openid/token`
- **Body:** `application/x-www-form-urlencoded`  
  `grant_type=access_key` + `client_id` + `client_secret` (from note; not stored here)

| Metric | Value |
|---|---|
| HTTP | **200** |
| `access_token` | present |
| `token_len` | **1295** |
| `expires_in` | **3600** |
| `token_type` | Bearer |

### B) IAM Public API JSON (documented auth_api)

- **POST** `https://iam.api.cloud.ru/api/v1/auth/token`
- **Body JSON:** `{ "keyId", "secret" }` (not stored)

| Metric | Value |
|---|---|
| HTTP | **200** |
| `token_len` | **~1287** |
| `expires_in` | **3600** |
| Top-level keys (names only) | `access_token`, `id_token`, `refresh_token`, `expires_in`, `refresh_expires_in`, `scopes`, `token_type`, `not_before` |

### JWT claims inspected (non-secret only)

| Claim | Observation |
|---|---|
| `sub_type` | **`user`** |
| `sub` / `sub_id` | UUID length 36 (user principal id; **not** SA id `8f07c1f7-…`) |
| `aud` | `iam` |
| `iss` | `https://auth.iam.cloud.ru/auth/system` |
| `scope` | `email openid profile roles` |
| `azp` | present, length 32 (matches access-key client shape; value not stored) |
| `preferred_username` | `\<user-uuid\>@iam.cloud.ru` shape |
| email | **human user email domain** (not `*.iam.cloud.ru` SA mailbox) — **not written here** |

**Inference:** Note Key ID/Secret authenticate a **human user**, which can **read** SA `home-nas-api`. They are **not** the SA’s own access keys and **not** an FM static API key.

---

## 2) Projects / tenants discovery

### Confirmed working reads

| Call | HTTP | Result |
|---|---|---|
| `GET https://iam.api.cloud.ru/api/v1/service-accounts/8f07c1f7-202a-4bfa-a66d-2550f2b2fa11` | **200** | `service_account` object; `namespace_id=d7322872-213e-4331-a522-8ac88ae15282` |
| `GET https://organization.api.cloud.ru/v3/projects` | **200** | `{"projects":[],"next_page_token":"…"}` — **0 projects** in first pages |

### Docs pointers (directory / org)

- Base IAM users/SA: `https://iam.api.cloud.ru`
- Catalogs / projects / quotas: `https://organization.api.cloud.ru`  
  Source: [Directory API overview](https://cloud.ru/docs/administration/ug/topics/guides__directory-api?source-platform=Evolution)

### Tried once (no inventing further)

| Call | HTTP | Notes |
|---|---|---|
| `iam.api…/api/v1/projects` (+ Accept variants) | **415** | unsupported media / content negotiation |
| `iam.api…/api/v1/service-accounts` (list) | **415** | list path not usable as plain GET JSON here |
| `organization.api…/api/v1/projects` | **404** | wrong version/path |
| `organization.api…/v1/projects` | **400** | live host, bad request |
| `organization.api…/v3/projects` | **200** | empty list; `next_page_token` advances (`Mg==`→`Mw==`→…) with still-empty `projects` |
| Query `project_id` / `namespace_id` = org UUID on compute | **422** | not a valid project scope for flavors filter |

**project_id for Compute:** **not discovered** from API in this probe. Console remains source of truth for Evolution project UUID.

**Do not treat** org/namespace UUID `d7322872-…` as `project_id`.

---

## 3) Foundation Models

### List models

`GET https://foundation-models.api.cloud.ru/v1/models` + Bearer IAM

| HTTP | Models |
|---|---|
| **200** | **98** (`data` array) |

(Catalog remains readable without useful auth; success ≠ inference entitlement.)

### Tiny chat

`POST https://foundation-models.api.cloud.ru/v1/chat/completions`  
Model: `ai-sage/GigaChat3-10B-A1.8B`, `max_tokens=8`, message `ping`  
Auth: Bearer IAM JWT

| HTTP | Body (sanitized) |
|---|---|
| **400** | `code=InvalidArgument`, message about invalid api key secret / **id invalid UUID length: 72** |

**Conclusion (unchanged vs prior probe):** IAM access-key JWT is **not** FM inference credential.  
Docs require **static API key** on the SA, header form **`Authorization: Api-Key <key>`** (service-scoped, e.g. Foundation Models).  
Refs:

- [FM authentication](https://cloud.ru/docs/foundation-models/ug/topics/api-ref__authentication?source-platform=Evolution)
- [Static API keys](https://cloud.ru/docs/console_api/ug/topics/guides__static-api-keys?source-platform=Evolution)
- [Auth overview](https://cloud.ru/docs/console_api/ug/topics/guides__auth_api?source-platform=Evolution)

---

## 4) Compute flavors

`GET https://compute.api.cloud.ru/api/v1/flavors?limit=5` + Bearer IAM

| Variant | HTTP | Notes |
|---|---|---|
| no project | **200** | `total=75`, `items=5` |
| `project_id=<org uuid>` | **422** | empty body |
| `project_id=<sa id>` | **422** | empty body |
| header `X-Project-Id` / `project_id` = org uuid | **200** | same catalog as no-project (header ignored or not required for list) |
| `free_tier=true` | **422** | empty body |
| `free_tier=false` | **422** | empty body |
| `type=standard` | **200** | `total=0` |

**Sample flavor names (public catalog, first 5):**

1. `vcpu-208-ram-1888-gpu-h100-80-nvlink-8`
2. `vcpu-52-ram-472-gpu-h100-hgx-80-nvlink-2`
3. `vcpu-104-ram-944-gpu-h100-hgx-80-nvlink-4`
4. `public-vcpu-224-ram-1880-gpu-a100-80-nvlink-8`
5. `public-vcpu-112-ram-940-gpu-a100-80-nvlink-4`

**Note:** Flavors list working without project_id is **catalog read**. VM create/list in a tenant still needs real **project** binding and roles — not proven here.

---

## 5) subjectId / objectId (role bind) — meaning & recommendation

Cloud.ru roles attach to **users, groups, and service accounts** at **organization / project / platform-service** levels  
([roles concepts](https://cloud.ru/docs/administration/ug/topics/concepts__roles?source-platform=Evolution)).

Typical IAM bind semantics (console + API naming):

| Field | Meaning |
|---|---|
| **subject** / **subjectId** | Who gets the role: user id, group id, or **service account id** (`8f07c1f7-…` for `home-nas-api`) |
| **object** / **objectId** | Where the role applies: **organization**, **project**, or service-scoped resource id |
| **role** | e.g. project admin `iam.project.admin`, project user/viewer, or service-specific roles |

**This probe:**

- Confirmed SA id and `namespace_id` (org/customer namespace).
- Did **not** find a clean 200 **list role-bindings** path with plain GET JSON (many IAM paths → **415**).
- Did **not** POST any bind (prefer report over blind write).

**Safe ops path for roles:** Console → Users → Service accounts → `home-nas-api` → **Change permissions**  
([edit SA access](https://cloud.ru/docs/console_api/ug/topics/guides__service_accounts_edit-access?source-platform=Evolution)).  
Assign at least a **project-level** role on the Evolution project that will own FM/S3 usage (docs quickstart often uses project admin for bootstrap; prefer least privilege once known).

---

## 6) Recommended next console clicks (FM API key)

**Goal:** one FM static API key for Jetson gateway; keep out of git.

1. Cloud.ru console → **Users** → **Service accounts** → open **`home-nas-api`** (`8f07c1f7-…`).
2. Ensure SA has a **project-level role** on the target project (edit permissions if missing).
3. Tab **API keys** / credentials → **Create API key**:
   - **Services:** **Foundation Models** (only).
   - Lifetime: e.g. **90 days** (docs allow 1 day–1 year).
   - Optional: IP allowlist = home/NAS egress if stable.
4. Save **Key Secret** once (password manager / host secrets file **outside** repo).  
   Header for calls: `Authorization: Api-Key <secret>` (per auth docs).
5. Smoke: `POST …/v1/chat/completions` with tiny `max_tokens` and model `ai-sage/GigaChat3-10B-A1.8B` → expect **200**, not 400 UUID error.
6. Optional second key later for **Object Storage** (or S3 access keys per S3 docs) — do not overload one key across unrelated services without need.
7. Copy **project name + project UUID** from console into private notes (not git) for Compute when needed.

**Do not:** paste Key Secret into this repo, coordination board, or commit history.

---

## Risks

1. **FM inference blocked** until SA static API key exists and is used as `Api-Key`.
2. **Keys in note are user keys** (`sub_type=user`) — rotating/revoking them affects the human console principal, not only the SA.
3. **No project_id** from API — Compute tenant ops and some filters remain incomplete.
4. **Org UUID ≠ project_id** — using email-domain UUID as `project_id` yields **422**.
5. Empty `v3/projects` may mean no projects in scope, filter required, or account layout not fully provisioned — verify in console.
6. Role API not confirmed — avoid automated bind until OpenAPI path + least-privilege role id are known.

---

## Rollback / cleanup

- No cloud resources created.
- No role bindings written.
- No secrets written to repo.
- Temp IAM token file under `%LOCALAPPDATA%\Temp\kilo` removed after probe.

---

## Next safe step

1. Console: create **FM-scoped static API key** on SA `home-nas-api`; store off-repo.  
2. One chat smoke test → record only HTTP status in a follow-up probe note.  
3. Note real **project_id** from console; retry compute only if VM work is planned.  
4. Keep gateway on non-Sber fallback until FM chat **200** is proven.

---

## Changed files

- `docs/plans/AUTH_PROBE_SA_HOME_NAS_API_2026-09-07.md` (this file)
