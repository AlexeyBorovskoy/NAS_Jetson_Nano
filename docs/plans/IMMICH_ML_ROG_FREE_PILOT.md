# Free pilot: Immich ML on ROG RTX (home LAN)

> 🇷🇺 Бесплатный пилот: `immich-machine-learning` на ASUS ROG (RTX) в домашней LAN.  
> 🇬🇧 Free pilot: Immich ML worker on ROG laptop, same `192.168.0.0/24` as Jetson `.50`.

**Status:** ⛔ **blocked on host 2026-09-12** — Docker Desktop не стартует: `Virtualization
support not detected`. Not 24/7 prod.  
**Cost:** $0 cloud (electricity only).  
**Related:** ADR-0010 (Cloud.ru path remains the paid/prod option).

---

## Статус на 2026-09-12 / Status as of 2026-09-12

🇷🇺 **Сделано:** образ привязан к версии сервера (**Immich 2.7.5** на Jetson, значит
ML-образ `…:v2.7.5-cuda`); создан `config/immich-ml-rog.env` (вне git, правило
`config/*.env` добавлено в `.gitignore`); порт **привязан к `127.0.0.1`**, а не к LAN.

🔴 **Блокер:** на станции **выключен гипервизор Windows**. Замер: `HypervisorPresent
= False` при `VirtualizationFirmwareEnabled = True` и поддержке SLAT, то есть железо и
BIOS готовы, не запущен сам гипервизор. Служба `com.docker.service` была остановлена
(запущена владельцем), но без гипервизора движок не поднимается. Лечение требует прав
администратора **и перезагрузки станции**:

```powershell
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
bcdedit /set hypervisorlaunchtype auto
# затем перезагрузка / then reboot
```

⚠️ На станции стоит **VMware Workstation 25** (виртуалок запущено 0). Версия официально
работает поверх гипервизора, но машины станут немного медленнее. Откат:
`bcdedit /set hypervisorlaunchtype off` + перезагрузка. Решение отложено владельцем.

🔴 **Схема связи изменилась против исходного runbook.** Раздел A предполагает, что ROG
и Jetson в одной подсети `192.168.0.0/24`. **Это больше не так:** станция живёт за Deco
в `192.168.68.0/22`, и Jetson её не достаёт — ping с Jetson даёт **100 % потерь**
(замер 2026-09-12). Рабочий путь — **обратный туннель со станции**, как уже сделано для
локальной языковой модели: на Jetson включён `GatewayPorts clientspecified`, поэтому
проброс нужно привязывать к `172.17.0.1`, иначе контейнеры его не увидят.

```powershell
# со станции, после запуска ML-контейнера
ssh -N -R 172.17.0.1:3003:127.0.0.1:3003 admin@192.168.0.50
# на Jetson: IMMICH_MACHINE_LEARNING_URL=http://172.17.0.1:3003
```

⚠️ На устройстве `docker-compose.immich.yml` **старее git** — переменной
`IMMICH_MACHINE_LEARNING_URL` в нём ещё нет, только `IMMICH_DISABLE_MACHINE_LEARNING`.
Правка compose на Jetson — это **деплой**, и делается только по слову владельца.

🇬🇧 **Done:** image pinned to the server version (Immich 2.7.5 → `…:v2.7.5-cuda`), local
env created outside git, ML port bound to `127.0.0.1` instead of the LAN.
**Blocked:** the Windows hypervisor is off on the station (`HypervisorPresent = False`
while firmware virtualization is enabled); enabling it needs admin rights and a reboot,
and VMware Workstation 25 is installed alongside. **Topology changed:** the station is
behind the Deco in another subnet and the Jetson cannot reach it (100 % packet loss), so
the pilot must use a reverse SSH tunnel bound to `172.17.0.1`, not a LAN URL.

## What / Что

| Host | Role |
|------|------|
| Jetson `192.168.0.50` | Immich server + microservices (no local ML) |
| ROG (home LAN) | Official Immich ML CUDA image on `:3003` |

Jetson points to ROG via `IMMICH_MACHINE_LEARNING_URL`. Photos stay on LAN.

## Files / Файлы

| Path | Purpose |
|------|---------|
| `docker/compose/docker-compose.immich-ml-rog.yml` | ML worker compose (GPU) |
| `config/immich-ml-rog.env.example` | ROG env template → copy to `immich-ml-rog.env` |
| `scripts/immich/start_ml_worker_rog.ps1` | Start + print LAN URLs |
| `scripts/immich/stop_ml_worker_rog.ps1` | Stop worker |
| `docker/compose/docker-compose.immich.yml` | `IMMICH_MACHINE_LEARNING_URL` on server + microservices |
| `config/.env.example` | commented pilot flags |

## Security / Безопасность

- Port **3003** only from **`192.168.0.0/24`** — never WAN forward, never VPS reverse for ML.
- Do not expose Immich/ML to the internet (AGENTS.md / ADR-0003).
- Stop worker when pilot ends (`stop_ml_worker_rog.ps1`).

## Runbook / Чеклист

### A. ROG (home Wi‑Fi/LAN, same subnet as Jetson)

1. Docker Desktop with NVIDIA GPU enabled.
2. Firewall (Admin PowerShell):

```powershell
New-NetFirewallRule -DisplayName "Immich ML ROG LAN" -Direction Inbound -Protocol TCP -LocalPort 3003 -RemoteAddress 192.168.0.0/24 -Action Allow
```

3. Sleep: Never on AC while jobs run.
4. Prefer pin `IMMICH_VERSION` to Jetson image tag (`docker inspect homecloud_immich_server --format '{{.Config.Image}}'`).
5. Start:

```powershell
cd "E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano"
.\scripts\immich\start_ml_worker_rog.ps1
# note printed http://192.168.0.x:3003
```

Manual equivalent:

```powershell
cd "E:\Linux mint\virtual_VM\shared\NAS_Jetson_Nano\docker\compose"
docker compose -f docker-compose.immich-ml-rog.yml --env-file ..\..\config\immich-ml-rog.env up -d
curl http://127.0.0.1:3003/ping
```

### B. Jetson

```bash
docker inspect homecloud_immich_server --format '{{.Config.Image}}'

# edit ~/nasa/config/.env (device only, not git):
# IMMICH_DISABLE_MACHINE_LEARNING=false
# IMMICH_MACHINE_LEARNING_URL=http://192.168.0.XX:3003

cd ~/nasa
docker compose -f docker/compose/docker-compose.immich.yml --env-file config/.env up -d

curl -sS http://192.168.0.XX:3003/ping
```

### C. Immich UI

Administration → Jobs → Face Detection / Smart Search on **one album** first.

### D. Morning / end of pilot

```powershell
.\scripts\immich\stop_ml_worker_rog.ps1
```

Optional Jetson: set `IMMICH_DISABLE_MACHINE_LEARNING=true` again if laptop is away long.

## Success criteria

- [ ] Jetson curls ROG `:3003` (`/ping`)
- [ ] Faces on test album
- [ ] Smart search works
- [ ] $0 cloud bill for this path

## Rollback

1. ROG: `stop_ml_worker_rog.ps1`
2. Jetson `.env`: `IMMICH_DISABLE_MACHINE_LEARNING=true`, clear `IMMICH_MACHINE_LEARNING_URL`
3. `docker compose ... up -d` Immich stack

## Risks

| Risk | Mitigation |
|------|------------|
| Laptop sleep / Wi‑Fi drop | AC power, sleep off; wired if possible |
| Version skew ML vs server | Pin same Immich release tag |
| CUDA image fail on ROG | Fall back to CPU image in `immich-ml-rog.env` |
| Accidental WAN open | Firewall remote `192.168.0.0/24` only |

## Next safe step

Home LAN pilot one album → measure time/quality → decide Cloud.ru (ADR-0010) vs occasional ROG batches.
