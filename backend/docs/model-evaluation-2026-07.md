# Avaliação quantitativa — julho de 2026

## Dados

- Fonte: Binance Spot Testnet.
- Intervalo: candles de 15 minutos.
- Período contínuo usado: 3.900 candles por símbolo, aproximadamente 40 dias.
- Símbolos: BTCUSDT, ETHUSDT e BNBUSDT.
- O início do histórico BTC continha 19 rupturas artificiais; o treino usou
  somente a janela contínua posterior.

## Metodologia

- Divisão temporal: 80% treino e 20% teste.
- Os 20% finais do treino formam uma janela de validação para calibrar o
  limiar de probabilidade.
- O conjunto de teste não participa da escolha do limiar.
- Custos por lado: 0,10% de taxa e 0,05% de slippage.
- Retornos são compostos e operações sobrepostas são evitadas.
- Promoção exige retorno líquido não negativo, F1 mínimo de 0,50, ROC-AUC
  mínimo de 0,55, pelo menos 20 operações e desempenho superior ao
  buy-and-hold.

## Resultado

O backtest EMA 9/21 permaneceu negativo: BTC -33,42%, ETH -22,58% e BNB
-31,27%.

No horizonte de 15 minutos, movimentos acima do custo estimado foram raros e
os modelos praticamente não abriram operações. No horizonte de uma hora, o
balanceamento e a calibração aumentaram a seletividade, mas todos os candidatos
continuaram com retorno líquido negativo fora da amostra.

Alguns modelos de ETH tiveram retorno positivo na validação e negativo no
teste. Isso indica instabilidade temporal e impede promoção segura. Nenhum
modelo foi marcado como `ACTIVE`.

## Próxima coleta recomendada

Não continuar ajustando parâmetros com base neste mesmo teste. O próximo ciclo
de pesquisa deve aguardar uma janela contínua maior, executar avaliação
walk-forward em múltiplos períodos e manter os candidatos apenas em observação
antes de qualquer integração com a execução automática.
