# Реестр рисков / Risk register

**Дата / Date:** 2026-08-30. Синтезировано из трёх параллельных read-only проверок (железо/Docker/сеть, инвентаризация/архитектура, безопасность/надёжность) / Synthesized from three parallel read-only investigations.

Уровни / Levels: `CRITICAL` `HIGH` `MEDIUM` `LOW`.

| ID | Риск / Risk | Вероятность / Probability | Impact | Доказательство / Evidence | Митигация / Mitigation |
|---|---|---|---|---|---|
| R-01 | Фото Immich (~6–9 ГБ, единственная копия) теряются безвозвратно при отказе SSD | MEDIUM | **CRITICAL** | `docs/plans/WAVE_0_OFFSITE_BACKUP.md`: offsite-бэкап покрывает только БД-дампы (restic, фаза 1); фото — только `/mnt/storage/immich` (12ГБ), нет photo-backup ни в `docker/compose/`, `systemd/`, `scripts/backup/` | Фаза 2 offsite-бэкапа фото — уже в «Ближайших задачах» CLAUDE.md, не начата |
| R-02 | Реальные значения `.env`/секретов существуют только на устройстве, без redacted-снапшота вовне; при потере устройства — полная перевыпуск-кампания | LOW-MEDIUM | HIGH | `.env.example` даёт только имена; 10 `.env.bak.*` без единого журнала; прецедент — ротация паролей 2026-06-28 | Задокументировать процедуру перевыпуска; рассмотреть зашифрованный offsite-снапшот `.env` |
| R-03 | Talk-видеозвонки снаружи LAN не проходят симметричный NAT — `coturn` в compose, но не развёрнут на VPS | HIGH (структурно, произойдёт при каждой попытке позвонить извне) | MEDIUM | `docker images`/`docker ps -a` на VPS — образ `coturn` не подтягивался ни разу | Развернуть `docker-compose.coturn.yml` на VPS **или** явно принять ограничение и задокументировать |
| R-04 | Наивный деплой переименованного кода на устройство сломает `/v1/report/now` и `/v1/actions/backup/now` (`report_cmd`/`backup_cmd` default указывают на несуществующие пути) | MEDIUM (реализуется только при Части B миграции) | MEDIUM | `services/nas_jetson_nano-api/app/config.py:47`; на устройстве файла `nas_jetson_nano-send-report-telegram.sh` нет, `.env` не переопределяет | Учтено в runbook `docs/plans/tranquil-wandering-truffle.md` §Часть B — переопределить пути ДО пересоздания контейнера |
| R-05 | Ubuntu 18.04.6 LTS (EOL стандартной поддержки с апреля 2023) — база хоста без подтверждённых патчей безопасности | MEDIUM | HIGH | `/etc/os-release`; ESM-статус не проверялся (`pro status` не выполнялся) | Проверить `pro status`; при отсутствии ESM — рассмотреть покупку или план миграции ОС в рамках будущей замены оборудования |
| R-06 | CORS `*` на API :8099 в сочетании с Bearer-JWT | LOW (LAN-only периметр) | MEDIUM | `services/nas_jetson_nano-api/app/main.py:171-176` | Сузить `allow_origins` до конкретных LAN-хостов |
| R-07 | `NAS_JETSON_NANO_API_JWT_SECRET` может не быть задан явно → секрет генерируется заново при каждом рестарте/пересборке, все токены аннулируются | UNKNOWN (не проверено, задан ли реально) | LOW (неудобство, не утечка) | `config.py:22` — `secrets.token_hex(32)` как default | Подтвердить, что переменная задана в `.env`; при отсутствии — задать явно |
| R-08 | `jms583-health.log` растёт без logrotate (2.7 МБ / 40к строк за 2 мес) | LOW (текущий темп) | LOW | `/etc/logrotate.d/` не содержит записи для `nasa-*`/`jms583` | Добавить logrotate-конфиг по аналогии с `nasa-api.jsonl` (уже ротируется) |
| R-09 | `storage_preflight.sh` не содержит явной проверки свободного места перед стартом сервисов | LOW сейчас (94% свободно на SSD) | MEDIUM (при реализации — тихий сбой деплоя/бэкапа) | `grep -n "df \|Avail\|disk.*full\|space"` в скрипте — ноль совпадений | Добавить явную проверку с порогом и явным отказом |
| R-10 | Непиннингованные зависимости `nasa-api` (включая JWT-библиотеки `python-jose`/`passlib`) — версии могут «уехать» при `--build` | MEDIUM (реализуется при каждой пересборке) | LOW-MEDIUM | `services/nas_jetson_nano-api/requirements.txt` — диапазоны `>=`, два других сервиса — точный пиннинг `==` | Закрепить версии `==`, как в `llm-gateway`/`backup-api` |
| R-11 | Плавающие теги `latest`/`release`/`apache` у 5 образов (Netdata, Portainer, Samba, LLM-Gateway/nasa-api локальные сборки, Immich/Nextcloud) | MEDIUM | MEDIUM (неконтролируемый апгрейд при следующем `pull`/`build`) | `DEPENDENCIES.md` §3 | Зафиксировать конкретные версии после проверки совместимости |
| R-12 | SD-карта (корень ФС, 41% занято) не имеет активного мониторинга износа — юнит `nas_jetson_nano-sd-wear` есть в git, не развёрнут | LOW-MEDIUM (годовой горизонт) | HIGH (отказ SD = полный простой хоста, включая journal/systemd) | `RUNTIME.md` §6; `sd_wear_check.sh` существует, не подключён к systemd/cron (устройство) | Развернуть таймер при следующем визите в проект — уже под рукой в git |
| R-13 | Уборка мониторинга неполная: Uptime Kuma покрывает только 5 HTTP-эндпоинтов, Samba/Portainer/БД/Redis отдельными мониторами не покрыты | LOW | LOW | Прочитано `kuma.db` (read-only), 5 активных http-мониторов | Не обязательно — Netdata покрывает системный уровень отдельно; явно принять как осознанный компромисс |

## Не включено как риск / Explicitly not a risk

- **27 ГБ `$RECYCLE.BIN` на `/mnt/hdd2tb`** — не риск, кандидат на ручную очистку (см. `AUDIT_REPORT.md` §26 Quick Wins).
- **GPU/CUDA/TensorRT простаивает** — осознанный архитектурный выбор (4 ГБ RAM), не дефект. См. `AI_STACK.md`.
- **HTTP без TLS внутри LAN** — принятый и ранее задокументированный риск, переисследование не изменило оценку.
