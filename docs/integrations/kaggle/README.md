# Kaggle — бесплатный GPU для подготовительных работ / free GPU for preparation work

> 🇷🇺 Ресурс заведён владельцем 2026-09-20, регистрация сделана **специально для этого проекта**.
> EN summary — в конце.

## 1. Зачем он здесь

У Jetson Nano есть GPU, но 4 ГБ общей памяти и старый CUDA: на нём нельзя ни обучать модели, ни спокойно
их сравнивать — там живут фотографии и файлы семьи. Kaggle даёт бесплатный GPU в браузере, и это удобное
место для работ **подготовительных**, результат которых потом переносится домой одним файлом.

## 2. Что можно (и это полезно проекту)

| Задача | Что делает Kaggle | Что приезжает домой |
|---|---|---|
| Голосовые сообщения `@бобик` | сравнить модели распознавания русской речи (Vosk small, whisper.cpp разных размеров) на **публичных** наборах: скорость, точность, вес | выбранная модель + числа для решения |
| Immich ML (если владелец вернётся к D4) | прогнать модели распознавания лиц и смыслового поиска на публичных фото, измерить память и время | вывод «влезает/не влезает в Jetson» с замерами |
| Подготовка моделей | квантование и конвертация (ONNX, GGUF) под слабое железо | готовый файл модели |
| Тяжёлые бенчмарки | то, что нельзя гонять на боевом Jetson | таблица замеров для статьи и решений |

## 3. Чего на Kaggle не делаем — жёстко

- **Семейные фотографии, видео, документы, переписка туда не уезжают.** Никогда, ни в каком виде, включая
  «только превью» и «только для теста». Это правило ADR-0010 и `AGENTS.md` п. 4; Kaggle — публичная площадка,
  ноутбуки по умолчанию видны всем.
- Не загружаем дампы баз, `.env`, ключи, токены, имена и логины членов семьи.
- Не делаем Kaggle частью рабочего контура: дом не должен зависеть от внешнего сервиса. Всё, что оттуда
  приходит, — файл модели или таблица чисел, а не работающий сервис.
- Результаты, полученные на чужом железе, не переносятся в проект как факт без перепроверки на Jetson:
  «на Kaggle 40 мс» ≠ «на Jetson 40 мс».

## 4. Доступ

- Токен: `kaggle/kaggle.json` в корне репозитория — каталог **в `.gitignore`** (строка `kaggle/`), в git не попадает.
- Копия ключа: Windows Credential Manager, ресурс `nas-kaggle-api` (имя пользователя = логин Kaggle).
- Проверка, что токен жив (ключ не печатается):
  ```powershell
  $j = Get-Content "…\kaggle\kaggle.json" -Raw | ConvertFrom-Json
  $auth = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($j.username):$($j.key)"))
  (Invoke-RestMethod -Uri "https://www.kaggle.com/api/v1/competitions/list?page=1" -Headers @{Authorization=$auth}).Count
  ```
  Замер 2026-09-20: ответ получен, API отвечает.
- Квоты бесплатного GPU (часы в неделю, длительность сессии, размер данных) — по документации Kaggle;
  **в проекте не замерены**, проверяются при первом реальном использовании и записываются сюда с датой.

## 5. Как результат попадает в проект

1. Ноутбук на Kaggle делает работу на публичных данных.
2. Наружу забирается **артефакт**: файл модели или таблица замеров.
3. Артефакт проверяется на Jetson (или в контейнере на станции) — числа снимаются заново.
4. В проект идёт решение с датой замера; сам ноутбук и сырые выгрузки остаются вне git
   (`docs/local/` или загрузки), в статью — только итог.

## 6. Ближайшее применение

Голосовые сообщения для `@бобик`: выбрать модель распознавания русской речи для Jetson. Это первая задача,
где Kaggle реально экономит время — иначе сравнение моделей пришлось бы гонять на боевом устройстве.

---

### EN summary
Kaggle was registered by the owner specifically for this project and gives free GPU time in the browser. It is
used only for preparation work whose result comes home as a single artefact: comparing Russian speech-recognition
models for the family bot's voice messages, checking whether Immich ML models fit the Jetson, quantising models
for weak hardware, and running benchmarks too heavy for a live Jetson. Family photos, videos, documents, chats,
database dumps and secrets never go there — Kaggle is a public platform, and this is the ADR-0010 rule. The token
lives in the git-ignored `kaggle/` directory and in Windows Credential Manager (`nas-kaggle-api`); free-tier
quotas are not measured yet and will be recorded here with a date when first used. Numbers measured on Kaggle
hardware are never carried into the project as facts without re-measuring on the Jetson.
