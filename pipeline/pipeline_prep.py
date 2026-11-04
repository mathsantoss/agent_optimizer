import pandas as pd
import numpy as np
import os
import time


def carregar_dados(caminho="pipeline/dados/dados_vendas.csv"):
    """Carrega o dataset de vendas otimizado."""
    if not os.path.exists(caminho):
        print("Arquivo não encontrado!")
        return pd.DataFrame()

    df = pd.read_csv(caminho)

    # Conversão vetorizada única para colunas de data
    for col in ["created_at", "updated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def engenharia_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engenharia de features vetorizada de alta performance para vendas.
    Elimina loops ineficientes (.iterrows()), .apply() desnecessários e cópias redundantes.
    """
    df = df.copy()

    # Garantir conversão de datas
    for col in ["created_at", "updated_at"]:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Operações vetorizadas para cálculos de preço e quantidade
    df["total_value_x"] = df["quantity"] * df["price_x"]
    df["total_value_y"] = df["quantity"] * df["price_y"]
    df["price_diff"] = df["price_x"] - df["price_y"]

    # Divisão segura vetorizada para price_ratio (evitando divisão por zero)
    df["price_ratio"] = np.where(
        df["price_y"] == 0,
        0.0,
        df["price_x"] / df["price_y"]
    )

    # Extração de componentes de data usando o acessor vetorizado .dt
    if "created_at" in df.columns:
        dt_col = df["created_at"].dt
        df["created_year"] = dt_col.year.fillna(0).astype(int)
        df["created_month"] = dt_col.month.fillna(0).astype(int)
        df["created_dayofweek"] = dt_col.dayofweek.fillna(0).astype(int)
        df["created_hour"] = dt_col.hour.fillna(0).astype(int)
    else:
        df["created_year"] = 0
        df["created_month"] = 0
        df["created_dayofweek"] = 0
        df["created_hour"] = 0

    # Agregações eficientes baseadas em transform/map vetorizados
    if "name" in df.columns:
        df["client_transaction_count"] = df.groupby("name")["sale_id"].transform("nunique")
        df["client_total_spent"] = df.groupby("name")["total_value_x"].transform("sum")
    else:
        df["client_transaction_count"] = 0
        df["client_total_spent"] = 0.0

    if "product" in df.columns and "price_y" in df.columns:
        df["product_mean_price"] = df.groupby("product")["price_y"].transform("mean")
    else:
        df["product_mean_price"] = 0.0

    # Tratamento de nulos vetorizado por tipo de coluna
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna("DESCONHECIDO")


    # Nova Feature: Soma total acumulada de price_x para a feature banana
    df['banana'] = df['price_x'].sum()
    return df


def executar_pipeline():
    print("Iniciando pipeline de engenharia de features otimizado...")

    inicio = time.time()

    df = carregar_dados()

    if df.empty:
        print("Dataset vazio. Encerrando pipeline.")
        return df

    print(
        f"Dados carregados com sucesso. "
        f"Linhas: {len(df)}, Colunas: {len(df.columns)}"
    )

    df_features = engenharia_features(df)
    df_features = df_features.reset_index(drop=True)

    fim = time.time()

    print("Engenharia de features concluída com sucesso!")
    print(f"Tempo de execução: {fim - inicio:.4f} segundos")
    print(f"Colunas geradas: {len(df_features.columns)}")

    return df_features


if __name__ == "__main__":
    executar_pipeline()
