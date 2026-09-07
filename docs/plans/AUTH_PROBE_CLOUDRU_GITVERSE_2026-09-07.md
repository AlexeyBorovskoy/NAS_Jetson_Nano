# Auth probe: Cloud.ru + GitVerse (read-only)

**Date:** 2026-09-07  
**Scope:** Owner-authorized **read-only** connectivity/auth probe.  
**No secrets** in this file. No cloud creates. No git push. No repo secret commits.

**Credential source (host only, not in git):** local downloads note + optional SSH key path.  
**Temp scripts:** `$env:TEMP\sber_auth_probe_20260907` (deleted after run).

---

## Executive result

| Area | Result | Notes |
|---|---|---|
| Cloud.ru IAM (`access_key`) | **OK** | HTTP 200, `access_token` present |
| Foundation Models `/v1/models` | **OK (public)** | 200 even without auth; 98 models |
| Foundation Models chat | **FAIL** | 400 `InvalidArgument` — access key ≠ FM API key |
| Compute flavors free_tier | **FAIL** | 401 (static) / 422 (IAM, empty body) |
| S3 ListBuckets | **OK empty** | Bearer list XML, **0** buckets |
| GitVerse REST | **OK** | `/user`, repos, `NAS_HOME` |
| GitVerse SSH | **FAIL** | `Permission denied (publickey)` |

**Key type inference**

- **Key ID + Key Secret** from the note behave as **Cloud.ru IAM access keys** (`grant_type=access_key` → OpenID token).
- They are **not** a Foundation Models / GigaChat **static API key** (chat expects a UUID-shaped API key id; errors say `invalid api key secret` / `id is invalid UUID`).
- FM **model catalog is unauthenticated** (NO_AUTH and garbage Bearer still 200) — catalog success does **not** prove FM inference credentials.
- GitVerse **Bearer token** is valid for REST. Local `gitverse_ed25519` is **not** accepted by `git@gitverse.ru` for this account (pubkey present locally; server rejects).

---

## A) Cloud.ru IAM token

**Endpoint:** `POST https://auth.iam.cloud.ru/auth/system/openid/token`  
**Body:** `grant_type=access_key` + `client_id` + `client_secret` (form-urlencoded)

| Attempt | HTTP | `access_token` | `token_len` | `expires_in` | Top-level keys (names only) |
|---|---|---|---|---|---|
| PowerShell first | connect fail | no | — | — | — |
| Retry TLS1.2 | **200** | **yes** | **1295** | **3600** | `access_token`, `id_token`, `expires_in`, `not-before-policy`, `scope`, `token_type`, `issued_token_type` |
| curl.exe | **200** | **yes** | **1295** | **3600** | same |

**Network:** DNS resolves; TCP 443 connects. First PS failure was transient/client stack; retry succeeded.

**Conclusion:** IAM access-key flow is valid for these credentials.

---

## B) APIs with token / key (read-only)

### B1) Foundation Models — list models

`GET https://foundation-models.api.cloud.ru/v1/models`

| Auth | HTTP | Model count | GigaChat ids present |
|---|---|---|---|
| IAM Bearer | 200 | 98 | yes (sample count 3 in first pass) |
| Key Secret as Bearer | 200 | 98 | yes |
| No auth | 200 | 98 | yes |
| Garbage Bearer | 200 | 98 | yes |

**First 15 model ids (public catalog):**

1. `ai-sage/GigaChat3.5-432B-A28B`
2. `GigaChat/GigaChat-2-Max`
3. `ai-sage/GigaChat3-10B-A1.8B`
4. `hivetrace/HiveTraceGuard-Pro`
5. `zai-org/GLM-5.1`
6. `moonshotai/Kimi-K2.6`
7. `deepseek-ai/DeepSeek-V4-Pro`
8. `MiniMaxAI/MiniMax-M3`
9. `MiniMaxAI/MiniMax-M2.5`
10. `zai-org/GLM-4.7`
11. `openai/gpt-oss-120b`
12. `Qwen/Qwen3.5-397B-A17B`
13. `Qwen/Qwen3.6-35B-A3B`
14. `Qwen/Qwen3-Coder-Next`
15. `Qwen/Qwen3-Embedding-0.6B`

### B2) Tiny chat (max 1 intentional spend probe family; several auth variants)

`POST https://foundation-models.api.cloud.ru/v1/chat/completions`  
Model tried: `ai-sage/GigaChat3-10B-A1.8B`, `max_tokens=8`, prompt `ping`

| Auth variant | HTTP | Result |
|---|---|---|
| Bearer Key Secret | 400 | `InvalidArgument` — invalid api key secret |
| Bearer IAM JWT | 400 | `InvalidArgument` — id invalid UUID (len 72 mentioned in error type) |
| `x-api-key: secret` | 400 | invalid api key secret |
| Bearer `keyId:secret` | 400 | invalid api key secret |
| Bearer Key ID only | 400 | invalid api key secret |
| Basic keyId:secret | 403 | `AccessDenied` — invalid authorization header format |

**No successful completion.** Do not treat IAM access keys as FM inference keys.  
**Next:** create/copy **Foundation Models API key** (UUID id) from Cloud.ru console / FM section; keep out of git.

### B3) Compute free-tier flavors

`GET https://compute.api.cloud.ru/api/v1/flavors?free_tier=true&limit=10`

| Auth | HTTP | Notes |
|---|---|---|
| Bearer Key Secret | **401** | unauthorized |
| Bearer IAM | **422** | empty body (no JSON keys); likely missing `project_id` / project scope |

**project_id:** not discovered (stopped; no URL spray). Console/project binding required before compute GETs are useful.

### B4) S3 — ListBuckets only (no create)

**Endpoint:** `https://s3.cloud.ru/`

| Method | HTTP | Notes |
|---|---|---|
| Bearer Key Secret | **200** | XML `ListAllMyBucketsResult`, Owner present, **0** bucket names |
| Bearer IAM | **200** | same, empty list, body_len ≈ 170 |
| SigV4 with Key ID/Secret as AWS keys (`ru-central-1`, `ru-central1`, `default`) | 400/403 | no reliable List with classic SigV4; tenant-prefixed access key format unknown → skipped |

**Conclusion:** Object listing via Bearer returns empty bucket set. No buckets created. SigV4 path needs documented Cloud.ru S3 access-key format (often tenant-scoped) — not confirmed here.

---

## C) GitVerse REST + SSH

**Base:** `https://api.gitverse.ru`  
**Headers:** `Authorization: Bearer <token>`, `Accept: application/vnd.gitverse.object+json;version=1`

| Call | HTTP | Result (no secrets) |
|---|---|---|
| `GET /user` | **200** | `login=Alexey_Borovskoy` |
| `GET /user/repos?per_page=30` | **200** | **count=2** — `Alexey_Borovskoy/NAS_HOME`, `Alexey_Borovskoy/ripas_asudd` |
| `GET /repos/Alexey_Borovskoy/NAS_HOME` | **200** | `private=True`, `visibility=private`, `default_branch=master` |

**SSH:** `git ls-remote git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git`

- Local key file exists; `.pub` type `ssh-ed25519` (comment indicates another project identity).
- Server: **`Permission denied (publickey)`** — key not registered (or wrong key) for this GitVerse user.
- REST token path is sufficient for API; git mirror over SSH needs pubkey upload in GitVerse settings (or HTTPS token remote — token not stored in repo).

---

## Risks

1. **FM chat will fail** in gateway until a real FM/GigaChat API key is provisioned (separate from IAM access key).
2. **Compute** blocked without project id / IAM project binding.
3. **S3 empty** — off-site restic target not created yet (by design this probe did not create).
4. **SSH GitVerse** not ready; avoid assuming deploy keys work.
5. Credentials live only on workstation downloads/SSH paths — never copy into NAS git tree.

---

## Next safe steps

1. Cloud.ru console: create **Foundation Models API key** (UUID); store in local secrets only; smoke **one** chat call.
2. Note **project_id** for Evolution Compute; retry flavors with documented project header/query.
3. If off-site backup wanted: create **one** S3 bucket via console (not agent), then restic config with proper S3 keys.
4. GitVerse: add `gitverse_ed25519.pub` to user SSH keys **or** use HTTPS remote with token outside git.
5. Wire gateway env to FM key when ready; keep DeepSeek fallback until chat 200 proven.
6. Optional: re-run this probe checklist after FM key exists (`AUTH_PROBE_…` follow-up date).

---

## Rollback / cleanup

- No cloud resources created.
- No git push / no secret commits.
- Temp dir under `%TEMP%\sber_auth_probe_20260907` removed after report write.
