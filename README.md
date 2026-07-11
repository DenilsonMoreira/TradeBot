# TradeBrain

Plataforma quantitativa para Binance Spot Testnet, com Data Lake de candles
e indicadores técnicos persistidos e versionados em PostgreSQL.

## Executar

```bash
docker compose build
docker compose up -d
docker compose ps
```

A API fica disponível em `http://localhost:8000` e o Swagger em
`http://localhost:8000/docs`.

O painel web fica disponível em `http://localhost:3000`.

Em celulares, o painel oferece navegação por toque e pode ser instalado pela
opção "Adicionar à tela inicial" do navegador. O acesso continua dependente da
API local; não há envio direto de ordens a partir da interface.

Serviços iniciados:

- `api`: FastAPI e migrations Alembic;
- `frontend`: painel operacional React;
- `worker`: sinais e gestão das posições Testnet;
- `candle-worker`: sincronização incremental dos candles;
- `indicator-worker`: cálculo idempotente dos indicadores;
- `db`: PostgreSQL 16.

## API de candles

```text
GET  /candles
GET  /candles/latest
POST /candles/sync
```

## API de indicadores

```text
GET  /indicators
POST /indicators/calculate
```

Indicadores disponíveis: EMA 9/21, RSI 14, MACD, ATR 14 e ADX 14.

## Pesquisa quantitativa

```text
POST /backtests/run
GET  /backtests
POST /datasets/build
GET  /datasets
POST /models/train
GET  /models
```

Backtests incluem taxas e slippage e executam sinais somente no candle
seguinte. Datasets usam divisão temporal. Modelos treinados não possuem
acesso ao serviço de execução de ordens.

Modelos disponíveis: baseline, Logistic Regression, Random Forest,
XGBoost CPU, LightGBM e CatBoost.

Ensembles podem ser avaliados sem promoção automática:

```text
POST /ensembles/evaluate
POST /models/{model_id}/promote
POST /models/{model_id}/deactivate
GET  /datasets/{dataset_id}/models/active
```

Inferência e recomendação:

```text
GET  /datasets/{dataset_id}/models/recommend
POST /predictions
GET  /datasets/{dataset_id}/predictions
```

Uma previsão nunca cria ordem diretamente. Qualquer uso operacional futuro
deve passar pelo gestor de risco e pelo serviço de execução.

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
