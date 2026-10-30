import pandas as pd
import numpy as np
import os

def carregar_dados(caminho="pipeline/dados/dados_vendas.csv"):
    """Carrega o dataset de vendas."""
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    df = pd.read_csv(caminho)
    return df

def engenharia_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria features para Machine Learning a partir do dataset dados_vendas:
    - total_value_x: quantidade * price_x
    - total_value_y: quantidade * price_y
    - price_diff: price_x - price_y
    - created_year, created_month, created_dayofweek: features temporais de created_at
    - client_order_count: número de transações por cliente (name)
    - product_avg_price: preço médio por produto (price_y)
    """
    df = df.copy()
    
    # Garantir conversão de datas
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
    
    # 1. Features financeiras e transacionais
    df['total_value_x'] = df['quantity'] * df['price_x']
    df['total_value_y'] = df['quantity'] * df['price_y']
    df['price_diff'] = df['price_x'] - df['price_y']
    
    # 2. Features temporais
    df['created_year'] = df['created_at'].dt.year
    df['created_month'] = df['created_at'].dt.month
    df['created_dayofweek'] = df['created_at'].dt.dayofweek
    df['created_hour'] = df['created_at'].dt.hour
    
    # 3. Features agregadas por cliente (Frequência de compras)
    client_counts = df.groupby('name')['sale_id'].nunique().reset_index(name='client_transaction_count')
    df = df.merge(client_counts, on='name', how='left')
    
    client_spend = df.groupby('name')['total_value_x'].sum().reset_index(name='client_total_spent')
    df = df.merge(client_spend, on='name', how='left')
    
    # 4. Features agregadas por produto
    product_mean_price = df.groupby('product')['price_y'].mean().reset_index(name='product_mean_price')
    df = df.merge(product_mean_price, on='product', how='left')
    
    # Preencher eventuais nulos decorrentes de conversões
    df.fillna(0, inplace=True)
    
    return df

def executar_pipeline():
    print("Iniciando pipeline de engenharia de features...")
    df = carregar_dados()
    print(f"Dados carregados com sucesso. Linhas: {len(df)}, Colunas: {len(df.columns)}")
    
    df_features = engenharia_features(df)
    print("Engenharia de features concluída com sucesso!")
    print(f"Colunas geradas ({len(df_features.columns)}): {list(df_features.columns)}")
    
    return df_features

if __name__ == "__main__":
    executar_pipeline()
