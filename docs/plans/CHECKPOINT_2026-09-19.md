# Точка проекта 2026-09-19 — W0.1 Hardening Sprint завершён

> ⚠️ **Поправка (аудит 2026-09-19, отзыв статусов).** Ниже записано «все 16 тестов прошли ✅» —
> **неверно**: на `d52c11b` падали 2 существующих теста, а каждый чат GigaChat отдавал HTTP 500
> (`full` до присваивания), удалён `_IMG_TAG_RE`. Найдено исполнением эндпоинта через `TestClient`;
> ворота не видели тестов шлюза. Исправлено коммитами `36c4ced` (шлюз, W0.2 доведён) и `b8f50c9` (CI).
> «Все сервисы ✅ Live» в §2 неполно: `nasa-ssd-recovery` был `failed` (исправление — `9ec1b15`, ждёт деплоя).
> Разбор: `docs/audit/2026-09-19_full_audit/REVIEW_GIGACODE_W0_2026-09-19.md`. Текущий план: `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` (сводная редакция).

> **Статус:** W0.1 ✅ в git, ✅ на GitHub  
> **Дата:** 2026-09-19 06:25  
> **Следующий шаг:** W0.2 (gateway auth) или W0.3 (NAS API RBAC)

---

## 1. Что сделано сегодня

### W0.1 — save_path restriction (audit_new G01, P0)

**Файл:** `services/llm-gateway/app/main.py`

**Что было:** `_finish_image` принимал произвольный `save_path` от клиента и писал в любую директорию контейнера. Это позволяло записать файл в persistent volume `/data` или любую доступную директорию.

**Что стало:**
- `IMAGE_OUTPUT_ROOT` env var (default: `/data/images`)
- `_sanitize_save_path(requested)`:
  - `None` → `Path("")` (no save, base64 in response)
  - `""` → 400 (empty filename)
  - `.` / `..` → 400 (invalid names)
  - `null byte` → 400
  - `../../etc/passwd` → `.name` → `passwd` → `/data/images/passwd` (безопасно!)
  - Resolve + `relative_to(root)` → 403 если выходит за root
- Health endpoint: `image_output_root: /data/images`
- Compose: `IMAGE_OUTPUT_ROOT` propagated from env

**Тесты:** 8 новых тестов в `test_smart_routing.py` — все 16 прошли ✅

### Smart routing (бесплатно, freemium)

- 50+ паттернов для определения сложных промптов
- Сложные → `GigaChat-2-Max`, простые → `GigaChat-2`
- Оба модели из одного freemium-ведра — просто умнее использование токенов

### Image presets (+5 семейных)

- `birthday_card`, `family_collage`, `child_drawing`, `postcard`, `meme`
- Итого: 8 пресетов (было 3)

### Документация

- `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` — волна Hardening Sprint W0.5
- `audit_new.md` — полный аудит проекта (24 gap, P0-P3)

---

## 2. Live snapshot (2026-09-19 06:16)

| Сервис | Порт | Статус |
|---|---|---|
| Nextcloud | 8080 | ✅ Live |
| Immich | 2283 | ✅ Live |
| LLM Gateway | 8090 | ✅ Live |
| NAS API | 8099 | ✅ Live |
| Samba | 445 | ✅ Live |
| SSH | 22 | ✅ Live |

### GigaChat баланс

| Модель | Остаток |
|---|---|
| Lite | 249 995 856 / 250M |
| Pro | 40 000 000 / 40M |
| Max | 24 991 737 / 25M |
| Ultra | 50 000 000 / 50M |

### Usage за месяц

| User | Токены | Вызовы |
|---|---|---|
| admin | 1 985 | 24 |
| unknown | 367 | 5 |
| diag | 109 | 2 |
| olga, ivan, alexey | 0 | 0 |

---

## 3. Следующие шаги

### Приоритет: W0.2 — Gateway service auth (P0)

Добавить service token middleware для `/v1/chat` и `/v1/image/*`:
- `LLM_GATEWAY_SERVICE_TOKEN` env var
- Без токена → 401
- С токеном → 200
- Health endpoint — без токена (для мониторинга)

### Приоритет: W0.3 — NAS API RBAC (P0)

Отделить `authenticated user` → `operator` → `owner`:
- Family user → read-only
- Operator → backup, status
- Owner → restart, privileged actions

### Приоритет: W0.4 — Diagnostic endpoints auth (P0)

Закрыть auth'ом: `/logs`, `/metrics`, `/containers`, `/report/now`, Talk status

### Приоритет: W0.5 — Privacy scrub HEAD

Убрать room IDs, family identifiers из current HEAD

---

## 4. Коммит

```
d52c11b feat(w0.1): save_path restriction (G01) + smart routing + 8 image presets + tests
```

---

## 5. Канон

- **План:** `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`
- **Аудит:** `docs/research/audit_new.md`
- **ADR:** `docs/decisions/ADR-0007`, `ADR-0008`, `ADR-0009`
- **Архитектура:** `docs/00_OVERVIEW.md`, `docs/03_ARCHITECTURE.md`

---

## 6. Жёсткие запреты

- ❌ Не трогать Amnezia на VPS
- ❌ Не удалять `nas_jetson_nano-lan` / `192.168.0.50`
- ❌ Не открывать сервисы в интернет
- ❌ Не форматировать HDD 2 ТБ
- ❌ Не деплоить без «деплой»
