param(
    [string]$EnvironmentFile = ".env.production",
    [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Arquivo de ambiente não encontrado: $EnvironmentFile"
}

$values = @{}
Get-Content -LiteralPath $EnvironmentFile | Where-Object { $_ -match "^[A-Z0-9_]+=" } | ForEach-Object {
    $key, $value = $_ -split "=", 2
    $values[$key] = $value
}
$domain = $values["TRADEBRAIN_DOMAIN"]
if ([string]::IsNullOrWhiteSpace($domain)) {
    throw "TRADEBRAIN_DOMAIN precisa estar definido em $EnvironmentFile."
}

$env:TRADEBRAIN_ENV_FILE = $EnvironmentFile
try {
    docker compose --env-file $EnvironmentFile -f docker-compose.prod.yml config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "A configuração do Docker Compose é inválida."
    }

    $expectedServices = @("proxy", "frontend", "api", "worker", "candle-worker", "indicator-worker", "db")
    $runningServices = @(docker compose --env-file $EnvironmentFile -f docker-compose.prod.yml ps --status running --services)
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível consultar os serviços de produção."
    }
    $missingServices = @($expectedServices | Where-Object { $_ -notin $runningServices })
    if ($missingServices.Count -gt 0) {
        throw "Serviços fora de execução: $($missingServices -join ', ')."
    }

    $health = Invoke-RestMethod -Uri "https://$domain/api/health/ready" -TimeoutSec $TimeoutSeconds
    if ($health.status -ne "ready" -or $health.database -ne "ok") {
        throw "A API respondeu, mas não está pronta."
    }

    $web = Invoke-WebRequest -Uri "https://$domain/" -TimeoutSec $TimeoutSeconds
    if ($web.StatusCode -ne 200) {
        throw "O painel respondeu com HTTP $($web.StatusCode)."
    }

    Write-Host "Produção saudável: https://$domain"
    Write-Host "Serviços em execução: $($runningServices -join ', ')"
    Write-Host "API pronta e PostgreSQL conectado."
}
finally {
    Remove-Item Env:TRADEBRAIN_ENV_FILE -ErrorAction SilentlyContinue
}
