import pandas as pd
import numpy as np
import os
import time
import warnings

warnings.filterwarnings("ignore")


def carregar_dados(caminho="krakenlake/catalog/sources/dados_vendas.csv"):
    if not os.path.exists(caminho) or not os.path.isfile(caminho):
        print("Arquivo não encontrado ou inválido")
        return pd.DataFrame()

    df = pd.read_csv(caminho)

    for col in ["created_at", "updated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def engenharia_features(df):
    df = df.copy() # Garante que as operações não modifiquem o DataFrame original

    # Operações vetorizadas para cálculo de valores
    df["total_value_x"] = df["quantity"] * df["price_x"]
    df["total_value_y"] = df["quantity"] * df["price_y"]
    df["price_diff"] = df["price_x"] - df["price_y"]

    # Evitar divisão por zero e vetorizar o cálculo do ratio
    df["price_ratio"] = df.apply(
        lambda row: row["price_x"] / row["price_y"] if row["price_y"] != 0 else 0,
        axis=1
    )

    # Recriar colunas 'lixo' ou redundantes para manter a equivalência com o pipeline original
    df["total_value_x_copy"] = df["total_value_x"]
    df["total_value_x_squared"] = df["total_value_x"] ** 2
    df["price_x_double"] = df["price_x"] * 2
    # A coluna 'banana' original somava todos os price_x e atribuía para cada linha.
    # Reproduzimos isso de forma vetorizada.
    df["banana"] = df["price_x"].sum()

    # Extração de features de data vetorizadas
    for col_date in ["created_at", "updated_at"]:
        if col_date in df.columns:
            # Garantir que a coluna é datetime, coerce errors result in NaT
            df[col_date] = pd.to_datetime(df[col_date], errors="coerce")

            # Crie features apenas se a coluna não for completamente nula após coerção
            if not df[col_date].isnull().all():
                prefix = col_date.replace("_at", "") # created, updated
                df[f"{prefix}_year"] = df[col_date].dt.year.fillna(0).astype(int)
                df[f"{prefix}_month"] = df[col_date].dt.month.fillna(0).astype(int)
                if prefix == "created": # created_day, created_hour, created_weekday só para created_at
                    df[f"{prefix}_day"] = df[col_date].dt.day.fillna(0).astype(int)
                    df[f"{prefix}_hour"] = df[col_date].dt.hour.fillna(0).astype(int)
                    df[f"{prefix}_weekday"] = df[col_date].dt.weekday.fillna(0).astype(int)
                elif prefix == "updated": # updated_hour só para updated_at
                    df[f"{prefix}_hour"] = df[col_date].dt.hour.fillna(0).astype(int)

    # Diferença de tempo de forma vetorizada
    if "created_at" in df.columns and "updated_at" in df.columns:
        df["time_difference"] = (df["updated_at"] - df["created_at"]).dt.total_seconds().fillna(0)
    else:
        df["time_difference"] = 0 # Define como 0 ou NaN se as colunas não existirem

    # Calcular estatísticas de cliente de forma vetorizada com groupby e merge
    if "name" in df.columns:
        client_stats = df.groupby("name").agg(
            transaction_count=("sale_id", "count"),
            total_spent=("total_value_x", "sum"),
            average_spent=("total_value_x", "mean")
        ).reset_index()
        client_stats.rename(columns={
            "transaction_count": "client_transaction_count",
            "total_spent": "client_total_spent",
            "average_spent": "client_average_spent"
        }, inplace=True)
        df = df.merge(client_stats, on="name", how="left")

    # Calcular estatísticas de produto de forma vetorizada com groupby e merge
    if "product" in df.columns:
        product_stats = df.groupby("product").agg(
            mean_price=("price_y", "mean")
        ).reset_index()
        product_stats.rename(columns={
            "mean_price": "product_mean_price"
        }, inplace=True)
        df = df.merge(product_stats, on="product", how="left")

    # Preenchimento de NaNs de forma vetorizada (para colunas numéricas e de objeto)
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

    print("Dados carregados:", len(df))

    df_features = engenharia_features(df)

    fim = time.time()

    print("Pipeline finalizado!")
    print("Linhas:", len(df_features))
    print("Colunas:", len(df_features.columns))
    print("Tempo:", fim - inicio)

    return df_features


if __name__ == "__main__":
    resultado = executar_pipeline()
    print("Resultado:")
    print(resultado.head())