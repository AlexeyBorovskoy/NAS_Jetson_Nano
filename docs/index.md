# NAS_Jetson_Nano

_Old hardware should live._ · _Старое железо должно жить._

> 🇷🇺 Семейное облако на NVIDIA Jetson Nano 2019 года: фотографии, файлы, контакты и
> календарь — дома. Проект опубликован целиком, включая ошибки и то, как они находились.
>
> 🇬🇧 A family cloud on a 2019 NVIDIA Jetson Nano: photos, files, contacts and calendar,
> at home. Published in full — including the mistakes and how they were caught.

## Состояние / State — 2026-08-22

🇷🇺 Замерено живыми командами в этот день, а не взято из прошлых документов. /
🇬🇧 Verified by live commands that day, not carried over from earlier docs.

| | |
|---|---|
| Контейнеры / Containers | 13 up, 0 рестартов |
| Immich | 7 476 ассетов / assets, 23 альбома |
| Nextcloud | v33.0.4, 5 пользователей / users |
| Хранилище / Storage | SSD 229 ГБ (6 %) + HDD 2 ТБ (76 %, 1.4 ТБ архива) |
| Бэкапы / Backups | ежедневно, ~151 МБ, restore проверен / verified 2026-08-09 |
| Внешний доступ / Remote access | реверс-туннель через VPS, портов наружу нет |

🔴 **Открытый долг / Open debt:** 🇷🇺 off-site бэкапа нет — всё в одном доме. /
🇬🇧 no off-site backup yet — everything sits in one building.

## Читать / Read

**О проекте / About**
- [🇷🇺 Черновик статьи для Habr](articles/habr_article_ru.md)
- [🇬🇧 Hackaday.io project draft](articles/hackaday_project_en.md)
- [Архитектура / Architecture](pages/architecture.md) · [`03_ARCHITECTURE`](03_ARCHITECTURE.md)
- [Почему не готовый NAS / Why not a NAS box](15_ALTERNATIVES_REVIEW.md)

**Как это держится / How it holds up**
- [Надёжность и проверка / Reliability and validation](pages/reliability.md)
- [Бэкап и восстановление / Backup and restore](12_BACKUP_RESTORE.md)
- [Мониторинг / Monitoring](13_MONITORING_RUNBOOK.md)
- [Доказательства / Evidence package](pages/evidence.md)

**Клиенты и сеть / Clients and network**
- [Android-клиенты / Android clients](pages/android.md) · [`24_CLIENT_SETUP`](24_CLIENT_SETUP.md)
- [Слепок домашней сети / Home network snapshot](28_NETWORK_SNAPSHOT_2026-08-22.md)

**Куда идём / Where next**
- [Вычисления, Kaggle, локальные модели / Compute, Kaggle, local models](29_COMPUTE_AND_LLM_ROADMAP.md)
- [Разбор критики читателей / Reader feedback](plans/POST_HABR_FEEDBACK_2026-08.md)

**Как это делалось с ИИ / Built with AI agents**
- [Модель работы с агентами / Agent operating model](20_AGENT_OPERATING_MODEL.md)

---

🇷🇺 Полный список документов — в [репозитории](https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano/tree/main/docs).
🇬🇧 The full document list lives in the repository.
