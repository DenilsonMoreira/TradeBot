# TradeBrain

Plataforma quantitativa para Binance Spot Testnet. A Fase 8 fornece um
Data Lake idempotente de candles em PostgreSQL.

## Executar

```bash
docker compose build
docker compose up -d
docker compose ps
```

A API fica disponível em `http://localhost:8000` e o Swagger em
`http://localhost:8000/docs`.

Serviços iniciados:

- `api`: FastAPI e migrations Alembic;
- `worker`: sinais e gestão das posições Testnet;
- `candle-worker`: sincronização incremental dos candles;
- `db`: PostgreSQL 16.

## API de candles

```text
GET  /candles
GET  /candles/latest
POST /candles/sync
```

## Testes

```bash
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose run --rm -e PYTHONPATH=/app -v ./backend/tests:/app/tests api pytest -q
```

## Controle do bot

Ativar Testnet:

```json
{
  "mode": "TESTNET_TRADING",
  "confirmation": "ATIVAR TESTNET"
}
```

Ativar monitoramento:

```json
{
  "mode": "MONITOR"
}
```

Desligar:

```json
{
  "mode": "OFF"
}
```
