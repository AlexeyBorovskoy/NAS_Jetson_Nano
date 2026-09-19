# Точка проекта 2026-09-18 — Hardening Sprint, smart routing, аудит

> **Статус:** канон развития — `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`  
> **Дата:** 2026-09-18  
> **Владелец:** скоро выключил ПК — контекст сохранён здесь

---

## 1. Что сделано сегодня

### Smart routing (бесплатно, freemium)
- **Файл:** `services/llm-gateway/app/main.py`
- **Что:** 50+ паттернов для определения сложных промптов (код, ошибки, диагностика) → `GigaChat-2-Max` вместо Lite
- **Зачем:** Max лучше рассуждает; оба модели из одного freemium-ведра
- **Health:** `smart_routing_enabled: true`, `gigachat_model_complex: GigaChat-2-Max`
- **Тесты:** `tests/llm_gateway/test_smart_routing.py` — 8 тестов, все прошли ✅

### Image presets (+5 семейных)
- **Файл:** `services/llm-gateway/app/main.py`
- **Что:** `birthday_card`, `family_collage`, `child_drawing`, `postcard`, `meme`
- **Итого:** 8 пресетов (было 3)
- **Стоимость:** 0₽, из freemium Max

### План развития обновлён
- **Файл:** `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`
- **Волна 0.5:** Hardening Sprint из `audit_new.md` — 16 задач (H01–H16)
- **P0:** save_path restriction, gateway auth, NAS API RBAC, diagnostic endpoints, privacy scrub
- **P1:** budget fail-closed, fallback semantics, image safety gate, compose fixes, non-root containers
- **Риски:** обновлены — добавлены P0/P1 из аудита

### Аудит проекта
- **Файл:** `docs/research/audit_new.md`
- **Вердикт:** «Функционально зрелая платформа с разрывом между policy/ADR и enforcement»
- **P0:** G01–G05 (gateway auth, save_path, RBAC, diagnostic endpoints, privacy scrub)
- **Порядок:** Policy enforcement → Authz → Backup → CI → Docs → New features

---

## 2. Текущее состояние (snapshot)

| Компонент | Статус |
|---|---|
| **Jetson** | 13 контейнеров; W1 Giga cutover ✅; W2 Immich→HDD ✅; balance timer ✅ |
| **LLM Gateway** | Giga-2 default; smart routing ✅; 8 presets ✅; tests ✅ |
| **Cloud.ru S3** | ❌ blocked (tenant_id); restic L2 not run |
| **GitVerse** | ✅ HTTPS mirror |
| **Hardening Sprint** | ✅ код в git; ❌ деплой на Jetson (ждёт «деплой») |

---

## 3. Следующие шаги (когда включишь ПК)

### Приоритет 1: Hardening Sprint W0.5 (код в git, без деплоя)
```
H01 — save_path restriction (P0)
H02 — gateway service auth (P0)
H03 — NAS API RBAC (P0)
H04 — diagnostic endpoints auth (P0)
H05 — privacy scrub HEAD (P0)
H06 — budget fail-closed (P1)
H07 — Giga 401≠DeepSeek fallback (P1)
H08 — image safety gate (P1)
H09 — Talk attachment size limit (P1)
H10–H14 — compose, non-root, docs (P1)
```

### Приоритет 2: Owner console
1. Cloud.ru → Object Storage → скопировать **tenant_id**
2. Создать bucket `nas-home-restic` + S3 keys
3. restic L2 dumps (off-site encrypted)

### Приоритет 3: Деплой (только по команде «деплой»)
- Все H01–H14 на Jetson
- Canary → read-only checks → continue/rollback

---

## 4. Что НЕ делать

- ❌ Не трогать Amnezia на VPS
- ❌ Не удалять профиль `nas_jetson_nano-lan` / `192.168.0.50`
- ❌ Не открывать сервисы в интернет
- ❌ Не форматировать HDD 2 ТБ
- ❌ Не разворачивать локальную LLM на Jetson
- ❌ Не деплоить без команды «деплой»

---

## 5. Канон развития

**Файл:** `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`  
**ADR:** `docs/decisions/ADR-0007`, `ADR-0008`, `ADR-0009`  
**Аудит:** `docs/research/audit_new.md`  
**Документация:** `docs/00_OVERVIEW.md`, `docs/03_ARCHITECTURE.md`, `docs/08_LLM_GATEWAY_DEEPSEEK.md`

---

## 6. Быстрые команды

```bash
# Проверить тесты
python -m pytest tests/llm_gateway/test_smart_routing.py -q

# Проверить gateway health
curl -s http://127.0.0.1:8090/health | python -m json.tool

# Проверить баланс Giga
curl -s http://127.0.0.1:8090/v1/provider/gigachat/balance | python -m json.tool

# Проверить usage
curl -s http://127.0.0.1:8090/v1/usage | python -m json.tool
```

---

## 7. Артефакты сегодня

| Файл | Что |
|---|---|
| `services/llm-gateway/app/main.py` | smart routing + 8 presets |
| `tests/llm_gateway/test_smart_routing.py` | 8 unit-тестов |
| `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` | волна Hardening Sprint |
| `docs/research/audit_new.md` | полный аудит проекта |
| `docs/plans/CHECKPOINT_2026-09-18.md` | этот файл |
