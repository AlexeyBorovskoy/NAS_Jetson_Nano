# HABR_PUBLICATION_CHECKLIST
> Generated: 2026-06-29
> Article: `docs/articles/publication/habr_final.md`
> Final publication target: Habr.com

---

## Чеклист публикации / Publication checklist

### БЛОК 1 — Текст статьи / BLOCK 1 — Article text

| # | Пункт / Item | Статус / Status | Примечание / Note |
|---|---|---|---|
| T1 | Число фото нормализовано (одно значение + пояснение расхождения) / Photo count normalized (one value + explanation of the discrepancy) | ❌ НЕ СДЕЛАНО / NOT DONE | Три разных числа: 6694/6697/6719 / Three different numbers: 6694/6697/6719 |
| T2 | Self-signed TLS помечен как временное решение / Self-signed TLS marked as a temporary solution | ❌ НЕ СДЕЛАНО / NOT DONE | Добавить «пока нет домена» / Add "no domain yet" |
| T3 | Docker 20.10.7 — добавлено объяснение constraint / Docker 20.10.7 — constraint explanation added | ❌ НЕ СДЕЛАНО / NOT DONE | Указать JetPack + CVE риск / Note the JetPack constraint + CVE risk |
| T4 | Off-site backup — добавлен план (restic + 2 ТБ HDD) / Off-site backup — plan added (restic + 2 TB HDD) | ❌ НЕ СДЕЛАНО / NOT DONE | Текущее: только «скрипты готовы» / Current: only "scripts are ready" |
| T5 | Добавлен раздел про USB-инциденты / USB-incident section added | ❌ НЕ СДЕЛАНО / NOT DONE | error-71, порт 4→2, CRLF / error-71, port 4→2, CRLF |
| T6 | Добавлен пример ошибки агента (WireGuard/DKMS) / Example of an agent mistake added (WireGuard/DKMS) | ❌ НЕ СДЕЛАНО / NOT DONE | Для баланса рекламного тона / To balance the promotional tone |
| T7 | GitHub-ссылка только в конце (убрать дубль из начала) / GitHub link only at the end (remove the duplicate from the top) | ⚠️ СПОРНО / DISPUTED | Верхняя ссылка — в метаданных хабов, это норма для Хабра / The top link is in the hub metadata, which is normal for Habr |
| T8 | Добавлен ответ на «почему не Synology» / Answer added to "why not Synology" | ❌ НЕ СДЕЛАНО / NOT DONE | Опционально / Optional |
| T9 | Добавлен раздел «Что бы я сделал иначе» / "What I would do differently" section added | ❌ НЕ СДЕЛАНО / NOT DONE | Опционально, но ценно / Optional, but valuable |
| T10 | Добавлен раздел «Безопасность: что закрыто» / "Security: what's locked down" section added | ❌ НЕ СДЕЛАНО / NOT DONE | Опционально / Optional |
| T11 | Нет реальных IP в тексте / No real IPs in the text | ✅ ГОТОВО / DONE | Все IP заменены на placeholders / All IPs replaced with placeholders |
| T12 | Нет паролей/токенов в тексте / No passwords/tokens in the text | ✅ ГОТОВО / DONE | Проверено / Verified |
| T13 | Нет личных данных (имена, email) без согласия / No personal data (names, email) without consent | ✅ ГОТОВО / DONE | Имена участников чата не упомянуты в тексте / Chat participant names are not mentioned in the text |

---

### БЛОК 2 — Изображения / BLOCK 2 — Images

| # | Пункт / Item | Статус / Status | Примечание / Note |
|---|---|---|---|
| I1 | android_davx5_caldav.jpg — VPS IP размыт / VPS IP blurred | ❌ НЕ СДЕЛАНО / NOT DONE | **КРИТИЧНО** / **CRITICAL** |
| I2 | immich_web.png — лица семьи: согласие/blur / family faces: consent/blur | ❌ НЕ СДЕЛАНО / NOT DONE | **КРИТИЧНО** / **CRITICAL** |
| I3 | nextcloud_talk.png — содержимое чата проверено / chat content reviewed | ❌ НЕ СДЕЛАНО / NOT DONE | **КРИТИЧНО** / **CRITICAL** |
| I4 | nas_jetson_nano_api_swagger.png — IP в адресной строке размыт / IP in the address bar blurred | ❌ НЕ СДЕЛАНО / NOT DONE | ВЫСОКИЙ / HIGH |
| I5 | beszel_systems_overview.png — IP проверен / IP checked | ❌ НЕ СДЕЛАНО / NOT DONE | СРЕДНИЙ / MEDIUM |
| I6 | android_immich_backup_stats.jpg — имя устройства проверено / device name checked | ❌ НЕ СДЕЛАНО / NOT DONE | СРЕДНИЙ / MEDIUM |
| I7 | nextcloud_dashboard.png — имена файлов проверены / file names checked | ❌ НЕ СДЕЛАНО / NOT DONE | СРЕДНИЙ / MEDIUM |
| I8 | beszel_jetson_metrics.png — просмотрен / reviewed | ❌ НЕ СДЕЛАНО / NOT DONE | НИЗКИЙ / LOW |
| I9 | Все 8 изображений загружены в Habr editor / All 8 images uploaded to the Habr editor | ❌ НЕ СДЕЛАНО / NOT DONE | Последний шаг / Final step |
| I10 | Alt-текст для каждого изображения заполнен / Alt text filled in for every image | ❌ НЕ СДЕЛАНО / NOT DONE | Habr editor |

---

### БЛОК 3 — Технические факты / BLOCK 3 — Technical facts

| # | Пункт / Item | Статус / Status | Примечание / Note |
|---|---|---|---|
| F1 | Подтверждено 13 контейнеров (docker ps) / 13 containers confirmed (docker ps) | ⚠️ SSH недоступен / SSH unavailable | Проверить через VPS tunnel / Verify via the VPS tunnel |
| F2 | goss 40/40 подтверждён / goss 40/40 confirmed | ⚠️ SSH недоступен / SSH unavailable | Последнее: 2026-06-28 / Last confirmed: 2026-06-28 |
| F3 | Write 250 MB/s подтверждён / Write 250 MB/s confirmed | ✅ Из checkpoint 2026-06-28 / From the 2026-06-28 checkpoint | Измерено после UAS quirk / Measured after the UAS quirk |
| F4 | Read 172 MB/s подтверждён / Read 172 MB/s confirmed | ✅ Из checkpoint 2026-06-28 / From the 2026-06-28 checkpoint | Измерено после UAS quirk / Measured after the UAS quirk |
| F5 | SSD 229 GB подтверждён / SSD 229 GB confirmed | ✅ CLAUDE.md | /mnt/storage |
| F6 | 5 человек в Talk / 5 people in Talk | ✅ Из checkpoint 2026-06-29 / From the 2026-06-29 checkpoint | admin+olga+ivan+ulyana+anna |

---

### БЛОК 4 — Habr-специфика / BLOCK 4 — Habr specifics

| # | Пункт / Item | Статус / Status | Примечание / Note |
|---|---|---|---|
| H1 | Теги выбраны (selfhosted, nextcloud, immich, etc.) / Tags selected | ✅ ГОТОВО / DONE | В заголовке статьи / In the article header |
| H2 | Хабы выбраны (Сисадмин, Open Source, AI, Self-hosted) / Hubs selected | ✅ ГОТОВО / DONE | В заголовке статьи / In the article header |
| H3 | `<cut>` тег стоит после первого абзаца / `<cut>` tag placed after the first paragraph | ✅ ГОТОВО / DONE | Есть в тексте после вводного абзаца / Present in the text after the intro paragraph |
| H4 | Заголовок статьи < 120 символов / Article title < 120 characters | ✅ ГОТОВО / DONE | «Старому «железу» новую жизнь…» / "New life for old hardware…" |
| H5 | Markdown скопирован в Habr editor / Markdown copied into the Habr editor | ❌ НЕ СДЕЛАНО / NOT DONE | Финальный шаг / Final step |
| H6 | Preview статьи в Habr проверен / Habr article preview checked | ❌ НЕ СДЕЛАНО / NOT DONE | Финальный шаг / Final step |
| H7 | Репозиторий публичный и доступен / Repository is public and reachable | ✅ ГОТОВО / DONE | github.com/AlexeyBorovskoy/NAS_Jetson_Nano |
| H8 | README.md репозитория обновлён / Repository README.md updated | ✅ ГОТОВО / DONE | По checkpoint 2026-06-27c / As of checkpoint 2026-06-27c |

---

### БЛОК 5 — Безопасность перед публикацией / BLOCK 5 — Security before publication

| # | Пункт / Item | Статус / Status | Примечание / Note |
|---|---|---|---|
| S1 | `./scripts/security/check_no_secrets.sh` прошёл / passed | ❌ НЕ ЗАПУСКАЛСЯ / NOT RUN | Запустить перед финальным push / Run before the final push |
| S2 | git history не содержит секретов / git history contains no secrets | ✅ Очищен / Cleaned | filter-repo выполнен 2026-06-28 / filter-repo run on 2026-06-28 |
| S3 | secrets.json в .gitignore / secrets.json in .gitignore | ✅ Подтверждено / Confirmed | |
| S4 | .env файлы не в репозитории / .env files not in the repository | ✅ Подтверждено / Confirmed | В .gitignore / In .gitignore |

---

## Порядок действий для публикации / Publication action sequence

🇷🇺
```
1. Запустить security check: ./scripts/security/check_no_secrets.sh
2. Открыть каждый из 8 скриншотов, провести проверку по IMAGE_REDACTION_CHECKLIST.md
3. Отредактировать скриншоты (android_davx5_caldav.jpg — обязательно, immich_web.png — обязательно)
4. Внести правки R1-R4 из HABR_ARTICLE_EDITOR_REPORT.md в habr_final_edited.md
5. Проверить habr_final_edited.md как финальную версию
6. Открыть habr.com → новая статья → скопировать текст из habr_final_edited.md
7. Загрузить все 8 скриншотов через Habr editor (использовать publication/screenshots/)
8. Проставить alt-тексты для каждого изображения
9. Нажать Preview — проверить рендеринг markdown и изображений
10. Опубликовать
```

🇬🇧
```
1. Run the security check: ./scripts/security/check_no_secrets.sh
2. Open each of the 8 screenshots and review it against IMAGE_REDACTION_CHECKLIST.md
3. Edit the screenshots (android_davx5_caldav.jpg — mandatory, immich_web.png — mandatory)
4. Apply fixes R1-R4 from HABR_ARTICLE_EDITOR_REPORT.md into habr_final_edited.md
5. Review habr_final_edited.md as the final version
6. Open habr.com → new article → paste the text from habr_final_edited.md
7. Upload all 8 screenshots through the Habr editor (use publication/screenshots/)
8. Fill in alt text for every image
9. Click Preview — check markdown and image rendering
10. Publish
```

---

## Текущий статус готовности / Current readiness status

🇷🇺
```
Текст статьи:           ⚠️ 7/10 — требует 4 обязательных правки
Изображения:            ❌ 0/8 — не проверены, критические риски
Технические факты:      ✅ 4/6 — 2 требуют SSH проверки
Habr-специфика:         ✅ 4/8 — финальные шаги в редакторе
Безопасность:           ✅ 3/4 — запустить check_no_secrets.sh

ИТОГО: НЕ ГОТОВО К ПУБЛИКАЦИИ — требует ~3-4 часа работы
```

🇬🇧
```
Article text:           ⚠️ 7/10 — needs 4 mandatory fixes
Images:                 ❌ 0/8 — unreviewed, critical risks
Technical facts:        ✅ 4/6 — 2 require SSH verification
Habr specifics:         ✅ 4/8 — final steps in the editor
Security:               ✅ 3/4 — run check_no_secrets.sh

TOTAL: NOT READY FOR PUBLICATION — needs ~3-4 hours of work
```
