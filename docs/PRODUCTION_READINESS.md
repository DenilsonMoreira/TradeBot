# Prontidão operacional do TradeBrain

O TradeBrain possui três níveis independentes de liberação:

1. **Docker local**: infraestrutura, autenticação, banco, feeds e execução
   controlada na Binance Testnet estão saudáveis.
2. **Servidor Testnet**: além do nível local, exige a campanha contínua de sete
   dias concluída e aprovada.
3. **Trading automático**: além dos níveis anteriores, exige ao menos um modelo
   aprovado e ativo. A promoção automática de modelos permanece proibida.

O painel e a API exibem os mesmos critérios:

```text
GET /readiness/report
```

## Auditoria local

Execute na raiz do projeto:

```powershell
.\deploy\check-local-readiness.ps1
```

Para também restaurar o backup mais recente em PostgreSQL temporário:

```powershell
.\deploy\check-local-readiness.ps1 -ValidateBackup
```

O script falha se algum dos sete serviços estiver parado, se API ou painel não
responderem, se o banco estiver em migration antiga, se o ambiente não for
Testnet, se houver bloqueio local ou se o backup estiver vencido.

## Bloqueios temporais atuais

- Campanha Testnet: iniciada em 15/07/2026 e prevista para terminar em
  22/07/2026 às 10:38 no horário de Fortaleza.
- Pesquisa quantitativa: uma nova rodada só ocorre após uma janela final
  completamente inédita. Nenhum modelo deve ser ativado apenas para eliminar
  um item pendente do relatório.

## Regra de liberação

Um resultado `PENDING` não é falha, mas impede o nível ao qual está associado.
Um resultado `FAIL` exige correção e nova auditoria. Nenhum bloqueio pode ser
removido manualmente no banco para simular aprovação.

