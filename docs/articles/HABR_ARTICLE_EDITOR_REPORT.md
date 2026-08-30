# HABR_ARTICLE_EDITOR_REPORT
> Generated: 2026-06-29
> Article: `docs/articles/publication/habr_final.md`
> Reviewer: Claude Code editorial agent

---

## 1. Сильные стороны текущей статьи / Strengths of the current article

🇷🇺 **Структура и подача:**
- Чёткое разделение на «шаги» — читатель понимает хронологию проекта.
- Начало с личной истории (нашёл Jetson сына) — сразу создаёт эмоциональный контекст.
- Честная оценка («Что ещё не сделано») — это редкость на Хабре и вызывает доверие.
- Архитектурная схема в ASCII — понятна без внешних изображений.
- Таблицы с mem_limit контейнеров — практически полезны, читатели-практики оценят.

**Технический контент:**
- Конкретные числа: 250 MB/s write, 172 MB/s read, 6697 фото, 40/40 goss — это хорошо.
- UAS quirk объяснён с флагом `u` и эффектом (8 MB/s → 250 MB/s) — наглядно.
- Объяснение выбора мониторинга (9 инструментов, почему не Zabbix) — показывает процесс принятия решений.
- AGENTS.md как «память агента» — нетривиальный инсайт, которого нет в большинстве AI-статей.
- Обоснование reverse SSH tunnel vs WireGuard/Tailscale — конкретные причины.

**Язык:**
- Живой, не академический. Фразы типа «написал агенту просто» работают.
- Промпты приведены как есть — это аутентично.

🇬🇧 **Structure and delivery:**
- Clear division into "steps" — the reader follows the project's chronology.
- Opening with a personal story (found the son's Jetson) — creates immediate emotional context.
- Honest assessment ("What's not done yet") — rare on Habr and builds trust.
- ASCII architecture diagram — understandable without external images.
- Container mem_limit tables — practically useful, practitioner readers will appreciate them.

**Technical content:**
- Concrete numbers: 250 MB/s write, 172 MB/s read, 6697 photos, 40/40 goss — good.
- The UAS quirk is explained with the `u` flag and its effect (8 MB/s → 250 MB/s) — clear and visual.
- Explanation of the monitoring stack choice (9 tools, why not Zabbix) — shows the decision-making process.
- AGENTS.md as "agent memory" — a non-trivial insight absent from most AI articles.
- Justification for the reverse SSH tunnel vs WireGuard/Tailscale — concrete reasons.

**Language:**
- Lively, not academic. Phrases like "just told the agent" work well.
- Prompts are quoted as-is — this feels authentic.

---

## 2. Слабые разделы / Weak sections

### 2.1. Отсутствует раздел про USB-инциденты / Missing USB-incident section

🇷🇺 Статья упоминает JMS583 и quirk, но скрывает **три реальных инцидента**, которые произошли в процессе:
1. error -71 (RTL9210B-CG autosuspend) — первый бокс вышел из строя
2. Сломанный USB-порт 4 на Jetson → переткнуть в порт 2
3. CRLF в shebang скриптов (Windows-специфичная проблема, уронила systemd units)

Это самый живой и интересный материал для технической аудитории Хабра — а его нет.

🇬🇧 The article mentions the JMS583 and the quirk, but hides **three real incidents** that happened along the way:
1. error -71 (RTL9210B-CG autosuspend) — the first enclosure failed
2. A broken USB port 4 on the Jetson → moved to port 2
3. CRLF in script shebangs (a Windows-specific problem that broke systemd units)

This is the liveliest and most interesting material for Habr's technical audience — and it's missing.

### 2.2. Раздел про Claude Code слишком рекламный / The Claude Code section reads as too promotional

🇷🇺 Фразы «агент определил сам что трогать нельзя» и «агент написал 9 роутеров, Pydantic-модели, JWT middleware» без единого упоминания о неудачах создают нереалистичную картину. Хабр-аудитория ценит честность. Нужен хотя бы один пример где агент ошибся.

🇬🇧 Phrases like "the agent figured out on its own what not to touch" and "the agent wrote 9 routers, Pydantic models, JWT middleware" without a single mention of failures create an unrealistic picture. The Habr audience values honesty. At least one example of the agent getting it wrong is needed.

### 2.3. Безопасность — только одна строка / Security — just one line

🇷🇺 «Финальная проверка безопасности — только человеком» — слишком кратко. Читатели захотят знать: что именно было сделано? Какие порты открыты? Есть ли firewall?

🇬🇧 "Final security review — human only" is too brief. Readers will want to know: what exactly was done? Which ports are open? Is there a firewall?

### 2.4. Self-signed TLS преподнесён как финальное решение / Self-signed TLS presented as a final solution

🇷🇺 «Браузер предупреждает один раз — принять сертификат и больше к этому не возвращаться» — это нормально для домашнего использования, но читатели могут воспринять как небрежность. Нужно добавить фразу «пока нет домена» и упомянуть Caddy/Let's Encrypt как следующий шаг.

🇬🇧 "The browser warns once — accept the certificate and never think about it again" is fine for home use, but readers may perceive it as carelessness. Add the phrase "no domain yet" and mention Caddy/Let's Encrypt as the next step.

### 2.5. Docker 20.10.7 упомянут без контекста / Docker 20.10.7 mentioned without context

🇷🇺 В разделе «Что ещё не сделано» стоит: «Docker 20.10.7 устарел — обновить нетривиально из-за JetPack зависимостей» — без объяснения почему это важно для безопасности (CVE) и что именно мешает обновить.

🇬🇧 The "What's not done yet" section states: "Docker 20.10.7 is outdated — upgrading is non-trivial due to JetPack dependencies" — without explaining why this matters for security (CVE) and what exactly blocks the upgrade.

### 2.6. Ссылка на GitHub в самом начале / GitHub link at the very top

🇷🇺 GitHub-ссылка вынесена в самый верх в хабах/тегах. Для Хабра это нормально, но в тексте ссылка повторяется ещё раз в конце — дублирование. Лучше одна ссылка — в конце.

🇬🇧 The GitHub link is placed at the very top in the hubs/tags. That's normal for Habr, but the link is repeated again at the end of the text — a duplication. Better to have a single link — at the end.

### 2.7. Нет раздела «Что бы я сделал иначе» / No "What I would do differently" section

🇷🇺 Опытная аудитория Хабра ценит рефлексию. Что не сработало? Что переделал бы?

🇬🇧 Habr's experienced audience values reflection. What didn't work? What would be redone?

---

## 3. Отсутствующие доказательства / Missing evidence

| Заявление / Claim | Доказательство / Evidence | Статус / Status |
|---|---|---|
| Write 250 MB/s | dd/fio вывод / dd/fio output | Отсутствует в статье / Missing from the article |
| Read 172 MB/s | dd/fio вывод / dd/fio output | Отсутствует в статье / Missing from the article |
| 40/40 goss | Terminal вывод / Terminal output | Не показан (только текст) / Not shown (text only) |
| 13 контейнеров up / 13 containers up | docker ps вывод / docker ps output | Не показан (есть Beszel screenshot) / Not shown (a Beszel screenshot exists) |
| JMS583 vs RTL9210B-CG сравнение / comparison | Таблица скоростей / Speed table | Отсутствует / Missing |
| Telegram daily report | Screenshot есть в assets/, но не использован / Screenshot exists in assets/ but unused | Можно добавить / Could be added |

🇷🇺 **Рекомендация:** Добавить хотя бы один terminal screenshot (goss или dd) для подтверждения ключевых цифр.

🇬🇧 **Recommendation:** Add at least one terminal screenshot (goss or dd) to back up the key figures.

---

## 4. Риски безопасности / приватности / Security / privacy risks

🇷🇺 **В тексте статьи:**
- `IP:192.168.x.x` в openssl команде — заменён на placeholder ✅ (это хорошо)
- `[Jetson Nano — домашняя сеть 192.168.x.x]` в ASCII-схеме — placeholder ✅
- Упоминание «VPS в Европе» без конкретного IP ✅
- Упоминание имён семьи (Шаг 6: «группа на 5 человек») — без имён ✅
- Telegram bot упомянут без токена ✅

**Потенциальные риски в скриншотах (требует ручной проверки):**
- `beszel_systems_overview.png` — могут быть видны IP-адреса серверов в Beszel UI
- `beszel_jetson_metrics.png` — может отображать hostname, LAN IP
- `nas_jetson_nano_api_swagger.png` — URL в браузере может содержать реальный IP
- `nextcloud_dashboard.png` — имена пользователей/файлов
- `nextcloud_talk.png` — имена участников чата, сообщения
- `android_immich_backup_stats.jpg` — имя телефона, email аккаунта
- `android_davx5_caldav.jpg` — URL с реальным IP VPS

**В secrets.json:**
- Файл содержит реальные пароли, IP и API-ключи
- Подтверждено: файл в .gitignore, не в репозитории
- НЕ ВКЛЮЧАТЬ в article evidence никакие значения из этого файла ✅

🇬🇧 **In the article text:**
- `IP:192.168.x.x` in the openssl command — replaced with a placeholder ✅ (good)
- `[Jetson Nano — home network 192.168.x.x]` in the ASCII diagram — placeholder ✅
- "VPS in Europe" mentioned without a specific IP ✅
- Family names mentioned (Step 6: "a group of 5 people") — without names ✅
- Telegram bot mentioned without the token ✅

**Potential risks in the screenshots (requires manual review):**
- `beszel_systems_overview.png` — server IP addresses may be visible in the Beszel UI
- `beszel_jetson_metrics.png` — may show hostname, LAN IP
- `nas_jetson_nano_api_swagger.png` — the browser URL may contain a real IP
- `nextcloud_dashboard.png` — usernames/file names
- `nextcloud_talk.png` — chat participant names, messages
- `android_immich_backup_stats.jpg` — phone name, account email
- `android_davx5_caldav.jpg` — URL with the real VPS IP

**In secrets.json:**
- The file contains real passwords, IPs, and API keys
- Confirmed: the file is in .gitignore, not in the repository
- DO NOT INCLUDE any values from this file in the article evidence ✅

---

## 5. Оценка рекламного характера упоминаний Claude Code / Assessment of how promotional the Claude Code mentions are

🇷🇺 **Текущее состояние:** Умеренно рекламный, но не агрессивно.

**Что работает нормально:**
- Конкретные промпты приведены как есть — это честно.
- «AI-агент — не волшебная кнопка» в разделе «Итог» — правильная нота.

**Что звучит как реклама:**
- «Агент сам определил что трогать нельзя» — звучит как функция продукта, а не описание работы.
- «Агент написал 9 роутеров, Pydantic-модели, JWT middleware, полную OpenAPI-документацию» — без упоминания итераций, правок, ошибок.
- «За один сеанс получил структурированный репозиторий, который вручную расставлял бы несколько часов» — возможно правда, но без показа сколько сессий ушло на доработку.

**Рекомендация:** Добавить 1-2 примера где агент дал неправильную рекомендацию (например, предложил WireGuard без учёта kernel constraint) и как это было скорректировано. Это увеличит доверие.

🇬🇧 **Current state:** Moderately promotional, but not aggressively so.

**What works fine:**
- Concrete prompts are quoted as-is — this is honest.
- "The AI agent is not a magic button" in the "Summary" section — the right note to strike.

**What sounds like advertising:**
- "The agent figured out on its own what not to touch" — sounds like a product feature rather than a description of the work.
- "The agent wrote 9 routers, Pydantic models, JWT middleware, full OpenAPI documentation" — without mentioning iterations, edits, or mistakes.
- "Got a structured repository in one session that would have taken hours to arrange by hand" — possibly true, but without showing how many sessions the follow-up work actually took.

**Recommendation:** Add 1-2 examples where the agent gave a wrong recommendation (e.g., suggested WireGuard without accounting for the kernel constraint) and how it was corrected. This will increase trust.

---

## 6. Возможные критические комментарии на Хабре / Possible critical comments on Habr

🇷🇺
1. **«Почему не просто купить Synology/QNAP?»** — нет явного ответа на это возражение. Нужно добавить 1-2 предложения про price/control tradeoff.
2. **«self-signed без домена — это не безопасность»** — нужно прямо сказать «временное решение».
3. **«Docker 20.10.7 с незакрытыми CVE»** — нужно признать риск прямо.
4. **«USB SSD для production — это риск»** — нужно упомянуть что это домашний сервер, не production.
5. **«Как Claude Code помогает? Покажи diff до/после»** — нет примеров кода до/после AI.
6. **«Три разных числа для фото (6694/6697/6719)»** — читатели заметят.
7. **«Где off-site backup? Без него это игрушка»** — статья честно упоминает отсутствие, но без плана.
8. **«Зачем NAS_Jetson_Nano API поверх всего? Портainер же есть»** — нет обоснования зачем REST API.

🇬🇧
1. **"Why not just buy a Synology/QNAP?"** — no explicit answer to this objection. Add 1-2 sentences about the price/control tradeoff.
2. **"self-signed without a domain isn't security"** — need to say plainly "a temporary solution."
3. **"Docker 20.10.7 with unpatched CVEs"** — need to acknowledge the risk directly.
4. **"USB SSD for production is a risk"** — need to mention that this is a home server, not production.
5. **"How does Claude Code actually help? Show a before/after diff"** — no before/after code examples.
6. **"Three different photo counts (6694/6697/6719)"** — readers will notice.
7. **"Where's the off-site backup? Without it this is a toy"** — the article honestly mentions the gap, but without a plan.
8. **"Why an API on top of everything? Portainer already exists"** — no justification for the REST API.

---

## 7. Обязательные правки перед публикацией / Mandatory fixes before publication

| # | Правка / Fix | Приоритет / Priority |
|---|---|---|
| R1 | Нормализовать число фото: одно число + объяснение расхождения / Normalize the photo count: one number + explanation of the discrepancy | КРИТИЧНО / CRITICAL |
| R2 | Добавить раздел «Три USB-инцидента» (error-71, порт 4→2, CRLF) / Add a "Three USB incidents" section (error-71, port 4→2, CRLF) | ВЫСОКИЙ / HIGH |
| R3 | Self-signed TLS — добавить «пока нет домена, следующий шаг — Caddy» / Add "no domain yet, next step is Caddy" | ВЫСОКИЙ / HIGH |
| R4 | Docker 20.10.7 — добавить «JetPack constraint, CVE-риск известен» / Add "JetPack constraint, CVE risk is known" | ВЫСОКИЙ / HIGH |
| R5 | Off-site backup — добавить план (restic на VPS, когда будет 2 ТБ HDD) / Add a plan (restic on the VPS, once the 2 TB HDD arrives) | СРЕДНИЙ / MEDIUM |
| R6 | Добавить 1 пример ошибки агента (WireGuard/DKMS) / Add 1 example of an agent mistake (WireGuard/DKMS) | СРЕДНИЙ / MEDIUM |
| R7 | Убрать дублирующуюся GitHub-ссылку из начала / Remove the duplicate GitHub link from the top | НИЗКИЙ / LOW |
| R8 | Добавить ответ на «почему не Synology» / Add an answer to "why not Synology" | СРЕДНИЙ / MEDIUM |

---

## 8. Опциональные улучшения / Optional improvements

| # | Улучшение / Improvement | Обоснование / Rationale |
|---|---|---|
| O1 | Раздел «Что бы я сделал иначе» / "What I would do differently" section | Повышает доверие, популярен на Хабре / Builds trust, popular on Habr |
| O2 | Раздел «Безопасность: что закрыто» (UFW, порты, sudo) / "Security: what's locked down" section (UFW, ports, sudo) | Снимает вопросы безопасности / Preempts security questions |
| O3 | Скриншот goss 40/40 terminal output | Доказательство ключевой цифры / Evidence for a key figure |
| O4 | Скриншот dd или fio (250 MB/s write) / Screenshot of dd or fio (250 MB/s write) | Доказательство скорости SSD / Evidence for the SSD speed |
| O5 | Telegram daily report screenshot | Уже есть в assets/, не использован / Already in assets/, unused |
| O6 | Таблица: JMS583 vs RTL9210B-CG (скорости, стабильность) / Table: JMS583 vs RTL9210B-CG (speeds, stability) | Наглядный контраст / A clear visual contrast |
| O7 | Добавить NAS_Jetson_Nano API обоснование (почему не только Portainer) / Add a justification for the NAS_Jetson_Nano API (why not just Portainer) | Снимает вопрос «зачем?» / Preempts the "why?" question |
| O8 | Добавить заметку про Xiaomi battery whitelist (конкретные шаги) / Add a note about the Xiaomi battery whitelist (concrete steps) | Практическая польза / Practical usefulness |

---

## Итоговая оценка готовности к публикации / Final publication-readiness assessment

🇷🇺 **Текущий рейтинг: 7/10 — требует правок перед публикацией**

Статья написана живым языком, технически честная, с реальными числами и промптами. Главные проблемы: несогласованные числа фото (3 разных значения), отсутствие USB-инцидентов (самый интересный материал), и слегка рекламная подача AI-компонента. После правок R1-R4 рейтинг выйдет на 8.5-9/10.

🇬🇧 **Current rating: 7/10 — needs fixes before publication**

The article is written in a lively style, is technically honest, and includes real numbers and prompts. The main problems: inconsistent photo counts (3 different values), missing USB incidents (the most interesting material), and a slightly promotional framing of the AI component. After fixes R1-R4, the rating should reach 8.5-9/10.
