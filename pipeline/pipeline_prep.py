"""
Pipeline de Engenharia de Features para Machine Learning
Dataset: dados_vendas.csv
Autor: Agente Otimizador (Agent FIAP)
"""

import pandas as pd
import numpy as np
import os

def carregar_dados(caminho="pipeline/dados/dados_vendas.csv"):
    """Carrega o dataset de vendas."""
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    df = pd.read_csv(caminho)
    return df

def criar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza a limpeza, tratamento e engenharia de features (Feature Engineering)
    para preparação de inputs de Machine Learning.
    """
    df = df.copy()
    
    # 1. Tratamento de Datas e Extração Temporal
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
    
    df['created_year'] = df['created_at'].dt.year
    df['created_month'] = df['created_at'].dt.month
    df['created_day'] = df['created_at'].dt.day
    df['created_dayofweek'] = df['created_at'].dt.dayofweek
    
    # 2. Features Financeiras e de Comércio (Vetorizadas)
    # Total da Venda = Preço unitário (price_x) * Quantidade
    df['total_sale_amount'] = df['price_x'] * df['quantity']
    
    # Razão de Preço (price_x / price_y) para identificar desvios em relação à referência do produto
    df['price_ratio'] = df['price_x'] / (df['price_y'] + 1e-5)
    
    # 3. Agregações por Cliente (Comportamento de Compra)
    if 'email' in df.columns:
        client_stats = df.groupby('email').agg(
            client_total_spent=('total_sale_amount', 'sum'),
            client_avg_quantity=('quantity', 'mean'),
            client_purchase_count=('sale_id', 'nunique')
        ).reset_index()
        
        df = df.merge(client_stats, on='email', how='left')
    
    # 4. Agregações por Produto (Popularidade e Média de Preço)
    if 'product_id' in df.columns:
        product_stats = df.groupby('product_id').agg(
            product_avg_price=('price_x', 'mean'),
            product_total_sold=('quantity', 'sum')
        ).reset_index()
        
        df = df.merge(product_stats, on='product_id', how='left')
        
    # 5. Tratamento de Valores Ausentes / Infinitos
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)
    
    return df

def executar_pipeline_prep(caminho_entrada="pipeline/dados/dados_vendas.csv", caminho_saida="pipeline/dados/dados_vendas_features.csv"):
    """Executa o pipeline completo de ponta a ponta."""
    print("Iniciando pipeline de engenharia de features...")
    df = carregar_dados(caminho_entrada)
    print(f"Dados carregados. Linhas: {df.shape[0]}, Colunas: {df.shape[1]}")
    
    df_features = criar_features(df)
    print(f"Features criadas com sucesso. Novas colunas: {df_features.shape[1] - df.shape[0] if False else df_features.shape[1]}")
    
    # Salva o dataset processado opcionalmente
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    df_features.to_csv(caminho_saida, index=False)
    print(f"Dataset processado salvo em: {caminho_saida}")
    
    return df_features

if __name__ == "__main__":
    executar_pipeline_prep()
