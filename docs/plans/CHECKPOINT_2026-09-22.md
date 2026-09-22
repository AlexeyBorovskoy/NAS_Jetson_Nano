# Точка проекта 2026-09-22 — P0 (вторая копия Immich) закрыт на HDD

> Устройство не перенастраивалось. VPN/Amnezia не трогались.  
> Замеры: SSH `jetson-via-vps`, 2026-09-22.

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

## Следующее (не P0)

1. Причина restic S3 `400` **с Jetson** (если снова понадобится off-site).  
2. Выкат E9 / D3 по «деплой».  
3. `usefact` Object Storage — непроверено.
