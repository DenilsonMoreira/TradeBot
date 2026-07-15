param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) {
    throw "Backup não encontrado: $BackupFile"
}

$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$containerName = "tradebrain-restore-check-$PID"

try {
    docker run -d --name $containerName `
        -e POSTGRES_DB=tradebrain_restore `
        -e POSTGRES_USER=tradebrain_restore `
        -e POSTGRES_PASSWORD=restore-test-only `
        postgres:16-alpine | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível iniciar o PostgreSQL temporário."
    }

    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        docker exec $containerName pg_isready `
            -U tradebrain_restore -d tradebrain_restore | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw "O PostgreSQL temporário não ficou pronto."
    }

    docker cp $resolvedBackup "${containerName}:/tmp/tradebrain.dump"
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível copiar o backup para o contêiner temporário."
    }

    docker exec $containerName pg_restore `
        -U tradebrain_restore `
        -d tradebrain_restore `
        --no-owner `
        --exit-on-error `
        /tmp/tradebrain.dump
    if ($LASTEXITCODE -ne 0) {
        throw "A restauração isolada falhou."
    }

    docker exec $containerName psql `
        -U tradebrain_restore `
        -d tradebrain_restore `
        -v ON_ERROR_STOP=1 `
        -c "SELECT (SELECT count(*) FROM candles) AS candles, (SELECT count(*) FROM orders) AS orders, (SELECT count(*) FROM positions) AS positions, (SELECT count(*) FROM datasets) AS datasets, (SELECT count(*) FROM trained_models) AS models;"
    if ($LASTEXITCODE -ne 0) {
        throw "A consulta de validação do banco restaurado falhou."
    }

    Write-Host "Backup restaurado e validado em PostgreSQL temporário."
}
finally {
    docker rm -f $containerName 2>$null | Out-Null
}
