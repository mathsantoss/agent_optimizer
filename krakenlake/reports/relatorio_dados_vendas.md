# Relatório Analítico Executivo - dados_vendas
**Dataset:** `dados_vendas` | **Data de Geração:** 12/11/2026 01:57

## 1. Resumo Executivo e Volumetria
- **Total de Linhas Analisadas:** 10
- **Total de Colunas:** 8
- **Uso de Memória:** ~0.94 KB

## 2. Qualidade dos Dados e Valores Ausentes
✓ **Nenhum valor ausente identificado no dataset.** Base com 100% de preenchimento.

## 3. Detecção de Outliers e Anomalias (Método IQR)
| Coluna | Outliers | % Outliers | Limite Inferior | Limite Superior | Severidade |
|---|---|---|---|---|---|
| quantidade | 1 | 10.0% | -0.5 | 3.5 | Alta |
| id_venda | 0 | 0.0% | -3.5 | 14.5 | Baixa |
| id_cliente | 0 | 0.0% | 97.5 | 107.5 | Baixa |
| id_produto | 0 | 0.0% | 498.625 | 505.625 | Baixa |
| preco_unitario | 0 | 0.0% | -118.75 | 411.25 | Baixa |
| desconto | 0 | 0.0% | -15.0 | 25.0 | Baixa |

## 4. Destaques de Correlação Linear
- **id_venda ↔ id_cliente:** 0.5868 (Moderada Positiva)
- **quantidade ↔ preco_unitario:** -0.53 (Moderada Negativa)
- **id_cliente ↔ desconto:** -0.3401 (Fraca/Nula)
- **id_produto ↔ preco_unitario:** -0.311 (Fraca/Nula)
- **id_produto ↔ quantidade:** 0.2216 (Fraca/Nula)

## 5. Recomendações e Próximos Passos
- Aplicar pipeline de deduplicação e normalização de datas.
- Aplicar transformações logarítmicas nas variáveis com assimetria positiva acentuada.
- Salvar o script reprodutível em `krakenlake/workspace/` para orquestração contínua.
