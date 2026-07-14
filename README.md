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

## Acesso do operador

Copie `.env.example` para `.env` e gere uma senha derivada, uma chave de sessão
e o segredo TOTP sem armazenar a senha em texto aberto:

```bash
docker compose run --rm api python scripts/generate_auth_credentials.py
```

Adicione os três valores exibidos ao `.env`, defina `AUTH_OPERATOR_EMAIL` e
cadastre `AUTH_TOTP_SECRET` em um aplicativo autenticador. O painel exige senha
e código de seis dígitos. Alterações do modo operacional, parada de emergência,
configurações de risco e ordens manuais também exigem sessão e proteção CSRF no
backend.

O gerador apresenta `AUTH_PASSWORD_HASH` com `$$` de propósito: essa é a forma
de preservar os separadores `$` do hash quando o Docker Compose lê o `.env`.
Ele também cria `backend/scripts/tradebrain-authenticator.png`; abra a imagem,
escaneie-a no aplicativo autenticador e apague o arquivo após concluir o
cadastro. O QR Code contém o segredo TOTP e é ignorado pelo Git.

Serviços iniciados:

- `api`: FastAPI e migrations Alembic;
- `frontend`: painel operacional React;
- `worker`: sinais e gestão das posições Testnet;
- `candle-worker`: sincronização incremental dos candles;
- `indicator-worker`: cálculo idempotente dos indicadores;
- `db`: PostgreSQL 16.

## Aplicativo nativo

O diretório `mobile` contém o aplicativo Expo/React Native para Android e iOS.
Copie `mobile/.env.example` para `mobile/.env` e ajuste `EXPO_PUBLIC_API_URL`.
No emulador Android, `10.0.2.2` aponta para o computador; em um aparelho físico,
use o IP local do computador e mantenha ambos na mesma rede.

```bash
cd mobile
npm install
npm start
```

O app usa a mesma senha e TOTP do painel, guarda a sessão curta no SecureStore
do dispositivo e envia o token CSRF nas ações críticas. Nenhuma chave da Binance
é armazenada no aplicativo.

## Publicação web com HTTPS

A implantação de produção usa Caddy como única porta de entrada. O painel fica
em `/` e a API em `/api`, enquanto API, PostgreSQL e workers permanecem na rede
interna do Docker. O Caddy obtém e renova o certificado automaticamente.

Pré-requisitos: servidor com Docker, domínio apontando para o IP público e
portas TCP 80/443 e UDP 443 liberadas. Depois:

```powershell
Copy-Item .env.production.example .env.production
# Preencha domínio, banco, Binance Testnet e credenciais de autenticação.
.\deploy\deploy-production.ps1
```

Em produção, `AUTH_COOKIE_SECURE=true` é obrigatório. Não exponha diretamente
as portas 3000, 5432 ou 8000 e mantenha o ambiente Binance em Testnet.

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
