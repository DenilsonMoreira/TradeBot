param(
    [Parameter(Mandatory = $true)]
    [string]$Confirmation
)

$ErrorActionPreference = "Stop"

if ($Confirmation -ne "PUBLICAR TESTNET") {
    throw 'Confirmação inválida. Use -Confirmation "PUBLICAR TESTNET".'
}

if (-not (Test-Path ".env.production")) {
    throw "Crie .env.production a partir de .env.production.example."
}

$required = @(
    "TRADEBRAIN_DOMAIN",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "BINANCE_TESTNET",
    "AUTH_OPERATOR_EMAIL",
    "AUTH_SECRET_KEY",
    "AUTH_PASSWORD_HASH",
    "AUTH_TOTP_SECRET",
    "AUTH_COOKIE_SECURE",
    "RESEARCH_PROMOTE_QUALIFIED"
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

if ($values["BINANCE_TESTNET"] -ne "true") {
    throw "BINANCE_TESTNET precisa permanecer true."
}
if ($values["AUTH_COOKIE_SECURE"] -ne "true") {
    throw "AUTH_COOKIE_SECURE precisa permanecer true."
}
if ($values["RESEARCH_PROMOTE_QUALIFIED"] -ne "false") {
    throw "RESEARCH_PROMOTE_QUALIFIED precisa permanecer false."
}

docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
