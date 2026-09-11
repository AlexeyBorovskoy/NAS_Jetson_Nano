# ADR-0010: Immich ML on Cloud.ru (not on Jetson)  
# ADR-0010: Immich ML в Cloud.ru (не на Jetson)

## Status / Статус

🇬🇧 **Proposed** (2026-09-11) — owner chose option A.  
🇷🇺 **Предложено** (2026-09-11) — владелец выбрал вариант A.

## Context / Контекст

🇬🇧 Immich smart search / faces / OCR need `immich-machine-learning`.  
🇷🇺 Умный поиск / лица / OCR Immich требуют `immich-machine-learning`.

🇬🇧 Jetson Nano 4 GB + CUDA 10.2 cannot run official Immich ML.  
🇷🇺 Jetson Nano 4 ГБ + CUDA 10.2 не тянет официальный Immich ML.

🇬🇧 Workstation RTX is out of prod (ADR-0007). GigaChat is not a drop-in Immich ML.  
🇷🇺 Станция RTX вне prod (ADR-0007). GigaChat ≠ замена Immich ML.

## Decision / Решение

1. 🇬🇧 Run **official Immich ML** on **Cloud.ru Evolution** (CPU VM first).  
   🇷🇺 Официальный Immich ML на **Cloud.ru** (сначала CPU VM).
2. 🇬🇧 Jetson Immich points to `IMMICH_MACHINE_LEARNING_URL` over HTTPS (outbound only).  
   🇷🇺 Jetson Immich → `IMMICH_MACHINE_LEARNING_URL` по HTTPS (только исходящий).
3. 🇬🇧 Photos/thumbs leave home for embedding — requires risk acceptance.  
   🇷🇺 Превью/кадры уходят в облако — нужно принятие риска ПДн.
4. 🇬🇧 Prefer **batch / scheduled** VM power to control cost; not 24/7 GPU.  
   🇷🇺 Предпочтительно **по расписанию**, не GPU 24/7.
5. 🇬🇧 GigaChat vision remains optional captions later — not this ADR.  
   🇷🇺 GigaChat vision — опционально позже, не этот ADR.

## Consequences / Последствия

🇬🇧 + Native Immich UI features. − Cloud bill. − PII leaves premises during ML.  
🇷🇺 + Родные функции Immich. − Счёт Cloud.ru. − ПДн уходят на время ML.

## Security

- ML endpoint not public to the world (allowlist Jetson/VPS IP or mTLS / private link).  
- TLS; no guest auth.  
- Start with one album test, not full library.

## Related

- Cost estimate: `docs/plans/IMMICH_ML_CLOUDRU_COST_ESTIMATE.md`  
- ADR-0007 nodes, ADR-0008 LLM (separate door)
