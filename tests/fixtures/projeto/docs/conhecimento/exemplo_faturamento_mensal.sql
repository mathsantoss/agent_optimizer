---
categoria: exemplo_sql
tabela: dados_vendas
linguagem: sql
versao: 1.0
---
-- Faturamento líquido mensal (apenas vendas concluídas)
SELECT strftime('%Y-%m', data_venda) AS mes,
       SUM(quantidade * preco_unitario - desconto) AS faturamento
FROM dados_vendas
WHERE status = 'concluida'
GROUP BY mes
ORDER BY mes;
