import pandas as pd
import numpy as np
import os
import random
import time
import warnings

warnings.filterwarnings('ignore')

def carregar_dados(filepath="pipeline/dados/dados_vendas.csv"):
    df = pd.read_csv(filepath)
    return df

# Função otimizada para calcular o preço da linha
def calcular_preco_linha(df: pd.DataFrame) -> pd.DataFrame:
    df['total_value_x'] = df['price_x'] * df['quantity']
    df['total_value_y'] = df['price_y'] * df['quantity']
    return df

# Função otimizada para calcular a diferença de preço
def calcular_diferenca(df: pd.DataFrame) -> pd.DataFrame:
    df['price_diff'] = df['price_y'] - df['price_x']
    return df

# Função otimizada para calcular a razão de preço
def calcular_ratio(df: pd.DataFrame) -> pd.DataFrame:
    df['price_ratio'] = df['price_y'] / df['price_x']
    return df

# Função otimizada para calcular estatísticas do cliente
def calcular_estatisticas_cliente(df: pd.DataFrame) -> pd.DataFrame:
    stats_cliente = df.groupby('email').agg(
        client_total_spent=('total_value_x', 'sum'),
        client_transaction_count=('sale_id', 'size'),
        client_average_spent=('total_value_x', 'mean')
    ).reset_index()
    df = df.merge(stats_cliente, on='email', how='left')
    return df

# Função otimizada para calcular estatísticas do produto
def calcular_estatisticas_produto(df: pd.DataFrame) -> pd.DataFrame:
    stats_produto = df.groupby('product_id')['price_x'].mean().rename('product_mean_price').reset_index()
    df = df.merge(stats_produto, on='product_id', how='left')
    return df

# Função otimizada para engenharia de features de tempo
def engenharia_features(df: pd.DataFrame) -> pd.DataFrame:
    # Convertendo para datetime uma única vez
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
    df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce', utc=True)

    df['created_year'] = df['created_at'].dt.year
    df['created_month'] = df['created_at'].dt.month
    df['created_day'] = df['created_at'].dt.day
    df['created_hour'] = df['created_at'].dt.hour
    df['created_weekday'] = df['created_at'].dt.dayofweek # Monday=0, Sunday=6

    # Calcular a diferença de tempo em segundos
    df['time_difference'] = (df['updated_at'] - df['created_at']).dt.total_seconds().fillna(0)

    return df

def executar_pipeline() -> pd.DataFrame:
    df = carregar_dados()
    df = calcular_preco_linha(df)
    df = calcular_diferenca(df)
    df = calcular_ratio(df)
    df = calcular_estatisticas_cliente(df)
    df = calcular_estatisticas_produto(df)
    df = engenharia_features(df)
    return df

if __name__ == "__main__":
    print("Iniciando pipeline otimizado...")
    df_processado = executar_pipeline()
    print("Pipeline otimizado concluído.")
    print(df_processado.head())