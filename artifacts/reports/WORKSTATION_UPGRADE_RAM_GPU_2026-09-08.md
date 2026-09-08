# Отчёт: апгрейд рабочей станции ASUS ROG Strix G17 (G713IE)

**Дата:** 2026-09-08  
**Модель (live):** `ROG Strix G713IE_G713IE` / baseboard `G713IE`  
**Шасси:** laptop (`ChassisTypes=10`, `PCSystemType=2`)  
**Покупки не выполнялись** — только анализ feasibility / ROI.

---

## 1. Live-инвентаризация (этот ПК)

### 1.1 RAM

| Параметр | Значение |
|----------|----------|
| Установлено | **2×16 GB = 32 GB** DDR4-3200 |
| Производитель / P/N | Kingston `9905744-108.A00G` |
| Слоты | DIMM 0 CHANNEL A + DIMM 0 CHANNEL B (2 канала) |
| FormFactor | 12 (SO-DIMM) |
| `Win32_PhysicalMemoryArray.MaxCapacity` | **33554432 KB = 32 GB** |
| `MemoryDevices` | **2** |
| OS TotalPhysicalMemory | ~31.4 GB usable |

**Вывод:** оба SO-DIMM заняты, firmware/SMBIOS заявляет потолок **32 GB**. Официальный max ASUS для G713 (2021) — **Max Capacity: 32GB** (2× DDR4-3200 SO-DIMM). Конфиг **2×32 GB (64 GB) официально не поддерживается** и по live MaxCapacity = N/A.

### 1.2 CPU

| Параметр | Значение |
|----------|----------|
| CPU | AMD Ryzen 7 4800H (8C/16T, boost до ~4.2 GHz) |
| Socket | **FP6** (BGA) |
| iGPU | AMD Radeon Graphics |

**Вывод:** CPU **припаян (soldered)**, замена невозможна без смены материнской платы / ноутбука.

### 1.3 GPU

| Параметр | Значение |
|----------|----------|
| dGPU | **NVIDIA GeForce RTX 3050 Ti Laptop GPU** |
| VRAM | **4096 MiB (4 GB)** GDDR6 |
| TGP (live / SM) | cap ~70 W (nvidia-smi); официально ROG Boost ~80 W (+Dynamic Boost до ~95 W) |
| Driver / CUDA | 596.36 / CUDA 13.2 |
| iGPU | AMD Radeon Graphics (Optimus) |

**Вывод:** dGPU на ROG Strix G17 2021 — **MXM/модуль не предусмотрен, GPU soldered** на MB. Замена «на более мощную карту» в сервисе = замена всей платы (нецелесообразно).

### 1.4 Накопители

| Диск | Ёмкость | Примечание |
|------|---------|------------|
| ADATA LEGEND 960 | ~1 TB NVMe | основной data (E:) |
| INTEL SSDPEKNU512GZ | ~512 GB NVMe | система (C:) |

**Свободное место (live):**

| Том | Размер | Свободно | % free |
|-----|--------|----------|--------|
| **C:** | 476 GB | **54.8 GB** | **11.5%** |
| **E:** | 954 GB | 121 GB | 12.7% |

Официально: **2× M.2 PCIe** — второй слот уже занят; апгрейд 2 TB возможен как замена одного из SSD (не «добавить третий»).

### 1.5 Батарея

| Параметр | Значение |
|----------|----------|
| Имя | `G513-36` |
| Status | OK, ~100% charge remaining |
| FullChargedCapacity (WMI) | **36641 mWh ≈ 36.6 Wh** |
| Официальный design (G713IE-класc) | обычно **56 Wh** 4S1P |
| Оценка health | ~**65%** design (если design=56 Wh; DesignedCapacity в WMI пустой) |
| Voltage | ~16.4 V |

### 1.6 Порты (eGPU / внешний GPU)

По официальным I/O G713 2021:

- 3× USB-A 3.2 Gen1  
- 1× **USB-C 3.2 Gen2** (DP / PD / G-SYNC) — **не Thunderbolt, не USB4**  
- HDMI 2.0b, RJ45  

**Thunderbolt / USB4 отсутствует** → классический eGPU (TB3/TB4 enclosure) **не поддерживается**. OCuLink/USB4 eGPU — N/A на этом шасси.

---

## 2. Feasibility (ответы на ключевые вопросы)

| # | Вопрос | Ответ |
|---|--------|--------|
| 1 | Можно ли заменить dGPU? | **Нет** (soldered). Сервисная «замена GPU» = MB swap, риск/цена ≈ новый ноут. |
| 2 | RAM выше 32 GB? | **Официально нет.** Live MaxCapacity=32 GB, ASUS Max=32 GB, 2 слота уже 2×16. **2×32 = N/A** (не рекомендуется; BIOS/IMC Ryzen 4000 теоретически 64, но ASUS/SMBIOS лимит и гарантия — 32). |
| 3 | CPU soldered? | **Да**, FP6 BGA. |
| 4 | Батарея — стоимость | Оригинал/совместимая A41N2103 / G513-класс: ориентир **6–15 тыс ₽** деталь + **3–8 тыс ₽** работа (РФ 2026, грубо). Итого **~9–25 тыс ₽**. |
| 5 | Cooling pad / repaste ROI | Pad: −2…8 °C, мало FPS; repaste+clean: −5…15 °C, меньше throttling на 4800H/3050 Ti. ROI средний при длительных нагрузках; не лечит 4 GB VRAM. |

Источники: live CIM/`nvidia-smi`; [ROG Strix G17 2021 Tech Specs](https://rog.asus.com/laptops/rog-strix/2021-rog-strix-g17-series/spec/) (Memory Max 32GB, 2× SO-DIMM, 2× M.2, USB-C без TB).

---

## 3. Сводная таблица опций

| option | possible? | effect | cost RUB rough | ROI 1–10 | recommendation |
|--------|-----------|--------|----------------|----------|----------------|
| **RAM 2×32 GB (64 GB)** | **N/A** (офиц. max 32; live MaxCapacity=32; слоты заняты 2×16) | нет гарантированного эффекта; риск нестабильности | 12–25k (зря) | **1** | **Не делать** |
| **RAM уже 32/32** | уже max | dual-channel OK | 0 | — | Держать; при сбое — заменить на 2×16 JEDEC 3200 |
| **Замена dGPU (внутри)** | **Нет** (soldered) | — | 40–80k+ MB | **1** | **Не делать** |
| **Новый ноут ≥8 GB VRAM** | Да (покупка) | +VRAM/CUDA, новый CPU/дисплей | 120–250k+ | **4** | Только если локальный ML/игры — must; иначе отложить |
| **eGPU (USB4/TB)** | **Нет** (нет TB/USB4) | — | 50–150k | **1** | **Невозможно** на G713IE |
| **Cloud GPU / Cloud.ru FM** | **Да** (уже есть доступ) | тяжёлый inference/train без VRAM-лимита 4 GB | pay-as-you-go / уже оплаченные квоты | **9** | **Приоритет #1** для GPU-задач |
| **Гигиена C:/RAM (free)** | **Да** | C: 11.5% free → pagefile/temp thrash; чистка даёт snappiness | **0** | **10** | **Сделать сейчас** |
| **Батарея (замена)** | Да | autonomy; health ~65% | 9–25k | **5** | Когда autonomy критична; не ускоряет GPU |
| **SSD 2 TB** (замена одного M.2) | Да (2 слота заняты → replace) | место под datasets/VM; не +VRAM | 8–18k (2TB NVMe) | **7** | Когда E:/C: упрутся; C: сначала почистить |
| **Repaste + чистка СО** | Да | меньше throttle, quieter | 0–5k DIY / 5–12k сервис | **6** | Если thrash/шум; ROI > pad |
| **Cooling pad** | Да | −несколько °C | 2–6k | **3** | Опционально; слабый ROI |
| **Внешний NVMe/HDD dock** | Да (USB) | архив без вскрытия | 3–10k | **6** | Альтернатива срочному 2TB internal |

---

## 4. Top-3 по ROI

1. **Гигиена C: и RAM (score 10)** — 54.8 GB free на системном томе (11.5%). Windows + pagefile + Docker/conda/temp на полном C: дают swap и лаги **бесплатно исправляемые**. Действия: Storage Sense, очистка `%TEMP%`, WinSxS/Delivery Optimization, перенос тяжёлых кэшей (HuggingFace, pip, Docker data-root, conda pkgs) на **E:**, отключение лишнего автозапуска. Не покупка.
2. **Cloud GPU / Cloud.ru Foundation Models (score 9)** — локально **4 GB VRAM** — жёсткий потолок для LLM/vision. Облако уже в экосистеме проекта (Sber/Cloud.ru) → максимальный эффект на $/час без железа.
3. **SSD 2 TB при нехватке места / после гигиены (score 7)** — или external dock; не путать с «апгрейдом GPU». Repaste (6) — рядом, если термотrottling доказан (HWInfo/GPU-Z).

**Не в топе:** 64 GB RAM, внутренняя замена GPU, eGPU, cooling pad как «апгрейд производительности».

---

## 5. Ограничения платформы (кратко)

```text
G713IE 2021 = «запечатанный» compute-узел:
  CPU  soldered FP6
  GPU  soldered RTX 3050 Ti 4GB
  RAM  max 32 GB (уже установлено)
  I/O  no TB / no USB4 → no eGPU
  M.2  2 слота (оба заняты: 512G + 1T)
```

Единственные реальные hardware-рычаги: **накопители**, **батарея**, **термопаста/пыль**. Производительность GPU/ML — **облако или новый ПК**.

---

## 6. Риски

- Попытка 2×32 GB: нестабильность POST/BSOD, отказ гарантии (если ещё есть), wasted money.
- BGA reball/GPU swap: brick + дороже нового ноута mid-range.
- Полный C: → скрытая деградация (не «слабый CPU»).
- Замена батареи неоригиналом: разъём/BMS/вздутие — только проверенный P/N.
- Cloud: не слать персональные фото/backup-манифесты во внешний LLM (правила AGENTS.md).

---

## 7. Rollback / без покупок

- Гигиена: только удаление кэшей/temp; перед массовым delete — backup списка путей.
- Hardware не трогали в рамках отчёта.

---

## 8. Следующий безопасный шаг

1. Освободить **≥20–25%** на C: (цель ≥100 GB free).  
2. Тяжёлый ML/inference — **Cloud.ru / уже имеющийся FM gateway**, не 4 GB local.  
3. 2 TB SSD — только после аудита занятости E:/C:; батарея — по факту autonomy.  
4. Новый ноут 8GB+ VRAM — отдельное решение бюджета, не «апгрейд G713».

---

## 9. Команды проверки (повтор)

```powershell
Get-CimInstance Win32_PhysicalMemory | ft Capacity,Speed,Manufacturer,PartNumber
Get-CimInstance Win32_PhysicalMemoryArray | ft MaxCapacity,MemoryDevices
Get-CimInstance Win32_ComputerSystem | ft Model,PCSystemType,TotalPhysicalMemory
Get-CimInstance Win32_SystemEnclosure | select ChassisTypes
nvidia-smi
Get-Volume C,E | ft DriveLetter,@{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,1)}}
Get-CimInstance -Namespace root\wmi BatteryFullChargedCapacity
```

---

*Отчёт сгенерирован агентом по live WMI/CIM + nvidia-smi + официальным tech specs ROG Strix G17 2021. Цены RUB — грубый market range 2026, не оферта.*
