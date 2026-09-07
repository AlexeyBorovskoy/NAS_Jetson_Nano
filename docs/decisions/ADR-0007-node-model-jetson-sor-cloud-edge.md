# ADR-0007: Модель узлов — Jetson SoR, VPS net-edge, Cloud.ru AI/storage edge

## Статус / Status

🇷🇺 **Принято** (2026-09-04). / 🇬🇧 **Accepted** (2026-09-04).

Канон развития: [`docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](../plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md).  
Заменяет операционную модель узлов из `docs/31_MASTER_PLAN.md` (2026-08-22).

## Контекст / Context

Владелец исключил из проекта NAS:

- рабочую станцию RTX (только разработка);
- Vostro (не off-site и не сторож для NAS).

Нужна модель, где семейные данные остаются дома, а интеллект и off-site могут жить в РФ-облаке (Сбер / Cloud.ru), без зависимости от кочующего ПК.

## Решение / Decision

| Узел | Роль |
|---|---|
| **Jetson Nano** | System of Record: Nextcloud, Immich, Samba, Talk-бот, LLM Gateway, on-site backups |
| **VPS** | Network edge: reverse SSH, nginx, Amnezia (не трогать без checklist) |
| **Cloud.ru Evolution** | Optional AI/storage edge: Foundation Models, Object Storage, later CA/VM |
| **GigaChat PERS** | Family LLM freemium via gateway |
| **Станция / Vostro** | **Вне** архитектуры NAS |

## Последствия / Consequences

- Immich ML / Ollama на станции **не** требуются для prod.
- Off-site больше не проектируется на Vostro; on-site 2-я копия Immich — HDD Jetson; off-site — S3 (ADR-0009).
- Документы 29–31 помечены superseded для topology.

## Не меняется / Unchanged

ADR-0003 (LAN-only), ADR-0005 (reverse tunnel), Amnezia safety, redaction gateway.
