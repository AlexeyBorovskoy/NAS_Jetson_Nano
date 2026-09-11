# Immich ML on Cloud.ru — cost estimate (option A)  
# Immich ML на Cloud.ru — оценка затрат (вариант A)

> **Date:** 2026-09-11  
> **Currency:** ₽, **ориентиры**, не прайс-лист. Точные цифры — калькулятор console.cloud.ru.  
> **Library size (approx):** Immich ~13 GB files / historically ~7k assets (grows).  
> 🇬🇧 Figures are order-of-magnitude for family planning.  
> 🇷🇺 Цифры порядка величины для семейного планирования.

---

## 1. What you pay for / За что платите

| Item / Статья | Why / Зачем |
|---|---|
| **VM vCPU + RAM** | runs `immich-machine-learning` |
| **Boot disk** | OS + Docker + ML models (~20–40 GB) |
| **Public IP** (if any) | Jetson reaches ML URL; can avoid with private + VPN later |
| **Egress traffic** | Jetson uploads thumbs/crops to ML; results small |
| **Optional GPU** | faster faces/CLIP; much more expensive |
| **Already paying** | GigaChat PERS freemium; FM chat if used — **separate** from Immich ML |

🇬🇧 Immich ML ≠ GigaChat billing. Different meter.  
🇷🇺 Immich ML и GigaChat — **разные** счета.

---

## 2. Workload model / Модель нагрузки

| Phase | Work | Duration feeling |
|---|---|---|
| **Backfill** | once: all existing photos | days–1–2 weeks on CPU; hours–days on GPU |
| **Steady** | only new uploads | minutes per day |

🇬🇧 After backfill, 24/7 fat VM is usually **waste**.  
🇷🇺 После прогона архива жирный VM 24/7 обычно **зря**.

---

## 3. Scenarios / Сценарии (₽)

### S0 — «Почти бесплатно / разведка» (не полный Immich ML)

| | |
|---|---|
| What | Only FM/Giga captions on sample (option B) — **not** this ADR |
| CapEx | 0 |
| OpEx | FM tokens if any |
| 🇬🇧 | Does **not** unlock Immich face clusters |
| 🇷🇺 | **Не** даёт лица Immich |

### S1 — **Рекомендуемый старт: CPU VM, не 24/7**

| Resource | Spec (typical) | Money (orient) |
|---|---|---|
| VM | 4 vCPU / 8–16 GB RAM | **~2 000–5 000 ₽/мес** if 24/7 |
| Disk | 40–80 GB SSD | **~200–600 ₽/мес** |
| IP | 1 public | **~150–400 ₽/мес** |
| **If ON only ~8 h/night** | same VM | **~30–40% of 24/7** → **~800–2 500 ₽/мес** |
| Backfill month | more hours ON | first month **×1.5–2** |
| Egress | thumbs for ~7–15k assets | often **hundreds ₽**, not tens of thousands if thumbs not full RAW |

**Family budget feel:**  
- First month (backfill): **~1 500–6 000 ₽**  
- Later months (new photos only, scheduled): **~500–2 500 ₽**  
- With leftover **grant/bonus**: first weeks may be ~0 until bonus ends  

### S2 — CPU 24/7 «забыли выключить»

| | |
|---|---|
| Same S1 VM always on | **~2 500–6 000 ₽/мес** steady |
| 🇬🇧 Easy but burns money after backfill | 🇷🇺 Просто, но жжёт деньги после прогона |

### S3 — GPU (fast backfill)

| | |
|---|---|
| GPU VM (e.g. T4-class) | often **~15 000–45 000 ₽/мес** 24/7 |
| GPU only 48–72 h for backfill | **~1 500–8 000 ₽ one-shot** then switch to S1 CPU or OFF |
| 🇬🇧 Use GPU as **burst**, not lifestyle | 🇷🇺 GPU = **вспышка**, не образ жизни |

### S4 — Free tier / грант

| | |
|---|---|
| Starter bonus (was ~4000) | may cover **days–few weeks** of small CPU, not a year of GPU |
| Free-tier VM flavors | if available in project — check `free_tier` in console; not guaranteed for ML size |
| 🇬🇧 Do not plan architecture on bonus alone | 🇷🇺 На одном гранте архитектуру не строить |

---

## 4. Cost drivers you control / Что вы контролируете

| Lever | Effect on ₽ |
|---|---|
| Thumbs/preview vs full resolution to ML | big traffic + time |
| One album test first | small bill, validate quality |
| Stop VM when queue empty | largest saving |
| CPU not GPU for steady state | 5–20× cheaper |
| Don’t re-run full library monthly | avoid repeat backfill |
| Soft billing alert in Cloud.ru console | prevent surprise |

---

## 5. Compared to alternatives / Сравнение

| Option | $/feel | Immich faces+search |
|---|---|---|
| A Cloud.ru Immich ML (S1) | **~0.5–6k ₽/мес** managed | **Yes** |
| B GigaChat vision only | tokens, spiky | **No** (captions only) |
| Workstation RTX when home | electricity ~0, your time | Yes while PC on |
| Buy N100/N150 box | **15–40k ₽ once** + power | Yes, home PII stays |

🇬🇧 If monthly Cloud.ru > ~3–4k steady forever, a small home box may win in 6–12 months — but violates “no new hardware” preference unless you buy.  
🇷🇺 Если Cloud.ru стабильно >3–4k/мес, домашний мини-ПК может окупиться — это уже покупка железа.

---

## 6. Recommended money policy / Денежная политика

1. **Cap:** soft limit **3 000 ₽/мес** Cloud.ru total (ML + FM + disk) unless you raise it.  
2. **Month 1:** S1 CPU, scheduled; budget **≤ 5 000 ₽**.  
3. **Month 2+:** VM off by default; on 1–2 h when new photos; target **≤ 1 500 ₽**.  
4. **GPU:** only if CPU backfill >2 weeks and you accept one-shot.  
5. **Alert:** Cloud.ru billing threshold 1 000 / 2 500 / 5 000 ₽.

---

## 7. Implementation steps (no spend until you say «создавай VM»)

1. Risk note (family photos → Cloud.ru ML) — accept in writing.  
2. Console: calculator for 4 vCPU / 16 GB / 60 GB disk / IP.  
3. Create VM **stopped** template + docker compose for immich-ml only.  
4. Firewall: allow Jetson egress IP only (or WireGuard).  
5. Jetson: `IMMICH_DISABLE_MACHINE_LEARNING=false`, `IMMICH_MACHINE_LEARNING_URL=…`.  
6. Process **one album** → check faces/search.  
7. Backfill nights; stop VM daytime.  
8. Billing review after 7 days.

---

## 8. Bottom line / Итог

| | ₽ |
|---|---|
| **Honest family range for option A** | **~500–3 000 ₽/мес** after setup if disciplined |
| **Sloppy 24/7 CPU** | **~3 000–6 000 ₽/мес** |
| **24/7 GPU** | **often 15k+** — not recommended |
| **First backfill month** | **budget 2 000–6 000 ₽** |

🇬🇧 Sber money here = **Cloud.ru compute**, not GigaChat freemium.  
🇷🇺 Деньги Сбера здесь = **Cloud.ru VM**, не freemium GigaChat.

**Next:** owner confirms monthly cap + «можно risk-note / VM» → then create resources.
