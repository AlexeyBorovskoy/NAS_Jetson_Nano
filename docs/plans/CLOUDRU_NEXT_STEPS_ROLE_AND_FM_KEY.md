# Cloud.ru next steps: SA roles + FM API key

**Date:** 2026-09-07  
**No secrets** in this file (no Key ID/Secret, no JWT, no FM API key material).  
**Related:** `docs/plans/AUTH_PROBE_SA_HOME_NAS_API_2026-09-07.md`

---

## Known non-secret IDs

| Field | Value |
|---|---|
| Project ID | `10dd738e-6389-4b75-9570-852df04c0165` |
| Project name (console/API) | default / «Новый Проект» |
| SA `home-nas-api` | `8f07c1f7-202a-4bfa-a66d-2550f2b2fa11` |
| Customer / namespace | `d7322872-213e-4331-a522-8ac88ae15282` |
| Org unit | `5298e7f5-36a1-4422-a979-512134d6e81a` |

---

## 1) IAM token (both methods work)

Personal access keys from the host note mint a **user** Bearer (`sub_type=user`, ~1h).

### A) OpenID access_key

```bash
curl -sS -X POST "https://auth.iam.cloud.ru/auth/system/openid/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=access_key" \
  --data-urlencode "client_id=$KEY_ID" \
  --data-urlencode "client_secret=$KEY_SECRET"
# → access_token, expires_in=3600
```

### B) IAM Public API JSON

```bash
curl -sS -X POST "https://iam.api.cloud.ru/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"keyId\":\"$KEY_ID\",\"secret\":\"$KEY_SECRET\"}"
# → access_token (+ id_token, refresh_token, …)
```

Use: `Authorization: Bearer $TOKEN`

Docs: [console_api quickstart](https://cloud.ru/docs/console_api/ug/topics/quickstart?source-platform=Evolution), [auth_api](https://cloud.ru/docs/console_api/ug/topics/guides__auth_api?source-platform=Evolution).

---

## 2) Role assignment API — **working**

### List permissions (confirmed 200)

```bash
curl -sS -G "https://iam.api.cloud.ru/api/v1/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" \
  --data-urlencode "resource_id=10dd738e-6389-4b75-9570-852df04c0165" \
  --data-urlencode "subject_id=8f07c1f7-202a-4bfa-a66d-2550f2b2fa11"
```

**Required query params:** both `resource_id` and `subject_id` (subject alone → 400).  
`resource_id` alone lists all principals on that project.

Also: `GET …/permissions?customer_id=<customer_uuid>` lists customer-level bindings.

### Assign role (confirmed endpoint; body shape)

```bash
curl -sS -X POST "https://iam.api.cloud.ru/api/v1/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "role": "platform.project.admin",
    "object_id": "10dd738e-6389-4b75-9570-852df04c0165",
    "object_type": "resource",
    "subject_id": "8f07c1f7-202a-4bfa-a66d-2550f2b2fa11",
    "subject_type": "service_account"
  }'
```

| Result | Meaning |
|---|---|
| **2xx** | Role assigned |
| **409** | Already assigned (seen 2026-09-07 for `platform.project.admin`) |
| **400** | Bad body / wrapper shapes (`permission` / `permissions` array wrappers rejected) |

**Do not use** (415 grpc / 404 / empty):  
`/api/v1/roles`, `/api/v1/role-bindings`, `/api/v1/access`, `/api/v1/policies`, `/v1/role-bindings` as plain JSON list/bind without the permissions contract above.

Field names match Giga assistant partial:  
`role`, `objectType`→API snake `object_type`=`resource`, `subjectType`→`subject_type`=`service_account`, `objectId`→`object_id`=project, `subjectId`→`subject_id`=SA.

Role catalog names: [Роли пользователей](https://cloud.ru/docs/administration/ug/topics/concepts__roles?source-platform=Evolution) — project admin = **`platform.project.admin`**.

### SA `home-nas-api` roles on project (as of 2026-09-07 probe)

Already present (all `enabled=true`, created ~`2026-09-07T10:34:13Z`):

- `platform.project.admin`
- `platform.project.iam-admin`
- `platform.project.user`
- `platform.project.service-user`
- `platform.project.viewer`
- `ai-agents.agents.admin` / `.user` / `.invoker`
- `ai-agents.prompts.admin`
- `ai-agents.mcp-servers.admin`

**Assign via API not required** — admin already on project. POST once returned **409**.

### Project GET (confirmed)

```bash
curl -sS "https://organization.api.cloud.ru/v3/projects/10dd738e-6389-4b75-9570-852df04c0165" \
  -H "Authorization: Bearer $TOKEN"
# 200; list /v3/projects may still return projects=[] without id path
```

---

## 3) UI path (roles — if console preferred)

Docs: [Изменить права сервисного аккаунта](https://cloud.ru/docs/console_api/ug/topics/guides__service_accounts_edit-access?source-platform=Evolution).

1. Console → **Пользователи** → **Сервисные аккаунты**.
2. Row **`home-nas-api`** → ⋮ → **Изменить права** (or open card → ⋮ → same).
3. Assign **Администратор проекта** / `platform.project.admin` on project `10dd738e-…` (already done).
4. **Сохранить**.

---

## 4) Next: Foundation Models static API key (still required)

IAM Bearer ≠ FM inference credential. Need **static API key** on the SA:

Docs: [FM authentication](https://cloud.ru/docs/foundation-models/ug/topics/api-ref__authentication?source-platform=Evolution), [static API keys](https://cloud.ru/docs/console_api/ug/topics/guides__static-api-keys?source-platform=Evolution).

### Exact UI clicks

1. Console → **Пользователи** → **Сервисные аккаунты** → **`home-nas-api`**.
2. Roles already OK (skip if list shows project admin).
3. Tab **API-ключи** / credentials → **Создать**.
4. Services: **Foundation Models** only; TTL e.g. 90 days; optional IP allowlist.
5. Save **Key Secret once** off-repo (password manager / host file outside git).
6. Calls: `Authorization: Api-Key <secret>` (not Bearer IAM).
7. Smoke:

```bash
curl -sS -X POST "https://foundation-models.api.cloud.ru/v1/chat/completions" \
  -H "Authorization: Api-Key $FM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"ai-sage/GigaChat3-10B-A1.8B","max_tokens":8,"messages":[{"role":"user","content":"ping"}]}'
# expect HTTP 200 (not 400 invalid UUID / api key)
```

---

## Risks

1. Host note keys are **user** access keys — rotate carefully.
2. SA currently holds **broad** project + ai-agents roles; trim later for least privilege if desired.
3. FM still blocked until static **Api-Key** exists and is used correctly.
4. Do not commit secrets; wipe any temp token files after use.

---

## Rollback

- Role POST was **409 only** (no new binding created this session).
- No FM key created by agent.
- No secrets written to repo.

---

## Next safe step

1. **UI:** create FM-scoped static API key on `home-nas-api`; store off-repo.  
2. One chat smoke → record HTTP status only.  
3. Optional: least-privilege trim of extra SA roles after FM works.

---

## Changed files

- `docs/plans/CLOUDRU_NEXT_STEPS_ROLE_AND_FM_KEY.md` (this file)
