# Immich ML на станции ROG (RTX 3050 Ti) — комплект D4, вариант Б (батч на станции).
#
# ЧТО ЭТО. Три команды одним скриптом: start / stop / status.
#   start  — поднять контейнер immich_ml_rog (docker-compose.immich-ml-rog.yml),
#            дождаться /ping, поднять обратный SSH-туннель до Jetson.
#   stop   — остановить туннель и контейнер.
#   status — контейнер, GPU (nvidia-smi), туннель, проверка с самого Jetson.
#
# ЗАЧЕМ ИМЕННО ТАК.
#
# 1. Порт ML-контейнера биндится на 127.0.0.1 станции (см. compose-файл, аудит
#    CF-4) — наружу в LAN он не виден вовсе. Единственный путь наружу — обратный
#    SSH-туннель, который САМА станция поднимает В СТОРОНУ Jetson (Jetson за
#    двойным NAT и сам не достанет станцию, см. CLAUDE.md/nas-tunnel.ps1).
#
# 2. Проброс обязан быть привязан на стороне Jetson к 172.17.0.1 (docker-мост),
#    а не к 127.0.0.1 — иначе контейнеры Immich его не увидят (другой network
#    namespace). На Jetson для этого уже включён `GatewayPorts clientspecified`.
#    Наружу в домашнюю LAN при этом ничего не открывается — родня grabli
#    "ssh -R не виден из контейнеров, пока GatewayPorts=no".
#
# 3. Туннель запускается через Invoke-CimMethod Win32_Process Create, а не
#    Start-Process/&, потому что процесс, запущенный из сессии агента или
#    интерактивной консоли, её не переживает — грабли CLAUDE.md
#    "Процессы, запущенные из сессии агента, её не переживают". CIM-процесс
#    отсоединён от родителя и продолжает жить после закрытия окна PowerShell.
#
# 4. Файл сохранён в UTF-8 С BOM (обязательно для .ps1 с кириллицей — грабли
#    2026-08-23: без BOM Windows PowerShell 5.1 читает файл как cp1251,
#    кириллица разваливается и скрипт перестаёт парситься целиком, симптом
#    нулевой). Проверка — scripts/quality/check_ps1_bom.py.
#
# ПРЕДУСЛОВИЯ (см. docs/plans/IMMICH_ML_STATION_RUNBOOK.ru.md):
#   - Гипервизор Windows включён (dism VirtualMachinePlatform, bcdedit
#     hypervisorlaunchtype auto) и станция перезагружена.
#   - Docker Desktop запущен, NVIDIA GPU включён в его настройках.
#   - Драйвер NVIDIA ≥ 545 (замер 2026-09: 596.36 — с запасом).
#   - Питание от сети, режим сна выключен на время прогона (иначе туннель и
#     Docker обрываются посреди индексации).
#
# Приватность: превью и эмбеддинги идут ТОЛЬКО внутри SSH-туннеля по домашней
# сети; наружу (WAN) ничего не уходит — ADR-0010, D4 §1.
#
# Ручная проверка одной командой:
#   powershell -ExecutionPolicy Bypass -File immich_ml_station.ps1 -Command status

param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Command = 'status'
)

$ErrorActionPreference = 'Stop'

$Root        = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ComposeDir  = Join-Path $Root "docker\compose"
$ComposeFile = "docker-compose.immich-ml-rog.yml"
$EnvFile     = Join-Path $Root "config\immich-ml-rog.env"
$EnvExample  = Join-Path $Root "config\immich-ml-rog.env.example"

$JetsonHost  = 'admin@192.168.0.50'          # LAN Jetson, ключевой SSH-доступ
$RemoteBind  = '172.17.0.1'                  # docker-мост на Jetson, НЕ 127.0.0.1
$MlPort      = 3003

$PidDir  = Join-Path $env:LOCALAPPDATA 'NAS_Jetson_Nano'
$PidFile = Join-Path $PidDir 'immich_ml_tunnel.pid'

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Ensure-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        Copy-Item $EnvExample $EnvFile
        Write-Host "Скопирован config\immich-ml-rog.env.example -> config\immich-ml-rog.env (правь локально, файл вне git)"
    }
}

function Get-TunnelMarker {
    # По этой подстроке отличаем НАШ туннель от прочих ssh.exe на станции
    # (например, nas-tunnel.ps1 для локальной модели держит порт 11435).
    "${RemoteBind}:${MlPort}:127.0.0.1:${MlPort}"
}

function Find-RunningTunnelProcess {
    $marker = Get-TunnelMarker
    try {
        Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" -ErrorAction Stop |
            Where-Object { $_.CommandLine -and $_.CommandLine.Contains($marker) }
    } catch {
        Write-Warning "Не удалось перечислить процессы ssh.exe: $($_.Exception.Message)"
        $null
    }
}

function Start-Tunnel {
    $existing = Find-RunningTunnelProcess
    if ($existing) {
        $ids = ($existing | ForEach-Object { $_.ProcessId }) -join ', '
        Write-Host "Туннель уже поднят (PID $ids)"
        return
    }

    $marker = Get-TunnelMarker
    $cmdLine = "ssh.exe -N -R $marker " +
               "-o ServerAliveInterval=30 -o ServerAliveCountMax=3 " +
               "-o ExitOnForwardFailure=yes -o BatchMode=yes " +
               "-o StrictHostKeyChecking=accept-new $JetsonHost"

    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdLine }
    if ($result.ReturnValue -ne 0) {
        throw "Win32_Process.Create вернул код $($result.ReturnValue) — туннель НЕ запущен. Проверь ssh.exe в PATH и ключ к $JetsonHost."
    }

    New-Item -ItemType Directory -Force -Path $PidDir | Out-Null
    Set-Content -Path $PidFile -Value $result.ProcessId -Encoding utf8
    Write-Host "Туннель запущен, PID $($result.ProcessId) -> $JetsonHost (удалённый бинд $marker)"
}

function Stop-Tunnel {
    $procs = Find-RunningTunnelProcess
    if (-not $procs) {
        Write-Host "Туннель не запущен"
    } else {
        foreach ($p in $procs) {
            Write-Host "Останавливаю туннель, PID $($p.ProcessId)"
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    if (Test-Path $PidFile) { Remove-Item $PidFile -Force -ErrorAction SilentlyContinue }
}

function Wait-MlPing {
    param([int]$TimeoutSeconds = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest "http://127.0.0.1:$MlPort/ping" -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) { return $true }
        } catch {
            # контейнер ещё грузит модели (start_period 120с в healthcheck) — ждём дальше
        }
        Start-Sleep -Seconds 5
    }
    return $false
}

function Invoke-ComposeCommand {
    param([string[]]$Args)
    Ensure-EnvFile
    Push-Location $ComposeDir
    try {
        & docker compose -f $ComposeFile --env-file $EnvFile @Args
    } finally {
        Pop-Location
    }
}

switch ($Command) {
    'start' {
        Invoke-ComposeCommand -Args @('up', '-d')

        Write-Host "Жду готовности ML-контейнера (http://127.0.0.1:$MlPort/ping)..."
        if (Wait-MlPing) {
            Write-Host "immich-machine-learning отвечает."
        } else {
            Write-Warning "ML-контейнер не ответил на /ping за отведённое время — смотри 'docker compose logs immich-machine-learning'"
        }

        Start-Tunnel

        Write-Section "Дальше"
        Write-Host "На Jetson (один раз за сессию пилота), прописать URL в Immich через API:"
        Write-Host "  bash scripts/immich/set_ml_url.sh http://${RemoteBind}:${MlPort}"
        Write-Host "Подробности и пробный прогон на одном альбоме — docs/plans/IMMICH_ML_STATION_RUNBOOK.ru.md"
    }

    'stop' {
        Stop-Tunnel
        Invoke-ComposeCommand -Args @('down')
    }

    'status' {
        Write-Section "Контейнер"
        Invoke-ComposeCommand -Args @('ps')

        Write-Section "GPU"
        try {
            & nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu --format=csv,noheader
        } catch {
            Write-Warning "nvidia-smi недоступен: $($_.Exception.Message)"
        }

        Write-Section "Туннель (станция -> Jetson)"
        $procs = Find-RunningTunnelProcess
        if ($procs) {
            foreach ($p in $procs) { Write-Host "жив, PID $($p.ProcessId)" }
        } else {
            Write-Host "не запущен"
        }

        Write-Section "Проверка с Jetson (curl -> ${RemoteBind}:${MlPort}/ping)"
        try {
            $out = & ssh -o ConnectTimeout=5 -o BatchMode=yes $JetsonHost "curl -s -m 5 http://${RemoteBind}:${MlPort}/ping" 2>&1
            if ($out) { Write-Host $out } else { Write-Warning "пустой ответ — Jetson недоступен или туннель не поднят" }
        } catch {
            Write-Warning "Не удалось спросить Jetson: $($_.Exception.Message)"
        }
    }
}
