param(
    [string]$EnvironmentFile = ".env.production",
    [string]$OutputDirectory = "backups"
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
if ([string]::IsNullOrWhiteSpace($values["POSTGRES_DB"]) -or [string]::IsNullOrWhiteSpace($values["POSTGRES_USER"])) {
    throw "POSTGRES_DB e POSTGRES_USER precisam estar definidos em $EnvironmentFile."
}

$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $outputPath "tradebrain-$timestamp.dump"
$arguments = @(
    "compose", "--env-file", $EnvironmentFile, "-f", "docker-compose.prod.yml",
    "exec", "-T", "db", "pg_dump", "-U", $values["POSTGRES_USER"],
    "-d", $values["POSTGRES_DB"], "-Fc"
)

$process = Start-Process -FilePath "docker" -ArgumentList $arguments -Wait -PassThru -NoNewWindow -RedirectStandardOutput $backupPath
if ($process.ExitCode -ne 0) {
    Remove-Item -LiteralPath $backupPath -ErrorAction SilentlyContinue
    throw "Falha ao criar o backup (código $($process.ExitCode))."
}

$size = (Get-Item -LiteralPath $backupPath).Length
if ($size -eq 0) {
    Remove-Item -LiteralPath $backupPath
    throw "O arquivo de backup foi criado vazio."
}

Write-Host "Backup criado: $backupPath ($size bytes)"
