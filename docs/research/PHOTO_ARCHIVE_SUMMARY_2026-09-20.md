# Инвентаризация фотоархива HDD 2 ТБ — сводка (2026-09-20)

🇷🇺 Русский | 🇬🇧 [English](#english-summary)

## Статус: инвентаризация частичная, прервана инцидентом

Полный обход архива (`find` по всем 1.9 ТБ раздела через `ntfs-3g`) был
прерван зависанием точки монтирования `/mnt/hdd2tb` примерно на 3-й минуте.
Подробности инцидента, диагностика и рекомендации по восстановлению — в
внегитовом документе `docs/local/PHOTO_ARCHIVE_INVENTORY_2026-09-20.md`
(содержит имена каталогов, здесь не публикуются).

**Коротко о причине:** одновременно оказалось запущено два тяжёлых рекурсивных
обхода одной и той же `ntfs-3g`-точки монтирования — именно та ситуация,
которую инструкция по инвентаризации прямо запрещала. Процессы-читатели
зависли (не убиваются `kill -9`, что типично для зависшего fuse-демона),
физического диска (`smartctl`, `dmesg`) это не касается — признаков
аппаратной ошибки или ошибки USB-моста не найдено. **Данные на архиве не
менялись** — все операции инвентаризации были read-only (`find`, `stat`,
`docker run -v ...:ro`); подтвердить это финальным `ls -ld` после инцидента
не удалось, так как точка монтирования не отвечала на момент завершения
работы.

Из-за этого нижеприведённые числа **не описывают весь архив** — только ту его
часть, что успела попасть в выборку до зависания (см. «Полнота охвата» ниже).
Числа приводятся с датой замера **2026-09-20** и явной пометкой охвата.

## Объём и охват

| Показатель | Значение |
|---|---|
| Раздел `/mnt/hdd2tb` целиком (`df`, 2026-09-20) | 1.9 TB, занято 1.4 TB (77%) |
| Успели каталогизировать до зависания | 271 220 файлов, ≈ 1241.7 GB |
| Оценка охвата по объёму | ≈ 86–89% занятого места (смещённая оценка — крупные RAW/видео-каталоги обходились первыми) |
| Не охвачено вовсе | несколько каталогов верхнего уровня, включая минимум один явно фотоориентированный (по внутренним пометкам, не публикуется здесь) |

## Состав по типам (в пределах собранной части, не всего архива)

| Категория | Файлов (оценка) | Объём (оценка) |
|---|---|---|
| Фотографии (jpg/tif/png/bmp + RAW: nef/arw/cr2) | ≈ 91 200 | ≈ 824 GB |
| Видео (avi/mkv/mp4/mov/wmv/mts) | ≈ 770 | ≈ 251 GB |
| Служебный превью-кэш (Lightroom `.lrprev` и т.п.) | ≈ 13 600 | ≈ 3 GB |
| Документы/офис (pdf/doc/docx/pptx/dwg) | ≈ 26 400 | ≈ 43 GB |
| Архивы/установщики (zip/rar/7z/exe/iso) | ≈ 2 000 | ≈ 90 GB |
| Прочее (аудио, системные, без расширения и т.д.) | остаток | остаток |

RAW-формат (`.nef`, Nikon) доминирует по объёму — 420 GB на 19 713 файлов,
то есть архив в основном первичный (несведённые RAW-кадры с зеркальной
камеры), а не только JPEG-выгрузки с телефонов.

## EXIF — метод подтверждён, статистика не собрана

Проверен и подтверждён рабочий способ чтения EXIF **без риска для Immich**:
контейнер `ghcr.io/immich-app/immich-server` уже содержит `exiftool`
(vendored, Perl); можно поднимать одноразовый `docker run --rm -v
/mnt/hdd2tb:/data:ro --entrypoint <exiftool> ...` — read-only монтирование,
отдельный контейнер, не трогает живой Immich и его БД.

На одном тестовом снимке подтверждено, что дата съёмки (`DateTimeOriginal`),
модель камеры и размер кадра читаются корректно. Статистика по всей выборке
(доля снимков с датой, распределение по годам/месяцам, геометки) **не
собрана** — обход прервался раньше. Грубая оценка (не замер) полного прохода
EXIF по собранной части (~91 тыс. фото): **30–150 минут** в одном потоке;
для полного архива — пропорционально больше с учётом неохваченных каталогов.

## Дубликаты — не оценено

Шаг не выполнен (обход прервался раньше).

## Пригодность для Immich и рекомендация

**Рекомендация одной строкой:** прежде чем принимать решение о подключении
архива к Immich, нужно (а) безопасно восстановить точку монтирования
`/mnt/hdd2tb` (решение и выполнение — за владельцем, не в периметре этой
задачи), и (б) повторить обход **по одному каталогу верхнего уровня за раз**,
без параллельных проходов — ровно так, как и было предписано, но не
соблюдено в этом заходе.

**Immich как внешняя библиотека (External Library):**
- Плюсы: поиск по дате/лицам/геометкам, «воспоминания», готовый UI и API,
  которые уже использует seмья.
- Стоимость по месту: миниатюры Immich (`thumbnail`/`preview`) по
  документации проекта создаются на **каждый** ассет в нескольких размерах;
  ориентировочно доли МБ – единицы МБ на фото в зависимости от разрешения —
  для ≥ 90 тыс. фото это грубо **десятки ГБ** дополнительно на SSD (не на
  HDD, если preview-кэш не вынесен туда явно) — **это оценка по порядку
  величины со ссылкой на общую документацию Immich, не измерение**, и требует
  проверки с актуальной версией Immich перед принятием решения.
- Стоимость по нагрузке: генерация миниатюр и (если включено) ML-индексация
  лиц/объектов для ~90 тыс.+ фото — заметная разовая нагрузка на Jetson Nano
  (4 ГБ ОЗУ, ZRAM и так плотно занят, см. основной `CLAUDE.md`); есть
  незавершённый параллельный трек по выносу Immich ML на рабочую станцию —
  использовать его, а не считать на самом Jetson.

**Альтернатива — свой лёгкий индекс:** SQLite с путями, размером, mtime и
(опционально) EXIF-датой/камерой, без превью и ML. Дешевле по месту и CPU,
но не даёт распознавания лиц/сцен и обычного просмотра — только текстовый
поиск и подборки по датам через бота. Разумный первый шаг, если решение по
Immich откладывается: можно построить прямо из уже собранного частичного
списка файлов после его пересборки.

---

## English summary

**Status: partial inventory, interrupted by an incident.** A full recursive
walk of the 1.9 TB `/mnt/hdd2tb` NTFS archive (via `ntfs-3g`) hung about 3
minutes in, after two heavy recursive scans ended up running against the same
mount concurrently — exactly the condition the inventory brief explicitly
prohibited. The reader processes could not be killed (`kill -9` had no
effect, typical of a wedged FUSE daemon); no USB/SCSI hardware errors were
found in kernel logs. **No data was modified** — every inventory operation
was read-only — but a final "unchanged" proof via `ls -ld` could not be
captured because the mount was still unresponsive when work stopped. Full
incident details live in the out-of-git local doc (directory names, not
published here).

**Coverage:** 271,220 files, ≈ 1241.7 GB were catalogued before the hang —
roughly 86–89% of the 1.4 TB used on the volume by size (a biased estimate,
since the largest RAW/video folders were walked first). At least one
top-level folder that is clearly a core personal photo archive by name was
**not reached at all**.

**Composition (within the collected portion only):** ≈ 91,200 photo files
(jpg/tif/png/bmp + RAW nef/arw/cr2) totalling ≈ 824 GB; ≈ 770 video files
(≈ 251 GB); Nikon RAW (`.nef`) dominates by volume (420 GB / 19,713 files),
so the archive is largely un-processed camera originals, not just phone
JPEGs.

**EXIF:** method verified safe and working — the Immich server image already
bundles `exiftool`; a throwaway `docker run --rm -v /mnt/hdd2tb:/data:ro
--entrypoint <exiftool> ...` reads dates/camera model correctly without
touching the live Immich container or its database. Bulk sampling (date
coverage, year/month distribution) was **not completed**. Rough estimate for
a full EXIF pass over the collected photos: 30–150 minutes single-threaded —
an estimate, not a measurement.

**Duplicates:** not assessed (walk was interrupted before this step).

**Recommendation:** before deciding on Immich, first safely recover the
`/mnt/hdd2tb` mount (owner decision, outside this task's scope), then repeat
the walk **one top-level folder at a time**, never in parallel. Immich as an
external library buys search/memories/faces on top of an existing UI, at the
cost of tens of GB of thumbnail storage (order-of-magnitude estimate from
Immich's general docs, not measured) and a one-time indexing load that
should run on the workstation ML offload track already in progress, not on
the Jetson itself. A lightweight SQLite path+date index is a cheaper
fallback if the Immich decision is deferred — no thumbnails, no face
detection, just text search and date-based bot digests.
