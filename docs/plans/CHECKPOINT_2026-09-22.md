# Точка проекта 2026-09-22 — P0 L1 закрыт; restic path-style; туннель Jetson лёг

> Устройство не перенастраивалось. VPN/Amnezia не трогались.  
> Замеры: SSH `jetson-via-vps` (утро); днём VPS жив, `:10022` нет.

## P0 закрыт (L1, не S3)

Checkpoint 2026-09-21 утверждал: фото Immich **в одном экземпляре на USB-SSD**, W2 «в git, не выкачен».  
**Это неверно на живой системе.** Off-site S3 по-прежнему пуст (решение владельца 21.09).  
Вторая копия **на HDD Jetson уже в бою**.

| Замер | Значение |
|-------|----------|
| Таймер | `nas_jetson_nano-immich-hdd-copy.timer` **active** |
| Последний прогон | 2026-09-22 04:22–04:25 UTC, **status=0 SUCCESS** |
| Следующий | 2026-09-23 04:15 UTC |
| Источник | `/mnt/storage/immich` **13 G**, 22 501 файл |
| Копия | `/mnt/hdd2tb/backups/immich` **13 G**, 22 515 файл |
| rsync stats | 37 606 entries; created 6; transferred 4 files / 21.5 MiB; total size 13 120 732 962 B |
| HDD | `/mnt/hdd2tb` 1.9 T, занято 1.4 T, свободно 437 G |
| SSD live | `/mnt/storage` 229 G, Immich 14 G used on fs |
| sha256 выборка | **3/3 OK** (preview jpeg из `library/thumbs/…`) |

Лишние 14 файлов на HDD: rsync **без `--delete`** (скрипт так и задуман — не стирает источник и не чистит dest). Не дефект P0.

## Что это закрывает / что нет

| Слой | Статус |
|------|--------|
| L0 live SSD | ✅ |
| **L1 HDD Immich** | ✅ **P0 «один экземпляр на SSD» закрыт** |
| L2 Cloud.ru S3 фото | ❌ пусто (владелец удалил 21.09); restic с Jetson → S3 `400` — **открыто отдельно** |
| Архив 1.4 T на HDD | по-прежнему без второй копии (B5, риск принят) |

## Документы

- Этот файл — текущая точка.
- `CLAUDE.md`, `DEVELOPMENT_PLAN_2026-09_SBER_ERA.md`, `docs/integrations/sber/CLOUD_RU.md` — статус P0.

## restic S3 400 (день)

| Факт | |
|------|--|
| restic на Jetson | 0.19.1 linux/arm64 `/usr/local/bin/restic` |
| Ключ | `AWS_ACCESS_KEY_ID` LEN=69, 1 `:` (форма `tenant:keyId`) |
| Репозиторий в `.env` | нет `RESTIC_REPOSITORY`; сборка `s3:https://s3.cloud.ru/nas-immich-offsite/immich` |
| Префикс `immich/` | пуст (удаление 21.09) |
| Гипотеза 400 | Cloud.ru path-style; dns/virtual-host → 400. В git: `-o s3.bucket-lookup=path` |
| Живой A/B probe | **не выполнен** — туннель Jetson уже мёртв |
| Коммит | `5c7258b` `restic_s3_cloudru_probe.sh` + example |

## Сеть (день)

| Узел | Статус |
|------|--------|
| VPS `95.163.176.103` | SSH OK; `amnezia-xray` / `amnezia-awg2` Up |
| VPS `:10022` Jetson reverse | **не слушает** |
| VPS `:10222` Vostro reverse | **не слушает** |
| `ssh jetson-via-vps` | fail (stdio forwarding) |
| `ssh admin@192.168.0.50` с этой станции | timeout (станция не в домашней LAN) |
| Amnezia | не трогали |

Из дома Jetson = `192.168.0.50`. Не из дома = только пока жив reverse на VPS.

## Зеркала git

| Remote | URL | 22.09 |
|--------|-----|--------|
| origin (канон) | GitHub `NAS_Jetson_Nano` HTTPS | `5c7258b` запушен |
| gitverse | `git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git` SSH | **таймаут :22** при пуше `ee262ea` и повтор |

Не «нельзя сделать зеркало», а **с этой сети SSH на gitverse.ru:22 не проходит**. Канон — GitHub; GitVerse — зеркало, когда порт жив (`git push gitverse main` и `main:master`).

HEAD на момент точки: после коммита этой правки.

## Следующее

1. Из дома: поднять Jetson reverse (`autossh` / юнит туннеля) — без Amnezia.  
2. На Jetson: `sudo bash scripts/backup/restic_s3_cloudru_probe.sh`  
3. `git push gitverse main; git push gitverse main:master` когда :22 GitVerse отвечает  
4. E9/D3 — по «деплой»
