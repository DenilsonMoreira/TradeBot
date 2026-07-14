$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env.production")) {
    throw "Crie .env.production a partir de .env.production.example."
}

$required = @(
    "TRADEBRAIN_DOMAIN",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "AUTH_OPERATOR_EMAIL",
    "AUTH_SECRET_KEY",
    "AUTH_PASSWORD_HASH",
    "AUTH_TOTP_SECRET"
)
$values = @{}
Get-Content ".env.production" | Where-Object { $_ -match "^[A-Z0-9_]+=" } | ForEach-Object {
    $key, $value = $_ -split "=", 2
    $values[$key] = $value
}
foreach ($key in $required) {
    if ([string]::IsNullOrWhiteSpace($values[$key]) -or $values[$key] -match "example|replace-with") {
        throw "Configure $key em .env.production antes de publicar."
    }
}

docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
