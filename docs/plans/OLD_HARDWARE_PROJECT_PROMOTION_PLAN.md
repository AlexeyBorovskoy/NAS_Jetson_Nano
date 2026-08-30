# План продвижения проекта: «Оживим старое железо» / Project promotion plan: "Let's revive old hardware"

**Проект / Project:** Home Cloud for Old Hardware  
**Рабочая идея / Working idea:** превращение старого оборудования в домашнее семейное облако / turning old equipment into a home family cloud  
**Базовый стек / Base stack:** Nextcloud, Immich, Samba/SFTP, Docker Compose, restic, DeepSeek API Gateway  
**Первичная платформа / Primary platform:** NVIDIA Jetson Nano + USB HDD с отдельным питанием / NVIDIA Jetson Nano + a self-powered USB HDD  
**Расширяемые платформы / Extended platforms:** Raspberry Pi 4/5, Orange Pi, mini-PC, старые ноутбуки, x86-серверы / Raspberry Pi 4/5, Orange Pi, mini-PCs, old laptops, x86 servers  
**Цель документа / Purpose of this document:** сформировать технологию публичного запуска, упаковки и продвижения проекта на GitHub и внешних площадках. / to define the approach to the public launch, packaging and promotion of the project on GitHub and on external platforms.

---

## 1. Позиционирование проекта / Project positioning

🇷🇺 Главная идея проекта: / 🇬🇧 The project's core idea:

```text
Старое железо не на свалку, а в домашнюю инфраструктуру.
Old hardware belongs in home infrastructure, not in the landfill.
```

🇷🇺 Рабочее международное позиционирование: / 🇬🇧 The working international positioning:

```text
Home Cloud for Old Hardware —
a blueprint for turning old SBCs, mini-PCs, laptops and USB HDDs into a private family cloud.
```

🇷🇺 Рабочее русскоязычное позиционирование: / 🇬🇧 The working Russian-language positioning:

```text
Оживим старое железо:
домашнее облако и фотоархив без Google, Xiaomi Cloud и ежемесячных подписок.
```

🇷🇺 Проект не должен позиционироваться как «ещё один docker-compose для Nextcloud». Основная ценность — воспроизводимая инженерная методика: от аппаратного аудита старого устройства до семейного облака, backup/restore и будущей Android-синхронизации.

🇬🇧 The project must not be positioned as "yet another docker-compose for Nextcloud". Its main value is a reproducible engineering method: from a hardware audit of an old device all the way to a family cloud, backup/restore and future Android synchronisation.

---

## 2. Продуктовая формула / The product formula

### 2.1. Английская формула / The English formula

```text
Home Cloud for Old Hardware is an engineering blueprint for turning unused devices into a private family cloud with files, photos, contacts, calendars, Android sync, backup/restore procedures and privacy-controlled LLM diagnostics.
```

### 2.2. Русская формула / The Russian formula

```text
Home Cloud for Old Hardware — инженерный шаблон для превращения старых устройств в частное семейное облако с файлами, фотоархивом, контактами, календарями, Android-синхронизацией, резервным копированием и безопасной LLM-диагностикой.
```

---

## 3. Что должно быть в публичном GitHub / What the public GitHub repository must contain

🇷🇺 Репозиторий должен выглядеть как инженерный blueprint, а не как личный экспериментальный каталог.

🇬🇧 The repository must look like an engineering blueprint, not like a personal experimental scratch directory.

### 3.1. Минимальная структура публичного проекта / The minimal structure of the public project

```text
home-cloud-old-hardware/
├── README.md
├── QUICK_START.md
├── HARDWARE_COMPATIBILITY.md
├── ARCHITECTURE.md
├── SECURITY.md
├── PRIVACY.md
├── BACKUP_RESTORE.md
├── OLD_HARDWARE_GUIDE.md
├── ANDROID_STAGE2.md
├── LLM_GATEWAY.md
├── docs/
├── docker/
├── scripts/
├── examples/
├── docs/prompts/
└── LICENSE
```

### 3.2. Назначение ключевых документов / The purpose of the key documents

| Документ / Document | Назначение / Purpose |
|---|---|
| `README.md` | Кратко объясняет идею, пользу и сценарии применения / Briefly explains the idea, the benefits and the use cases |
| `QUICK_START.md` | Пошаговый запуск за 30–60 минут / A step-by-step launch in 30–60 minutes |
| `OLD_HARDWARE_GUIDE.md` | Как выбрать и проверить старое железо / How to choose and test old hardware |
| `HARDWARE_COMPATIBILITY.md` | Таблица совместимости Jetson Nano, Raspberry Pi, mini-PC, ноутбуков / A compatibility table for the Jetson Nano, Raspberry Pi, mini-PCs and laptops |
| `ARCHITECTURE.md` | Целевая архитектура и связи сервисов / The target architecture and the links between services |
| `SECURITY.md` | Безопасность, VPN, доступы, hardening / Security, VPN, access, hardening |
| `PRIVACY.md` | Что хранится локально, что нельзя отправлять во внешний API / What is stored locally, what must never be sent to an external API |
| `BACKUP_RESTORE.md` | Стратегия резервного копирования и восстановления / The backup and restore strategy |
| `ANDROID_STAGE2.md` | Архитектура будущего Android-клиента / The architecture of the future Android client |
| `LLM_GATEWAY.md` | DeepSeek Gateway, privacy-фильтр, режимы диагностики / The DeepSeek Gateway, the privacy filter, the diagnostic modes |
| `docs/references/` | Ссылки на внешнюю документацию / Links to external documentation |
| `scripts/` | Диагностика, backup, обслуживание / Diagnostics, backup, maintenance |
| `docs/prompts/` | Промты для Codex/агентов / Prompts for Codex/agents |

---

## 4. Главный тезис для README / The main thesis for the README

🇷🇺 README должен начинаться не с Docker и не с контейнеров, а с проблемы пользователя.

🇬🇧 The README must open with the user's problem, not with Docker and not with containers.

### 4.1. Английский вариант / The English version

```markdown
# Home Cloud for Old Hardware

This project helps turn old hardware into a private family cloud.

Target use cases:
- reuse old Jetson Nano, Raspberry Pi, mini-PC or laptop;
- store family photos and videos locally;
- replace part of Google Drive / Xiaomi Cloud / Google Photos workflow;
- sync Android photos, contacts and calendars;
- keep data under personal control;
- use external LLM API only for diagnostics, not for private media.

Initial target hardware:
- NVIDIA Jetson Nano;
- USB HDD with external power;
- home router;
- Android phones.
```

### 4.2. Русский вариант / The Russian version

```markdown
# Оживим старое железо

Проект предназначен для превращения старого оборудования в домашнее семейное облако.

Цель:
- не выбрасывать старое железо;
- поднять домашний NAS;
- хранить фото и видео семьи локально;
- синхронизировать Android-телефоны;
- использовать Nextcloud для файлов, контактов и календарей;
- использовать Immich для фотоархива;
- подключать DeepSeek API только для технической диагностики.
```

---

## 5. Уникальность проекта / What makes the project unique

🇷🇺 Отдельные компоненты уже существуют: Nextcloud, Immich, Samba, restic, DAVx5, Syncthing, OpenMediaVault. Уникальность проекта не в создании нового файлового сервера, а в сборке, методике и фокусе на старом железе.

🇬🇧 The individual components already exist: Nextcloud, Immich, Samba, restic, DAVx5, Syncthing, OpenMediaVault. The project's uniqueness is not in building a new file server, but in the assembly, the method and the focus on old hardware.

| Обычные проекты / Ordinary projects | Данный проект / This project |
|---|---|
| Просто docker-compose для Nextcloud / Just a docker-compose for Nextcloud | Полный путь от старого железа до семейного облака / The complete path from old hardware to a family cloud |
| Только фотоархив / A photo archive only | Фото + файлы + контакты + календарь + backup / Photos + files + contacts + calendar + backup |
| Только NAS / A NAS only | NAS + Android-сценарии + будущий restore client / A NAS + Android scenarios + a future restore client |
| Без методики / No method | Пошаговый инженерный runbook / A step-by-step engineering runbook |
| Для серверов / For servers | Для Jetson Nano, Raspberry Pi, mini-PC, старых ноутбуков / For the Jetson Nano, Raspberry Pi, mini-PCs and old laptops |
| Без AI / No AI | LLM Gateway для диагностики без отправки личных данных / An LLM Gateway for diagnostics without sending personal data |

🇷🇺 Ключевая формула: / 🇬🇧 The key formula:

```text
Не новый сервис, а воспроизводимая технология оживления старого железа.
Not a new service, but a reproducible technique for reviving old hardware.
```

---

## 6. Целевая аудитория / Target audience

| Аудитория / Audience | Что им важно / What matters to them |
|---|---|
| Домашние пользователи / Home users | Сохранить фото, документы, контакты / Preserving photos, documents and contacts |
| Владельцы старых SBC / Owners of old SBCs | Применить Jetson/Raspberry/Orange Pi / Putting a Jetson/Raspberry/Orange Pi to use |
| Linux-энтузиасты / Linux enthusiasts | Self-hosted, Docker, NAS |
| Android-пользователи / Android users | Альтернатива Google/Xiaomi Cloud / An alternative to Google/Xiaomi Cloud |
| Семьи / Families | Семейный архив и восстановление телефонов / A family archive and phone restoration |
| Разработчики / Developers | Архитектура, Codex-ready проект, будущий Android-клиент / The architecture, a Codex-ready project, the future Android client |
| Privacy-сообщество / The privacy community | Контроль данных, VPN, LLM privacy policy / Data control, VPN, an LLM privacy policy |
| Homelab-сообщество / The homelab community | Практический домашний сервер из имеющегося железа / A practical home server from hardware they already own |
| Экологические инициативы / Environmental initiatives | Повторное использование электроники / Reusing electronics |

---

## 7. Название проекта / The project name

### 7.1. Варианты названия / Naming options

| Название / Name | Оценка / Assessment |
|---|---|
| `home-cloud-old-hardware` | Максимально ясно / As clear as it gets |
| `revive-home-cloud` | Хорошее международное / Good internationally |
| `old-hardware-cloud` | Понятное / Understandable |
| `family-cloud-sbc` | Техническое / Technical |
| `jetson-family-cloud` | Слишком узко / Too narrow |
| `revivebox` | Брендовое / Brand-like |
| `oldbox-cloud` | Короткое / Short |
| `homecloud-revival` | Хорошее / Good |

### 7.2. Рекомендуемое название / The recommended name

```text
home-cloud-old-hardware
```

### 7.3. Слоган / The slogan

🇷🇺 Английский: / 🇬🇧 English:

```text
Revive old hardware into a private family cloud.
```

🇷🇺 Русский: / 🇬🇧 Russian:

```text
Оживляем старое железо и превращаем его в домашнее семейное облако.
```

---

## 8. Дорожная карта публикации / The publication roadmap

### 8.1. Этап 1. Подготовить публичный репозиторий / Stage 1. Prepare the public repository

🇷🇺 Перед публикацией необходимо: / 🇬🇧 Before publishing it is necessary to:

```text
1. Очистить проект от секретов.
2. Проверить .gitignore.
3. Добавить LICENSE.
4. Добавить README.md.
5. Добавить QUICK_START.md.
6. Добавить схемы архитектуры.
7. Добавить статус проекта: Experimental / Alpha.
8. Добавить SECURITY.md.
9. Добавить CONTRIBUTING.md.
10. Добавить Issue templates.

1. Clear the project of secrets.
2. Check .gitignore.
3. Add a LICENSE.
4. Add README.md.
5. Add QUICK_START.md.
6. Add architecture diagrams.
7. Add the project status: Experimental / Alpha.
8. Add SECURITY.md.
9. Add CONTRIBUTING.md.
10. Add issue templates.
```

🇷🇺 Рекомендуемый статус: / 🇬🇧 The recommended status:

```text
Project status: Alpha / hardware validation stage.
```

### 8.2. Этап 2. Сделать минимально воспроизводимый MVP / Stage 2. Build a minimally reproducible MVP

🇷🇺 MVP должен быть простым: / 🇬🇧 The MVP must be simple:

```text
Jetson Nano / Raspberry Pi / mini-PC
+
USB HDD
+
Docker Compose
+
Nextcloud
+
Immich
+
Samba/SFTP
+
backup scripts
```

🇷🇺 Критерий MVP: / 🇬🇧 The MVP criterion:

```text
Пользователь может взять старое железо, выполнить инструкции и получить рабочее домашнее облако.
A user can take old hardware, follow the instructions and end up with a working home cloud.
```

### 8.3. Этап 3. Опубликовать первый релиз / Stage 3. Publish the first release

🇷🇺 Первый релиз: / 🇬🇧 The first release:

```text
v0.1.0-alpha
```

🇷🇺 Состав релиза: / 🇬🇧 The contents of the release:

```text
- документация;
- docker-compose templates;
- .env.example;
- scripts/diagnostics;
- scripts/backup;
- hardware audit checklist;
- Jetson Nano guide;
- public roadmap;
- ссылки на внешнюю документацию;
- ограничения проекта.

- documentation;
- docker-compose templates;
- .env.example;
- scripts/diagnostics;
- scripts/backup;
- a hardware audit checklist;
- the Jetson Nano guide;
- a public roadmap;
- links to external documentation;
- the project's limitations.
```

### 8.4. Этап 4. Собрать обратную связь / Stage 4. Collect feedback

🇷🇺 Нужно включить GitHub Issues templates: / 🇬🇧 GitHub issue templates must be enabled:

```text
Bug report
Hardware compatibility report
Installation problem
Feature request
Security issue
Documentation improvement
```

🇷🇺 Особенно важен шаблон: / 🇬🇧 One template matters most:

```text
Hardware compatibility report
```

🇷🇺 Пользователи должны добавлять: / 🇬🇧 Users should supply:

```text
- устройство;
- архитектура CPU;
- RAM;
- диск;
- ОС;
- способ установки;
- результат;
- проблемы;
- логи.

- the device;
- the CPU architecture;
- RAM;
- the disk;
- the OS;
- the installation method;
- the result;
- the problems;
- the logs.
```

🇷🇺 Это позволит создать живую базу совместимости.

🇬🇧 This will make it possible to build a living compatibility database.

---

## 9. Как сделать проект заметным / How to make the project visible

### 9.1. README должен быть визуальным / The README must be visual

🇷🇺 В README нужны: / 🇬🇧 The README needs:

```text
1. короткий тезис;
2. схема архитектуры;
3. фото железа;
4. список поддерживаемого оборудования;
5. быстрый старт;
6. предупреждение по backup;
7. roadmap;
8. ссылка на обсуждения.

1. a short thesis;
2. an architecture diagram;
3. a photo of the hardware;
4. a list of supported equipment;
5. a quick start;
6. the backup warning;
7. a roadmap;
8. a link to the discussions.
```

### 9.2. Базовая схема для README / The basic diagram for the README

```text
Android Phones
   │
   ├── Nextcloud App ── files/documents
   ├── Immich App ──── photos/videos
   └── DAVx5 ───────── contacts/calendar
          │
          ▼
Old Hardware Server
   ├── Nextcloud
   ├── Immich
   ├── Samba/SFTP
   ├── Backup jobs
   └── DeepSeek Gateway for diagnostics
          │
          ▼
USB HDD / External Storage
```

### 9.3. Реальные фото стенда / Real photos of the rig

🇷🇺 Проекту нужны фотографии: / 🇬🇧 The project needs photographs of:

```text
- Jetson Nano;
- USB HDD;
- роутер;
- собранный стенд;
- web-интерфейс Nextcloud;
- web-интерфейс Immich;
- Android autoupload;
- результат backup script.

- the Jetson Nano;
- the USB HDD;
- the router;
- the assembled rig;
- the Nextcloud web interface;
- the Immich web interface;
- Android autoupload;
- the output of the backup script.
```

🇷🇺 Реальные фото повышают доверие сильнее, чем абстрактные схемы.

🇬🇧 Real photos build more trust than abstract diagrams.

### 9.4. Короткое видео / A short video

🇷🇺 Темы первого видео: / 🇬🇧 Topics for the first video:

```text
1. Старый Jetson Nano как домашнее облако.
2. Заменяем Google Photos дома.
3. Nextcloud + Immich на старом железе.
4. Семейный архив без подписок.

1. An old Jetson Nano as a home cloud.
2. Replacing Google Photos at home.
3. Nextcloud + Immich on old hardware.
4. A family archive without subscriptions.
```

🇷🇺 Формат: / 🇬🇧 Format:

```text
5–8 минут
результат в первые 60 секунд
без чрезмерной теории

5–8 minutes
the result within the first 60 seconds
no excessive theory
```

---

## 10. Где продвигать проект / Where to promote the project

| Площадка / Platform | Что публиковать / What to publish |
|---|---|
| GitHub | Основной репозиторий / The main repository |
| Habr | Инженерная статья / An engineering article |
| Reddit r/selfhosted | Англоязычная self-hosted аудитория / The English-speaking self-hosted audience |
| Reddit r/homelab | Старое железо и домашняя инфраструктура / Old hardware and home infrastructure |
| Reddit r/DataHoarder | Хранение фото и данных / Storing photos and data |
| Reddit r/NextCloud | Nextcloud-сценарии / Nextcloud scenarios |
| Reddit r/Immich | Фотоархив / The photo archive |
| Telegram-каналы Linux/self-hosted / Linux/self-hosted Telegram channels | Русскоязычный охват / Russian-language reach |
| YouTube | Демонстрация проекта / A demonstration of the project |
| Дзен / VC / Habr | Популярная версия / The popular-science version |

### 10.1. Заголовок для Habr / The Habr title

```text
Оживляем старое железо: домашнее облако на Jetson Nano, USB HDD, Nextcloud и Immich

Reviving old hardware: a home cloud on a Jetson Nano, a USB HDD, Nextcloud and Immich
```

### 10.2. Заголовок для Reddit / The Reddit title

```text
I turned an old Jetson Nano into a private family cloud with Nextcloud, Immich and Android sync
```

---

## 11. Стратегия контента / Content strategy

### 11.1. Серия публикаций / A series of publications

🇷🇺 Не рекомендуется публиковать всё одной большой статьёй. Лучше сделать серию.

🇬🇧 Publishing everything as one long article is not recommended. A series works better.

| Выпуск / Issue | Тема / Topic |
|---:|---|
| 1 | Почему старое железо ещё полезно / Why old hardware is still useful |
| 2 | Аппаратный аудит Jetson Nano / A hardware audit of the Jetson Nano |
| 3 | Подготовка USB HDD и структуры хранения / Preparing the USB HDD and the storage layout |
| 4 | Samba/SFTP как базовый NAS / Samba/SFTP as a basic NAS |
| 5 | Nextcloud для файлов, контактов и календарей / Nextcloud for files, contacts and calendars |
| 6 | Immich как домашний Google Photos / Immich as a home Google Photos |
| 7 | Backup/restore без самообмана / Backup/restore without self-deception |
| 8 | DeepSeek Gateway для диагностики, не для личных данных / The DeepSeek Gateway for diagnostics, not for personal data |
| 9 | Android restore client: архитектура второго этапа / The Android restore client: the stage-two architecture |
| 10 | Сравнение со старыми ноутбуками, Raspberry Pi и mini-PC / A comparison with old laptops, the Raspberry Pi and mini-PCs |

### 11.2. Главное сообщение каждой публикации / The core message of every publication

```text
Старое железо может выполнять полезную инфраструктурную роль.
Главное — не перегружать его, а правильно подобрать функции.

Old hardware can play a useful infrastructural role.
The point is not to overload it, but to pick the right set of functions.
```

---

## 12. Что может «взлететь» / What could take off

### 12.1. Экономика / Economics

```text
Семейный архив без ежемесячной подписки.
A family archive with no monthly subscription.
```

### 12.2. Экология / Ecology

```text
Не выбрасывать рабочее железо.
Do not throw away hardware that still works.
```

### 12.3. Контроль данных / Data control

```text
Фото, контакты и календарь хранятся дома.
Photos, contacts and the calendar are stored at home.
```

### 12.4. Практичность / Practicality

```text
Старый Jetson/Raspberry/mini-PC получает новую роль.
An old Jetson/Raspberry/mini-PC gets a new role.
```

### 12.5. Android/Xiaomi

```text
Резервное копирование семейных Xiaomi-устройств без привязки к Xiaomi Cloud.
Backing up the family's Xiaomi devices without being tied to Xiaomi Cloud.
```

🇷🇺 Эта ниша перспективна, потому что у многих есть Android-телефоны и старое железо, но нет цельной инструкции.

🇬🇧 This niche is promising because many people have Android phones and old hardware, but no coherent set of instructions.

---

## 13. Что может помешать / What could get in the way

| Риск / Risk | Как обработать / How to handle it |
|---|---|
| Jetson Nano слаб для Immich / The Jetson Nano is too weak for Immich | Писать честно: ML отключить, стартовать с малого архива / Be honest: disable ML, start with a small archive |
| Пользователи захотят «одной кнопкой» / Users will want a one-click setup | Сделать `install.sh`, но после стабилизации инструкции / Provide `install.sh`, but only after the instructions have stabilised |
| Потеря данных у пользователей / Users losing data | Жёстко писать: это не backup без второго носителя / State it bluntly: this is not a backup without a second medium |
| Секреты в репозитории / Secrets in the repository | `.env.example`, secret scan, правила агентов / `.env.example`, a secret scan, agent rules |
| Сложность для новичков / Too hard for newcomers | `QUICK_START.md` и пошаговые команды / `QUICK_START.md` and step-by-step commands |
| Споры «зачем Jetson, лучше mini-PC» / Arguments of the "why a Jetson, a mini-PC is better" kind | Поддержать разные классы железа / Support several classes of hardware |
| Безопасность внешнего доступа / The security of external access | На первом этапе только VPN, не прямой интернет / At the first stage, VPN only, never direct internet |
| Перегрев старого железа / Old hardware overheating | Добавить thermal checklist / Add a thermal checklist |
| Слабые microSD-карты / Weak microSD cards | Рекомендовать вынос данных на HDD/SSD / Recommend moving the data onto an HDD/SSD |
| Разные CPU-архитектуры / Differing CPU architectures | Ввести профили ARM64/x86_64 / Introduce ARM64/x86_64 profiles |

---

## 14. Лицензия / Licence

### 14.1. Варианты / Options

| Лицензия / Licence | Когда использовать / When to use it |
|---|---|
| MIT | Если нужен максимально простой режим использования / If the simplest possible terms of use are wanted |
| Apache-2.0 | Если нужна более формальная защита по патентам / If more formal patent protection is wanted |
| GPLv3 | Если нужно требовать открытости производных работ / If derivative works must be required to stay open |
| CC BY 4.0 | Для документации, если отделять от кода / For the documentation, if it is separated from the code |

### 14.2. Рекомендация / Recommendation

🇷🇺 Для инженерного проекта рекомендуется: / 🇬🇧 For an engineering project the recommendation is:

```text
Apache-2.0
```

🇷🇺 Причина: / 🇬🇧 The reason:

```text
Формальная и распространённая лицензия, подходящая для инфраструктурного open-source проекта.
A formal and widely used licence, suitable for an infrastructure open-source project.
```

🇷🇺 Документацию можно позднее вынести под: / 🇬🇧 The documentation can later be moved under:

```text
CC BY 4.0
```

🇷🇺 На старте допустимо использовать одну лицензию Apache-2.0 для всего репозитория.

🇬🇧 At the start it is acceptable to use a single Apache-2.0 licence for the whole repository.

---

## 15. GitHub-оформление / GitHub presentation

### 15.1. Topics

🇷🇺 Рекомендуемые GitHub topics: / 🇬🇧 Recommended GitHub topics:

```text
self-hosted
home-cloud
old-hardware
jetson-nano
raspberry-pi
nextcloud
immich
android-backup
family-cloud
docker-compose
nas
privacy
deepseek
llm-gateway
backup
homelab
```

### 15.2. Описание репозитория / The repository description

🇷🇺 Английское: / 🇬🇧 English:

```text
Revive old hardware into a private family cloud with Nextcloud, Immich, Android sync and privacy-controlled LLM diagnostics.
```

🇷🇺 Русское: / 🇬🇧 Russian:

```text
Домашнее семейное облако на старом железе: Nextcloud, Immich, Android-синхронизация и безопасная LLM-диагностика.
```

---

## 16. Технология раскрутки по шагам / The promotion process step by step

### 16.1. Шаг 1. Сделать проект публично понятным / Step 1. Make the project understandable to the public

🇷🇺 До публикации должны быть готовы: / 🇬🇧 These must be ready before publication:

```text
README.md
QUICK_START.md
ARCHITECTURE.md
OLD_HARDWARE_GUIDE.md
HARDWARE_COMPATIBILITY.md
SECURITY.md
PRIVACY.md
BACKUP_RESTORE.md
```

### 16.2. Шаг 2. Опубликовать GitHub / Step 2. Publish on GitHub

🇷🇺 После публикации: / 🇬🇧 After publication:

```text
- добавить topics;
- включить Discussions;
- добавить Issue templates;
- добавить Projects/Roadmap;
- создать release v0.1.0-alpha;
- добавить CHANGELOG.md;
- добавить CONTRIBUTING.md.

- add topics;
- enable Discussions;
- add issue templates;
- add Projects/Roadmap;
- create release v0.1.0-alpha;
- add CHANGELOG.md;
- add CONTRIBUTING.md.
```

### 16.3. Шаг 3. Написать первую статью / Step 3. Write the first article

🇷🇺 Тема: / 🇬🇧 Topic:

```text
Оживляем старое железо: домашнее облако на Jetson Nano с Nextcloud и Immich

Reviving old hardware: a home cloud on a Jetson Nano with Nextcloud and Immich
```

🇷🇺 Структура статьи: / 🇬🇧 The article's structure:

```text
1. Проблема.
2. Железо.
3. Архитектура.
4. Что получилось.
5. Ограничения.
6. Как повторить.
7. Ссылка на GitHub.

1. The problem.
2. The hardware.
3. The architecture.
4. What came of it.
5. The limitations.
6. How to repeat it.
7. The GitHub link.
```

### 16.4. Шаг 4. Сделать демонстрационный стенд / Step 4. Build a demonstration rig

🇷🇺 Показать: / 🇬🇧 Show:

```text
- вход в Nextcloud;
- загрузку файла;
- контакты/календарь;
- Immich с тестовыми фото;
- Android автозагрузку;
- backup script;
- DeepSeek diagnostic report.

- logging into Nextcloud;
- uploading a file;
- contacts/calendar;
- Immich with test photos;
- Android auto-upload;
- the backup script;
- a DeepSeek diagnostic report.
```

### 16.5. Шаг 5. Собрать обратную связь / Step 5. Collect feedback

🇷🇺 Запрашивать у пользователей: / 🇬🇧 Ask users for:

```text
- какое старое железо есть;
- что получилось запустить;
- какие ошибки;
- какие устройства добавить в compatibility matrix.

- what old hardware they have;
- what they managed to get running;
- what errors they hit;
- which devices to add to the compatibility matrix.
```

### 16.6. Шаг 6. Расширить проект за пределы Jetson / Step 6. Extend the project beyond the Jetson

🇷🇺 Добавить профили: / 🇬🇧 Add profiles:

```text
profiles/
├── jetson-nano/
├── raspberry-pi-4/
├── raspberry-pi-5/
├── orange-pi/
├── old-laptop/
├── mini-pc/
└── x86-server/
```

🇷🇺 Это важно. Проект не должен умереть как частный случай Jetson Nano.

🇬🇧 This matters. The project must not die as a special case of the Jetson Nano.

---

## 17. MVP для публичного интереса / The MVP for public interest

### 17.1. Минимальный MVP / The minimal MVP

```text
1. Аппаратный аудит.
2. Подготовка USB HDD.
3. Samba/SFTP.
4. Docker Compose.
5. Nextcloud.
6. Immich.
7. restic backup.
8. DeepSeek Gateway только для диагностики.

1. A hardware audit.
2. Preparing the USB HDD.
3. Samba/SFTP.
4. Docker Compose.
5. Nextcloud.
6. Immich.
7. restic backup.
8. The DeepSeek Gateway for diagnostics only.
```

### 17.2. Что не включать в MVP / What not to include in the MVP

```text
1. Локальную LLM.
2. Сложный Android-клиент.
3. Публичный доступ без VPN.
4. Автоматический one-click installer без тестирования.
5. Machine learning Immich на слабом железе по умолчанию.

1. A local LLM.
2. A complex Android client.
3. Public access without a VPN.
4. An automatic one-click installer that has not been tested.
5. Immich machine learning enabled by default on weak hardware.
```

---

## 18. Публичная матрица совместимости / The public compatibility matrix

🇷🇺 В проекте нужно создать `HARDWARE_COMPATIBILITY.md`.

🇬🇧 The project needs a `HARDWARE_COMPATIBILITY.md`.

🇷🇺 Пример таблицы: / 🇬🇧 An example table:

| Устройство / Device | CPU/RAM | Storage | Status | Notes |
|---|---|---|---|---|
| Jetson Nano 4GB | ARM64 / 4 GB | USB HDD | Testing | ML in Immich disabled |
| Raspberry Pi 4 4GB | ARM64 / 4 GB | USB SSD | Planned | Good baseline |
| Raspberry Pi 5 8GB | ARM64 / 8 GB | USB SSD | Planned | Better performance |
| Old laptop x86_64 | x86_64 / 8 GB+ | SATA/USB HDD | Planned | Recommended for larger archives |
| Mini-PC x86_64 | x86_64 / 8–16 GB | SSD/HDD | Planned | Best low-power option |

---

## 19. Правила безопасности для публичной версии / Safety rules for the public version

🇷🇺 В публичной документации обязательно указать: / 🇬🇧 The public documentation must state:

```text
1. Не открывать SMB/FTP/Nextcloud напрямую в интернет на первом этапе.
2. Использовать VPN для внешнего доступа.
3. Не коммитить .env.
4. Не коммитить DeepSeek API key.
5. Не отправлять личные фото/контакты/календарь в LLM.
6. Делать backup на второй носитель.
7. Проверять восстановление, а не только создание backup.

1. Do not expose SMB/FTP/Nextcloud directly to the internet at the first stage.
2. Use a VPN for external access.
3. Do not commit .env.
4. Do not commit the DeepSeek API key.
5. Do not send personal photos/contacts/calendar to an LLM.
6. Back up to a second medium.
7. Test the restore, not just the creation of the backup.
```

---

## 20. Главный практический вывод / The main practical conclusion

🇷🇺 Проект может получить интерес, если не позиционировать его как «ещё одна установка Nextcloud», а подать как:

🇬🇧 The project can attract interest if it is not positioned as "yet another Nextcloud installation" but presented as:

```text
методику повторного использования старого оборудования
для домашнего облака и семейного цифрового архива.

a method for reusing old equipment
to build a home cloud and a family digital archive.
```

🇷🇺 Главный фокус: / 🇬🇧 The main focus:

```text
Оживим старое железо.
Let's revive old hardware.
```

🇷🇺 Техническое ядро: / 🇬🇧 The technical core:

```text
Nextcloud + Immich + USB HDD + Docker Compose + Backup + Android sync + DeepSeek diagnostics.
```

🇷🇺 Сильная общественная идея: / 🇬🇧 A strong social idea:

```text
Старые платы, ноутбуки и mini-PC могут стать полезными домашними серверами, а не электронным мусором.
Old boards, laptops and mini-PCs can become useful home servers instead of electronic waste.
```

---

## 21. Контрольный чек-лист перед публичной публикацией / The checklist before going public

```text
[ ] README.md написан простым языком.
[ ] QUICK_START.md проверен на чистой системе.
[ ] В репозитории нет .env и секретов.
[ ] Есть .env.example.
[ ] Есть LICENSE.
[ ] Есть SECURITY.md.
[ ] Есть BACKUP_RESTORE.md.
[ ] Есть OLD_HARDWARE_GUIDE.md.
[ ] Есть HARDWARE_COMPATIBILITY.md.
[ ] Есть Issue templates.
[ ] Есть первый GitHub Release.
[ ] Есть предупреждение: один HDD не является полноценным backup.
[ ] Есть ограничение: Jetson Nano не предназначен для локальной LLM.
[ ] Есть ограничение: Immich ML на слабом железе отключать.
[ ] Есть Roadmap Stage 1 / Stage 2 / Stage 3.

[ ] README.md is written in plain language.
[ ] QUICK_START.md has been verified on a clean system.
[ ] There is no .env and no secrets in the repository.
[ ] There is a .env.example.
[ ] There is a LICENSE.
[ ] There is a SECURITY.md.
[ ] There is a BACKUP_RESTORE.md.
[ ] There is an OLD_HARDWARE_GUIDE.md.
[ ] There is a HARDWARE_COMPATIBILITY.md.
[ ] There are issue templates.
[ ] There is a first GitHub Release.
[ ] There is a warning: a single HDD is not a real backup.
[ ] There is a limitation stated: the Jetson Nano is not meant for a local LLM.
[ ] There is a limitation stated: Immich ML must be disabled on weak hardware.
[ ] There is a Roadmap with Stage 1 / Stage 2 / Stage 3.
```

---

## 22. Рекомендуемый порядок ближайших действий / The recommended order of the next actions

```text
1. Переименовать проект в home-cloud-old-hardware или оставить home-cloud-jetson как hardware profile.
2. Обновить README под концепцию «оживим старое железо».
3. Добавить OLD_HARDWARE_GUIDE.md.
4. Добавить HARDWARE_COMPATIBILITY.md.
5. Добавить публичный Roadmap.
6. Подготовить первый аппаратный аудит Jetson Nano.
7. Сделать первый release v0.1.0-alpha.
8. Написать первую статью на Habr.
9. Добавить поддержку профилей Raspberry Pi / mini-PC / old laptop.

1. Rename the project to home-cloud-old-hardware, or keep home-cloud-jetson as a hardware profile.
2. Rewrite the README around the "let's revive old hardware" concept.
3. Add OLD_HARDWARE_GUIDE.md.
4. Add HARDWARE_COMPATIBILITY.md.
5. Add a public Roadmap.
6. Prepare the first hardware audit of the Jetson Nano.
7. Cut the first release, v0.1.0-alpha.
8. Write the first Habr article.
9. Add support for the Raspberry Pi / mini-PC / old laptop profiles.
```
