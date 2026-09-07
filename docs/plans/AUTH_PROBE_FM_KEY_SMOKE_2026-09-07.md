# Auth probe: Foundation Models static key smoke (2026-09-07)

**Date:** 2026-09-07  
**Scope:** Read-only / tiny-spend inference smoke against Cloud.ru Foundation Models.  
**No secrets** in this file (no key material, no Key ID/Secret, no full Authorization values).  
**Credential source (host only, plaintext):** `C:\Users\Alexey\Downloads\сбер\git.md` → section **«Данные API-ключа»** (one-line value; structure `part.part`, lengths 48.32).  
**Base URL:** `https://foundation-models.api.cloud.ru/v1`

**Jetson env (later, do not commit value):** `CLOUDRU_FM_API_KEY`  
**Related:** `docs/integrations/sber/CLOUD_RU.md`, `docs/plans/AUTH_PROBE_SA_HOME_NAS_API_2026-09-07.md`

---

## Executive result

| Finding | Result |
|---|---|
| Working auth header | **`Authorization: Bearer <CLOUDRU_FM_API_KEY>`** |
| `Authorization: Api-Key …` | **FAIL 403** — `AccessDenied` / invalid authorization header format (full key and secret-only part) |
| Chat inference (pre top-up) | **Auth OK, billing block** — HTTP **402** `Not enough money` |
| Chat inference (**post top-up 2026-09-07**) | **HTTP 200** — see re-probe table below |
| `GET /v1/models` | **200**, ~98 models; **public without auth** (catalog) |
| Key storage risk | Still **plaintext in Downloads** — move to password manager; never commit |

**Bottom line:** FM static key from «Данные API-ключа» is accepted as **Bearer**. After owner balance top-up, chat completions return **200** with `finish_reason=stop`.

---

## Attempts (chat completions)

**Endpoint:** `POST /v1/chat/completions`  
**Body shape:** `model`, `messages: [{role:user, content:"ping"}]`, `max_tokens: 8`

| # | Auth style | Model | HTTP | Success | finish_reason | content_len | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Api-Key` | `ai-sage/GigaChat3-10B-A1.8B` | **403** | n | — | 0 | `AccessDenied`: Invalid authorization header format |
| 2 | `Bearer` | `ai-sage/GigaChat3-10B-A1.8B` | **402** | n | — | 0 | `Not enough money` — **auth accepted** |
| 3 | `Api-Key` | `GigaChat/GigaChat-2-Max` | **403** | n | — | 0 | same format reject |
| 4 | `Bearer` | `GigaChat/GigaChat-2-Max` | **402** | n | — | 0 | billing |
| 5 | `Api-Key` | `ai-sage/GigaChat3.5-432B-A28B` (first giga from public list) | **403** | n | — | 0 | same |
| 6 | `Bearer` | `ai-sage/GigaChat3.5-432B-A28B` | **402** | n | — | 0 | billing |
| 7 | `api-key` (lowercase scheme) | GigaChat3-10B | **403** | n | — | 0 | format reject |
| 8 | `X-API-Key` header only | GigaChat3-10B | **401** | n | — | 0 | Missing authorization |
| 9 | `Api-Key` + secret segment only (after `.`) | GigaChat3-10B | **403** | n | — | 0 | format reject |

No completion text returned on any attempt (no preview) **before** top-up.

### Re-probe after balance top-up (2026-09-07 ~13:40 UTC)

**Body:** `messages: [{role:user, content:"Ответь одним словом: ок"}]`, `max_tokens: 16`  
**Auth:** `Authorization: Bearer` (same key source)

| # | Model | HTTP | Success | finish_reason | content (short) | usage (p/c/t) |
|---|---|---|---|---|---|---|
| 10 | `ai-sage/GigaChat3-10B-A1.8B` | **200** | y | `stop` | `Да` | 997 / 2 / 999 |
| 11 | `GigaChat/GigaChat-2-Max` | **200** | y | `stop` | `Ок` | 18 / 2 / 20 |

Notes: response `model` for #11 may show `GigaChat/GigaChat-2-Max:latest`. Prompt token count on #10 is elevated (server-side accounting); completion still tiny. No secrets logged.

---

## GET /models

| Auth | HTTP | Notes |
|---|---|---|
| none | **200** | Public catalog (~98) |
| `Api-Key` | **200** | Same catalog (not proof of key validity) |
| `Bearer` | **200** | Same catalog |

Sample id observed: `ai-sage/GigaChat3.5-432B-A28B` (first giga-like id in list order used for alt chat).

---

## Header guidance (docs vs live)

| Source | Claim | Live 2026-09-07 |
|---|---|---|
| Some internal notes / static-key guides | `Authorization: Api-Key <secret>` | **403** with this key material |
| `docs/integrations/sber/CLOUD_RU.md` | Bearer (SA API key scoped to FM) | **Matches live** — Bearer accepted (402 billing) |
| OpenAPI BearerAuth | Bearer | **Matches** |

Use **Bearer + `CLOUDRU_FM_API_KEY`** for Jetson/gateway until Cloud.ru docs for this key type say otherwise. Re-test `Api-Key` only if console issues a differently formatted FM-scoped static key.

---

## Security

1. **Do not** write the key into the repo, compose files committed to git, or agent coordination board.  
2. Host file `Downloads\сбер\git.md` still holds plaintext key (+ IAM Key ID/Secret nearby) — **password manager** (or OS secret store) and delete/rotate plaintext copy when practical.  
3. Jetson: export `CLOUDRU_FM_API_KEY` from env/secret file with mode `600`, not from git.  
4. Optional companion env: `CLOUDRU_FM_BASE_URL=https://foundation-models.api.cloud.ru/v1`, `CLOUDRU_FM_MODEL=ai-sage/GigaChat3-10B-A1.8B`.

---

## Verify after billing top-up

```bash
# On operator host or Jetson — key from env only
curl -sS -o /tmp/fm_out.json -w "%{http_code}\n" \
  -X POST "${CLOUDRU_FM_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${CLOUDRU_FM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"ai-sage/GigaChat3-10B-A1.8B","messages":[{"role":"user","content":"ping"}],"max_tokens":8}'
# Expect: HTTP 200, choices[0].finish_reason set, small content_len
```

---

## Risks

- Balance can drain — keep `max_tokens` low on smokes; monitor Cloud.ru billing.  
- Conflicting internal docs (`Api-Key` vs `Bearer`) — live key behaves as **Bearer**.  
- Plaintext key in Downloads increases leak risk.  
- Catalog `GET /models` is public — do not treat 200 on models as auth proof.

## Next safe step

1. Install `CLOUDRU_FM_API_KEY` on Jetson via secret channel (env/file mode `600`); never commit.  
2. Device/gateway smoke: `provider=cloudru` with default model `ai-sage/GigaChat3-10B-A1.8B` (needs «деплой»).  
3. Remove or encrypt plaintext copy under Downloads; rotate key if file was shared.
