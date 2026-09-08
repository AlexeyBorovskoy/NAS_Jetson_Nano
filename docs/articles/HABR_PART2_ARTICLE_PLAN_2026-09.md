# Habr Part 2 article plan (2026-09) / План статьи Habr — Часть 2

> 🇬🇧 **Status:** writing plan (not a full draft yet).  
> 🇷🇺 **Статус:** план к написанию (не черновик текста).  
>
> 🇬🇧 Part 1 → https://habr.com/ru/articles/1062914/ (13K, +6, 9 comments, none after 2026-07-30).  
> 🇷🇺 Часть 1 → тот же URL.  
>
> 🇬🇧 Fact canon: `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`, ADR-0007/8/9.  
> 🇷🇺 Канон фактов: тот же.  
>
> 🇬🇧 Do **not** center Part 2 on “ML on Vostro” — Vostro is **out** of NAS architecture.  
> 🇷🇺 **Не** делать сюжет «ML на Vostro» каноном.

---

## 1. Зачем вторая часть

Часть 1 = **как поднять** домашнее облако на старом Nano + USB-драма + CGNAT.  
Часть 2 = **как жить дальше**, когда:

- семья уже пользуется (Talk-бот, фото, VPN);
- читатели спросили про ML / GPU / «зачем Jetson»;
- пришлось **пересобрать модель узлов** (не 4 машины, а SoR + edge);
- подключилась **РФ-экосистема Сбера** (GigaChat + Cloud.ru) без выноса фото в облако «как в Google».

**Обещание читателю:** честный post-mortem «что сломалось в голове архитектуры», а не список галочек «поставил ещё один сервис».

---

## 2. Рабочий заголовок (варианты)

1. **«Домашнее облако на Jetson Nano, часть 2: GigaChat, Cloud.ru и почему станция с RTX больше не узел»**  
2. «После Habr: как семья получила бота, а мы убрали Vostro из схемы и не открыли порты»  
3. «SoR дома, мозги в РФ-облаке: LLM Gateway на 4 ГБ RAM»

Рекомендация: **вариант 1** — конкретика + интрига + ответ комментаторам.

Хабы: DIY, sys_admin, artificial_intelligence (осторожно), hardware / antikvariat.

---

## 3. Угол и тезис

**Тезис:**  
> На 4 ГБ Jetson нельзя «всё локально». Зато можно сделать **единственную дверь наружу** (redaction gateway), держать **фото дома**, а интеллект — в freemium GigaChat / Cloud.ru FM, не превращая gaming-ноут и чужой Vostro в production.

**Антитезис читателя (закрыть в тексте):**  
«Просто поставь всё в Yandex/Sber Cloud» — нет: SoR, CGNAT, VPN семьи, Amnezia, персональные фото.

---

## 4. Структура статьи (≈12–18 мин чтения)

| § | Блок | Содержание | Доказательства |
|---|---|---|---|
| 0 | Лид | 3 месяца после Part 1: 13K, комментарии, что обещали и что реально сделали | ссылка на Part 1, метрики 2026-09 |
| 1 | Ответы Habr без воды | vvzvlad / tklim / dE1l / falcon4fun — таблица «замечание → что сделали / что честно не сделали» | POST_HABR_FEEDBACK + live |
| 2 | Слом 4-узловой мечты | Станция кочует, Vostro чужой/sleep, Jetson SoR. ADR-0007 | схема «было / стало» |
| 3 | LLM Gateway как продукт | Один redaction+budget door; DeepSeek → **Giga-first**; failover; 1 stream PERS | health JSON, без ключей |
| 4 | Два Giga | PERS `api.giga.chat` vs Cloud.ru FM Bearer; 402→пополнение; модель 2-Max | урок биллинга |
| 5 | Бэкапы без иллюзий | Пустые ночные dumps; T0 на Vostro emergency; Immich 13G→HDD; S3 blocked tenant | честный fail |
| 6 | Git / GitVerse | Публичный GitHub + зеркало GitVerse; SSH | ссылки |
| 7 | Что **не** сделали | Immich ML на Nano CUDA 10.2; GPU Nano; K8s; открытые порты | ответ «зачем Jetson» |
| 8 | Уроки агентной разработки | AGENTS.md, quality gate, abort деплоя, dual remote | без хвастовки |
| 9 | Roadmap Part 3 (коротко) | S3 L2, optional Immich ML offload, Part 3 если будет | |
| 10 | CTA | GitHub, GitVerse, Part 1 | |

Объём: **8–12k знаков** основного текста + 4–6 схем/скринов.

---

## 5. Скриншоты / визуал (чеклист съёмки)

| # | Кадр | Где снять | Статус |
|---|---|---|---|
| 1 | Схема узлов Part1 vs Part2 | draw.io / excalidraw | todo |
| 2 | `curl /health` gigachat + providers | Jetson SSH | todo (редact) |
| 3 | Talk @бобик ответ | телефон семьи | todo |
| 4 | Immich size SSD = HDD backup | `du -sh` | todo |
| 5 | restic snapshot list (Vostro) без путей с PII | Vostro | optional |
| 6 | Cloud.ru FM chat 200 (без ключа в кадре) | workstation | optional |
| 7 | GitHub + GitVerse twin | browser | easy |
| 8 | Habr Part1 stats 13K | habr UI | easy |

---

## 6. Тон и табу

**Тон:** как Part 1 — инженерный дневник, RU, без «enterprise».  
**Табу:**

- пароли, IP внутренних хостов без нужды, peer count Amnezia детально;
- обещание «Immich ML уже на Nano»;
- реклама Сбера — только «как клиент физлица»;
- doxxing семьи.

**Можно:** названия сервисов, HTTP-коды, размеры 13G, ADR-номера, ссылки на public git.

---

## 7. Ответы комментаторам (каркас абзацев)

1. **GPU/JetPack** — GPU всё ещё не в prod ML; ценность Nano = low-power SoR + community JetPack stack, не «ChatGPT дома». Интеллект ушёл в gateway+cloud.  
2. **4 GB** — mem_limit, monitoring pressure; не раздували локальную LLM.  
3. **Immich ML** — CUDA 10.2 vs official 11/12; offload на RTX-ноут отвергли как prod-узел (кочует); Cloud.ru/очередь — другой путь.  
4. **Порты** — Part1 уже VPN-only; Part2 подтверждает, что так и осталось.  
5. **«Купи N150»** — не купили; дожали имеющееся + РФ API.

---

## 8. Календарь работ

| Шаг | Владелец | Оценка |
|---|---|---|
| Утвердить заголовок + тезис | owner | 1 день |
| Собрать скрины 1–8 | owner/agent | 1 вечер |
| Черновик 60% | agent | 1–2 сессии |
| Правка фактов (дата, размеры, SHA) | agent | 0.5 |
| Вычитка RU | owner | 1 вечер |
| Публикация Habr | owner | — |
| Анонс: GitHub README badge, Part1 cross-link | agent | 0.5 |

Целевое окно: **октябрь 2026** (не горячить до S3, если не готов честный «S3 ещё нет»).

---

## 9. Критерии «статья готова»

- [ ] Все цифры сверены с live (health, 13G, snapshot id optional)  
- [ ] Нет секретов на скринах  
- [ ] ADR-0007/8/9 объяснены человеческим языком  
- [ ] Комментарии Part1 закрыты по смыслу  
- [ ] CTA на GitHub + Part1  
- [ ] Part2 **не** врёт про Vostro-ML как текущий канон  

---

## 10. Связанные файлы

| Файл | Роль |
|---|---|
| Part1 live | https://habr.com/ru/articles/1062914/ |
| Feedback | `docs/plans/POST_HABR_FEEDBACK_2026-08.md` |
| Activity 2026-09 | `artifacts/reports/HABR_GITHUB_ACTIVITY_2026-09-08.md` |
| Canon | `docs/plans/DEVELOPMENT_PLAN_2026-09_SBER_ERA.md` |
| Drafts Part1 | `docs/articles/publication/habr_final.md` (не копипастить в Part2) |
| Этот план | `docs/articles/HABR_PART2_ARTICLE_PLAN_2026-09.md` |

---

## 11. EN one-liner

Part 2 Habr plan: after shipping a home NAS on Jetson, we re-architected around **Jetson as SoR**, dropped roaming GPU PC and corporate Vostro from prod, put **GigaChat-first** behind a redaction gateway, dual-homed RU cloud (PERS + Cloud.ru FM), and told the truth about backups (empty dumps, Immich→HDD, S3 still blocked). Answers Part 1 commenters without buying an N150.
