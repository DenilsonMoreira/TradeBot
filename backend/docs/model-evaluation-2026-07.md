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
- Antes do teste final, a estabilidade é medida em três folds walk-forward
  expansivos e não sobrepostos, todos contidos na janela de treino.
- Cada fronteira temporal descarta do treino uma quantidade de linhas igual ao
  horizonte previsto, impedindo que o rótulo atravesse para a janela de teste.
- Custos por lado: 0,10% de taxa e 0,05% de slippage.
- Retornos são compostos e operações sobrepostas são evitadas.
- Promoção exige retorno líquido não negativo, F1 mínimo de 0,50, ROC-AUC
  mínimo de 0,55, pelo menos 20 operações, retorno walk-forward não negativo,
  lucro em pelo menos dois dos três folds e desempenho superior ao
  buy-and-hold.

## Resultado

O backtest EMA 9/21 permaneceu negativo: BTC -33,42%, ETH -22,58% e BNB
-31,27%.

No horizonte de 15 minutos, movimentos acima do custo estimado foram raros e
os modelos praticamente não abriram operações. No horizonte de uma hora, o
balanceamento e a calibração aumentaram a seletividade, mas todos os candidatos
continuaram com retorno líquido negativo fora da amostra.

Na avaliação v4 com purga temporal, a regressão logística de ETH obteve +1,37%
no walk-forward, mas lucro em apenas um dos três folds, e perdeu 12,98% no
teste final, com F1 de 0,19 e ROC-AUC de 0,54. Portanto, falhou nos critérios
de estabilidade e nos critérios finais. Todos os demais
candidatos tiveram retorno walk-forward negativo ou também falharam no teste
final. Nenhum modelo foi marcado como `ACTIVE`.

## Coleta automatizada

Não continuar ajustando parâmetros com base neste mesmo teste. O próximo ciclo
de pesquisa deve aguardar uma janela contínua maior, repetir o walk-forward e
manter os candidatos apenas em observação antes de qualquer integração com a
execução automática.

O `trainer-worker` implementa essa espera. Ele consulta o progresso a cada
hora, mas só cria um novo dataset depois de 778 candles posteriores ao último
teste para cada símbolo. Esse valor cobre os 774 registros de teste e a margem
de quatro candles do horizonte. A promoção automática permanece desligada.
