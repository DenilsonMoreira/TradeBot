# TradeBrain — status consolidado

Este arquivo substitui, no repositório executável, o roadmap inicial que ainda
apontava a fase 8.2 como atual. As decisões arquiteturais originais continuam
válidas, especialmente Testnet obrigatória, risco centralizado, Alembic,
Decimal/Numeric e ausência de promessa de lucro.

## Implementação entregue

| Área | Estado |
|---|---|
| Infraestrutura Docker e Binance Spot Testnet | Concluída |
| Ordens, posições, P&L e emergência | Concluída |
| Gestão de risco e auditoria | Concluída |
| Data Lake de candles e indicadores | Concluída |
| Backtest com taxas e slippage | Concluída |
| Datasets temporais e treinamento | Concluída |
| Ensemble, registry e previsões | Concluída |
| Painel web responsivo e 2FA | Concluída |
| Pesquisa walk-forward e reavaliação automática | Concluída |
| Campanha contínua Testnet de R$ 500 | Em validação |
| Experiência mobile | Adiada por decisão do produto |
| Multiusuário e SaaS | Não iniciado |

## Validação operacional atual

1. A campanha contínua deve coletar sete dias reais de candles de BTCUSDT,
   ETHUSDT e BNBUSDT.
2. A cobertura mínima é 95%, sem feeds atrasados, ordens rejeitadas ou violações
   dos limites de risco.
3. O ciclo controlado de compra e venda de 6 USDT foi executado na Testnet.
4. A liberação para servidor continua bloqueada até a campanha terminar.
5. Trading automático continua bloqueado até existir modelo aprovado e ativo.

O estado oficial e reproduzível está em `GET /readiness/report` e no script
`deploy/check-local-readiness.ps1`.

## Próximos marcos

- 22/07/2026: encerramento e auditoria automática da campanha Testnet.
- Após completar a janela inédita: nova avaliação quantitativa.
- Depois das aprovações: auditoria final, domínio, HTTPS e deploy em servidor
  mantendo Binance Spot Testnet.

