# WORKSTATION INVENTORY — 2026-09-07

> Dev-workstation владельца (Windows). **Не** production NAS-узел (ADR-0007).  
> Источник: live WMI / systeminfo / nvidia-smi / docker / wsl на хосте `ALEXEY3D`.  
> Язык отчёта: RU. Секреты / MAC / IP не для публикации вовне без нужды (ниже — факты для внутреннего использования).

---

## 1. Паспорт машины (таблица факт)

| Параметр | Значение (измерено) |
|---|---|
| **Hostname** | `ALEXEY3D` |
| **Форм-фактор** | Ноутбук (PCSystemType=2 Mobile, ChassisTypes=10) |
| **Модель** | ASUSTeK **ROG Strix G17** `G713IE_G713IE` (board `G713IE`) |
| **BIOS** | AMI `G713IE.329`, 01.03.2023 |
| **CPU** | **AMD Ryzen 7 4800H** (Zen 2 Renoir), **8 cores / 16 threads**, L3=8 MB, WMI MaxClock **2901 MHz** (типичный boost линейки ~4.2 GHz, WMI не отдаёт boost) |
| **iGPU** | AMD Radeon Graphics (Renoir) |
| **dGPU** | **NVIDIA GeForce RTX 3050 Ti Laptop** (DEV_25A0), **4096 MiB** FB, TGP cap ~**72 W** (nvidia-smi Power Cap), Max Power Limit report **95 W** |
| **NVIDIA driver** | **596.36** (DriverDate 23.04.2026), **CUDA runtime 13.2** (`nvidia-smi`); **nvcc / CUDA Toolkit не установлен** |
| **GPU temp idle** | **42 °C**, P8, ~8 W draw, ~9 MiB used |
| **RAM** | **32 GB** (WMI TotalPhysicalMemory ≈ 31.42 GiB usable): **2×16 GB DDR4-3200** Kingston `9905744-108.A00G`, dual-channel, оба слота заняты |
| **RAM slots / max (WMI)** | **2** слота SODIMM; `Win32_PhysicalMemoryArray.MaxCapacity` = **32 GB** (официальный потолок по SMBIOS; 64 GB — не подтверждено без datasheet/ручной проверки) |
| **Диск 0** | **ADATA LEGEND 960** NVMe SSD **~954 GB**, Healthy → том **E:** Used 766 GB / Free **187 GB** |
| **Диск 1** | **INTEL SSDPEKNU512GZ** NVMe SSD **~477 GB**, Healthy → том **C:** Used 408 GB / Free **~69 GB** |
| **Дисплей** | Встроенный **1920×1080** (BOE) + внешний **MSI 2560×1440** |
| **Сеть wired** | Realtek PCIe **GbE** 1 Gbps (Up) |
| **Сеть Wi‑Fi** | MediaTek **Wi‑Fi 6 MT7921**, 802.11ax 5 GHz, RX/TX **1201 Mbps**, signal ~82% |
| **ОС** | **Windows 11 Enterprise** (маркетинг), build **22000.376**, DisplayVersion **21H2** (старый канал 2021), x64, locale ru-RU |
| **Загрузка ОС** | Boot ~18.08.2026; uptime к моменту съёма — длинный сеанс |
| **Батарея** | Li-ion `G513-36`; Design **55 997 mWh**, Full charge **36 641 mWh** → **~65%** от design (**износ ~35%**); charge 100% (на питании). Cycle count в отчёте Windows — «-» |
| **Виртуализация firmware** | Enabled (SLAT, VMX/SVM OK) |
| **Docker Desktop** | Клиент **29.5.3** установлен; **daemon STOPPED** (`com.docker.service` Manual/Stopped; pipe `dockerDesktopLinuxEngine` отсутствует) |
| **WSL** | **WSL2**, default **Ubuntu-22.04**, state **Stopped** |
| **Hyper-V services** | `vmms` Running Automatic, `vmcompute` Running (частичный стек; feature query без elevation → err) |
| **VMware Workstation** | **25.0.0** build-24995812 (службы VMnet/Authd Running) |
| **VirtualBox** | **7.2.4** (`C:\Program Files\Oracle\VirtualBox\`), VBoxSDS Stopped |
| **Python** | **3.11.9** (default `PATH`), также **3.13**, **3.7** |
| **Ollama** | **0.33.2**; модель: `belgorod-intent-qwen3-8b:real-v1-f16` **16 GB** |
| **Node / npm** | v22.17.0 / 10.9.2 |
| **Git / gh** | 2.54.0.windows.1 / gh 2.74.1 |
| **PowerShell** | 5.1.22000 |
| **Pagefile** | `C:\pagefile.sys` Allocated **~52.5 GB**, peak usage ~13.5 GB |
| **RAM pressure (снимок)** | Free **~7 GB** / Used **~78%**; top WS: Memory Compression, gigacode×N, kilo, Code, MsMpEng, browsers |

**Примечание по IP/VPN (внутреннее):** Wi‑Fi LAN + AmneziaVPN/WireGuard + ICS/hotspot-like Realtek 192.168.137.1 + VMware/VBox host-only. Не использовать как 24/7 SoR семьи.

---

## 2. Сильные/слабые стороны для dev + LLM

### Сильные
- **8C/16T Zen 2** — достаточно для параллельной разработки двух проектов (NAS_Jetson_Nano + Belgorod_platform), IDE, git, лёгких контейнеров.
- **32 GB RAM** — минимально приемлемо для dual-IDE + browser + один локальный 7–8B LLM (уже есть Ollama 8B F16).
- **RTX 3050 Ti + свежий драйвер (596 / CUDA 13.2 capability)** — CUDA-инференс мелких моделей, Immich ML «на пробу», кодирование/лёгкий ML.
- **Два NVMe** (0.5 + 1 TB) — можно разнести OS/tools vs data/models/repos (`C:` vs `E:`).
- **Wi‑Fi 6 + 1G Ethernet**, внешний **1440p** — комфортный dev desktop mode.
- Уже стоит стек: **Docker Desktop, WSL2, VMware, VBox, Ollama, Python multi, Node, gh** — не greenfield.
- ROG-шасси с относительно жирным GPU TGP для 3050 Ti laptop class.

### Слабые
- **4 GB VRAM** — жёсткий потолок: комфортно Q4/Q5 **7B–8B**; 13B+ с offload медленно; 30B+/vision-heavy Immich на GPU — плохо.
- **Zen 2 (2020)** vs 2025–26 silicon: IPC/iGPU/NPU нет; энергоэффективность и single-thread слабее Ryzen 7000/AI 300.
- **C: ~69 GB free** при pagefile 50+ GB и Docker/WSL образах — риск «диск забит» и thrashing.
- **RAM 78% занята** в обычной сессии (несколько IDE/агентов) → swap, деградация LLM и Docker.
- **ОС 21H2 / 22000** — сильно отстаёт от актуальных 23H2/24H2; security/WSL/Docker friction.
- **Батарея ~65% health** — роуминг/sleep OK как dev laptop, не как always-on.
- **Три гипервизора сразу** (Hyper-V services + VMware + VBox + Docker/WSL) — конфликт CPU/features, лишняя RAM, сложнее отладка.
- Официально по WMI **max 32 GB RAM** — апгрейд RAM может быть невозможен без замены платформы.

---

## 3. Узкие места (bottlenecks)

| # | Узкое место | Влияние |
|---|---|---|
| 1 | **VRAM 4 GB** | Local LLM >8B, SD/Comfy, тяжёлый Immich ML, multi-model GPU |
| 2 | **Свободная RAM + pagefile на C:** | Dual-project + Ollama 16GB model + browsers → swap, UI freeze |
| 3 | **Свободное место C: ~69 GB** | WSL/Docker/pagefile/Windows Update; риск ENOSPC |
| 4 | **CPU Zen 2 / 45W H-class thermal** | Долгий CPU-LLM и concurrent builds — throttling в корпусе ноутбука |
| 5 | **Docker daemon off + WSL stopped** | «Есть Docker», но не hot-ready; cold start + RAM spike |
| 6 | **Старый Windows build 22000** | Совместимость toolchain, security baseline |
| 7 | **Батарея −35%** | Не держит длинные offline-сессии; не 24/7 |
| 8 | **1G LAN only** | Для NAS bulk sync OK; 2.5G не критично на Wi‑Fi 1.2G |

---

## 4. Модернизация — варианты

Цены — **ориентир ₽, РФ 2026**, вторичка/ритейл; не оферта. Перед покупкой — совместимость G713IE (сервис-мануал ASUS).

| Вариант | Что купить / сделать | Эффект | Сложность | Риск | Ориентир ₽ |
|---|---|---|---|---|---|
| **B0. Hygiene (budget 0)** | Вынести pagefile/модели/кэши на **E:**; закрыть лишние IDE; не держать VMware+VBox+Docker одновременно; `docker`/WSL start only on demand | +RAM, −swap, стабильность | Низкая | Низкий | 0 |
| **B1. Место на C:** | Перенос тяжёлого на E:, очистка WinSxS/Docker unused, symlink models → E: | Снимает ENOSPC | Низкая | Низкий | 0–2 000 |
| **B2. Охлаждение** | Хорошая подставка с вентиляторами, свежая термопаста (если умеете / сервис) | Меньше throttle на LLM/build | Низкая–средняя | Средний (вскрытие) | 2–8 000 |
| **B3. Внешний NVMe 2 TB** | USB4/USB3.2 enclosure + NVMe | Модели/датасеты/бэкапы dev | Низкая | Низкий | 8–18 000 |
| **M1. RAM 2×32 GB DDR4-3200 SODIMM** | **Только если** board/BIOS реально принимают 64 GB (WMI сейчас max 32) | Комфорт dual-agent + 8–13B offload | Средняя | Средний (не заведётся / money loss) | 12–25 000 |
| **M2. Обновление Windows → 23H2/24H2** | In-place или чистая (бэкап!) | Security, WSL/Docker | Средняя | Средний (драйверы ROG) | 0 (+время) |
| **M3. Один гипервизор** | Оставить **WSL2+Docker** *или* VMware; VBox выключить из автозагрузки | −RAM, −конфликты | Низкая | Низкий | 0 |
| **H1. Новый ноутбук mid** | Ryzen 7 8845HS/AI 9 или Intel Ultra + **RTX 4060/4070 8 GB**, 32–64 GB | x2–4 LLM/ML, тише | Высокая (миграция) | Средний | 120–220 000 |
| **H2. Новый ноутбук high** | RTX 4080/5070 Ti laptop 12–16 GB, 64 GB RAM | Серьёзный local LLM/Immich ML lab | Высокая | Средний | 220–350 000+ |
| **H3. Desktop mini/ITX dev box** (отдельно от NAS) | AM5 + 64–96 GB + RTX 4060/4070 **desktop 8–12 GB** | Лучший $/токен, upgrade path | Высокая | Средний (место/шум) | 100–200 000 |
| **H4. Cloud burst** | Аренда GPU (RunPod/Selectel/etc.) для редких тяжёлых job | Без CapEx | Низкая | Данные/секреты | 5–30 000/мес при активном use |

**Нецелесообразно на этой платформе:** eGPU (нет удобного OCuLink/TB GPU-friendly на G713IE в типичной конфигурации), замена пайяной dGPU, превращение ноутбука в 24/7 home server.

---

## 5. Что НЕ делать (anti-patterns)

1. **Не делать из этого ПК production NAS / Immich SoR / family 24/7** — sleep, battery wear, Wi‑Fi roaming, ADR-0007.
2. **Не открывать** Nextcloud/Immich/SSH/LLM gateway с этой машины в интернет без risk-doc (AGENTS.md).
3. **Не гонять** одновременно VMware + VirtualBox + Docker Desktop + тяжёлый Ollama 16GB F16 + 3 IDE — гарантированный swap hell.
4. **Не ставить** локальную LLM «на Jetson Nano Stage 1» сюда же как замену NAS policy — это dev host, не SoR.
5. **Не заливать** личные фото/backup manifests в облачный LLM (AGENTS.md §2.4).
6. **Не форматировать** диски / не чистить Docker volumes production-подобных данных без явного confirm.
7. **Не покупать RAM 64 GB вслепую** — сначала проверка max memory в manual/BIOS/`CPU-Z SPD` community для **G713IE**.
8. **Не stress-test GPU** часами в рюкзаке/на коленях — thermal + battery.
9. **Не держать** pagefile 50 GB на C: при 69 GB free — перенос/уменьшение после снижения RAM pressure.
10. **Не смешивать** Amnezia/семейный VPN experiments с destructive `wg set` на EU VPS (ADR-0003) — к этой машине не относится напрямую, но VPN-клиенты здесь есть.

---

## 6. Рекомендация топ-3 шагов по ROI

| Приоритет | Шаг | Почему ROI высокий |
|---|---|---|
| **1** | **Освободить C: и снизить RAM pressure** (модели/кэши → E:; один IDE-агент; Docker/WSL/VMware не «всегда on»; Ollama model quant Q4/Q5 вместо F16 16 GB если качество ок) | 0 ₽, сразу snappier dev + LLM |
| **2** | **Политика одного виртуализатора** + Docker start script only when needed | Меньше конфликтов Hyper-V/VMware, +4–8 GB RAM |
| **3** | **План платформы 2026 H2:** либо подтверждённый **RAM 64 GB** (если board allows), либо **копить на mid-laptop/desktop с 8+ GB VRAM** — 4 GB VRAM не лечится софтом | Единственный реальный unlock для LLM 13B+ / Immich ML |

**Для текущих задач NAS_Jetson_Nano + Belgorod:** машина **пригодна как dev workstation** (SSH/docs/compose/gh/агенты).  
**Local LLM:** OK для **7–8B** (уже используется); не рассчитывать на heavy Immich ML или multi-agent GPU.  
**Docker:** готов после старта Desktop/WSL; держать stopped по умолчанию из‑за RAM.

---

## 7. Commands used (for reproducibility)

```powershell
systeminfo

Get-CimInstance Win32_Processor | Format-List Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, L2CacheSize, L3CacheSize
Get-CimInstance Win32_ComputerSystem | Format-List Manufacturer, Model, TotalPhysicalMemory, PCSystemType, HypervisorPresent
Get-CimInstance Win32_BaseBoard | Format-List Manufacturer, Product, Version
Get-CimInstance Win32_BIOS | Format-List SMBIOSBIOSVersion, ReleaseDate
Get-CimInstance Win32_PhysicalMemory | Format-Table BankLabel, DeviceLocator, Capacity, Speed, ConfiguredClockSpeed, Manufacturer, PartNumber
Get-CimInstance Win32_PhysicalMemoryArray | Format-List MemoryDevices, MaxCapacity

Get-CimInstance Win32_VideoController | Format-List Name, AdapterRAM, DriverVersion, DriverDate
nvidia-smi
nvidia-smi -q   # filter Product/CUDA/Memory/Temp/Power

Get-PhysicalDisk | Format-Table FriendlyName, MediaType, BusType, Size, HealthStatus
Get-Disk | Format-Table Number, FriendlyName, Size, PartitionStyle, BusType
Get-PSDrive -PSProvider FileSystem
Get-Volume | Where-Object DriveLetter

Get-NetAdapter | Format-Table Name, InterfaceDescription, Status, LinkSpeed
netsh wlan show interfaces

Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, WindowsBuildLabEx, OsArchitecture, CsModel, CsPCSystemType
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Select-Object ProductName, DisplayVersion, CurrentBuild, UBR
Get-CimInstance Win32_Battery
powercfg /batteryreport /output "$env:TEMP\battery-report.html"

docker version
Get-Service com.docker.service, LxssManager, vmcompute, vmms
wsl --status
wsl -l -v
Get-ItemProperty HKLM:\SOFTWARE\Oracle\VirtualBox
Get-ItemProperty 'HKLM:\SOFTWARE\VMware, Inc.\VMware Workstation'

python --version; py -0p
ollama --version; ollama list
node --version; npm --version; git --version; gh --version
nvcc --version   # not found

Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory, TotalVirtualMemorySize, FreeVirtualMemory
Get-CimInstance Win32_PageFileUsage
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 12
Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens
Get-CimInstance WmiMonitorBasicDisplayParams -Namespace root\wmi
```

**Не выполнялось:** установка ПО, правки BIOS, stress-test GPU, destructive disk ops, изменения NAS production.

---

## Краткие выводы

| Вопрос | Ответ |
|---|---|
| Что это? | ASUS ROG Strix G17 (G713IE), Ryzen 7 4800H, 32 GB, RTX 3050 Ti 4 GB, 512 GB + 1 TB NVMe, Win11 Ent 21H2 |
| Dev dual-project? | **Да**, при дисциплине RAM/диска |
| Local LLM / Ollama? | **Да, 7–8B**; 4 GB VRAM + RAM pressure — потолок |
| Immich ML? | Только лёгкие/пробные нагрузки |
| Docker? | Установлен, **сейчас off**; WSL2 Ubuntu ready |
| 24/7 NAS? | **Нет** (антипаттерн) |
| Лучший ROI | Hygiene C:/RAM → один гипервизор → план GPU 8 GB+ (новая платформа) |

---

*Отчёт сгенерирован 2026-09-07. Путь: `artifacts/reports/WORKSTATION_INVENTORY_2026-09-07.md`.*
