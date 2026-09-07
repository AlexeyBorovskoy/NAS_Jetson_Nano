# Public read-only probe: Cloud.ru + GitVerse

> **Date:** 2026-09-04 (inventory revised same day)  
> **Mode:** documentation + OpenAPI first; limited public live probes only where method+path confirmed  
> **Scope:** NAS_Jetson_Nano API inventory (no secrets, no creates)  
>
> **Rules (owner 2026-09-04):** do **not** GET API roots (`…api.cloud.ru/`); 404 on `/` = `ROOT_PATH_NOT_IMPLEMENTED`, not “API missing”. Do not GET methods that OpenAPI defines as POST/PUT/…. Do not re-hit GitVerse docs under 429. WebFetch ≠ curl with custom headers.
>
> Status vocabulary:
> - `CONFIRMED_PUBLIC` — correct method+path live without auth
> - `CONFIRMED_AUTH_REQUIRED` — correct path live; OpenAPI/docs require auth; unauth got 401/403 or docs mandate token
> - `DOC_CONFIRMED_NOT_PROBED` — path/method from official docs/OpenAPI; no correct live probe yet
> - `ROOT_PATH_NOT_IMPLEMENTED` — GET `/` on API host returned 404 (expected)
> - `WRONG_HTTP_METHOD` — probed with wrong verb (e.g. GET on POST-only)
> - `RATE_LIMITED` — HTTP 429
> - `TRANSPORT_ERROR` — network/TLS failure
> - `NOT_VERIFIED` — insufficient data

**Not done:** authorized calls, IAM token POST, GitVerse Bearer, resource create.

**Secrets:** none used, none written.

---

## 0. Canonical API inventory (docs/OpenAPI first)

| Service | Official docs URL | Base endpoint | Confirmed API path | HTTP method | Authentication | Public probe possible | Probe result | Interpretation | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| **IAM OpenID token** | [console_api quickstart](https://cloud.ru/docs/console_api/ug/topics/quickstart?source-platform=Evolution) | `https://auth.iam.cloud.ru` | `/auth/system/openid/token` | **POST** | `grant_type=access_key` + `client_id` + `client_secret` (form); returns Bearer | **No** (needs secrets) | GET was tried earlier → 404 | Token mint is POST-only; GET = wrong method | High |
| **IAM static API keys** | [static keys](https://cloud.ru/docs/console_api/ug/topics/guides__static-api-keys?source-platform=Evolution) | (console / console_api) | manage keys via guides + [api-ref static keys](https://cloud.ru/docs/console_api/ug/topics/api-ref__static-api-keys?source-platform=Evolution) | per guide | SA-bound static key, service-scoped | No for create; list needs auth | — | Alternate auth to per-service Bearer without token exchange | High |
| **Foundation Models — list models** | [api-ref](https://cloud.ru/docs/foundation-models/ug/topics/api-ref?source-platform=Evolution) + [OpenAPI YAML](https://cloud.ru/docs/api/specs/foundation-models/ug/_downloads/f2949c1237d79b17b2df8e523e02a89a/openapi__foundation-models.yaml?source-platform=Evolution) | `https://foundation-models.api.cloud.ru` | `/v1/models` | **GET** | OpenAPI: BearerAuth; **live unauth returned 200** | **Yes** (catalog) | **200**, 98 models | Catalog is publicly readable; inference still keyed | High → **CONFIRMED_PUBLIC** |
| **Foundation Models — chat** | same OpenAPI | same | `/v1/chat/completions` | **POST** | BearerAuth | **No** without key; must not GET | GET → 404 earlier | Inference only via POST + key | High → chat = **CONFIRMED_AUTH_REQUIRED** (docs); GET = **WRONG_HTTP_METHOD** |
| **Virtual Machines — flavors** | [api-ref](https://cloud.ru/docs/virtual-machines/ug/topics/api-ref?source-platform=Evolution) + [openapi-v3.yaml](https://cloud.ru/docs/api/specs/virtual-machines/ug/_downloads/43c42ff22a171c77371e690a08181c3f/openapi-v3.yaml?source-platform=Evolution) | `https://compute.api.cloud.ru` | `/api/v1/flavors` | **GET** | `userPlaneApiToken` (Bearer) | No (auth) | unauth **403** | Path correct; auth required; supports `free_tier` query | High → **CONFIRMED_AUTH_REQUIRED** |
| **Virtual Machines — AZs** | same OpenAPI | same | `/api/v1/availability-zones` | **GET** | Bearer | No | not probed correctly beyond OpenAPI | List AZs; `free_tier_default` query in schema | High docs → **DOC_CONFIRMED_NOT_PROBED** |
| **Virtual Machines — disks** | same OpenAPI | same | `/api/v1/disks` | **GET** list / **POST** create | Bearer | GET list only after auth; POST forbidden now | — | List needs `project_id`; create = paid risk | High → GET **DOC_CONFIRMED_NOT_PROBED**; POST out of scope |
| **Virtual Machines — root /** | — | `https://compute.api.cloud.ru` | `/` | GET | n/a | n/a | **404** | Not an API resource | High → **ROOT_PATH_NOT_IMPLEMENTED** |
| **Object Storage S3** | [api getting-started](https://cloud.ru/docs/s3e/ug/topics/api__getting-started?source-platform=Evolution) | `https://s3.cloud.ru` | S3 API (`ListBuckets`, `ListObjects`, …) via AWS CLI/SDK | GET-like S3 ops | AWS **SigV4**; Access Key ID = `tenant_id:key_id` | Anonymous ListBuckets returned empty XML | **200** empty buckets | Host public; tenant data needs SigV4 | High host public; tenant **CONFIRMED_AUTH_REQUIRED** |
| **Managed PostgreSQL** | [api-ref](https://cloud.ru/docs/paas-postgresql/ug/topics/api-ref?source-platform=Evolution) | `https://postgresql.api.cloud.ru` | paths on [api-ref__postgresql](https://cloud.ru/docs/paas-postgresql/ug/topics/api-ref__postgresql?source-platform=Evolution) | per that page | auth page in section | No until path list from OpenAPI without guessing | root GET 404 only | Do not invent paths | Med → base **DOC_CONFIRMED**; ops **DOC_CONFIRMED_NOT_PROBED** |
| **Container Apps** | [api-ref](https://cloud.ru/docs/container-apps-evolution/ug/topics/api-ref?source-platform=Evolution) | `https://containers.api.cloud.ru` | paths on [api__container-apps](https://cloud.ru/docs/container-apps-evolution/ug/topics/api__container-apps?source-platform=Evolution) | per page | auth in section | No | root 404 only | Same | Med → **DOC_CONFIRMED_NOT_PROBED** |
| **Artifact Registry** | [api-ref](https://cloud.ru/docs/artifact-registry-evolution/ug/topics/api-ref?source-platform=Evolution) | `https://ar.api.cloud.ru` | paths on [api__artifact-registry](https://cloud.ru/docs/artifact-registry-evolution/ug/topics/api__artifact-registry?source-platform=Evolution) | per page | auth in section | No | root 404 only | Same | Med → **DOC_CONFIRMED_NOT_PROBED** |
| **Managed RAG — Public API** | [api](https://cloud.ru/docs/rag/ug/topics/api?source-platform=Evolution) | `https://managed-rag.api.cloud.ru` | paths in [public-managed-rag](https://cloud.ru/docs/rag/ug/topics/api-ref__public-managed-rag?source-platform=Evolution) | per specs | auth | No | root 404 only | KB manage API | Med → **DOC_CONFIRMED_NOT_PROBED** |
| **Managed RAG — Search API** | same | `https://<knowledge_base_public_url>.managed-rag.inference.cloud.ru` | search paths in Search API spec | per specs | KB access token | No (instance-specific) | — | Per-KB hostname | Med → **DOC_CONFIRMED_NOT_PROBED** |
| **AI Agents** | [api-ref](https://cloud.ru/docs/ai-agents/ug/topics/api-ref?source-platform=Evolution) | (see [authentication](https://cloud.ru/docs/ai-agents/ug/topics/api-ref__authentication?source-platform=Evolution) + [specs](https://cloud.ru/docs/ai-agents/ug/topics/api-ref__specs?source-platform=Evolution)) | per specs | per specs | auth required | No | — | Agents/MCP manage | Med → **DOC_CONFIRMED_NOT_PROBED** |
| **API registry (index)** | [reestr_api](https://cloud.ru/docs/console_api/ug/topics/overview__reestr_api?source-platform=Evolution) | n/a | n/a | n/a | n/a | n/a | page loaded | Index of official API refs | High |
| **GigaChat PERS (Sber developers)** | [gigachat guides](https://developers.sber.ru/docs/ru/gigachat/guides/main) | `https://api.giga.chat` (new); OAuth `ngw.devices.sberbank.ru:9443` | `/v1/models`, `/v1/chat/completions`, `/balance`, … | GET models; POST chat; POST oauth | OAuth Basic→Bearer 30m, scope PERS | models/balance need token | earlier session OAuth+models OK | Separate from Cloud.ru FM | High (prior probe) |
| **GitVerse Public API** | Belgorod/NAS notes + intended [public-api docs](https://gitverse.ru/docs/developers/public-api/) / [rest-api-description](https://gitverse.ru/gitverse/rest-api-description) | `https://api.gitverse.ru` | `/user`, `/user/repos`, `/repos/{owner}/{repo}`, issues… | mostly **GET** for read | Bearer + `Accept: application/vnd.gitverse.object+json;version=1` | Not via WebFetch (headers); curl later | docs **429**; `/user` no auth **400** | Auth + headers required; docs rate-limited | Med → API **CONFIRMED_AUTH_REQUIRED**; docs **RATE_LIMITED** |
| **GitVerse git SSH** | ssh config / prior session | `git@gitverse.ru` | `Alexey_Borovskoy/NAS_HOME.git` | git protocol | SSH key | n/a this pass | earlier ls-remote OK | Mirror exists | High (prior) |

---

## 0b. Status rollup

| Classification | Items |
|---|---|
| **CONFIRMED_PUBLIC** | FM `GET /v1/models` (98 ids); S3 endpoint anonymous empty ListBuckets |
| **CONFIRMED_AUTH_REQUIRED** | VM `GET /api/v1/flavors` (403); FM chat POST; S3 tenant; GitVerse REST; GigaChat after OAuth; IAM usage of APIs |
| **DOC_CONFIRMED_NOT_PROBED** | VM AZs/disks GET; PG/CA/AR path ops; RAG Public/Search; AI Agents specs |
| **ROOT_PATH_NOT_IMPLEMENTED** | GET `/` on compute, postgresql, containers, ar, managed-rag hosts |
| **WRONG_HTTP_METHOD** | GET IAM token URL; GET FM chat/completions |
| **RATE_LIMITED** | gitverse.ru docs / rest-api-description |
| **NOT_VERIFIED** | full GitVerse Issues/CI/webhooks path list without OpenAPI body this session |

---

## 1. Cloud.ru — confirmed hosts (from official docs)

| Service | Doc source | Runtime base (docs) | Auth scheme (docs) |
|---|---|---|---|
| IAM token | [console_api quickstart](https://cloud.ru/docs/console_api/ug/topics/quickstart?source-platform=Evolution) | `POST https://auth.iam.cloud.ru/auth/system/openid/token` body `grant_type=access_key` + client_id/secret | access key → Bearer token |
| Static API keys | [static keys](https://cloud.ru/docs/console_api/ug/topics/guides__static-api-keys?source-platform=Evolution) | per-service | Bearer static key (SA), service-scoped |
| Foundation Models | [api-ref](https://cloud.ru/docs/foundation-models/ug/topics/api-ref?source-platform=Evolution) | `https://foundation-models.api.cloud.ru/v1/` | Bearer API key (SA, service FM) |
| Virtual Machines | [api-ref](https://cloud.ru/docs/virtual-machines/ug/topics/api-ref?source-platform=Evolution) | `https://compute.api.cloud.ru` | Bearer (`userPlaneApiToken` in OpenAPI) |
| Object Storage | [api getting-started](https://cloud.ru/docs/s3e/ug/topics/api__getting-started?source-platform=Evolution) | `https://s3.cloud.ru` (AWS CLI `--endpoint-url`) | AWS SigV4; Access Key = `tenant_id:key_id` |
| Managed PostgreSQL | [api-ref](https://cloud.ru/docs/paas-postgresql/ug/topics/api-ref?source-platform=Evolution) | `https://postgresql.api.cloud.ru` | auth page in same section |
| Container Apps | [api-ref](https://cloud.ru/docs/container-apps-evolution/ug/topics/api-ref?source-platform=Evolution) | `https://containers.api.cloud.ru` | auth page in same section |
| Artifact Registry | [api-ref](https://cloud.ru/docs/artifact-registry-evolution/ug/topics/api-ref?source-platform=Evolution) | `https://ar.api.cloud.ru` | auth page in same section |
| Managed RAG | [api](https://cloud.ru/docs/rag/ug/topics/api?source-platform=Evolution) | Public API `https://managed-rag.api.cloud.ru`; Search `https://<kb>.managed-rag.inference.cloud.ru` | per api-ref quickstart |
| AI Agents | [api-ref](https://cloud.ru/docs/ai-agents/ug/topics/api-ref?source-platform=Evolution) | (in authentication + specs pages) | auth required |
| API registry | [reestr](https://cloud.ru/docs/console_api/ug/topics/overview__reestr_api?source-platform=Evolution) | links to all Evolution API refs | — |

OpenAPI downloads used:
- FM: [openapi__foundation-models.yaml](https://cloud.ru/docs/api/specs/foundation-models/ug/_downloads/f2949c1237d79b17b2df8e523e02a89a/openapi__foundation-models.yaml?source-platform=Evolution) — paths `/v1/models`, `/v1/chat/completions`
- VM: [openapi-v3.yaml](https://cloud.ru/docs/api/specs/virtual-machines/ug/_downloads/43c42ff22a171c77371e690a08181c3f/openapi-v3.yaml?source-platform=Evolution) — e.g. `GET /api/v1/flavors` (security required), disks, AZs, free_tier filter on flavors

---

## 2. Live public probe results

| Target | Method | Result code / note | Classification |
|---|---|---|---|
| `GET https://foundation-models.api.cloud.ru/v1/models` | GET no auth | **200** OpenAI-style list; **98** models; ids include GigaChat×3, DeepSeek×10, Qwen×19, whisper×1, embedding×6, rerank×4, OCR×1 | **CONFIRMED_PUBLIC** |
| `GET https://foundation-models.api.cloud.ru/v1/chat/completions` | GET (wrong method; chat is POST) | 404 | **WRONG_PROBE_METHOD** (POST + auth expected per OpenAPI) |
| `GET https://auth.iam.cloud.ru/auth/system/openid/token` | GET | 404 | **WRONG_PROBE_METHOD** (docs: **POST** form-urlencoded only) |
| `GET https://compute.api.cloud.ru/` | GET root | 404 | bare root not a resource; API is under `/api/v1/...` |
| `GET https://compute.api.cloud.ru/api/v1/flavors?limit=1` | GET no auth | **403** (host+path live; OpenAPI security) | **CONFIRMED_AUTH_REQUIRED** |
| `GET https://postgresql.api.cloud.ru/` | GET root | 404 | host resolves; path needs api-ref paths + auth → **DOC_ONLY** / auth |
| `GET https://containers.api.cloud.ru/` | GET root | 404 | same |
| `GET https://ar.api.cloud.ru/` | GET root | 404 | same |
| `GET https://s3.cloud.ru/` | GET no auth | **200** XML `ListAllMyBucketsResult` empty Owner/Buckets | **CONFIRMED_PUBLIC** host; **empty anonymous list** (not your tenant data) |
| `GET https://managed-rag.api.cloud.ru/` | GET root | 404 | base confirmed in docs; root empty → **DOC_ONLY** until path+auth |
| `GET https://api.giga.chat/v1/models` | GET | transport error this session | **NOT_VERIFIED** here (separate PERS stack; previously live with OAuth) |

**FM public model sample (ids only, not full JSON):**  
`ai-sage/GigaChat3.5-432B-A28B`, `GigaChat/GigaChat-2-Max`, `ai-sage/GigaChat3-10B-A1.8B`, `deepseek-ai/DeepSeek-V4-Pro`, `Qwen/Qwen3-Coder-Next`, `BAAI/bge-m3`, `openai/whisper-large-v3`, `deepseek-ai/DeepSeek-OCR-2`, plus many external GPT/Claude/Gemini ids in the same catalog.

**Note:** Public `GET /v1/models` does **not** mean free inference. Chat/completions and paid metering still require API key per docs (20 rps/key on product page).

---

## 3. GitVerse

| Target | Result | Classification |
|---|---|---|
| Docs `gitverse.ru/docs/developers/public-api/` | HTTP **429** | **CONFIRMED_RATE_LIMITED** |
| OpenAPI page `gitverse.ru/gitverse/rest-api-description` | HTTP **429** | **CONFIRMED_RATE_LIMITED** |
| `GET api.gitverse.ru/user` no auth | **400** (earlier session) | **CONFIRMED_AUTH_REQUIRED** (needs Bearer + Accept header per Belgorod/NAS notes) |
| `GET api.gitverse.ru/users/Alexey_Borovskoy` no auth | **400** | needs headers and/or auth — **NOT_VERIFIED** as public without Accept |
| SSH `git@gitverse.ru` / `ls-remote NAS_HOME` | OK in earlier session (key on machine) | authenticated git path exists; not re-run this public-only pass |

API host (from project notes + Belgorod access_registry, not re-fetched under 429):  
`https://api.gitverse.ru` with headers `Authorization: Bearer …` and `Accept: application/vnd.gitverse.object+json;version=1`.

---

## 4. What is available publicly vs needs authentication

### Public without credentials
- **FM model catalog** listing (98 ids) — discovery only.
- **S3 endpoint host** answers (anonymous empty bucket list).
- **Official documentation + OpenAPI YAML downloads** for FM and VM.
- Product/marketing free-tier descriptions (S3 15 GB std, Container Apps CPU/RAM hours, etc.) — docs only.

### Requires authentication (do not call until owner allows)
- IAM **POST** token exchange (`grant_type=access_key`).
- FM **POST** `/v1/chat/completions` (and any non-list inference).
- VM **GET/POST** under `compute.api.cloud.ru/api/v1/*` (flavors may still need token per OpenAPI security).
- PostgreSQL, Container Apps, Artifact Registry project-scoped APIs.
- Object Storage **tenant** list/put/get with SigV4 keys.
- Managed RAG Public + Search APIs.
- AI Agents Public API.
- GitVerse user/repos/issues/CI with Bearer.
- GigaChat PERS OAuth + chat (separate key store).

---

## 5. Safe step-2 operations (read-only, after explicit owner OK)

Only after permission to use existing credentials. **Still no creates.**

| # | Call | Purpose | Abort if |
|---|---|---|---|
| 1 | `POST auth.iam.cloud.ru/.../token` access_key | obtain Bearer | non-2xx |
| 2 | `GET compute.../api/v1/flavors?free_tier=true&limit=20` | free-tier VM SKUs | would POST |
| 3 | `GET compute.../api/v1/availability-zones?free_tier_default=true` | AZ free tier | — |
| 4 | FM Bearer `GET /v1/models` | confirm key scope FM | — |
| 5 | FM `POST /v1/chat/completions` **max_tokens≤16** internal model e.g. `ai-sage/GigaChat3-10B-A1.8B` | smoke (may consume tokens/bonus) | owner forbids any spend |
| 6 | S3 `aws s3 ls --endpoint-url https://s3.cloud.ru` | list **existing** buckets only | no `mb` |
| 7 | PG/Containers/AR list GET if paths known from OpenAPI | inventory empty/non-empty | no POST |
| 8 | GitVerse `GET /user`, `GET /user/repos`, `GET /repos/.../NAS_HOME` | mirror state | no create repo |
| 9 | Billing GET balance if api-ref path known | bonus/ruble | — |

**Forbidden in step 2:** VM create, disk create, bucket create, RAG KB create, agent create, git push, IAM role change, key reissue without backup.

---

## 6. Relation to NAS plan

- FM public catalog validates **Cloud.ru multi-model edge** for LLM Gateway adapter (phase C in `SBER_PLATFORM_IMPLEMENTATION_PLAN.md`).
- S3 endpoint validates **off-site object target** candidate (encrypted restic), separate from on-site HDD Immich copy.
- VM OpenAPI `free_tier` filters support **optional always-on small compute** research — not decided.
- GitVerse rate limits mean docs must be cached locally; API probe needs credentials + Accept header.

---

## 7. EN summary

Public probe only: Foundation Models `GET /v1/models` returns 98 models without auth (catalog). S3 host responds anonymously with empty bucket list. IAM token and nearly all IaaS/PaaS APIs require authentication (POST token or SigV4). GitVerse docs hit 429; user API needs Bearer. No secrets used. Step-2 is owner-gated read-only inventory with existing keys.

---

## 8. Next action

Owner phrase to continue: **«разрешаю auth probe Cloud.ru+GitVerse read-only»**  
Then execute §5 only; append results to a new dated section (still no secret values).
