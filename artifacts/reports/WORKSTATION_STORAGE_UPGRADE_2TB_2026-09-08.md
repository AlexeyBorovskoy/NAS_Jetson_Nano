# Апгрейд накопителей workstation → 2 TB (2026-09-08)

> Хост: `ALEXEY3D` · ASUS **ROG Strix G17** `G713IE_G713IE` (board `G713IE`)  
> Источник: live PowerShell / WMI / Storage cmdlets / PnP (без wipe, без покупок).  
> Серийные номера **не** публикуются.  
> Связанный паспорт: `artifacts/reports/WORKSTATION_INVENTORY_2026-09-07.md`.

---

## 0. Краткое резюме

| Факт | Значение |
|---|---|
| Форм-фактор | **Ноутбук** (PCSystemType=2, ChassisTypes=10) |
| Платформа | AMD **Ryzen 7 4800H** (Renoir, **PCIe 3.0**) + RTX 3050 Ti Laptop |
| Внутренние NVMe | **2 шт., оба слота заняты** |
| Системный | **INTEL SSDPEKNU512GZ** ~477 GB → **C:** (boot/system) |
| Данные | **ADATA LEGEND 960** ~954 GB → **E:** (проекты/VM/модели) |
| Свободно C: / E: | **~61 GB** (87% занято) / **~138 GB** (86% занято) |
| Третий внутренний M.2 | **Нет свободного** — только замена одного из двух |
| Рекомендуемый ход | **C: оставить**, **E: заменить 1 TB → 2 TB** NVMe 2280 (Gen3/Gen4 OK) |

---

## 1. Факт: что стоит сейчас

### 1.1 Шасси / плата

| Параметр | Измерено 2026-09-08 |
|---|---|
| Manufacturer | ASUSTeK COMPUTER INC. |
| Model | `ROG Strix G713IE_G713IE` |
| Baseboard | `G713IE` v1.0 |
| BIOS | AMI `G713IE.329` (2023-03-01) |
| Chassis | Laptop (тип 10) |
| CPU | AMD Ryzen 7 **4800H** (8C/16T) — корневой PCIe **Gen3** |
| GPU | NVIDIA GeForce RTX 3050 Ti Laptop + AMD Radeon Graphics |
| RAM | ~32 GB (см. inventory 2026-09-07) |

### 1.2 Физические диски (NVMe)

| # | Модель | Шина | Ёмкость | Health | Роль | Том |
|---|---|---|---|---|---|---|
| Disk 1 | **INTEL SSDPEKNU512GZ** (OEM, линейка 670p-class, QLC) | NVMe | **~476.9 GB** | Healthy | **Boot + System** | **C:** |
| Disk 0 | **ADATA LEGEND 960** (Phison E18-class, Gen4 SSD) | NVMe | **~953.9 GB** | Healthy | **Данные** | **E:** |

- Firmware: Intel `002C` · ADATA `A232W74H`
- PartitionStyle: оба **GPT**
- MediaType: SSD · SpindleSpeed: 0
- `Get-StorageReliabilityCounter` — **PermissionDenied** (нужен elevated admin); SMART-детали не сняты. HealthStatus Storage API = **Healthy** на обоих.
- PnP: **2** контроллера «Стандартный контроллер NVM Express»  
  - `VEN_8086&DEV_F1AA` → Intel  
  - `VEN_1CC1&DEV_622A` → ADATA  

### 1.3 Разметка и тома

**Disk 1 (Intel 512) — система**

| Part | Тип | Размер | Буква |
|---|---|---|---|
| 1 | EFI System | 100 MB | — |
| 2 | MSR | 16 MB | — |
| 3 | Basic NTFS | ~476 GB | **C:** (IsBoot=True) |
| 4 | Recovery | ~616 MB | — |

**Disk 0 (ADATA 1 TB) — данные**

| Part | Тип | Размер | Буква |
|---|---|---|---|
| 1 | EFI System | 100 MB | — (остаток старой разметки/клона) |
| 2 | MSR | 16 MB | — |
| 3 | Basic NTFS | ~953.8 GB | **E:** |

**Свободное место (live)**

| Том | ФС | Размер | Свободно | Занято % |
|---|---|---|---|---|
| **C:** | NTFS | 476.2 GB | **~61.2 GB** | **~87%** |
| **E:** | NTFS | 953.8 GB | **~137.5 GB** | **~86%** |

Pagefile: `C:\pagefile.sys` (~61 GB allocated) — на C:, не на E:.  
На корне E: видны `hiberfil.sys` / `swapfile.sys` (наследие/артефакты; boot — с Intel/C:).

### 1.4 Что лежит на E: (второй диск = user data)

Снимок крупных каталогов E:\ (рекурсивный size, top):

| Каталог | ~GB | Назначение |
|---|---|---|
| `Linux mint\` | **~516** | VM / shared / NAS_Jetson_Nano дерево |
| `Users\` | **~207** | Профили/данные пользователя (перенос с C:) |
| `ollama_models\` | **~48** | Локальные LLM-веса |
| `LLM_MCP\` | **~39** | LLM/MCP стек |
| `Workspaces\` | **~8** | Рабочие пространства |
| `Belgorod_platform\`, `agent_coordination\`, `amnezia\`, проекты… | <2 each | Dev / соседние репо |

**Вывод:** E: — **не система**, а **data/models/projects/VM**. C: — Windows + pagefile + apps. Апгрейд 2 TB логичен **именно для второго слота (замена ADATA)**.

### 1.5 Внешнее (не для апгрейда M.2)

- В PnP есть **Samsung Portable SSD T5** (Status Unknown на снимке) — внешний USB, не внутренний слот.
- Optical D: — пустой CD/DVD class (DriveType 5).

---

## 2. Слоты / можно ли просто заменить 2-й диск

### 2.1 Сколько M.2 / NVMe

| Проверка | Результат |
|---|---|
| Физических NVMe в OS | **2** |
| NVM Express controllers | **2** |
| Свободный третий NVMe в PnP | **Нет** |
| Типичная схема G713IE (ROG Strix G17, Renoir) | **2× M.2 2280** NVMe (оба заняты) |

**Live-вывод:** оба внутренних NVMe-слота **заняты**. Добавить «просто ещё один 2 TB» **нельзя** без:

- замены одного из существующих дисков, **или**
- внешнего (USB4/TB/enclosure) — медленнее и неудобнее для VM/моделей.

Официальный teardown G17 G713-серии: два M.2 под нижней крышкой (часто с термопрокладками). Точная маркировка «Slot 1 / Slot 2 Gen» в WMI **не** отдаётся; платформа **4800H = PCIe 3.0** → оба слота эффективно **PCIe 3.0 x4** (Gen4 SSD работают с даунгрейдом линка).

### 2.2 Форм-фактор / поколение

| Параметр | Рекомендация под эту машину |
|---|---|
| Form factor | **M.2 2280** (ключ **M**, NVMe) |
| Интерфейс | NVMe PCIe **3.0 x4** минимум; **Gen4 x4** — OK (совместимо, скорость упрётся в Gen3 ~3500 MB/s) |
| Gen5 | Бессмысленно дорого: ноутбук **не** даст Gen5 |
| SATA M.2 | Не брать (другой ключ/режим, хуже) |
| Высота / heatsink | Низкопрофильный; штатные термопрокладки ASUS важны — не ставить огромный «desktop» радиатор без проверки крышки |

### 2.3 Можно ли «просто заменить 2-й диск»

**Да.** Целевой диск для замены: **ADATA LEGEND 960 (E:)** → новый **2 TB**.

| Действие | Intel 512 (C:) | ADATA 1 TB (E:) |
|---|---|---|
| Оставить как system | **Да (рекомендуется)** | — |
| Заменить на 2 TB | Не обязательно сейчас | **Да — основной апгрейд** |
| Клонировать C: на 2 TB | Опционально позже (усложняет boot) | Не цель |

**Не** требуется трогать bootloader/C:, если миграция только E: (copy/clone data volume → letter E:).

Риск: на ADATA есть EFI/MSR-разделы (100+16 MB) — при чистой GPT+один NTFS на новом диске их можно **не** переносить; boot идёт с Intel.

---

## 3. Рекомендации покупки 2 TB (budget / mid / top)

Цены **ориентир РФ, осень 2026**, розница/маркетплейсы; плавают ±15–25%. Поколение: **PCIe 4.0 NVMe 2280** (будет работать как Gen3) или честный **Gen3** если сильно дешевле.

| Tier | SKU-стиль (пример) | Тип | Ожидаемая скорость в G713IE | ~RUB (2026) | Заметки |
|---|---|---|---|---|---|
| **Budget** | Kingston NV2 / NV3 2TB, WD Green SN350 2TB, Team MP44L 2TB | Gen3/entry Gen4, QLC/ TLC budget | ~3000–3500 MB/s seq | **9–13 тыс.** | Дешевле; QLC хуже на долгую запись VM/моделей |
| **Mid (рекомендуемый класс)** | **WD Black SN770 2TB**, Samsung 990 EVO 2TB, Kingston KC3000 2TB, ADATA LEGEND 850/960 2TB | TLC, DRAMless или HMB / хороший контроллер | упрётся в **Gen3 ~3.5 GB/s** | **14–20 тыс.** | Лучший баланс $/надёжность/нагрев в ноутбуке |
| **Top** | Samsung 990 PRO 2TB, WD Black SN850X 2TB, Crucial T700 2TB | Top Gen4 TLC + DRAM | всё равно ~Gen3 ceiling | **22–30+ тыс.** | Переплата за Gen4/PS5-class; в 4800H **нет** выигрыша seq vs mid |

**Совместимость PCIe:** CPU Renoir → **не** гонитесь за Gen5/T700 ради MB/s. Важнее: **TLC**, нормальный TBW (≥1200 TBW на 2TB), умеренный нагрев, гарантия 5 лет.

**DRAM vs DRAMless:** для VM-образов + много мелких файлов проектов предпочтительнее модели с **DRAM** или сильным HMB (SN770/KC3000/990 EVO — приемлемо mid).

---

## 4. План миграции: C 512 system stay, second 2 TB for data

**Цель:** C: без изменений; E: 1 TB → 2 TB с сохранением буквы **E:** и путей (`E:\Linux mint\...`, `E:\Users\...`, `E:\ollama_models\...`).

### 4.1 Подготовка (без wipe)

1. **Backup критичного** на внешний диск (T5/другой): минимум  
   - `E:\Users`  
   - `E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano` (и другие active repos)  
   - `E:\ollama_models`, `E:\LLM_MCP`  
   - список junction/subst/path в IDE  
2. Зафиксировать свободное место: нужно **≥ объёма занятых данных E:** на временном носителе **или** поочерёдный copy (см. ниже). Занято E: ≈ **816 GB** → для полного offline-клона нужен буфер **≥900 GB** free на external **или** clone disk-to-disk в enclosure.
3. Закрыть: VMware/VBox VM на E:, Ollama, Docker/WSL если cache на E:, IDE с workspace на E:.
4. Записать текущие mount paths / services, смотрящие на `E:\`.

### 4.2 Вариант A — **предпочтительный: fresh GPT + robocopy** (не clone partitions)

Подходит, т.к. E: — data, не boot.

1. Выключить ноут, снять низ, **антистатик**, фото термопрокладок.  
2. Извлечь **ADATA LEGEND 960** (второй NVMe; не тот, с которого грузится Windows — Windows на Intel).  
   - Если не уверены какой физический слот: после установки нового можно оставить ADATA во внешнем USB-M.2 box как source.  
3. Установить **новый 2 TB** в тот же слот, термопрокладка.  
4. Загрузка с Intel/C: (должен грузиться как сейчас).  
5. `Disk Management` / PowerShell: инициализация GPT → один NTFS раздел → буква **E:**.  
6. Подключить старый ADATA через **USB M.2 enclosure** (или временно второй слот, если вынимали Intel — **не рекомендуется** трогать system).  
7. Копирование (пример, admin PowerShell):

```powershell
# Source = старый том (например F:), Dest = новый E:
robocopy F:\ E:\ /MIR /COPY:DAT /DCOPY:DAT /R:2 /W:5 /MT:8 /XJ /XD "$RECYCLE.BIN" "System Volume Information" /LOG:C:\Temp\robocopy_E_migrate.log
```

   - Для первого прохода лучше **/E** без /MIR, затем догон.  
   - **Не** копировать `hiberfil.sys` / `pagefile.sys` / `swapfile.sys` со старого корня.  
8. Проверить выборочно размеры top-dirs, git status в ключевых репо, запуск 1 VM.  
9. Переназначить letter если нужно; обновить Ollama model path / env если был hardcode.  
10. 3–7 дней dual-hold старого ADATA как cold backup → затем wipe/перепродать.

**Плюсы:** чистая таблица разделов, полный 2 TB usable, меньше сюрпризов boot.  
**Минусы:** нужно время copy (~816 GB; USB3 enclosure ≈ 1.5–4 ч).

### 4.3 Вариант B — sector clone 1 TB → 2 TB + extend

1. Clone (Macrium Reflect / dd / vendor tool) ADATA → new 2 TB.  
2. Boot C: unchanged; новый диск подхватывает старый layout (~1 TB partition).  
3. Extend NTFS partition до конца диска.  

**Плюсы:** bit-identical, сохраняются ACL/junctions.  
**Минусы:** тащит лишние EFI/MSR/мусор; риск clone tool error; всё равно нужен offline.

### 4.4 Чего **не** делать в миграции

- Не клонировать **C:** на 2 TB «заодно» без отдельного плана BCD (dual complexity).  
- Не форматировать ADATA **до** проверки copy checksum/size.  
- Не `rm -rf` / diskpart clean «на глаз» ночью без backup.  
- Не ставить 2 TB в слот, **вынимая Intel**, если не умеете вернуть boot (BitLocker? keys?).  
- Не включать BitLocker на новом E: пока не закончена верификация (или сразу с recovery key offline).

### 4.5 После миграции — лёгкий уход за C:

C: **~61 GB free** — узкое место останется. Отдельно (не в этом шаге wipe):

- перенос pagefile cap / clean WinSxS / Docker data root на E:  
- не раздувать pagefile без нужды  

Это **не** замена апгрейда E:, а follow-up.

---

## 5. Чего не делать

1. **Не** открывать Amnezia/EU VPS и не путать этот апгрейд с NAS Jetson storage (ADR/AGENTS).  
2. **Не** wipe Docker volumes / VHDX VM на E: «для ускорения copy».  
3. **Не** покупать Gen5 / exotic 22110 / SAS.  
4. **Не** ставить QLC budget 2 TB, если основной workload = **VMware VMDK + ollama gguf** (write amp).  
5. **Не** заполнять новый диск «под завязку» в день миграции — оставить **≥15–20% free** для SSD endurance.  
6. **Не** выкидывать старый ADATA сразу.  
7. **Не** менять оба диска в один день без external golden backup.  
8. **Не** публиковать серийники дисков/платы во внешние LLM/чаты.  
9. **Не** трогать partition table Intel (C:) «заодно».  
10. **Не** считать, что Gen4 2 TB даст 7 GB/s в этом ноутбуке — **не даст**.

---

## 6. Top pick — одна SKU-рекомендация

### Выбор: **WD Black SN770 2 TB** (M.2 2280, PCIe 4.0 x4, TLC)

| Почему | |
|---|---|
| Класс | Mid: TLC, адекватный TBW, часто лучшая цена 2 TB в РФ vs 990 PRO |
| Платформа G713IE | Gen4 → работает на **PCIe 3.0**; seq ~лимит шины, для VM/моделей достаточно |
| Нагрев | DRAMless HMB, в ноутбуке обычно спокойнее «топов» SN850X/990 PRO |
| Задача E: | Замена ADATA LEGEND 960 1 TB → запас ~1 TB free под VM + models + repos |
| Альтернатива 1:1 | Если SN770 нет в наличии: **Kingston KC3000 2TB** или **Samsung 990 EVO 2TB** |
| Budget fallback | Kingston NV2/NV3 2TB — только если бюджет жёсткий и готовность к QLC |
| Top only if | Уже есть купон/почти та же цена на 990 PRO — иначе overpay |

**Ориентир цены SN770 2TB (RU, 2026):** порядка **15–19 тыс. ₽** (проверять М.Видео / DNS / Wildberries / Ozon на день покупки).

**Сопутствующее (опционально):** USB 3.2 M.2 NVMe enclosure (~1.5–3 тыс. ₽) — чтобы старый ADATA стал source/backup без второго вскрытия.

---

## 7. Риски

| Риск | Митигация |
|---|---|
| Перепутать слоты / вынуть system SSD | Маркировать Intel = C: boot; фото до съёма; не вынимать оба сразу |
| Потеря junction/`E:\Users` paths | robocopy с ACL (`/COPY:DAT` + при необходимости `/SEC`); smoke-test login paths |
| VM paths absolute | После copy открыть VMware/VBox и re-register VMs |
| Thermal pad damage | Сфотографировать, не рвать; при необходимости комплект thermal pad 0.5–1 mm |
| C: ENOSPC во время copy | Pagefile на C:; чистить C: **до** тяжёлой миграции; не клонировать на C: |
| SMART не снят | Перед покупкой/после установки — elevated `Get-StorageReliabilityCounter` или CrystalDiskInfo |

---

## 8. Команды проверки (повторный съём)

```powershell
Get-PhysicalDisk | Format-Table FriendlyName, BusType, MediaType, @{N='GB';E={[math]::Round($_.Size/1GB,1)}}, HealthStatus -AutoSize
Get-Disk | Format-Table Number, FriendlyName, BusType, PartitionStyle, @{N='GB';E={[math]::Round($.Size/1GB,1)}}, IsBoot, IsSystem -AutoSize
Get-Volume | Where-Object DriveLetter | Format-Table DriveLetter, FileSystem, @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,1)}} -AutoSize
Get-CimInstance Win32_ComputerSystem | Select Manufacturer, Model, PCSystemType
Get-CimInstance Win32_BaseBoard | Select Manufacturer, Product
Get-CimInstance Win32_SCSIController | Where-Object { $_.Name -match 'NVM' } | Select Name, DeviceID
# elevated:
Get-PhysicalDisk | Get-StorageReliabilityCounter | Format-List
```

---

## 9. Rollback

- Старый ADATA хранить доверия 1–2 недели в enclosure.  
- При проблемах нового диска: вернуть ADATA в слот → буква E: / repair letter → пути на месте.  
- C:/Intel **не** участвует → rollback OS не нужен.

---

## 10. Следующий безопасный шаг

1. Купить **WD Black SN770 2TB** (или KC3000 / 990 EVO 2TB) + при отсутствии — USB M.2 enclosure.  
2. Полный backup top-dirs E: на external.  
3. Один weekend: замена **только** data-NVMe, robocopy, verify, не трогать C:.  
4. Отдельно позже: разгрузить C: (pagefile/Docker) — другой шаг.

---

## 11. Изменённые файлы этого отчёта

- `artifacts/reports/WORKSTATION_STORAGE_UPGRADE_2TB_2026-09-08.md` (**создан**)

Покупки и wipe **не** выполнялись.
