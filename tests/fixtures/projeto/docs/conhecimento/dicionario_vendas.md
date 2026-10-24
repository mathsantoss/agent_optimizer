---
categoria: dicionario_dados
tabela: dados_vendas
versao: 1.0
atualizado_em: 2026-10-24
---
# Dicionário de dados: dados_vendas

Arquivo: `pipeline/dados/dados_vendas.csv`. Granularidade: uma linha por venda (`id_venda` é a chave única).

## Colunas
- `id_venda`: identificador único da venda.
- `id_cliente`: identificador do cliente que comprou.
- `id_produto`: identificador do produto vendido.
- `data_venda`: data da venda (formato YYYY-MM-DD).
- `quantidade`: unidades vendidas na linha.
- `preco_unitario`: preço de tabela de uma unidade.
- `desconto`: valor absoluto de desconto (em moeda) aplicado à linha inteira, não por unidade e não percentual.
- `status`: `concluida` ou `cancelada`.
