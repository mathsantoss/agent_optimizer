---
categoria: regra_negocio
tabela: dados_vendas
versao: 1.0
atualizado_em: 2026-10-24
---
# Definições de métricas e regras de negócio

## Faturamento
Faturamento líquido = soma de `quantidade * preco_unitario - desconto`, considerando somente vendas com `status = 'concluida'`. Vendas canceladas nunca entram no faturamento.

## Ticket médio
Ticket médio = faturamento líquido dividido pelo número de vendas concluídas (`COUNT(id_venda)`).

## Cliente recorrente
Cliente recorrente é aquele com 2 ou mais vendas concluídas. Cliente novo tem exatamente 1 venda concluída.

## Taxa de cancelamento
Vendas canceladas dividido pelo total de vendas no período.

## Convenções de implementação
- Pipelines são procedurais (somente `def`), com função `run()` que orquestra as demais.
- Use type hints, docstrings e operações vetorizadas.
- Features temporais devem usar apenas dados anteriores à data de referência da predição.
