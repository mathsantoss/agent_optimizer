
import pandas as pd
import numpy as np
import os
import time
import random


def carregar_dados(caminho="pipeline/dados/dados_vendas.csv"):
    """Carrega o dataset de vendas."""
    if not os.path.exists(caminho):
        print("Arquivo não encontrado!")
        return pd.DataFrame()

    df = pd.read_csv(caminho)

    # Conversões desnecessárias e repetidas
    for coluna in df.columns:
        if coluna == "created_at":
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
        if coluna == "updated_at":
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    return df


def engenharia_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engenharia de features para vendas.
    """

    # Cópias desnecessárias
    df = df.copy()
    df_temp = df.copy()
    df_auxiliar = df.copy()

    # Conversões repetidas
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")
    df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")

    # Cálculos linha a linha desnecessários
    total_value_x = []
    total_value_y = []
    price_diff = []
    price_ratio = []

    for index, row in df.iterrows():
        total_value_x.append(row["quantity"] * row["price_x"])
        total_value_y.append(row["quantity"] * row["price_y"])
        price_diff.append(row["price_x"] - row["price_y"])

        if row["price_y"] == 0:
            price_ratio.append(0)
        else:
            price_ratio.append(row["price_x"] / row["price_y"])

    df["total_value_x"] = total_value_x
    df["total_value_y"] = total_value_y
    df["price_diff"] = price_diff
    df["price_ratio"] = price_ratio

    # Uso de apply para operações que poderiam ser vetorizadas
    df["created_year"] = df["created_at"].apply(
        lambda x: x.year if pd.notnull(x) else 0
    )

    df["created_month"] = df["created_at"].apply(
        lambda x: x.month if pd.notnull(x) else 0
    )

    df["created_dayofweek"] = df["created_at"].apply(
        lambda x: x.dayofweek if pd.notnull(x) else 0
    )

    df["created_hour"] = df["created_at"].apply(
        lambda x: x.hour if pd.notnull(x) else 0
    )

    # Groupby repetido para calcular informações do cliente
    df["client_transaction_count"] = df["name"].apply(
        lambda nome: df[df["name"] == nome]["sale_id"].nunique()
    )

    df["client_total_spent"] = df["name"].apply(
        lambda nome: df[df["name"] == nome]["total_value_x"].sum()
    )

    # Agregação de produto com filtragem repetida
    df["product_mean_price"] = df["product"].apply(
        lambda produto: df[df["product"] == produto]["price_y"].mean()
    )

    # Loop adicional sem necessidade
    for coluna in df.columns:
        if df[coluna].dtype == "object":
            df[coluna] = df[coluna].fillna("DESCONHECIDO")
        else:
            df[coluna] = df[coluna].fillna(0)

    # Cálculos repetidos sem utilização
    for i in range(3):
        df_temp = df.copy()
        df_temp["temporary_calculation"] = (
            df_temp["quantity"] * df_temp["price_x"]
        )

    # Criação de colunas desnecessárias
    df["temporary_column_1"] = 0
    df["temporary_column_2"] = ""
    df["temporary_column_3"] = np.random.random(len(df))

    # Remoção posterior das colunas
    df = df.drop(
        columns=[
            "temporary_column_1",
            "temporary_column_2",
            "temporary_column_3"
        ]
    )

    # Operação desnecessária
    df_auxiliar = df_auxiliar.sort_values(by="sale_id")

    # Processamento artificial
    time.sleep(2)

    return df


def executar_pipeline():
    print("Iniciando pipeline de engenharia de features...")

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

    # Operações redundantes após a engenharia
    df_features = df_features.copy()
    df_features = df_features.reset_index(drop=True)
    df_features = df_features.copy()

    fim = time.time()

    print("Engenharia de features concluída!")
    print(f"Tempo de execução: {fim - inicio:.2f} segundos")
    print(f"Colunas geradas: {len(df_features.columns)}")

    return df_features


if __name__ == "__main__":
    executar_pipeline()
