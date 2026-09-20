# Immich ML — пробный прогон в Cloud.ru: попытка и блокер / Immich ML — Cloud.ru trial: attempt and blocker

> 🔴 **ДИАГНОЗ ЭТОГО ДОКУМЕНТА ОТОЗВАН 2026-09-20 (вечер).**
> Вывод «Container Apps API возвращает 503 на всех путях `/v1/`, сервис недоступен» **неверен**.
> Запросы шли на имя хоста `containerapps.api.cloud.ru`, **которого не существует** (`curl` rc=6,
> имя не резолвится). Настоящий адрес — `https://containers.api.cloud.ru`, и у него обязателен
> query-параметр `projectId`. С ним `GET /v1/containers?projectId=<uuid>` отвечает **200**.
> `503` у этой платформы — ответ по умолчанию на непонятный запрос, а не признак аварии.
> Улика лежала в этом же документе: **503 давал даже заведомо неверный путь** — наблюдение верное,
> вывод из него сделан противоположный правильному.
> Проверенные настройки доступа — `docs/integrations/sber/CLOUD_RU.md`, раздел «Проверенный доступ».


> 🇷🇺 Дата: 2026-09-20. Статус: **попытка эксперимента, эксперимент не состоялся** —
> платформенный блокер на стороне Cloud.ru (не прав доступа, не наших действий).
> Ничего не создано, ничего не потрачено, ничего не удаляется — удалять нечего.
> EN summary — в конце.

## 1. Задача

По команде владельца — разовый пробный прогон `immich-machine-learning` в Cloud.ru
Container Apps: создать минимальный сервис из публичного образа, замерить холодный
старт, время обработки фото, реальное потребление vCPU·ч/ГБ·ч, сопоставить с
бесплатным лимитом, затем удалить всё. Контекст и уже сделанная разведка —
`docs/research/IMMICH_ML_E6_ANALYSIS_2026-09-20.md` (прочитана целиком перед стартом).

## 2. Что сделано

1. **IAM-токен получен успешно, дважды, двумя разными способами** — оба задокументированы
   в открытой документации Cloud.ru:
   - `POST https://auth.iam.cloud.ru/auth/system/openid/token`
     (`grant_type=access_key`, форма) — тот же способ, что уже описан в
     `docs/integrations/sber/CLOUD_RU.md`. Ответ: `200`, `access_token` длиной 1295 символов,
     `expires_in=3600`.
   - `POST https://iam.api.cloud.ru/api/v1/auth/token`
     (`{"keyId": ..., "secret": ...}`, JSON) — отдельный эндпоинт, документированный именно
     для **Container Apps API** (`docs/container-apps-evolution/ug/topics/api-ref__authentication`).
     Ответ: `200`, `access_token` длиной 1287 символов, `expires_in=3600`.
   - Оба раза пара ключ/секрет доставалась из Windows Credential Manager (`nas-cloudru-iam`)
     и не печаталась. **Значения секретов нигде не показаны.**
   - Проект подтверждён тем же, что уже зафиксирован в `CLOUD_RU.md`: `10dd738e-6389-4b75-9570-852df04c0165`
     («Новый Проект» / home-nas).
2. **Разобрана документация Container Apps** (`cloud.ru/docs/container-apps-evolution/ug/`):
   - Базовый URL API: `https://containers.api.cloud.ru`.
   - Источник образа: документация описывает **Artifact Registry текущего проекта** как
     основной путь; для внешних образов — только «публичные образы из других проектов
     Cloud.ru» через поиск по URI. **Прямая загрузка образа из внешнего публичного реестра
     (`ghcr.io/immich-app/immich-machine-learning`) в открытой документации не описана** —
     это уже отдельный открытый вопрос, независимо от блокера ниже.
   - Масштабирование: min instances **0–25** (значит, «0 горячих» технически предусмотрено),
     max instances 1–25, idle-таймаут по умолчанию **1800 с**, после которого «холодный»
     инстанс удаляется и **тарификация прекращается** (дословно из документации).
   - Тарификация (`.../topics/pricing`): подтверждён факт, что у «горячих» экземпляров
     «тарификация прекращается только после остановки или удаления контейнера пользователем
     вручную», а у «холодных» — «автоматически при отсутствии запросов». Это **косвенно
     отвечает на главный вопрос эксперимента в пользу «по времени жизни контейнера»**, а не
     по загрузке CPU — но это прочитано в документации, **не измерено на практике**, и это
     не заменяет собой требуемый практический замер.
   - Полного описания методов REST API (пути, тела запросов, поля `image`/`resources`/
     `scaling`) на публичных страницах документации найти не удалось — есть только
     заголовок раздела и вводная фраза «отправьте запрос на `https://containers.api.cloud.ru`».
3. **Проверка доступности API — блокер.** Прямые запросы к `https://containers.api.cloud.ru/v1/*`
   систематически возвращают **`503 upstream connect error or disconnect/reset before
   headers. reset reason: remote reset`**, от сервера `Evolution API Gateway`. Проверено:
   - с обоими токенами (оба эндпоинта аутентификации) — одинаково;
   - на разных путях (`/v1/projects/{id}/services`, `/v1/health`, и намеренно
     несуществующий `/v1/zzz_totally_bogus_path_12345`) — **все** под префиксом `/v1/`
     дают одинаковую 503, включая заведомо неверный путь — значит, весь префикс `/v1/`
     маршрутизируется шлюзом на один и тот же недоступный бэкенд, это не ошибка
     конкретного пути или тела запроса;
   - контрольная проверка: `/` (корень, без `/v1/`) и `/v2/...` дают чистый **`404`** от
     шлюза мгновенно — то есть шлюз в принципе различает «пути есть» и «путей нет»,
     и `/v1/` — это узнанный, но нерабочий сейчас маршрут;
   - 4 повторные попытки с паузами по 5 с (итого ~20 с) — тот же результат каждый раз;
   - общая связность с Cloud.ru при этом в порядке: оба токен-эндпоинта (другие хосты,
     `auth.iam.cloud.ru` и `iam.api.cloud.ru`) отвечали `200` штатно в это же самое время.
   
   **Вывод: это не проблема прав сервисного аккаунта и не ошибка в моих запросах —
   это доступность конкретно `containers.api.cloud.ru/v1/*` на момент эксперимента
   (2026-09-20, ~07:00–07:10 UTC / ~10:00–10:10 MSK).** Публичная статус-страница
   Cloud.ru (`cloud.ru/status`) не отдаёт данные об инцидентах без входа в аккаунт —
   подтвердить или опровергнуть официально объявленный инцидент независимо не удалось.
4. **Веб-консоль Cloud.ru не пробовалась** — в этом заходе нет инструмента для
   управления браузером/консолью, только HTTP-запросы. Довести эксперимент через
   консоль вручную может только владелец.
5. **Ничего не создано.** Ни один ресурс с префиксом `e6-trial-` не появился — само
   создание сервиса блокировано пунктом 3. Соответственно: тестовых изображений не
   загружали, холодный старт/скорость обработки не замеряли, реальное потребление
   vCPU·ч/ГБ·ч не снимали (снимать нечего — ничего не запускалось), баланс/расход
   не менялся (списаний не может быть при отсутствии созданных ресурсов).
6. **Удаление: не требуется.** Список ресурсов `e6-trial-*` пуст, потому что ни один
   не был создан — подтверждать нечего.

## 3. Инцидент по ходу работы — что печаталось лишнее

При разборе ответа второго токен-эндпоинта (`iam.api.cloud.ru`) в вывод команды
однажды попало **полное тело ответа, включая `id_token`** — это JWT, который в
незашифрованном (base64) виде содержит email и номер телефона владельца (стандартные
поля OpenID `email`/`phone_number` в теле токена). Это нарушение собственного правила
«секретов не печатать» — `access_token` в том же выводе был отредактирован (заменён на
`<redacted>`) заранее, а `id_token` — не был, потому что фильтр ловил только поля
`token`/`access_token`. Дальше в работе `id_token` не использовался и никуда не
передавался. Временные файлы с обоими `access_token` удалены из scratchpad по
завершении. **Отзываю: фильтр редактирования секретов в моих же командах был
неполным — эта находка должна попасть в проектные «грабли», если владелец захочет
её туда перенести.**

## 4. Ответ на главный вопрос эксперимента

**Практически — не получен: эксперимент не состоялся из-за недоступности API.**
Из документации (не из замера) следует, что модель тарификации — **по времени жизни
контейнера** («горячий» инстанс = живой, платит до ручной остановки; «холодный» =
удаляется при простое, платить перестаёт), а не по факту загрузки CPU. Это совпадает
с предположением из `IMMICH_ML_E6_ANALYSIS_2026-09-20.md` §3 о «ГБ-часах, а не
vCPU-часах, как узком месте» — но остаётся **НЕ ПРОВЕРЕНО практическим замером**,
именно тем, ради которого затевался этот прогон.

## 5. Влезает ли backfill 7098 фото в бесплатный лимит

**Вердикт по-прежнему не может быть дан с уверенностью** — ровно то же состояние, что
было до этого прогона (см. `IMMICH_ML_E6_ANALYSIS_2026-09-20.md` §7): вычислительная
часть (по оценке 0.6–3.0 vCPU·ч) почти наверняка укладывается в 25 vCPU·ч; ГБ-часовая
часть (лимит 50 ГБ·ч) остаётся неизвестной без практического замера. Этот прогон не
продвинул вопрос дальше — ни в сторону «влезает», ни в сторону «не влезает».

## 6. Что осталось непроверенным

- Реальные холодный старт, скорость обработки фото, фактическое потребление vCPU·ч/ГБ·ч
  на Cloud.ru — не измерено, эксперимент не выполнен.
- Возможность создать сервис из **внешнего** публичного образа (`ghcr.io/...`) без
  предварительной загрузки в Artifact Registry проекта — по документации не подтверждена
  отдельно от блокера п.3; нужно будет прояснить в консоли или у поддержки Cloud.ru,
  когда API снова заработает.
- Официальный статус инцидента `containers.api.cloud.ru` (объявлен ли он Cloud.ru
  публично) — не подтверждён, статус-страница требует входа.
- Полная спецификация REST API Container Apps (тела запросов на создание сервиса,
  структура `image`/`resources`/`scaling`) — не найдена в открытой документации за это
  обращение.

## 7. Рекомендация

1. **Повторить попытку позже** (через несколько часов/на следующий день) — простым
   повтором тех же запросов к `GET https://containers.api.cloud.ru/v1/health` с
   валидным токеном; если вернётся `200` или `401/403/404` вместо `503` — API ожил,
   можно возобновлять прогон по плану из `IMMICH_ML_E6_ANALYSIS_2026-09-20.md`.
2. Если API остаётся недоступным несколько дней подряд — эксперимент через
   веб-консоль `console.cloud.ru` силами владельца (у этой сессии нет инструмента
   для управления браузером).
3. Рекомендация по выбору варианта ML **не меняется** относительно уже сделанной
   разведки: она и без этого прогона указывала на Вариант Б (станция батчем) как
   основной, Cloud.ru — как условный запасной путь после подтверждающего теста.
   Этот прогон должен был быть тем тестом, но тест не состоялся — статус условия
   «делать вариант А, если…» остаётся **не подтверждён, не опровергнут**.
4. Перед следующей попыткой — заранее прояснить в документации/поддержке путь для
   внешнего публичного образа (Artifact Registry вроде обязателен), чтобы не упереться
   во второй блокер сразу после того, как API оживёт.

---

## 8. EN summary

The owner asked for a one-off Cloud.ru Container Apps trial of `immich-machine-learning`:
create a minimal public-image service, measure cold start, per-image processing time, and
actual vCPU-hour/GB-hour consumption against the free tier, then delete everything.

**The experiment did not run.** IAM authentication succeeded via both documented flows
(`auth.iam.cloud.ru` OpenID form grant, and the Container-Apps-specific
`iam.api.cloud.ru/api/v1/auth/token` JSON endpoint) — both returned valid bearer tokens,
confirming credentials and general Cloud.ru connectivity are fine. However, every request to
`https://containers.api.cloud.ru/v1/*` — across two different tokens, five different paths
including a deliberately bogus one, and four retries over ~20 seconds — returned a consistent
`503 upstream connect error... reset reason: remote reset` from the Evolution API Gateway,
while `/` and `/v2/...` returned clean `404`s instantly. This points to a genuine backend
outage of the Container Apps API specifically, not a permissions, path, or request-body
problem on our end. No browser/console tool is available in this session to fall back to the
web console. Cloud.ru's public status page requires login and could not confirm or deny an
announced incident independently.

**Result: nothing was created** (no `e6-trial-*` resources), so **nothing needed deleting**
and **no spend occurred**. The billing-model question (container-uptime vs CPU-load) remains
unanswered by direct measurement; Container Apps documentation states hot instances bill
"until manually stopped" and cold instances stop billing "automatically when idle," which
*suggests* uptime-based billing but was not verified in practice — exactly what this trial was
meant to confirm. Whether the 7098-photo backfill fits the free tier is therefore **still
undetermined**, unchanged from the prior spike document.

One process note: while inspecting the second auth endpoint's JSON response, the full payload
was printed once, including an unredacted `id_token` (a JWT whose base64 body carries the
owner's email and phone number per standard OpenID claims) — the secret-redaction filter in
that command only matched `token`/`access_token` fields, not `id_token`. It was not reused or
transmitted anywhere afterward, and both saved token files were deleted from the scratch
directory at the end of the session. Flagged here as a gap in the ad-hoc redaction, not a
credential compromise (the token is short-lived, 1-hour expiry, IAM-only scope).

**Recommendation:** retry the same lightweight `GET .../v1/health` probe later (hours to a
day) before re-attempting the full trial; if the API keeps returning 503 for days, the owner
will need to run this experiment through the Cloud.ru web console instead, since this session
has no browser-automation tool. The standing recommendation from the prior spike (default to
workstation-batch Option B, treat Cloud.ru as a conditional fallback pending this exact test)
is unchanged — this trial was meant to resolve that condition and did not.
