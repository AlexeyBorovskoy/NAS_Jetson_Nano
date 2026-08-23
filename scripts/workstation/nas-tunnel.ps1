# Обратный туннель со станции на Jetson: локальная модель и (позже) Immich ML.
#
# ЗАЧЕМ ИМЕННО ТАК. Станция кочует между домашней и корпоративной сетью и
# выключается, а Jetson за двойным NAT сам инициировать соединение не может.
# Значит связь всегда поднимает станция, и путь выбирается по тому, где она:
#
#   дома      -> напрямую по LAN до 192.168.0.50   (быстро, из дома не выходит)
#   на работе -> через VPS: ProxyJump на порт 10022 (медленно, но работает)
#   выключена -> ничего; очередь на Jetson просто ждёт
#
# Привязка ОБЯЗАТЕЛЬНО к 172.17.0.1 — это адрес docker-моста на Jetson.
# Контейнеры видят хост именно так; порт, привязанный к 127.0.0.1, для них
# недоступен (другой сетевой namespace). На Jetson для этого включено
# `GatewayPorts clientspecified`; наружу в LAN ничего не открывается.
#
# Проверить вручную:  powershell -ExecutionPolicy Bypass -File nas-tunnel.ps1 -Once
# Остановить службу:  Unregister-ScheduledTask -TaskName 'NAS-Tunnel'

param(
    [switch]$Once,                       # один прогон, без бесконечного цикла
    [int]$RetrySeconds = 30
)

$ErrorActionPreference = 'Continue'

$JetsonLan   = '192.168.0.50'
$JetsonUser  = 'admin'
$VpsHost     = '95.163.176.103'
$VpsUser     = 'root'
$VpsKey      = "$env:USERPROFILE\.ssh\borovskoy_new_ed25519"
$VpsSshPort  = 10022                     # обратный туннель Jetson, слушает loopback VPS

# Что пробрасываем: Ollama на станции -> docker-мост Jetson
$RemoteBind  = '172.17.0.1'
$RemotePort  = 11435
$LocalPort   = 11434

function Test-Jetson-Lan {
    try {
        $t = Test-NetConnection -ComputerName $JetsonLan -Port 22 -WarningAction SilentlyContinue
        return $t.TcpTestSucceeded
    } catch { return $false }
}

function Start-Tunnel {
    $fwd = "${RemoteBind}:${RemotePort}:127.0.0.1:${LocalPort}"

    if (Test-Jetson-Lan) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] дома: прямой путь по LAN"
        & ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 `
              -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new `
              -o BatchMode=yes `
              -R $fwd "$JetsonUser@$JetsonLan"
    }
    elseif (Test-Path $VpsKey) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] не дома: путь через VPS"
        $proxy = "ssh -i `"$VpsKey`" -W %h:%p $VpsUser@$VpsHost"
        & ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 `
              -o ServerAliveCountMax=3 -o StrictHostKeyChecking=accept-new `
              -o BatchMode=yes `
              -o "ProxyCommand=$proxy" -p $VpsSshPort `
              -R $fwd "$JetsonUser@127.0.0.1"
    }
    else {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] нет ни LAN, ни ключа к VPS — пропускаю"
        return $false
    }
    return $true
}

if ($Once) {
    Start-Tunnel | Out-Null
    exit 0
}

Write-Host "Туннель до Jetson: слежу и переподключаюсь. Ctrl+C для остановки."
while ($true) {
    Start-Tunnel | Out-Null
    Write-Host "[$(Get-Date -Format HH:mm:ss)] соединение закрылось, повтор через $RetrySeconds c"
    Start-Sleep -Seconds $RetrySeconds
}
