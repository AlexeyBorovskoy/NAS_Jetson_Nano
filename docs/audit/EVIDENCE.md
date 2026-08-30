# Доказательства / Evidence

**Дата / Date:** 2026-08-30. Куратированная выборка наиболее значимых находок (не весь сырой вывод команд) / Curated set of the most significant findings (not the raw command dump).

---

**Evidence ID: EV-001**
Command: `cat /etc/nv_tegra_release; cat /proc/device-tree/model`
Result: `R32 (release), REVISION: 7.1` → L4T R32.7.1 / JetPack 4.6.1; `NVIDIA Jetson Nano Developer Kit`
Interpretation: Платформенный потолок подтверждён — новее JetPack на этой плате не ставится (JetPack 5+/6 требуют Xavier/Orin).

---

**Evidence ID: EV-002**
Command: `tegrastats` (15 замеров за 15с)
Result: `GR3D_FREQ 0%` на всех 15 точках
Interpretation: GPU физически простаивает всё время наблюдения — подтверждает вывод из `grep -rn "runtime: nvidia"` по всем 8 compose-файлам (ноль совпадений): ни один сервис проекта не использует GPU.

---

**Evidence ID: EV-003**
Command: `docker ps -a` + `docker inspect --format '{{.RestartCount}} {{.State.OOMKilled}}'` (цикл по 13 контейнерам)
Result: 13 контейнеров `Up`, `RestartCount=0`, `OOMKilled=false` у всех; 12/13 `healthy`, `homecloud_portainer` — без healthcheck
Interpretation: Система стабильна на момент замера, нет истории аварийных перезапусков. Portainer — единственное исключение из паттерна healthcheck, не критично (UI-инструмент, не сервис с прямой зависимостью других компонентов).

---

**Evidence ID: EV-004**
Command: `git status --short` на устройстве (`~/nasa`)
Result: 33 строки (13 `M`, 20 `??` — `.bak.*`)
Interpretation: Уточняет цифру из CLAUDE.md («более 10 файлов») — точное число на 2026-08-30 составляет 33 строки git status, из них 13 реально изменённых файлов.

---

**Evidence ID: EV-005**
Command: `grep -rn "IMMICH_DISABLE_MACHINE_LEARNING" docker/compose/docker-compose.immich.yml`
Result: `IMMICH_DISABLE_MACHINE_LEARNING: ${IMMICH_DISABLE_MACHINE_LEARNING:-true}` (строки 61, 92); контейнера `immich-machine-learning` нет в `docker ps`
Interpretation: ML внутри Immich осознанно выключен на Jetson — согласуется с 4 ГБ RAM и простаивающим GPU (EV-002).

---

**Evidence ID: EV-006**
Command: `docker images | grep coturn` + `docker ps -a | grep coturn` (на VPS)
Result: пусто в обоих случаях
Interpretation: `docker-compose.coturn.yml` в репозитории описывает план, который никогда не был исполнен на целевом хосте — Talk-видеозвонки вне LAN, вероятно, не проходят TURN-релей (гипотеза, не подтверждена живым звонком — см. UNKNOWNS.md U-11).

---

**Evidence ID: EV-007**
Command: `cat services/nas_jetson_nano-api/app/main.py` (строки 171-176)
Result: `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])`
Interpretation: Полностью открытый CORS на API-порту 8099 — принято как находка MEDIUM (эксплуатируемость снижена LAN-only периметром, но нарушает принцип наименьших привилегий).

---

**Evidence ID: EV-008**
Command: `ls -la ~/nasa/config/*.bak.*`
Result: 10 файлов, от `.env.bak.20260531-125535` до `.env.bak.talktimeout.20260824`, все права `600`
Interpretation: Организационно корректно (закрытые права), но без политики удаления старых версий — растущее число копий секретов на одном диске.

---

**Evidence ID: EV-009**
Command: `bash scripts/security/check_no_secrets.sh`
Result: `No obvious secrets found outside allowed files.`
Interpretation: Чисто после собственного фикса ложного срабатывания в этом же заходе (коммит `7707d0e`) — до фикса скрипт ложно блокировал каждый коммит на строке `RESTIC_PASSWORD_FILE=/root/...` (путь, не значение).

---

**Evidence ID: EV-010**
Command: `du -xhd1 /mnt/storage` / `timeout 90 du -hd1 /mnt/hdd2tb`
Result: `/mnt/storage/immich` = 12G из 13G занятых; `/mnt/hdd2tb/$RECYCLE.BIN` = 27G (частичный обход, не завершён)
Interpretation: Immich — основной потребитель SSD (ожидаемо). Корзина Windows на архивном HDD — вероятный кандидат на очистку, не измерена целиком из-за медленного NTFS-3g/FUSE на 1.4 ТБ.

---

**Evidence ID: EV-011**
Command: `grep -rn "requirements.txt"` + чтение содержимого 3 файлов requirements
Result: `llm-gateway`/`backup-api` — `fastapi==0.115.12` (pinned); `nas_jetson_nano-api` — `fastapi>=0.111` (не pinned)
Interpretation: Несогласованная политика закрепления зависимостей внутри одного проекта — единственный непиннингованный сервис несёт auth-логику (JWT).

---

**Evidence ID: EV-012**
Command: `cat /etc/os-release` (устройство) + `python3 --version`
Result: Ubuntu 18.04.6 LTS; Python 3.6.9
Interpretation: Оба — EOL upstream (Ubuntu 18.04 с 04/2023, Python 3.6 с 12/2021). ESM-статус Ubuntu не подтверждён (см. UNKNOWNS.md U-06) — определяет, реален ли риск непропатченных уязвимостей.

---

**Evidence ID: EV-013**
Command: `cat services/nas_jetson_nano-api/app/config.py` (строка 47) + `ls /usr/local/sbin/*.sh` на устройстве
Result: default `report_cmd` = `/usr/local/sbin/nas_jetson_nano-send-report-telegram.sh`; реально существует `nasa-send-report-telegram.sh`
Interpretation: Прямое следствие незавершённого переименования — наивный деплой сломал бы `/v1/report/now` и `/v1/actions/backup/now`. Учтено в runbook миграции (`docs/plans/tranquil-wandering-truffle.md`).

---

**Evidence ID: EV-014**
Command: `docker inspect` (Netdata, Portainer, nasa-api) — поле `Mounts`
Result: 3 контейнера монтируют `/var/run/docker.sock` с флагом `:ro`
Interpretation: Read-only снижает, но не устраняет риск — доступ к Docker API раскрывает список контейнеров и их окружение любому, кто скомпрометирует один из этих трёх контейнеров. Принятый, а не устранённый риск.
