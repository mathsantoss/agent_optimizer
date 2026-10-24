import pandas as pd
import os

# Função para carregar os dados
def carregar_dados(caminho_arquivo):
    return pd.read_csv(caminho_arquivo)

# Função para calcular métricas
def calcular_metricas(df):
    # Calcular média de vendas por cliente
    df['media_vendas_cliente'] = df.groupby('id_cliente')['quantidade'].transform('mean')

    # Calcular frequência de compras por cliente
    df['freq_compras_cliente'] = df.groupby('id_cliente')['data_venda'].transform('count')

    # Calcular total de produtos distintos comprados por cliente
    df['total_produtos_cliente'] = df.groupby('id_cliente')['id_produto'].transform('nunique')

    # Calcular desconto médio
    df['desconto_medio'] = df['desconto'] / df['preco_unitario']

    # Calcular preço médio após desconto
    df['preco_medio'] = df['preco_unitario'] - df['desconto']

    # Converter datas
    df['dia_semana'] = pd.to_datetime(df['data_venda']).dt.dayofweek
    df['mes_do_ano'] = pd.to_datetime(df['data_venda']).dt.month

    return df

# Função principal
def run():
    # Carregar os dados
    df = carregar_dados('pipeline/dados/dados_vendas.csv')

    # Calcular métricas
    df = calcular_metricas(df)

    # Remover colunas que não serão utilizadas
    df.drop(['data_venda', 'desconto', 'preco_unitario'], axis=1, inplace=True)

    # Salvar resultado
    if not os.path.exists('pipeline/features'):
        os.makedirs('pipeline/features')

    df.to_csv('pipeline/features/features_credit.csv', index=False)
