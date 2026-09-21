# Точка проекта 2026-09-21 — P0 снова открыт, две неверные формулы подряд, Cloud.ru открыт соседу

> Устройство: изменений нет, кроме удаления объектов в облаке. Контейнеры не трогались,
> VPN на VPS не трогался (правило №13), конфигурация Jetson не менялась.
> Все числа ниже — замеры 2026-09-21, не воспоминания.

---

## 1. Главное: off-site копия фотографий удалена

**Решение владельца**, принятое дважды: сначала на вопрос «удалять ли, зная цену»,
затем повторно — после того, как выяснилось, что причина удаления отпала.

| Что | Значение |
|---|---|
| Корзина | `nas-immich-offsite`, префикс `immich/` |
| Удалено | **462 объекта, 7.50 ГБ**, отказов 0 |
| Проверка после | повторная опись — **0 объектов** |
| Чем меряли | `ListObjectsV2` подписью SigV4 с самого Jetson, сумма `Size` |

**Следствие: P0 снова открыт.** Фотографии Immich (7098 ассетов) существуют
**в одном экземпляре, на USB-SSD Jetson**. Вторая копия на HDD 2 ТБ (задача W2)
в git готова, но **на устройство не выкачена** — это самый дешёвый способ закрыть дыру,
не трогая облако.

**Причина, названная при постановке задачи, не подтвердилась.** Владелец просил освободить
место под соседний проект. `work` ответил на доске (`m0137`), что Object Storage ему нужно
**ноль**: их сценарий — веса модели около 35 ГБ, то есть вдвое больше всех 15 ГБ бесплатного
тарифа, и они отказались от него сами. Общий дефицит у нас не в гигабайтах, а в деньгах:
организация **общая** (тот же `customerId`, тот же ключ владельца), на счету 99.97 ₽ и
4000 бонусов, и их разовая GPU-проба может их выесть. Это было сообщено владельцу **до**
повторного подтверждения — решение принято со знанием.

---

## 2. 🔴 Находка, которая дороже удаления: restic с устройства репозиторий не открывал

При попытке замерить репозиторий перед удалением:

```
Stat(<config/>) returned error, retrying after 5.4s: Stat: 400 Bad Request
... 17 повторов с нарастающей паузой ...
Fatal: unable to open config file: Stat: 400 Bad Request
```

При этом **на той же машине, тем же ключом** прямой S3 подписью SigV4 отработал без единого
отказа — опись, пакетное удаление, повторная опись. И `AWS_ACCESS_KEY_ID` в `config/.env`
устройства оказался **в правильной форме** `<tenant>:<keyId>` (36 + 32 симв.), то есть дело
не в ключе и не в префиксе `tenant_id`.

**Что это значит.** 2026-09-20 было записано: «восстановление проверено по-настоящему,
20 случайных снимков сверены по sha256, 20 из 20». Это правда — но проверка шла **не с Jetson**.
То есть «копия есть» и «копию может достать тот, кому придётся её доставать» оказались
**разными утверждениями**, и разошлись они молча.

**Причина 400 не установлена.** Регион, path-style, версия minio-go — всё гипотезы, ни одна
не проверена. Записано как неизвестное, а не как удобная версия.

**Правило на будущее:** восстановление проверять **с той машины, которая будет восстанавливать**,
а не с той, где удобнее отлаживать. Передано соседнему проекту (`m0140`) — они забрали себе.

---

## 3. 🔴 Биллинг Cloud.ru: одна выгрузка, три прочтения, верно третье

Самый поучительный эпизод дня. Ошибку нашёл сосед, через час отозвал **свою же** поправку,
и обе версии пришлось проверять здесь независимо.

| Как считали | Результат | Вердикт |
|---|---|---|
| сумма `cost` | 953.34 ₽ | сложение **ставок** — неверно |
| сумма `amount × cost` | 7.7222 ₽ | деньги на ставку второй раз — неверно, **успело уйти в `main` (`f92c71a`)** |
| **сумма `amount`** | **0.0263 ₽** (0.0321 с НДС) | верно |

За полтора месяца (01.08–21.09) на счету израсходовано **две с половиной копейки**.

### Семантика полей, доказанная замером — 13 строк из 13

| Поле | Что это | Проверка |
|---|---|---|
| `usefact` | количество в единице из `unit` (млн шт, ГБ, тыс. шт) | — |
| `cost` | **ставка** тарифа, рублей за единицу | — |
| `amount` | **начислено, рублей без НДС** | ровно `usefact × cost`, 13/13 |
| `amount_nds` | начислено с НДС | ровно `amount × 1.22`, 13/13 |

Решающий довод — **НДС**: он лежит на `amount`. На количество НДС не начисляют.

### Признак, который стоял перед глазами и не был использован

В собственной выгрузке: `amount / usefact` у токенов даёт ровно **466.67** — то есть ставку.
Значит `amount` уже произведение. Этого числа хватило бы, чтобы не выкатывать вторую неверную
версию. Родня уже записанному правилу проекта: **объяснение появилось раньше, чем была
проверена входная величина**.

### Что починено

- Деньги = сумма `amount`, ничего не умножается. Добавлено `cost_nds`.
- Убран откат `usefact` → `amount`: количество и деньги — разные величины.
- Тревога `total_cost > 0` больше не срабатывает от самого наличия тарифной строки
  (шесть строк Object Storage с `amount = 0` подняли бы её на пустом месте).
- `tests/unit/test_cloudru_cost_is_a_rate.py` — 12 проверок, включая проверку **самих данных**
  (`amount == usefact × cost` и `amount_nds == amount × 1.22`), чтобы изменение выгрузки
  ломало тест, а не подгонялось под код.
- В `test_cloudru_consumption_poll.py` исправлены фикстуры, которые клали в `amount` штуки
  и часы — такая выгрузка от Cloud.ru прийти не может.

Коммиты: `f92c71a` (неверный, отозван) → **`b215d07`** (верный).

---

## 4. 🟠 Открытый вопрос: что значит `usefact` для Object Storage

Равенство `amount = usefact × cost` проверено **только на токенах**. У хранилища `amount = 0`
(уложились в бесплатный тариф), и произведение не проверяет ничего — ноль умножается на что угодно.

Замер 2026-09-21: в день, когда в корзине реально лежало **7.5 ГБ**, биллинг показал
`usefact` **0.0656** (20.09) и **0.1250** (21.09) — **расхождение в 60 раз**.

Непроверенная гипотеза (в документацию не кладётся): похоже на долю месяца —
`7.5 ГБ × (0.75 суток / 30 суток) = 0.19`, что близко к сумме двух строк `0.1907`.
Но это подгонка под два числа, а не замер.

**Практическое следствие:** сопоставление `FREE_TIER_LIMITS` для Object Storage помечено
как **непроверенное**. Пока не выяснено, правило «остаток бесплатного тарифа вычитаем
по `usefact`» для хранилища даёт **ложное спокойствие**: половина лимита выглядит
как меньше процента. Указано соседним проектом (`m0142`), ответ — `m0143`.

---

## 5. Cloud.ru открыт соседнему проекту

По поручению владельца выложена карта без секретов:
`E:\agent_coordination\shared\nas\CLOUDRU_FULL_ACCESS_2026-09-21.md` (доска — `m0135`).

Содержит: где лежат три независимых секрета (IAM в Credential Manager `nas-cloudru-iam`;
FM-ключ в локальном keystore владельца; отдельный S3-ключ **не нужен** — годится IAM-ключ
с префиксом `tenant_id`), идентификаторы, проверенные рецепты API, ловушки (`503` = «не понял
запрос»; `id_token` содержит почту и телефон владельца), готовый код NAS и карту SSH
с жёсткими правилами по VPS.

**Ответ соседа (`m0137`):** организация общая, Object Storage они занимать не будут,
боевого опыта Evolution VM / ML Inference / Artifact Registry / Secret Management
у них **нет** — честное «нет» вместо вежливого «может быть».

---

## 6. Разбор Jev Model Router (запрос владельца)

Прочитаны исходники модов `davila7/claude-code-templates`.

**Устройство.** Хуки `prompt.submit`, `turn.step`, `agent.spawn`. Классификатор оценивает
**tier** (механика / обычная инженерия / трудное), **effort** (4 уровня) и **risky**
(бой, деньги, учётные данные, необратимое). Решающая модель **никогда не видит имени модели**.
Пороги несимметричны: усложнить при уверенности ≥0.3, упростить только при ≥0.6,
`risky > 0.7` перебивает оба. Мод скиллов возвращает `{text: null}` на `skill_listing`
и подставляет один подходящий скилл вместо полного перечня.

**Оценка для нас.**
1. Это автоматизация политики, которая у нас **уже написана прозой** в `CLAUDE.md`
   (раздел «Экономия токенов» и таблица оркестрации субагентов).
2. Измерение **`risky` ценнее экономии**: сегодня две неверные формулы подряд ушли в `main`.
   Автоматический флаг «задача про деньги и необратимое → максимальная модель» страхует
   ровно там, где оступились.
3. На тарифе **Claude Max** экономятся не рубли, а **лимит сессии** — заголовок
   «экономим токены» читается не буквально.

**Чего остерегаться.** `npx claude-code-templates@latest --mod ...` ставит чужой код,
видящий каждый промпт; в `.claude/settings*.json` этого семейства проектов лежат
**настоящие** секреты (токен GitHub, sudo-пароль соседа). С ключом наружу уезжает текст
промпта на `api.typesafe.ai` или Vercel Gateway. Без ключа оба мода падают на встроенный
классификатор и **наружу не ходят вовсе** (`provider: "builtin"`).

**Что можно реализовать (по приоритету).**
- **B. D5 smart routing для `@бобик`** — задача уже в плане и висит нерешённой. Классифицировать
  вопрос семьи и отправлять простые к локальной модели, трудные к GigaChat. Скопировать из
  чужого дизайна **несимметричные пороги** и **override по риску**. Живёт целиком в нашем
  шлюзе, ничего чужого не ставится, наружу не ходит. Экономит общий счёт с Belgorod.
- **A. Форк роутера на наш LLM Gateway** — мод открытый, бэкенд выбирается конфигом.
  У нас есть локальная `qwen3.5:4b` на станции через обратный туннель, редактирование,
  персональный учёт. Нужен небольшой адаптер: у нас `/v1/chat` своей формы.
- **C. Аналог skill-suggestion** — отложить: список скиллов приходит от харнесса, выигрыш меньше.

**Не проверено:** устойчивость и документированность самого API модов
(`prompt.submit` / `turn.step` / `agent.spawn`). Форк имеет смысл, только если точка
расширения не переедет.

---

## 7. Побочное наблюдение

**Аптайм Jetson — 2 д 16 ч** (замер 2026-09-21 06:55 UTC), то есть устройство перезагружалось
около **18.09**. В `CLAUDE.md` значится «аптайм с 2026-08-17». Расхождение реальное,
причина не выяснялась. Зафиксировано, не объяснено.

---

## 8. Следующие шаги

| Приоритет | Что | Почему |
|---|---|---|
| 🔴 | **W2 — вторая копия Immich на HDD 2 ТБ** | единственный дешёвый способ убрать «фото в одном экземпляре»; скрипт в git, окна не надо |
| 🔴 | **Причина `400` у restic** | пока не найдена, любая следующая off-site копия наследует ту же ловушку |
| 🟠 | **`usefact` для хранилища** | без этого учёт бесплатного тарифа по хранению — ложное спокойствие |
| 🟠 | **D5 smart routing (вариант B выше)** | решение владельца по плану; экономит общий счёт с Belgorod |
| 🟠 | Аптайм 18.09 — проверить или записать как неизвестное | правило: записывать неизвестное, а не удобную версию |

---

## 9. Что НЕ делалось

- Устройство не перенастраивалось, контейнеры не пересоздавались, `git pull` на Jetson не делался.
- VPN на VPS не трогался: `amnezia-*` не перезапускались, портов не добавлялось (правило №13).
- Временный скрипт `/tmp/s3_cloudru.py` с устройства удалён после работы.
- Секреты не печатались: авторизация выводила только длину токена и `expires_in`,
  поля `*_token` отфильтрованы (грабли 2026-09-20 про `id_token`).

---

## EN summary

**Off-site photo copy deleted (owner's decision, confirmed twice).** Bucket `nas-immich-offsite`,
prefix `immich/`: **462 objects, 7.50 GB** removed, zero failures, re-listing confirms **0 objects**.
Measured directly via `ListObjectsV2` (SigV4) from the Jetson itself. **P0 is open again** — the
7098 Immich assets now exist in a single copy on one USB SSD, and the HDD second copy (W2) is in
git but not deployed. The stated reason for freeing space did not hold: the neighbouring project
answered that it needs **zero** Object Storage; the shared shortage is money, not gigabytes
(shared organisation, 99.97 ₽ + 4000 bonus credits). The owner was told this **before** confirming.

**The more expensive finding:** `restic` never opened that repository **from the device** —
`Stat(<config/>): 400 Bad Request`, 17 retries, fatal — while plain SigV4 S3 from the same machine
with the same key worked flawlessly, and the access key was already in the correct
`<tenant>:<keyId>` form. So yesterday's "restore verified, 20 of 20 sha256 matches" was true but
performed **elsewhere**: "a copy exists" and "the machine that will need it can fetch it" turned
out to be different statements, and they diverged silently. Cause of the 400 is **unknown** and
recorded as unknown. Rule taken away: verify restores **from the machine that will restore**.

**Billing semantics, one dataset read three ways, only the third correct:** sum of `cost` =
953.34 ₽ (summing rates), sum of `amount × cost` = 7.7222 ₽ (money times rate — this version
shipped to `main`), sum of `amount` = **0.0263 ₽** (0.0321 with VAT) — correct. Proven on 13 of
13 rows: `usefact` is quantity, `cost` is the per-unit rate, `amount` is money already charged
(= `usefact × cost`), `amount_nds` = `amount × 1.22`. The decisive argument is VAT: it sits on
`amount`, and VAT is not charged on quantities. The clue was in our own dump — `amount / usefact`
for tokens is exactly 466.67, the rate — and it was not used. Fixed in `b215d07` with 12 tests
that check the data itself, not only the code.

**Still open:** for Object Storage the identity cannot be verified (`amount = 0` there), and on
the day 7.5 GB were stored billing reported `usefact` 0.0656 and 0.1250 — a 60× gap, unexplained.
Free-tier matching for storage is therefore marked **unverified**: half the allowance looks like
under one percent.

**Cloud.ru opened to the neighbouring project** — secret-free map in the shared folder, covering
where the three independent credentials live, verified API recipes, the platform's traps
(`503` means "request not understood"; the auth response carries the owner's e-mail and phone
inside `id_token`) and the hard VPS rules.

**Jev Model Router reviewed** (owner's request): hooks `prompt.submit` / `turn.step` /
`agent.spawn`, classifying tier, effort and risk with asymmetric confidence thresholds — cheaper
choices require higher confidence than expensive ones. It automates the model-routing policy this
project already states in prose. Its `risky` dimension matters more to us than token savings, and
on a Max plan the gain is fewer limit cutoffs rather than roubles. Installing the third-party mod
blind is the wrong move here — the settings files in this project family hold real secrets — but
the code is open, and the same design can run against our own gateway and local model. Recommended
first step is the gateway-side variant (task D5), which leaves nothing to a third party.
