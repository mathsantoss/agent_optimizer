import pandas as pd
import numpy as np
import os
import time
import warnings

warnings.filterwarnings("ignore")


def carregar_dados(caminho="krakenlake/catalog/sources/dados_vendas.csv"):
    if not os.path.exists(caminho):
        print(f"Arquivo não encontrado: {caminho}")
        return pd.DataFrame()

    df = pd.read_csv(caminho)

    # Conversão de datas vetorizada
    for col in ["created_at", "updated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def calcular_estatisticas_cliente(df):
    # Agregação vetorizada
    cliente_stats = df.groupby("name").agg(
        transaction_count=("name", "size"),
        total_spent=("total_value_x", "sum"),
        average_spent=("total_value_x", "mean")
    ).reset_index()
    # Renomear colunas para corresponder ao contrato original
    cliente_stats = cliente_stats.rename(columns={
        "transaction_count": "client_transaction_count",
        "total_spent": "client_total_spent",
        "average_spent": "client_average_spent"
    })
    return cliente_stats


def calcular_estatisticas_produto(df):
    # Agregação vetorizada
    produto_stats = df.groupby("product").agg(
        mean_price=("price_y", "mean")
    ).reset_index()
    # Renomear colunas para corresponder ao contrato original
    produto_stats = produto_stats.rename(columns={
        "mean_price": "product_mean_price"
    })
    return produto_stats


def engenharia_features(df):
    # Evitar cópias excessivas - operações Pandas retornam novas Series/DataFrames

    # Cálculos vetorizados
    df["total_value_x"] = df["quantity"] * df["price_x"]
    df["total_value_y"] = df["quantity"] * df["price_y"]

    df["price_diff"] = df["price_x"] - df["price_y"]
    # Tratar divisão por zero e NaNs para price_ratio
    df["price_ratio"] = df["price_x"] / df["price_y"]
    df["price_ratio"] = df["price_ratio"].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Features de data vetorizadas
    if "created_at" in df.columns:
        df["created_year"] = df["created_at"].dt.year.fillna(0).astype(int)
        df["created_month"] = df["created_at"].dt.month.fillna(0).astype(int)
        df["created_day"] = df["created_at"].dt.day.fillna(0).astype(int)
        df["created_hour"] = df["created_at"].dt.hour.fillna(0).astype(int)
        df["created_weekday"] = df["created_at"].dt.weekday.fillna(0).astype(int)

    if "updated_at" in df.columns:
        df["updated_year"] = df["updated_at"].dt.year.fillna(0).astype(int)
        df["updated_month"] = df["updated_at"].dt.month.fillna(0).astype(int)
        df["updated_hour"] = df["updated_at"].dt.hour.fillna(0).astype(int)
        df["time_difference"] = (
            df["updated_at"] - df["created_at"]
        ).dt.total_seconds().fillna(0)

    # Agregações de cliente e produto otimizadas e mescladas
    if "name" in df.columns:
        cliente_stats = calcular_estatisticas_cliente(df)
        df = pd.merge(df, cliente_stats, on="name", how="left")
        # Preencher NaNs que podem surgir do merge para as novas colunas
        df["client_transaction_count"] = df["client_transaction_count"].fillna(0).astype(int)
        df["client_total_spent"] = df["client_total_spent"].fillna(0)
        df["client_average_spent"] = df["client_average_spent"].fillna(0)

    if "product" in df.columns:
        produto_stats = calcular_estatisticas_produto(df)
        df = pd.merge(df, produto_stats, on="product", how="left")
        # Preencher NaNs que podem surgir do merge para a nova coluna
        df["product_mean_price"] = df["product_mean_price"].fillna(0)

    # Cálculos vetorizados adicionais
    df["total_value_x_copy"] = df["total_value_x"]
    df["total_value_x_squared"] = df["total_value_x"] ** 2
    df["price_x_double"] = df["price_x"] * 2

    # Re-introduzir a coluna 'banana' para equivalência, com comportamento vetorizado
    # O comportamento original era a soma total de 'price_x' do dataframe, replicada para todas as linhas.
    banana_value = df["price_x"].sum() if "price_x" in df.columns else 0
    df["banana"] = banana_value

    # Preenchimento de NaN para todas as colunas de forma vetorizada
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("DESCONHECIDO")
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)

    return df


def executar_pipeline():
    print("Iniciando pipeline...")
    inicio = time.time()

    df = carregar_dados()

    if df.empty:
        print("Dataset vazio")
        return df

    df_processed = df.copy()

    print(f"Dados carregados: {len(df_processed)} linhas")

    df_features = engenharia_features(df_processed)

    fim = time.time()

    print("Pipeline finalizado!")
    print(f"Linhas: {len(df_features)}")
    print(f"Colunas: {len(df_features.columns)}")
    print(f"Tempo: {fim - inicio:.4f} segundos")

    return df_features


if __name__ == "__main__":
    resultado = executar_pipeline()
    print("Resultado:")
    print(resultado.head())