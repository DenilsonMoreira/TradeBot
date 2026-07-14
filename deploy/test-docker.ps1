param(
    [switch]$KeepContainers
)

$ErrorActionPreference = "Stop"
$project = "tradebrain-test"
$composeFile = "docker-compose.test.yml"

try {
    docker compose -p $project -f $composeFile config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "A configuração do ambiente de testes é inválida."
    }

    docker compose -p $project -f $composeFile up --build --abort-on-container-exit --exit-code-from test
    if ($LASTEXITCODE -ne 0) {
        throw "A suíte Docker falhou."
    }
}
finally {
    if (-not $KeepContainers) {
        docker compose -p $project -f $composeFile down --volumes --remove-orphans
    }
}
