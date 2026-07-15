param(
    [string]$BackupDirectory = "backups",
    [int]$MaxBackupAgeHours = 24,
    [switch]$ValidateBackup
)

$ErrorActionPreference = "Stop"
$expectedServices = @(
    "frontend",
    "api",
    "worker",
    "candle-worker",
    "indicator-worker",
    "trainer-worker",
    "db"
)

docker compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "A configuração do Docker Compose local é inválida."
}

$runningServices = @(docker compose ps --status running --services)
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível consultar os serviços locais."
}
$missingServices = @($expectedServices | Where-Object { $_ -notin $runningServices })
if ($missingServices.Count -gt 0) {
    throw "Serviços fora de execução: $($missingServices -join ', ')."
}
$runningExpectedServices = @($expectedServices | Where-Object { $_ -in $runningServices })

$health = Invoke-RestMethod -Uri "http://localhost:8000/health/ready" -TimeoutSec 15
if ($health.status -ne "ready" -or $health.database -ne "ok" -or $health.environment -ne "testnet") {
    throw "A API local não está pronta e isolada na Testnet."
}
$web = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:3000/" -TimeoutSec 15
if ($web.StatusCode -ne 200) {
    throw "O painel local respondeu com HTTP $($web.StatusCode)."
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
$reportOutput = @(docker compose exec -T api python -c $python)
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível gerar o relatório interno de prontidão."
}
$report = ($reportOutput -join "`n") | ConvertFrom-Json
if (-not $report.local_stack_ready) {
    $blocked = @($report.checks | Where-Object { "LOCAL" -in $_.gates -and $_.status -ne "PASS" })
    throw "Docker local bloqueado: $(($blocked | ForEach-Object { $_.label }) -join '; ')."
}

$backup = Get-ChildItem -LiteralPath $BackupDirectory -Filter "tradebrain-*.dump" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $backup) {
    throw "Nenhum backup foi encontrado em $BackupDirectory."
}
$backupAge = (Get-Date) - $backup.LastWriteTime
if ($backupAge.TotalHours -gt $MaxBackupAgeHours) {
    throw "O backup mais recente tem $([math]::Round($backupAge.TotalHours, 1)) horas."
}

if ($ValidateBackup) {
    & "$PSScriptRoot\test-database-backup.ps1" -BackupFile $backup.FullName
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backup.FullName).Hash
Write-Host "Docker local aprovado: $($runningExpectedServices -join ', ')"
Write-Host "Critérios internos: $($report.summary.passed)/$($report.summary.total) aprovados"
Write-Host "Servidor Testnet pronto: $($report.server_release_ready)"
Write-Host "Trading automático pronto: $($report.automatic_trading_ready)"
Write-Host "Backup: $($backup.FullName)"
Write-Host "SHA256: $hash"
