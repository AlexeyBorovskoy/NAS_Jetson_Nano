$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$EnvFile = Join-Path $Root "config\immich-ml-rog.env"
if (-not (Test-Path $EnvFile)) {
    $EnvFile = Join-Path $Root "config\immich-ml-rog.env.example"
}
Set-Location (Join-Path $Root "docker\compose")
docker compose -f docker-compose.immich-ml-rog.yml --env-file $EnvFile down
