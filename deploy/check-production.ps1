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

    $expectedServices = @("proxy", "frontend", "api", "worker", "candle-worker", "indicator-worker", "trainer-worker", "db")
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

    $python = @'
import json
from app.database import SessionLocal
from app.services.readiness_service import ReadinessService
db = SessionLocal()
try:
    print(json.dumps(ReadinessService(db).report(), default=str))
finally:
    db.close()
'@
    $reportOutput = @(docker compose --env-file $EnvironmentFile -f docker-compose.prod.yml exec -T api python -c $python)
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível consultar a prontidão interna da produção."
    }
    $report = ($reportOutput -join "`n") | ConvertFrom-Json
    if (-not $report.server_release_ready) {
        $blocked = @($report.checks | Where-Object { "SERVER" -in $_.gates -and $_.status -ne "PASS" })
        throw "Servidor ainda bloqueado: $(($blocked | ForEach-Object { $_.label }) -join '; ')."
    }

    Write-Host "Produção saudável: https://$domain"
    Write-Host "Serviços em execução: $($runningServices -join ', ')"
    Write-Host "API pronta e PostgreSQL conectado."
    Write-Host "Gate interno de servidor aprovado."
}
finally {
    Remove-Item Env:TRADEBRAIN_ENV_FILE -ErrorAction SilentlyContinue
}
