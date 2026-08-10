# 08. LLM Gateway / DeepSeek

## 1. Назначение / Purpose

🇷🇺 LLM Gateway — отдельный сервис, который изолирует домашнее облако от прямой интеграции с DeepSeek API.
🇬🇧 LLM Gateway is a dedicated service that isolates the home cloud from direct DeepSeek API integration.

## 2. Почему шлюз обязателен / Why the gateway is mandatory

🇷🇺 Без шлюза каждый сервис начнёт самостоятельно обращаться к LLM, что создаёт риски:
🇬🇧 Without the gateway each service would call the LLM independently, creating risks:

- 🇷🇺 утечка персональных данных / 🇬🇧 personal data leak
- 🇷🇺 отсутствие лимитов расходов / 🇬🇧 no spending limits
- 🇷🇺 неуправляемые промты / 🇬🇧 uncontrolled prompts
- 🇷🇺 сложность смены провайдера / 🇬🇧 hard to switch providers
- 🇷🇺 невозможность аудита / 🇬🇧 no audit trail

## 3. Провайдеры / Providers

🇷🇺 Шлюз поддерживает **двух** провайдеров. Ключевой инвариант: оба ходят через
**одно и то же** редактирование и **один и тот же** бюджет. Добавление провайдера
не должно открывать вторую, неохраняемую дверь — ради этого шлюз и существует.

🇬🇧 Two providers, one door: both go through the same redaction and the same budget.

| Провайдер | Значение `LLM_PROVIDER` | Транспорт | Статус |
|---|---|---|---|
| **DeepSeek** | `deepseek` | OpenAI-совместимый SDK | ✅ проверен вживую |
| **GigaChat (Сбер)** | `gigachat` | OAuth + REST, OpenAI-совместимый формат | ✅ проверен вживую 2026-08-10 |

Провайдера можно выбрать **на конкретный запрос** полем `provider` в `POST /v1/chat` —
удобно для честного сравнения ответов на одной задаче.

### 3а. GigaChat — как устроено подключение

🇷🇺 Схема авторизации отличается от DeepSeek: не постоянный ключ, а обмен
Authorization key на **временный токен**.

1. `POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
   с заголовками `Authorization: Basic <base64(client_id:client_secret)>`,
   `RqUID: <uuid4>` и телом `scope=GIGACHAT_API_PERS`.
2. Ответ содержит `access_token`, **живущий 30 минут**. Шлюз кэширует его и
   обновляет сам за минуту до истечения — вызывающей стороне об этом знать не нужно.
3. `POST https://gigachat.devices.sberbank.ru/api/v1/chat/completions`
   с `Authorization: Bearer <token>`, тело в OpenAI-совместимом формате.

### 3б. 🔴 Грабля TLS, на которой спотыкаются все

🇷🇺 Эндпоинты Сбера подписаны **НУЦ Минцифры**, которого нет в стандартном
хранилище доверия Python/Debian. Первый же запрос падает так:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
self-signed certificate in certificate chain
```

Массовый совет в интернете — `verify=False`. **Так делать не надо:** это снимает
проверку подлинности сервера целиком, а мы через этот канал отправляем семейные данные.

**Правильное решение:** положить корневой и промежуточный сертификаты и указать бандл.
Сделано в `config/certs/` (см. README там же), путь передаётся переменной
`GIGACHAT_CA_BUNDLE`. Проверено 2026-08-10: с бандлом OAuth и `chat/completions`
проходят **с включённой проверкой TLS**.

`GIGACHAT_VERIFY_SSL=false` оставлен только как аварийный путь для диагностики —
чтобы отличить «неверные ключи» от «нет сертификата».

## 4. Модели / Models

🇷🇺 GigaChat / 🇬🇧 GigaChat:

```env
LLM_PROVIDER=gigachat
GIGACHAT_AUTH_KEY=<base64(client_id:client_secret)>
GIGACHAT_SCOPE=GIGACHAT_API_PERS      # физлица; для организаций — _B2B / _CORP
GIGACHAT_MODEL=GigaChat               # также GigaChat-Pro, GigaChat-Max
GIGACHAT_CA_BUNDLE=/certs/russian_trusted_bundle.pem
```

## 4. Модели / Models

🇷🇺 Текущая конфигурация / 🇬🇧 Current configuration:

```env
LLM_PROVIDER=deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_REASONER_MODEL=deepseek-reasoner
```

🇷🇺 `deepseek-chat` / `deepseek-reasoner` — рабочие имена DeepSeek API (подтверждено живым вызовом 2026-05-31). Имена `deepseek-v4-flash` / `deepseek-v4-pro` зарезервированы на будущее и сейчас API не принимаются.
🇬🇧 `deepseek-chat` / `deepseek-reasoner` are the live DeepSeek API names (confirmed by live call 2026-05-31). Names `deepseek-v4-flash` / `deepseek-v4-pro` are reserved for the future and are not accepted by the API now.

## 5. Разрешённые сценарии Stage 1 / Allowed Stage 1 scenarios

| Сценарий / Scenario | Разрешено / Allowed |
|---|---:|
| Анализ обезличенных логов / Analyze anonymized logs | Да / Yes |
| Объяснение ошибок Docker / Explain Docker errors | Да / Yes |
| Формирование runbook / Generate runbook | Да / Yes |
| Помощь с командами диагностики / Help with diagnostic commands | Да / Yes |
| Работа с проектной документацией / Project documentation | Да / Yes |
| Анализ личных фото/видео / Analyze personal photos/videos | Нет / No |
| Анализ контактов и календаря / Analyze contacts & calendar | Нет / No |
| Анализ личных документов / Analyze personal documents | Нет / No |
| Передача backup-архивов / Send backup archives | Нет / No |

## 6. API шлюза / Gateway API

```http
GET  /health          # + сколько имён загружено в фильтр
GET  /v1/usage        # сколько потрачено сегодня и за месяц
POST /v1/redact       # показать, что фильтр сделает с текстом (без вызова провайдера)
POST /v1/chat
POST /v1/diagnostics/explain
```

🇷🇺 Пример запроса / 🇬🇧 Example request:

```json
{
  "task": "explain_docker_error",
  "context": "service immich-server restarted 3 times, no personal data",
  "mode": "safe"
}
```

🇷🇺 `mode: "raw"` отвергается с 400 — обойти редактирование через API нельзя.

## 6а. Бюджет / Budget — ЭНФОРСИТСЯ

🇷🇺 До 2026-08-10 переменные лимитов были в `.env.example` и в этом документе,
но **код их не читал** — потолка не существовало ни на токены, ни на деньги.
Исправлено: проверка идёт **до** исходящего вызова (fail-closed), при превышении
шлюз отвечает `429`.

🇬🇧 Until 2026-08-10 the limit variables were documented but **never read by the
code** — there was no cap at all. Now enforced fail-closed before the call.

| Переменная | Смысл |
|---|---|
| `LLM_DAILY_TOKEN_LIMIT` | суточный потолок токенов; `0` = без лимита |
| `LLM_MONTHLY_COST_LIMIT_USD` | месячный потолок оценочной стоимости |
| `LLM_PRICE_USD_PER_MTOKEN` | цена для оценки; вынесена в конфиг, потому что меняется |
| `LLM_USAGE_FILE` | файл счётчиков; том `llm_usage` переживает рестарт |

Счётчики видны в `GET /v1/usage`. Суточный и месячный периоды перекатываются сами.

## 7. Privacy-фильтр / Privacy filter

🇷🇺 **Что фильтр делает на самом деле** (сверено с кодом 2026-08-10, а не с намерением):
🇬🇧 **What the filter actually does** (verified against code, not intent):

| Категория | Статус | Как реализовано |
|---|---|---|
| e-mail | ✅ | регулярное выражение |
| 🇷🇺 телефоны / phones | ✅ | регулярное выражение |
| 🇷🇺 токены, ключи, пароли / tokens, keys, passwords | ✅ | `api_key=`, `token=`, `secret=`, `password=`, `bearer` |
| 🇷🇺 приватные ключи / private keys | ✅ | блок `-----BEGIN … PRIVATE KEY-----` |
| 🇷🇺 упоминания в чате / chat mentions | ✅ | `@username`, `@"Display Name"` |
| 🇷🇺 домашние пути / home paths | ✅ | `/home/<user>`, `/Users/<user>` |
| 🇷🇺 персональные имена / personal names | ⚠️ **список слов** | `LLM_REDACT_NAMES`, склонения выводятся автоматически |
| 🇷🇺 точные адреса / exact addresses | ❌ **не реализовано** | улицы и дома не распознаются |

### ⚠️ Главное ограничение фильтра имён — проверено тестом

🇷🇺 Это **список слов, а не модель распознавания сущностей**. Склонения строятся
автоматически от основы (`Ольга` → `Ольге`, `Ольгой`, `Ольгу`), но
**уменьшительные имена — это другая основа и автоматически НЕ выводятся.**

Проверено прогоном, а не предположением:

```
IN : Оля спросила: что подарить Ульяне на день рождения?
OUT: Оля спросила: что подарить [REDACTED_NAME] на день рождения?   ← «Оля» прошла!

IN : Ольгой куплен билет, Алексея не будет
OUT: [REDACTED_NAME] куплен билет, [REDACTED_NAME] не будет          ← склонения ловятся
```

🇷🇺 В русском семейном чате говорят именно уменьшительными. Поэтому в
`LLM_REDACT_NAMES` нужно перечислять **все формы**: `Ольга Оля Ульяна Уля Иван
Ваня Алексей Лёша`. Иначе фильтр создаёт ложное чувство защиты.

🇬🇧 Diminutives are a different stem and are NOT derived automatically — list
every form your family actually uses, or the filter gives false confidence.

**Проверить, что фильтр видит именно ваши имена:** `POST /v1/redact` покажет
результат без обращения к провайдеру, и `GET /health` вернёт `names_configured`.

## 8. Логирование / Logging

🇷🇺 По умолчанию / 🇬🇧 By default:

```env
LLM_LOG_PROMPTS=false
LLM_LOG_RESPONSES=false
LLM_REDACT_PERSONAL_DATA=true
```

🇷🇺 Логировать можно только метаданные:
🇬🇧 Only metadata may be logged:

- 🇷🇺 время запроса / 🇬🇧 request timestamp
- 🇷🇺 тип задачи / 🇬🇧 task type
- 🇷🇺 модель / 🇬🇧 model
- 🇷🇺 оценка токенов / 🇬🇧 token estimate
- 🇷🇺 статус ответа / 🇬🇧 response status
- 🇷🇺 ошибка при наличии / 🇬🇧 error if any
