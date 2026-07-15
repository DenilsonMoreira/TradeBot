param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$EnvironmentFile = ".env.production",
    [string]$ComposeFile = "docker-compose.prod.yml",
    [Parameter(Mandatory = $true)]
    [string]$Confirmation
)

$ErrorActionPreference = "Stop"

if ($Confirmation -cne "RESTAURAR-BANCO") {
    throw 'Restauração cancelada. Informe -Confirmation "RESTAURAR-BANCO" explicitamente.'
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Arquivo de ambiente não encontrado: $EnvironmentFile"
}
if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    throw "Arquivo do Docker Compose não encontrado: $ComposeFile"
}
if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) {
    throw "Backup não encontrado: $BackupFile"
}

$values = @{}
Get-Content -LiteralPath $EnvironmentFile | Where-Object { $_ -match "^[A-Z0-9_]+=" } | ForEach-Object {
    $key, $value = $_ -split "=", 2
    $values[$key] = $value
}
if ([string]::IsNullOrWhiteSpace($values["POSTGRES_DB"]) -or [string]::IsNullOrWhiteSpace($values["POSTGRES_USER"])) {
    throw "POSTGRES_DB e POSTGRES_USER precisam estar definidos em $EnvironmentFile."
}

$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$arguments = @(
    "compose", "--env-file", $EnvironmentFile, "-f", $ComposeFile,
    "exec", "-T", "db", "pg_restore", "-U", $values["POSTGRES_USER"],
    "-d", $values["POSTGRES_DB"], "--clean", "--if-exists", "--no-owner", "--exit-on-error"
)

$process = Start-Process -FilePath "docker" -ArgumentList $arguments -Wait -PassThru -NoNewWindow -RedirectStandardInput $resolvedBackup
if ($process.ExitCode -ne 0) {
    throw "Falha ao restaurar o banco (código $($process.ExitCode))."
}

Write-Host "Banco restaurado a partir de: $resolvedBackup"
