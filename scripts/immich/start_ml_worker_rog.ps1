$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ComposeDir = Join-Path $Root "docker\compose"
$EnvFile = Join-Path $Root "config\immich-ml-rog.env"
$Ex = Join-Path $Root "config\immich-ml-rog.env.example"
if (-not (Test-Path $EnvFile)) { Copy-Item $Ex $EnvFile }
Set-Location $ComposeDir
docker compose -f docker-compose.immich-ml-rog.yml --env-file $EnvFile up -d
Start-Sleep 8
docker compose -f docker-compose.immich-ml-rog.yml --env-file $EnvFile ps
try {
    (Invoke-WebRequest http://127.0.0.1:3003/ping -UseBasicParsing).Content
} catch {
    "wait for models..."
}
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -like "192.168.*" } |
    ForEach-Object { "http://$($_.IPAddress):3003" }
