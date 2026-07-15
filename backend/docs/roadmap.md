# Nosso Roadmap oficial
## Fase 8

Data Lake

✔ Candles

✔ Downloader

✔ Atualização

## Fase 9

Indicadores

✔ Modelo e migration versionados

✔ EMA

✔ RSI

✔ MACD

✔ ATR

✔ ADX

✔ Repository e persistência idempotente

✔ API e worker

## Fase 10

✔ Backtest sem look-ahead

✔ Taxas, slippage, operações e métricas

✔ Persistência e API

## Fase 11

✔ Features e labels reproduzíveis

✔ Divisão temporal sem leakage

✔ Versionamento e API

## Fase 12

✔ Baseline

✔ Logistic Regression

✔ Random Forest

✔ XGBoost CPU

✔ LightGBM

✔ CatBoost

✔ Métricas estatísticas e financeiras

✔ Registry local de artefatos e API

## Fase 13

✔ Ciclo de vida do Model Registry

✔ Promoção e desativação

✔ Soft voting por probabilidades

✔ Avaliação no teste temporal

✔ Inferência versionada e idempotente

✔ Recomendação por métricas financeiras fora da amostra

✔ Separação obrigatória entre previsão, risco e execução

## Fase 14

✔ Painel React responsivo

✔ Visão operacional, candles, posições, modelos e backtests

✔ Parada de emergência e atualização manual

✔ Integração local via Docker e CORS restrito

Pendente: hospedagem pública após disponibilização HTTPS da API

## Fase 15

Aplicativo

✔ Dashboard adaptado para uso móvel

✔ Navegação inferior e alvos de toque acessíveis

✔ Resumo diário e parada de emergência ao alcance de uma mão

✔ Web app instalável com manifest e suporte a safe areas

✔ Login do operador com senha derivada e TOTP

✔ Sessão HTTP-only, expiração e proteção CSRF em ações críticas

✔ Proteção autenticada das consultas operacionais e dados de pesquisa

✔ Proteção CSRF em sincronização, cálculo, treinamento e ciclo de modelos

✔ Aplicativo nativo Expo/React Native para Android e iOS

✔ Sessão móvel curta armazenada no SecureStore

✔ Status, posições, modelo ativo e parada de emergência no app

Fase 15 concluída

## Fase 16

Web operacional

✔ Controle autenticado do modo do bot

✔ Configuração dos limites de risco

✔ Saldo Testnet, sinais e ações manuais protegidas

✔ Auditoria operacional persistente e autenticada

✔ Central de notificações internas por operador

✔ Severidade, contador de não lidas e confirmação de leitura

✔ Ambiente de produção com proxy HTTPS e renovação automática

✔ Cookies seguros, headers defensivos e serviços internos não expostos

✔ Bloqueio temporário de login e feedback de espera no painel

✔ Healthcheck com PostgreSQL, backup, restauração e rotação de logs

✔ Diagnóstico automatizado pós-publicação

✔ Suíte Docker isolada do banco operacional local

✔ Navegação ativa, modais operacionais e feedback de validação

✔ Histórico de compras/vendas e explicações de sinais e carteira Testnet

✔ Mercado multiativo com candles OHLC e atualização automática visível

✔ Backfill idempotente de 3.000 candles por mercado e validação de continuidade

✔ Pipeline temporal real com seis candidatos e critérios conservadores de promoção

✔ Ciclo completo de compra e venda validado na Testnet com mínimo seguro de 6 USDT

✔ Backup local validado por restauração em PostgreSQL temporário

Pendente: apontar domínio e executar a publicação no servidor


# O que muda no nosso desenvolvimento?

A partir de agora, cada fase seguirá um padrão fixo.

## 1. Objetivo

O que vamos construir.

## 2. Arquivos

Quais arquivos serão criados ou alterados.

## 3. Testes

Como validar.

## 4. Critério de aprovação

O que precisa funcionar antes de avançar.

## 5. Commit

Mensagem de commit. Assim, nunca teremos dúvidas sobre onde estamos.
