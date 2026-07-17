param(
    [string]$EnvironmentFile = ".env.production",
    [string]$ComposeFile = "docker-compose.prod.yml",
    [string]$OutputDirectory = "backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) {
    throw "Arquivo de ambiente não encontrado: $EnvironmentFile"
}
if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    throw "Arquivo do Docker Compose não encontrado: $ComposeFile"
}

$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$fileName = "tradebrain-model-artifacts-$timestamp.tar.gz"
$containerPath = "/tmp/$fileName"
$backupPath = Join-Path $outputPath $fileName
$compose = @("compose", "--env-file", $EnvironmentFile, "-f", $ComposeFile)

& docker @compose exec -T api sh -lc "find /app/artifacts -maxdepth 1 -type f -print -quit | grep -q . && tar -czf $containerPath -C /app/artifacts ."
if ($LASTEXITCODE -ne 0) {
    throw "Não há artefatos para salvar ou o empacotamento falhou."
}

& docker @compose cp "api:$containerPath" $backupPath
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $backupPath)) {
    throw "Falha ao copiar o backup dos modelos."
}

$size = (Get-Item -LiteralPath $backupPath).Length
$hash = (Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash
Write-Host "Artefatos salvos: $backupPath ($size bytes)"
Write-Host "SHA256: $hash"
