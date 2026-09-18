# ADR-0011: `@бобик` — structured tools + safety gate  
# ADR-0011: `@бобик` — структурированные tools и safety gate

## Status / Статус

🇬🇧 **Accepted in git** (2026-09-18) — code + unit tests; **device deploy pending** «деплой».  
🇷🇺 **Принято в git** (2026-09-18) — код + unit-тесты; **выкат на Jetson** — по слову «деплой».

Source / Источник идей: `E:\Belgorod_platform\docs\research\обзор.md`  
(structured outputs, SafeGate/DAR, tool-calling, shadow) — adapted to **family home cloud**, not ASUDD.

## Context / Контекст

🇬🇧 Today `@бобик` → Talk → LLM Gateway (Giga first, ADR-0008) with PII redaction, budgets, and `LLM_ALLOW_IMAGE_ANALYSIS=false`. Free-form chat works; **home actions** are ad-hoc or buried in prose.  
🇷🇺 Сейчас `@бобик` ходит в gateway с redaction и лимитами. Свободный чат есть; **домашние действия** не оформлены как контракт.

🇬🇧 Belgorod research shows: JSON Schema / structured outputs cut format failures; a **pre-execution gate** cuts dangerous acceptance (DAR); schemas alone do not fix “wrong plan”.  
🇷🇺 Исследование work: схемы режут ошибки формата; **gate до исполнения** режет опасные accept; схема ≠ ум.

🇬🇧 We must not import ASUDD MCP, controller IPs, or mutation APIs into the family bot. Corp access stays on Vostro bastion (separate path).  
🇷🇺 АСУДД/MCP work и мутации контроллеров в семейный бот **не** тащим. Корп — только через Vostro bastion.

## Decision / Решение

### 1. Pipeline (target)

```text
Talk @бобик
  → Admission / Safety gate   (execute | refuse | clarify)
  → Generator (LLM, ADR-0008) optional for free chat
  → Structured plan (JSON Schema) when action requested
  → Validator (schema + policy)
  → Runner (allowlisted home tools only)
  → Audit log (no secrets / no raw family PII)
```

Optional later: **shadow** second provider for metrics only (no user-visible switch).

### 2. Structured outputs for actions

🇬🇧 Any **side-effecting or system** answer from the bot MUST be representable as JSON matching a published schema (tool name + args), not free prose alone.  
🇷🇺 Любое **действие** — JSON по схеме (tool + args), не только текст.

🇬🇧 Free chat (weather smalltalk, “что на ужин”) may stay text after admission allows “chat”.  
🇷🇺 Свободный чат после admission=`chat` остаётся текстом.

🇬🇧 Prefer provider structured output / JSON mode when available (Giga/DeepSeek); always **validate server-side** (gateway or bot). Client trust = zero.  
🇷🇺 Structured mode провайдера — плюс; **валидация у нас** обязательна.

### 3. Safety gate (admission) — before tools and before cloud

| Decision | When |
|----------|------|
| **refuse** | wipe/format disk, open WAN ports, dump secrets, send photos out, ASUDD/corp mutations, “ignore previous rules” jailbreaks |
| **clarify** | ambiguous destructive intent, missing room/user bound |
| **chat** | general Q&A via gateway (redaction + budget as now) |
| **execute** | allowlisted tool with valid schema |

🇬🇧 Target **DAR** (dangerous acceptance rate) on a fixed contrast set: aim **&lt; 1%** on owned test pack (not ToolBench scale).  
🇷🇺 Целевой DAR на своём мини-наборе: **&lt; 1%**.

🇬🇧 Gate implementation: start **rules + denylist** (fast, offline); optional small classifier later — **not** a 27B local model on Jetson.  
🇷🇺 Сначала правила/denylist; классификатор позже; **не** локальная huge-LLM на Jetson.

### 4. Allowlisted home tools (v1 — read-mostly)

| Tool | Effect | Notes |
|------|--------|------|
| `home.status` | read | containers / tunnel ping summary |
| `home.backup_age` | read | last dump / Immich HDD copy age |
| `home.disk` | read | `/mnt/storage`, `/mnt/hdd2tb` free % |
| `home.whoami` | read | Talk room → family label (no secrets) |
| `home.help` | read | list tools |

🇬🇧 **v1 forbidden:** restart containers, compose down, ufw, SSH to Vostro/corp, Immich job trigger, any write to photos DB.  
🇷🇺 **v1 запрет:** рестарты, firewall, корп/Vostro, jobs Immich, запись в фото.

🇬🇧 v2+ only after explicit owner OK + risk note (e.g. “restart one named container”).  
🇷🇺 v2+ только с OK владельца и risk-доком.

### 5. What we explicitly do **not** adopt from the research note

- Full **ToolBench / MCP-Atlas / MirrorAPI** as runtime  
- **LoRA/QLoRA on Jetson or VPS** (VPS ~2 GiB; Jetson SoR not ML train — ADR-0007)  
- Belgorod **ASUDD MCP** tools inside `@бобик`  
- Publishing family prompts/logs to external LLM training  

### 6. Observability & tests

- Structured audit: `{ts, user/room id hash, admission, tool?, ok|refuse, latency}` — no raw prompt by default (`LLM_LOG_PROMPTS=false` stays)  
- Pytest: schema validation; denylist fixtures; timeout chain (bot &gt; gateway — already learned)  
- Optional McNemar when comparing providers on fixed 30–50 family questions  

### 7. Rollout (small steps)

| Step | Where | Deploy? |
|------|-------|---------|
| A | JSON schemas + unit tests in repo | git only |
| B | Admission rules in bot/gateway code | git; device on «деплой» |
| C | Runner for read-only tools via existing API | «деплой» |
| D | Shadow metrics (optional) | later |
| E | One Habr-facing narrative: “house that answers safely” | docs |

## Consequences / Последствия

🇬🇧 + Deterministic home actions; clearer safety story; aligns with gateway redaction.  
🇷🇺 + Предсказуемые действия; явная безопасность; стык с redaction.

🇬🇧 − More code paths; free-form “just do it” becomes refuse/clarify more often.  
🇷🇺 − Больше кода; «просто сделай» чаще refuse/clarify.

🇬🇧 − Family must learn short commands or accept clarify loops.  
🇷🇺 − Семье нужны короткие команды или уточнения.

## Security / Безопасность

- Tools bind to **Talk identity / room**, not anonymous internet.  
- No tool reaches **corp LAN** or Vostro from bot path.  
- Photos/files: keep `LLM_ALLOW_IMAGE_ANALYSIS=false`; tools must not attach library blobs to cloud LLM.  
- Amnezia / router / Jetson LAN profile unchanged (ADR-0003).  

## Rollback / Откат

1. Feature flag `TALK_BOT_STRUCTURED_TOOLS=false` → legacy free chat only.  
2. Empty tool registry → admission chat-only.  
3. No DB migration required if audit is append-only file/volume.

## Related / Связанное

- ADR-0007 node model · ADR-0008 Giga first · ADR-0003 LAN  
- `docs/07_LLM_GATEWAY.md` · Talk bot Phase C  
- Research (read-only neighbor): Belgorod `docs/research/обзор.md`  
- Immich ML: ADR-0010 / ROG pilot — **out of scope** for this ADR  

## Open questions for owner / Вопросы владельцу

1. Accept **Proposed** → implement step A in git only?  
2. Any v1 tool to add beyond read-only four?  
3. Should refuse messages be kid-friendly fixed templates (no model)?  

## Implementation (git 2026-09-18)

| Piece | Path |
|-------|------|
| Gate + DAR fixtures | `services/nas_jetson_nano-api/app/bobik_gate.py` |
| Bot wire-up | `services/nas_jetson_nano-api/app/routers/talk_bot.py` |
| Settings | `talk_bot_structured_tools`, `talk_bot_safety_gate` |
| Tests | `tests/unit/test_bobik_gate.py` |
| Env example | `TALK_BOT_STRUCTURED_TOOLS`, `TALK_BOT_SAFETY_GATE` |

```bash
python -m pytest tests/unit/test_bobik_gate.py -q
```

## Next safe step / Следующий шаг

🇬🇧 Owner says «деплой» → rebuild/restart `homecloud_nasa_api` on Jetson; smoke `@бобик статус` (local) and a refuse phrase.  
🇷🇺 Слово «деплой» → пересборка API на Jetson; smoke: локальный tool и refuse.