# Immich ML на станции ROG — runbook запуска (D4, вариант Б)

> Дата: 2026-09-26. Статус: **комплект готов, ждёт включения гипервизора на
> станции** (административный шаг владельца, см. §2). На устройстве и станции
> ничего не менялось при подготовке — только чтение и файлы в git. Английская
> версия — `IMMICH_ML_STATION_RUNBOOK.md`. Решение и цифры — `D4_IMMICH_ML_DECISION.md`;
> исходный пилот-план — `IMMICH_ML_ROG_FREE_PILOT.md`.

## 1. Что это

Immich на Jetson никогда не запускал `immich-machine-learning` — 0 % ML-обработки
на 7646 ассетов (`smart_search`=0, `asset_face`=0, замер 2026-09-26). Вариант Б
(`D4_IMMICH_ML_DECISION.md`) — считать смысловой поиск и распознавание лиц
разовым батчем на домашней станции ROG (RTX 3050 Ti, 4 ГиБ VRAM, драйвер 596.36),
через обратный SSH-туннель, тем же способом, что и локальная языковая модель.
Превью и эмбеддинги не покидают дом ни на шаг (`AGENTS.md` §4, ADR-0010).

Файлы комплекта:

| Файл | Роль |
|---|---|
| `docker/compose/docker-compose.immich-ml-rog.yml` | ML-воркер на станции, порт на `127.0.0.1`, GPU через `deploy.resources.reservations.devices` |
| `config/immich-ml-rog.env.example` → `config/immich-ml-rog.env` (вне git) | версия закреплена на `v2.7.5` (как на Jetson) |
| `scripts/workstation/immich_ml_station.ps1` | `start` / `stop` / `status` на станции |
| `scripts/immich/set_ml_url.sh` | `set` / `restore` / `show` — правит `machineLearning` в Immich через API |

## 2. Предусловия

Ничего из runbook'а не выполняется, пока не закрыты все пункты:

1. **Гипервизор Windows включён** и станция перезагружена:
   ```powershell
   dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   bcdedit /set hypervisorlaunchtype auto
   # затем перезагрузка
   ```
   Проверка: `(Get-ComputerInfo).HyperVisorPresent` → `True`. Это единственный
   административный блокер, отложенный владельцем с 2026-09-12 (`D4` §4).
2. **Docker Desktop запущен**, в настройках включена поддержка GPU (WSL2-бэкенд,
   NVIDIA Container Toolkit ставится автоматически с современным Docker Desktop).
3. **Драйвер NVIDIA ≥ 545** (для CUDA 12.3, `docs.immich.app/features/ml-hardware-acceleration`).
   Замер 2026-09: 596.36 — с запасом.
4. **Питание от сети, сон выключен** на время прогона — обрыв Wi-Fi/спящий режим
   роняет и туннель, и Docker посреди индексации (риск из `IMMICH_ML_ROG_FREE_PILOT.md`).
5. **`config/immich-ml-rog.env`** создан на станции (копия `.example`, вне git).
   `IMMICH_VERSION` в нём обязан совпадать с версией на Jetson — сверить:
   ```bash
   ssh admin@192.168.0.50 "docker inspect homecloud_immich_server --format '{{.Config.Image}}'"
   ```
6. **API-ключ Immich с правами на `system-config`.** Создаётся в самом Immich:
   Administration → Settings → API Keys → New API Key (права администратора).
   Хранить вне git — как пароли restic (Windows Credential Manager), не печатать
   в логах и не коммитить.
7. **SSH-ключ станция → Jetson рабочий** — тот же, что уже использует
   `scripts/workstation/nas-tunnel.ps1` для локальной модели.

## 3. Запуск

На станции:

```powershell
cd "E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano"
powershell -ExecutionPolicy Bypass -File scripts\workstation\immich_ml_station.ps1 -Command start
```

Скрипт: поднимает `immich_ml_rog` (`docker compose up -d`), ждёт `/ping`
на `127.0.0.1:3003`, поднимает обратный туннель на `172.17.0.1:3003` на Jetson
(`GatewayPorts clientspecified` там уже включён — контейнеры увидят порт именно
по этому адресу, не по `127.0.0.1`).

Дальше — один раз за сессию пилота — прописать URL в самом Immich (не в `.env`
и не перезапуском контейнера: с версии с Admin UI это хранится в БД и
перезаписывает переменную окружения):

```bash
export IMMICH_API_KEY='...'                         # не коммитить, не печатать
# запускать либо на Jetson (IMMICH_BASE_URL по умолчанию http://127.0.0.1:2283),
# либо с любой машины в домашней LAN (IMMICH_BASE_URL=http://192.168.0.50:2283)
bash scripts/immich/set_ml_url.sh set http://172.17.0.1:3003
```

Скрипт сам: читает текущий `system-config`, сохраняет его копию в
`/mnt/storage/backups/immich-system-config/system-config.<UTC-время>.json`
(на Jetson; со станции — в `./immich-system-config-backups`), затем шлёт
`PUT /api/system-config` с `machineLearning.enabled=true` и новым `urls`.

Проверить состояние с самой станции:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\workstation\immich_ml_station.ps1 -Command status
```

Покажет: статус контейнера, `nvidia-smi`, жив ли туннель, и ответ на
`/ping` **с самого Jetson** (кросс-проверка, а не только со станции).

## 4. Пробный прогон на одном альбоме

Честно, по проверке OpenAPI-спеки Immich (закреплена на тег `v2.7.5`, та же
версия, что на Jetson):

- **Face Detection МОЖНО ограничить конкретными снимками** — `POST /api/assets/jobs`
  принимает `{"assetIds": [...], "name": "refresh-faces"}` (`AssetJobName` включает
  `refresh-faces`). Значит можно взять состав одного альбома и прогнать
  распознавание лиц только по нему:

  ```bash
  ALBUM_ID='...'   # Administration → Albums, или из URL альбома в UI
  ASSET_IDS=$(curl -s -H "x-api-key: $IMMICH_API_KEY" \
      "$BASE/api/albums/$ALBUM_ID" | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps([a['id'] for a in d['assets']]))")
  curl -s -X POST -H "x-api-key: $IMMICH_API_KEY" -H "Content-Type: application/json" \
      -d "{\"assetIds\": $ASSET_IDS, \"name\": \"refresh-faces\"}" \
      "$BASE/api/assets/jobs"
  ```

- **Smart Search (CLIP) ограничить одним альбомом НЕЛЬЗЯ.** В спеке нет
  per-asset/per-album эндпоинта для смыслового поиска — только
  библиотека целиком, через очередь `smartSearch` (Administration → Jobs →
  Smart Search → «Missing»/«All», или тот же вызов через API:
  `PUT /api/jobs/smartSearch` с телом `{"command":"start","force":false}` —
  `force:false` соответствует кнопке «Missing», `force:true` — «All»).

  Честный компромисс для пробы: запустить Smart Search сразу на всю
  библиотеку (7646 ассетов), но **в первый раз — с открытым `status`**
  (GPU-утилизация, память) и SQL-счётчиком (§8), а не «запустить и уйти».
  Если через 10–15 минут `smart_search` не растёт и GPU простаивает —
  остановить (`docker compose ... down` на станции) и разбираться, не ждать
  часами.

- Заодно распознавание лиц (`facialRecognition` — сборка эмбеддингов в
  «людей», в отличие от `faceDetection`/`refresh-faces` — поиска самих лиц на
  кадре) тоже не сузить до альбома — это отдельная библиотечная очередь.

## 5. Полный прогон

Проще всего — через UI: **Administration → Jobs → Smart Search / Face
Detection / Facial Recognition → Missing** (или «All», если нужно
переиндексировать всё заново, включая уже обработанное).

Во время прогона следить:

```powershell
# на станции, повторять
powershell -File scripts\workstation\immich_ml_station.ps1 -Command status
```

и держать открытым `docker stats` для `homecloud_immich_server` /
`homecloud_immich_microservices` на Jetson — см. риск в §6.

## 6. Что происходит, когда станция выключена

Два факта, оба проверены в вебе 2026-09-26, друг другу не противоречат, но
дают разную степень доверия:

1. **У Immich есть штатная защита** — `machineLearning.availabilityChecks`
   (`enabled`/`interval`/`timeout`, подтверждено в OpenAPI-схеме
   `MachineLearningAvailabilityChecksDto`) — это периодический пинг ML-URL,
   задуманный именно для того, чтобы не слать задания на мёртвый адрес.
2. 🔴 **Но есть открытая (на момент 2026-09-26 не подтверждена как
   исправленная) проблема апстрима** — [immich-app/immich#27617](https://github.com/immich-app/immich/issues/27617):
   на версии v2.6.2 недоступный внешний ML-URL приводил не к паузе очереди, а
   к разгону памяти `immich-server` до OOM-убийства контейнера за секунды.
   Затронута ли v2.7.5 (наша версия) — **не проверено**, issue открыт против
   более старой версии и не содержит подтверждения фикса.

**Практический вывод:** не полагаться только на `availabilityChecks`.
Выключая станцию надолго — явно откатывать `machineLearning` (§7), а не
оставлять `enabled=true` с адресом, который скоро станет недоступен.
Отдельно: упавшие из-за недоступности ML задания не подхватываются
автоматически бесконечно — по опыту сообщества (обсуждение
[immich-app/immich#17331](https://github.com/immich-app/immich/issues/17331))
после возвращения станции в строй нужно вручную нажать **«Missing»** в
Administration → Jobs для Smart Search и Face Detection, чтобы досчитать то,
что скопилось, пока станция была выключена.

## 7. Откат

1. На станции:
   ```powershell
   powershell -File scripts\workstation\immich_ml_station.ps1 -Command stop
   ```
   Гасит и туннель, и контейнер.
2. На Jetson — вернуть `machineLearning` ровно в состояние до пилота, из
   бэкапа, который `set_ml_url.sh set` сохранил перед правкой:
   ```bash
   ls -t /mnt/storage/backups/immich-system-config/*.json | head -1
   bash scripts/immich/set_ml_url.sh restore /mnt/storage/backups/immich-system-config/system-config.<TS>.json
   ```
3. Проверить, что откатилось именно то, что нужно:
   ```bash
   bash scripts/immich/set_ml_url.sh show
   ```

## 8. Проверки после (числа должны расти)

```bash
ssh admin@192.168.0.50 \
  'docker exec homecloud_immich_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
   -c "select count(*) from smart_search;" \
   -c "select count(*) from asset_face;"'
```

Базовая линия (замер 2026-09-26): **0 и 0** из 7646 ассетов (7014 фото + 609
видео + новые с 20.09). После прогона оба числа должны расти к общему числу
ассетов; не бенчмаркалось отдельно, обрабатываются ли видео тем же путём, что
фото, или только их превью-кадр (открытый вопрос, `D4` §7).

## 9. Приватность

- Порт ML-воркера на станции — **только `127.0.0.1`** (compose-файл, аудит
  CF-4). Наружу в LAN не виден.
- Виден он только через обратный SSH-туннель, который САМА станция поднимает
  до Jetson; на Jetson бинд — `172.17.0.1` (docker-мост, `GatewayPorts
  clientspecified`), не LAN и не WAN.
- Наружу (WAN) не публикуется ничего ни на одном шаге — ADR-0010 соблюдён.

## 10. Открытые вопросы

- Точное время индексации на реальной связке станция+туннель+наша библиотека
  — не измерено, только общая практика GPU-инференса (`D4` §7).
- Риск OOM `immich-server` при обрыве связи со станцией во время прогона
  (§6, issue #27617) — не проверено на v2.7.5 предметно.
- Обработка 609 видео отдельно от фото не бенчмаркалась.

## Источники

- Поле `machineLearning` в `GET`/`PUT /api/system-config`, схема
  `SystemConfigMachineLearningDto` (`enabled`, `urls`, `availabilityChecks`) —
  OpenAPI-спека Immich, тег `v2.7.5`:
  `https://raw.githubusercontent.com/immich-app/immich/v2.7.5/open-api/immich-openapi-specs.json`.
- Per-asset job `refresh-faces` (`AssetJobName`) и отсутствие per-asset job для
  смыслового поиска — та же спека, `paths./assets/jobs`, `paths./jobs/{name}`.
- Аутентификация `x-api-key` — та же спека, `components.securitySchemes`.
- GPU-конфигурация `deploy.resources.reservations.devices` (driver `nvidia`) —
  `https://docs.immich.app/features/ml-hardware-acceleration` (проверено 2026-09-26).
- Риск OOM при недоступном внешнем ML — `https://github.com/immich-app/immich/issues/27617`.
- Ручной retry упавших заданий — `https://github.com/immich-app/immich/issues/17331`.
