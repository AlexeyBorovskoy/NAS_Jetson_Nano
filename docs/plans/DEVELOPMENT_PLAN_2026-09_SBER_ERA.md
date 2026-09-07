# План развития NAS_Jetson_Nano — эра Сбер / Cloud.ru (2026-09)

> **Статус:** канон развития (замена операционной части `docs/31_MASTER_PLAN.md` 2026-08-22).  
> **Дата:** 2026-09-04 · **Обновлено:** 2026-09-07 (commit pack + Cloud.ru/GitVerse live)  
> **Входы владельца:** станция RTX и Vostro **вне проекта**; Immich 2-я копия на HDD Jetson; Сбер/Cloud.ru/GitVerse; деплой Jetson — только по «деплой».  
> **Доказательная база:** audit 2026-08-30; probes 2026-09-04…07; offline pack + unit tests.
>
> 🇬🇧 Project canon for development. EN summary §14.

---

## Progress log / Журнал выполнения

| Когда | Шаг | Статус | Артефакты |
|---|---|---|---|
| 2026-09-04 | W0.2 ADR-0007 node model | ✅ git | `docs/decisions/ADR-0007-…` |
| 2026-09-04 | W0.3 ADR-0008 LLM Giga first | ✅ git | `docs/decisions/ADR-0008-…` |
| 2026-09-04 | W0.4 ADR-0009 backup topology | ✅ git | `docs/decisions/ADR-0009-…` |
| 2026-09-04 | W0.5 banners 29–31 | ✅ git | superseded notes |
| 2026-09-04 | W0.9 `docs/integrations/sber/` | ✅ git | README, GIGACHAT, CLOUD_RU, GITVERSE |
| 2026-09-04 | W1 templates (no device deploy) | ✅ git | `.env.example`, compose defaults, Talk `TALK_BOT_LLM_PROVIDER` |
| 2026-09-04 | W1.1–1.3 **device cutover** | ⏳ blocked | needs «деплой»; runbook `DEPLOY_W1_GIGA_CUTOVER.md` |
| 2026-09-04 | W2 Immich→HDD script | ✅ git | `scripts/backup/immich_hdd_second_copy.sh` |
| 2026-09-07 | W1 gateway code defaults + 1-flight lock | ✅ git | `services/llm-gateway/app/main.py` |
| 2026-09-07 | W2 systemd timer/service | ✅ git | `systemd/nas_jetson_nano-immich-hdd-copy.*` |
| 2026-09-07 | docs 12 / deploy runbook | ✅ git | `12_BACKUP_RESTORE.md`, `DEPLOY_W1_GIGA_CUTOVER.md` |
| 2026-09-07 | W2 **install on device** | ⏳ blocked | deploy |
| 2026-09-04 | W3 Cloud.ru / W4 GitVerse push | ⏳ later | |
| 2026-09-07 | Board: Sber Q&A open for `work` | ✅ | `E:\agent_coordination\shared\nas\SBER_OPEN_ACCESS_FOR_WORK.md` + BOARD #8 |
| 2026-09-07 | Workstation inventory (dev PC) | ✅ | `artifacts/reports/WORKSTATION_INVENTORY_2026-09-07.md` |
| 2026-09-07 | Code audit Sber | ✅ | `artifacts/reports/CODE_AUDIT_SBER_2026-09-07.md` |
| 2026-09-07 | Gateway: cloudru + balance + Giga→DS failover + tests | ✅ git | `main.py`, `test_sber_routing.py` |
| 2026-09-07 | **Offline Sber pack complete** | ✅ git | `OFFLINE_SBER_READY_PACK.md`, `scripts/sber/*`, `sber.env.snippet`, CONSOLE_CHECKLIST, FULL deploy |
| 2026-09-07 | Auth probe Cloud.ru + GitVerse (RO) | ✅ | `AUTH_PROBE_CLOUDRU_GITVERSE_2026-09-07.md` |
| 2026-09-07 | SA `home-nas-api` + project role | ✅ | SA id `8f07c1f7-…`; project `10dd738e-…`; `platform.project.admin` |
| 2026-09-07 | FM API key smoke | ✅ auth / ❌ 402 | Bearer OK; **Not enough money** — need grant/balance |
| 2026-09-07 | FM chat re-probe (post top-up) | ✅ **200** | `GigaChat3-10B` + `GigaChat-2-Max`; `finish_reason=stop`; see `AUTH_PROBE_FM_KEY_SMOKE` |
| 2026-09-07 | GitVerse remote + push | ✅ | `main`=`master`=`HEAD` aligned; HTTPS oauth2 token |
| 2026-09-07 | Docs refresh + commit this pack | ✅ | this release |
| 2026-09-07 | W3.3 S3 bucket + W4 SSH key API | ❌ blocked | S3 needs console tenant_id; GitVerse public API has no SSH keys — UI only |

### Snapshot 2026-09-07 (end of day)

| Item | State |
|---|---|
| Code/docs Sber-era | in git (this commit) |
| GitHub `origin/main` | push target |
| GitVerse `NAS_HOME` main+master | mirror of same tip after push |
| Jetson device cutover | **not** done (offline / no «деплой») |
| GigaChat PERS | keys owner-side; gateway ready |
| Cloud.ru FM inference | **OK** (200 chat) after top-up; key still host-only |
| Cloud.ru S3 bucket | **blocked** — need console tenant_id; no keys created |
| GitVerse SSH | **fail** — public API has no key endpoint; add in UI |
| Immich→HDD timer | units in git; not installed on device |

**Owner rule 2026-09-04:** git/docs/code autonomous; **no Jetson deploy** without «деплой».  
**Owner 2026-09-07:** Sber Q&A for `work` on board; GitVerse + FM key path confirmed.

---

## 0. Executive summary

| Было (31_MASTER / 30_NEXT_LEAP) | Стало (этот план) |
|---|---|
| 4 узла: Jetson + станция ML + Vostro off-site + VPS | **2 прод-узла:** Jetson + VPS; dev-ПК вне модели |
| Immich ML / Ollama на RTX | **Нет** зависимости от станции; ML — Cloud.ru FM / позже optional GPU VM |
| Off-site на Vostro restic | **On-site** 2-я копия Immich на HDD 2 ТБ; **off-site** → Cloud.ru Object Storage (restic) |
| LLM: DeepSeek default, Giga second, local third | **GigaChat PERS** family default; DeepSeek fallback; **Cloud.ru FM** multi-model edge |
| Код только GitHub | GitHub канон + **GitVerse `NAS_HOME` mirror** |
| «Слабый Jetson — потолок» | Jetson = **System of Record (SoR)** данных; интеллект и off-site — **edge в РФ-облаке** |

**Не ломаем:** Amnezia на VPS, LAN `.50`, redaction gateway, фото analysis off, quality gate, ADR-0003/0005.

---

## 1. Решения владельца (зафиксированы)

1. Рабочая станция (RTX 3050 Ti) — **только разработка**, не узел платформы.  
2. Vostro — **исключён** из архитектуры NAS (историческая Волна 0 phase 1 = legacy).  
3. Вторая копия Immich — **`/mnt/hdd2tb/...` на Jetson**, не off-site.  
4. Платформа Сбера — **усилить проект** (GigaChat freemium, Cloud.ru Evolution, GitVerse).  
5. Допустимы **переделка структуры** docs/кода и **пересмотр ограничений** Stage 1, без выноса семейных фото в LLM и без открытия NAS в интернет мимо VPN.

---

## 2. Новая целевая архитектура

```
                    ┌─────────────────────────────────────┐
                    │  Семья: Talk / Immich / Nextcloud     │
                    │  доступ только LAN или VPN→VPS       │
                    └─────────────────┬───────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ VPS Frankfurt   │         │ Jetson Nano     │         │ Cloud.ru Evol.  │
│ nginx, Amnezia  │◄─SSH R──│ SoR: NC+Immich  │──API───►│ FM · S3 · (VM?) │
│ reverse tunnel  │         │ Samba, bot, GW  │         │ free tier edge  │
│ НЕ хранит фото  │         │ SSD live+HDD×2  │         │ SANITIZED only  │
└─────────────────┘         └────────┬────────┘         └─────────────────┘
                                     │
                            GitHub ◄──┤──► GitVerse NAS_HOME
                                     │
                            GigaChat PERS (api.giga.chat)  freemium
                            DeepSeek API                   fallback
```

### 2.1. Роли (новая таблица)

| Узел | В архитектуре? | Роль | Запрещено |
|---|---|---|---|
| **Jetson** | ✅ SoR | Файлы, фото, БД, Samba, Talk-бот, LLM Gateway, алерты, on-site backup | Локальная LLM; CUDA Immich ML; хранить cloud secrets в git |
| **VPS** | ✅ edge net | Туннель, nginx, Amnezia (~19 peers), Beszel hub | Семейные bulk-данные; трогать Amnezia без check |
| **Cloud.ru** | ✅ edge AI/storage | FM multi-model; S3 off-site dumps/restic; optional small VM/Container Apps | Сырые семейные фото в FM/RAG без risk ADR; K8s «для галочки» |
| **GigaChat PERS** | ✅ family LLM | Default `@бобик`, freemium 365M/12м | 1 stream; analysis альбома Immich |
| **GitVerse** | ✅ mirror | `NAS_HOME` public/private mirror | Secrets; dual-pushurl origin; support backend |
| **Станция RTX** | ❌ out | IDE, git, occasional build | Любой timer/systemd «должен быть online» |
| **Vostro** | ❌ out | — | NAS backup/watchdog |

### 2.2. Пересмотренные ограничения

| Старое ограничение | Новое чтение |
|---|---|
| «Нет off-site» | Off-site = **S3 Cloud.ru** (encrypted), не Vostro |
| «Нет compute кроме станции» | Compute = **FM API** + optional **Cloud.ru VM/CA**; Jetson не считает ML |
| «Local model third provider» | Ollama path **deprecated in prod** (`LLM_PREFER_LOCAL=false`) |
| «Jetson RAM ceiling blocks AI» | AI **не на Jetson** — ceiling снимается архитектурно |
| «Только DeepSeek наружу» | **Giga first** (РФ, freemium) + DeepSeek + FM |
| «Документация = 31/30 про станцию» | Документы 29–31 **пометить superseded** этим планом |

### 2.3. Что остаётся жёстким (не пересматриваем)

- Amnezia / peer count / порты 22·443·40568.  
- Jetson `192.168.0.50`, профиль LAN.  
- Redaction + budget на **всех** cloud providers.  
- `LLM_ALLOW_IMAGE_ANALYSIS=false` default.  
- No secrets in git / GitVerse.  
- Quality gate before deploy.  
- Destructive disk/volume ops only with explicit OK.

---

## 3. Текущее состояние (факты 2026-09-04)

| Факт | Значение |
|---|---|
| Jetson | 13 containers healthy; tunnel up; SSD 6%; HDD 76% (462G free) |
| LLM Gateway | `gigachat=true`, default **deepseek**, `prefer_local=true`, model legacy `GigaChat`, URL devices.sberbank |
| GigaChat PERS balance | Lite ~250M, Pro 40M, Max ~25M, Ultra 50M |
| Stable model id | `GigaChat-2` on `api.giga.chat`; legacy `GigaChat` flaky/404 on new host |
| Embeddings PERS | **402** (нет пакета) |
| FM Cloud.ru | **GET /v1/models public** = 98 models (Giga/DeepSeek/Qwen/Whisper/OCR/…) |
| GitVerse | HTTPS mirror OK; SSH ❌ until UI key add; REST Bearer+Accept (no SSH API) |
| Cloud.ru keys | у владельца (Downloads); **не** в git; auth = IAM POST access_key |
| P0 audit | Immich single copy on SSD still CRITICAL until HDD copy live |

---

## 4. Волны работ (порядок)

Жёсткие зависимости: W0 → W1; W2∥W1; W3 after W1 auth OK; W4 structure anytime low-risk; W5 optional.

### Волна 0 — Документальный канон и структура репо (1–2 дня, git only)

**Зачем:** один источник правды; убрать противоречия «станция/Vostro».

| # | Задача | Артефакт |
|---|---|---|
| 0.1 | Этот план = entry для развития | `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` |
| 0.2 | ADR-0007: node model (Jetson SoR + VPS + Cloud.ru edge; no workstation/Vostro) | `docs/decisions/ADR-0007-…` |
| 0.3 | ADR-0008: LLM routing (Giga default, DeepSeek fallback, FM optional, no prod ollama) | `docs/decisions/ADR-0008-…` |
| 0.4 | ADR-0009: backup topology (SSD live, HDD on-site Immich, S3 off-site encrypted) | `docs/decisions/ADR-0009-…` |
| 0.5 | Banner на `31_MASTER_PLAN`, `30_NEXT_LEAP`, `29_COMPUTE…`: **superseded 2026-09** | правки 3 файлов |
| 0.6 | `docs/08_LLM_GATEWAY_*.md` rename/retitle multi-provider | docs |
| 0.7 | `CLAUDE.md` / README «Ближайшие задачи» синхрон с этим планом | CLAUDE, README |
| 0.8 | `docs/index.md` + `plans/README` ссылки | docs |
| 0.9 | Structure: `docs/integrations/sber/` указатель (Giga, Cloud.ru, GitVerse) | new thin index |
| 0.10 | Archive note: WAVE_0 Vostro = historical | WAVE_0 header |

**Не трогать:** docker/systemd paths на устройстве в этой волне.

### Волна 1 — GigaChat family-ready на Jetson (P0 UX + cost)

| # | Задача | Verify |
|---|---|---|
| 1.1 | Device `.env`: `GIGACHAT_BASE_URL=https://api.giga.chat/v1`, `GIGACHAT_MODEL=GigaChat-2`, image Max | chat 200 |
| 1.2 | `LLM_PREFER_LOCAL=false` | health prefer_local false |
| 1.3 | `LLM_PROVIDER=gigachat` **или** dual (owner pick); Talk payload `provider` | @бобик via Giga |
| 1.4 | Semaphore 1 in-flight Giga | no parallel storm |
| 1.5 | `/v1/provider/gigachat/balance` + daily alert threshold | balance visible |
| 1.6 | DeepSeek hard fallback on 429/5xx | test |
| 1.7 | Regression: analysis 403; generate text-only OK | tests |
| 1.8 | `.env.example` + compose defaults align | git |

**Rollback:** restore previous env keys; `LLM_PROVIDER=deepseek`.

### Волна 2 — Immich → HDD 2 ТБ (P0 data) ∥ с W1

| # | Задача | Verify |
|---|---|---|
| 2.1 | Каталог `/mnt/hdd2tb/backups/immich/` (не мешать архиву Borovskoy_Hard) | path exists |
| 2.2 | restic local repo **или** rsync+hardlink rotation | first snapshot |
| 2.3 | systemd timer (nice/ionice night) | timer active |
| 2.4 | Restore drill: 1 file | file matches |
| 2.5 | preflight free space HDD | script |
| 2.6 | Docs `12_BACKUP_RESTORE` + ADR-0009 | docs |

**Риск:** NTFS + 1.4T archive — only under `backups/`. Not off-site.

### Волна 3 — Cloud.ru edge (после owner «auth OK»)

| # | Задача | Примечание |
|---|---|---|
| 3.0 | Auth probe read-only (IAM token, flavors free_tier, s3 ls, FM key scope) | no creates |
| 3.1 | FM adapter in LLM Gateway: `provider=cloudru` OpenAI-compatible base | Bearer FM key; redaction same door |
| 3.2 | Policy: **internal** models only for family (Giga/DeepSeek/Qwen internal); external Claude/GPT opt-in admin | data residency |
| 3.3 | S3 bucket for **encrypted** restic (DB dumps + optional configs) — free tier 15GB start | no raw Immich bulk without size plan |
| 3.4 | Optional: Container Apps **watchdog** (curl Jetson via VPS loopback health) | replaces Vostro watcher idea |
| 3.5 | Optional later: small VM if free_tier flavors exist (OpenAPI has `free_tier` on flavors) | only after 3.0 inventory |
| 3.6 | Billing/balance alert | soft caps |
| 3.7 | **Not now:** K8s, Managed PG for NC/Immich, Managed RAG with family photos, ML Finetune |

### Волна 4 — GitVerse + repo hygiene

| # | Задача |
|---|---|
| 4.1 | `git remote add gitverse …NAS_HOME.git` (if missing) |
| 4.2 | Push `main` after preflight secrets; document dual remote |
| 4.3 | Badge/README mirror link |
| 4.4 | Optional: issues not used as SoR tasks |
| 4.5 | Move plaintext secrets from Downloads → password manager; rotate if ever exposed in chat logs |

### Волна 5 — Platform maturity (после W1–W3)

| # | Задача |
|---|---|
| 5.1 | Device migration Part B (rename layout) — maintenance window | 
| 5.2 | Quick wins audit: pin nasa-api deps, SD-wear timer, CORS, logrotate | 
| 5.3 | coturn decision (LAN-only doc vs deploy) | 
| 5.4 | Network mesh (Deco) if switch purchased — optional | 
| 5.5 | Admin RAG: runbooks via FM embeddings **or** Giga embeddings after pay | never family album |
| 5.6 | Immich smart search: only if Cloud.ru/batch or future hardware — **not** Jetson CUDA | 
| 5.7 | Article Habr part 2: «SoR at home, brains in RU cloud» | 

---

## 5. Переделка структуры репозитория

### 5.1. Docs layout (additive, low risk)

```
docs/
  integrations/
    sber/
      README.md                 # указатель
      GIGACHAT.md               # extract/short from 08
      CLOUD_RU.md               # FM + S3 + IAM inventory pointer
      GITVERSE.md               # mirror runbook
  plans/
    DEVELOPMENT_PLAN_2026-09_SBER_ERA.md   # THIS (canon candidate)
    SBER_PLATFORM_IMPLEMENTATION_PLAN.md   # detailed Sber phases
    CLOUD_RU_GITVERSE_PUBLIC_PROBE_2026-09-04.md
  decisions/
    ADR-0007-node-model-jetson-sor-cloud-edge.md
    ADR-0008-llm-routing-giga-first.md
    ADR-0009-backup-ssd-hdd-s3.md
```

### 5.2. Code layout (phased)

| Change | When | Notes |
|---|---|---|
| `services/llm-gateway`: provider `cloudru`, model matrix, giga queue, balance route | W1–W3 | keep single redaction door |
| `services/.../talk_bot`: `TALK_BOT_LLM_PROVIDER` | W1 | |
| `scripts/backup/immich_hdd_*.sh` + systemd unit | W2 | |
| `scripts/backup/restic_s3_cloudru_*.sh` | W3 | secrets env only |
| Deprecate prod paths to ollama/workstation scripts | W0 banner + W1 env | keep code archived |
| Do **not** rename `docker/` `systemd/` bulk until Part B window | W5.1 | |

### 5.3. Secrets layout (process)

```
gitignored:
  config/.env                 # device truth (on Jetson)
  gigachat/                   # already ignored
  # NEVER commit Downloads/сбер/git.md contents

password manager:
  Cloud.ru Key ID/Secret
  GitVerse token
  GigaChat auth key
  S3 tenant keys
```

### 5.4. Compose mental model (unchanged files, clearer docs)

Keep split compose files; document **profiles**:

- `core` — NC, Immich, Samba, redis, postgres  
- `gateway` — llm-gateway, nasa-api  
- `monitor` — netdata, kuma, …  
- `edge` — nothing on Jetson for Cloud.ru (client only)

---

## 6. Матрица провайдеров LLM (целевая)

| Priority | Provider | Model default | Use | Failover |
|---|---|---|---|---|
| 1 | `gigachat` | `GigaChat-2` | Family Talk | → 2 |
| 2 | `deepseek` | `deepseek-chat` | Fallback / tech | → 3 |
| 3 | `cloudru` | internal e.g. `ai-sage/GigaChat3-10B-A1.8B` or Qwen | Admin/heavy; multi-model | → error |
| — | `ollama` | — | **dev only** | off in prod |
| — | external FM (GPT/Claude) | — | explicit admin + SANITIZED | off default |

Image: Giga `GigaChat-2-Max` text→image only.  
Vision of family photos: **deny**.

---

## 7. Backup topology (целевая)

| Layer | What | Where | RPO/RTO aim |
|---|---|---|---|
| L0 live | Immich + NC data | SSD `/mnt/storage` | — |
| L1 on-site | Immich library copy | HDD `/mnt/hdd2tb/backups/immich` | daily / hours |
| L1b on-site | DB dumps | SSD + optional HDD | nightly |
| L2 off-site | restic encrypted dumps (+ later incremental policy) | Cloud.ru S3 | nightly / day |
| L3 code | git | GitHub + GitVerse | continuous |

Vostro restic (if still running) → document as **legacy optional**, not required.

---

## 8. Риски и митигации

| Risk | Mitigation |
|---|---|
| Cloud.ru spend | free tier + bonus first; billing API alert; soft monthly cap |
| FM public catalog ≠ free chat | never assume; meter after auth probe |
| Giga 1 stream | queue in gateway |
| S3 holds family-adjacent data | encrypt restic; no plaintext photos; lifecycle |
| HDD full / NTFS issues | dedicated backup dir; preflight; SMART already OK |
| Amnezia break | never touch in W1–W4; checklist if VPS work |
| Secret in Downloads plaintext | rotate + password manager (W4.5) |
| Doc drift 29–31 | superseded banners W0 |
| Device rename Part B | separate window only |

---

## 9. Критерии приёмки «эры Сбер» (MVP)

- [x] ADR-0007/8/9 in git; 29–31 marked superseded  
- [x] Repo templates: Giga-2 + `api.giga.chat` + Talk provider  
- [x] Gateway code: default gigachat, flight lock, base URL helper  
- [x] W2 script + systemd units in git  
- [ ] `@бобик` answers via **GigaChat-2** on `api.giga.chat` **(needs deploy)**  
- [ ] `prefer_local=false` on device **(needs deploy)**  
- [ ] Immich second copy on HDD; restore drill OK **(needs deploy)**  
- [ ] balance visible to admin  
- [ ] GitVerse `NAS_HOME` has current main (no secrets)  
- [ ] Cloud.ru: auth probe done; FM adapter **or** explicit “defer W3”  
- [ ] S3 off-site dumps **or** explicit defer with risk acceptance  
- [ ] Amnezia peer count unchanged throughout  

---

## 10. Что сознательно не делаем

- Перенос Nextcloud/Immich **в** Cloud.ru как primary.  
- K8s / Managed PG for family apps on free tier dreams.  
- Managed RAG over Immich library.  
- Immich ML on Jetson ARM.  
- Production dependency on workstation or Vostro.  
- Opening service ports on VPS beyond VPN model.  
- Committing Cloud.ru/GitVerse/Giga secrets.

---

## 11. Рекомендуемый календарь (ориентир)

| Неделя | Фокус |
|---|---|
| W0 | Docs ADR + superseded banners + CLAUDE sync |
| W1 | Giga cutover on Jetson + Talk provider |
| W1–W2 | Immich HDD backup |
| W2 end | GitVerse push + secret hygiene |
| W3 | Owner auth OK → FM adapter + S3 restic dumps |
| W4+ | Part B migration, coturn decision, article |

---

## 12. Связь с существующими документами

| Document | Relation |
|---|---|
| `31_MASTER_PLAN.md` | **Superseded** for node roles/sequence by this plan |
| `30_NEXT_LEAP.md` | Layers 1–2 station-based **cancelled**; layer 3 voice optional via FM Whisper later |
| `29_COMPUTE_AND_LLM_ROADMAP.md` | Kaggle still OK for experiments; prod compute → Cloud.ru |
| `SBER_PLATFORM_IMPLEMENTATION_PLAN.md` | Detailed Sber phases; subordinate to waves here |
| `CLOUD_RU_GITVERSE_PUBLIC_PROBE_*.md` | API inventory evidence |
| `WAVE_0_OFFSITE_BACKUP.md` | Historical Vostro; L2 moves to S3 |
| `docs/audit/*` | P0 photo still valid until W2 done |

---

## 13. Следующий шаг (Jetson offline)

1. **Secrets hygiene** — password manager; leave Downloads plaintext.  
2. **Prep done in git:** [`DEVICE_ENV_CHECKLIST.md`](DEVICE_ENV_CHECKLIST.md), [`../integrations/sber/S3_AND_BUDGET_CHECKLIST.md`](../integrations/sber/S3_AND_BUDGET_CHECKLIST.md), `scripts/sber/smoke_cloudru_fm.sh`.  
3. **Optional now:** create S3 bucket in console (record name only).  
4. **When Jetson on + «деплой»:** [`DEPLOY_FULL_SBER_CUTOVER.md`](DEPLOY_FULL_SBER_CUTOVER.md) — Giga PERS first, then FM key, then Immich HDD.  

FM chat verified paid (2026-09-07). Default family still PERS when device is up.

Offline pack: [`OFFLINE_SBER_READY_PACK.md`](OFFLINE_SBER_READY_PACK.md).

---

## 14. EN summary

Architecture shifts from four nodes (Jetson, roaming RTX, Vostro, VPS) to **Jetson as system of record**, **VPS as network edge**, **Cloud.ru + GigaChat as RU AI/storage edge**. Workstation and Vostro leave the design. Immich gets an on-site HDD second copy; true off-site becomes encrypted S3. LLM becomes Giga-first with DeepSeek fallback and optional Foundation Models. Repo structure gains `docs/integrations/sber/`, three ADRs, and superseded banners on plans 29–31. Execution is five waves: docs → Giga cutover → HDD backup → Cloud.ru/GitVerse → maturity. Hard safety rules (Amnezia, redaction, no photo analysis, no secrets in git) stay.

---

## 15. Changelog of this document

| Date | Change |
|---|---|
| 2026-09-04 | Initial plan from owner directives + probes + audits |
| 2026-09-04 | Progress log; W0 done in git; W1 templates; deploy gated |
