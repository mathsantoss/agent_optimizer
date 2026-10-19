
import pandas as pd
import os

# Ler arquivo
df = pd.read_csv('pipeline/dados/dados_vendas.csv')

# Calcular algumas informações dos clientes
df['media_vendas_cliente'] = df.groupby('id_cliente')['quantidade'].transform('mean')
df['freq_compras_cliente'] = df.groupby('id_cliente')['data_venda'].transform('count')

# Calcular total de produtos
df['total_produtos_cliente'] = df.groupby('id_cliente')['id_produto'].transform('nunique')

# Calcular desconto e preço
df['desconto_medio'] = df['desconto'] / df['preco_unitario']
df['preco_medio'] = df['preco_unitario'] - df['desconto']

# Converter datas várias vezes
df['dia_semana'] = pd.to_datetime(df['data_venda']).dt.dayofweek
df['mes_do_ano'] = pd.to_datetime(df['data_venda']).dt.month

# Calcular algumas métricas novamente sem necessidade
df['media_auxiliar'] = df.groupby('id_cliente')['quantidade'].transform('mean')
df['produtos_auxiliar'] = df.groupby('id_cliente')['id_produto'].transform('nunique')

df['media_vendas_cliente'] = df.groupby('id_cliente')['quantidade'].transform('mean')
df['freq_compras_cliente'] = df.groupby('id_cliente')['data_venda'].transform('count')

# Remover colunas que não serão utilizadas
df.drop(['data_venda', 'desconto', 'preco_unitario'], axis=1, inplace=True)

# Remover colunas auxiliares
df.drop(['media_auxiliar', 'produtos_auxiliar'], axis=1, inplace=True)

# Salvar resultado
if not os.path.exists('pipeline/features'):
    os.makedirs('pipeline/features')

df.to_csv('pipeline/features/features_credit.csv', index=False)
