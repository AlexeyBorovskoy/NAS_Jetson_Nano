# ADR-0007: Node model — Jetson SoR, VPS net-edge, Cloud.ru AI/storage edge  
# ADR-0007: Модель узлов — Jetson SoR, VPS net-edge, Cloud.ru AI/storage edge

## Status / Статус

🇬🇧 **Accepted** (2026-09-04).  
🇷🇺 **Принято** (2026-09-04).

Canon: [`docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`](../plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md).  
Replaces node roles from `docs/31_MASTER_PLAN.md` (2026-08-22).

## Context / Контекст

🇬🇧 The owner removed from the NAS project:  
🇷🇺 Владелец исключил из проекта NAS:

- 🇬🇧 workstation RTX (dev only) / 🇷🇺 рабочую станцию RTX (только разработка);
- 🇬🇧 Vostro (not off-site, not watchdog) / 🇷🇺 Vostro (не off-site и не сторож).

🇬🇧 Family data must stay at home; intelligence and off-site may live in RU cloud (Sber / Cloud.ru), without depending on a roaming PC.  
🇷🇺 Семейные данные дома; интеллект и off-site — в РФ-облаке, без зависимости от кочующего ПК.

## Decision / Решение

| Node / Узел | Role / Роль |
|---|---|
| **Jetson Nano** | 🇬🇧 System of Record: Nextcloud, Immich, Samba, Talk bot, LLM Gateway, on-site backups / 🇷🇺 SoR: те же сервисы |
| **VPS** | 🇬🇧 Network edge: reverse SSH, nginx, Amnezia (do not touch without checklist) / 🇷🇺 сетевой edge |
| **Cloud.ru Evolution** | 🇬🇧 Optional AI/storage edge: FM, Object Storage / 🇷🇺 опциональный AI/storage edge |
| **GigaChat PERS** | 🇬🇧 Family LLM freemium via gateway / 🇷🇺 семейный LLM через шлюз |
| **Workstation / Vostro** | 🇬🇧 **Outside** NAS architecture / 🇷🇺 **Вне** архитектуры NAS |

## Consequences / Последствия

🇬🇧 Immich ML / Ollama on the workstation are **not** required for prod.  
🇷🇺 Immich ML / Ollama на станции **не** нужны в prod.

🇬🇧 Off-site is no longer designed on Vostro; Immich second copy = Jetson HDD; off-site = S3 (ADR-0009).  
🇷🇺 Off-site не на Vostro; 2-я копия Immich = HDD Jetson; off-site = S3 (ADR-0009).

🇬🇧 Docs 29–31 marked superseded for topology.  
🇷🇺 Документы 29–31 помечены superseded для topology.

## Unchanged / Не меняется

ADR-0003 (LAN-only), ADR-0005 (reverse tunnel), Amnezia safety, redaction gateway.
