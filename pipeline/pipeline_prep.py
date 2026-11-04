import pandas as pd
import numpy as np
import os
import time

def carregar_dados(caminho="pipeline/dados/dados_vendas.csv"):
    """Carrega o dataset de vendas otimizado."""
    if not os.path.exists(caminho):
        print("Arquivo não encontrado!")
        return pd.DataFrame()

    # Carrega colunas de data diretamente com parse_dates para máxima eficiência
    df = pd.read_csv(caminho, parse_dates=["created_at", "updated_at"])
    return df


def engenharia_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engenharia de features vetorizada e otimizada para vendas.
    """
    df = df.copy()

    # Tratamento de nulos vetorizado por tipo de dado
    cols_obj = df.select_dtypes(include=["object"]).columns
    cols_num = df.select_dtypes(include=[np.number]).columns
    
    if len(cols_obj) > 0:
        df[cols_obj] = df[cols_obj].fillna("DESCONHECIDO")
    if len(cols_num) > 0:
        df[cols_num] = df[cols_num].fillna(0)

    # Operações aritméticas vetorizadas
    df["total_value_x"] = df["quantity"] * df["price_x"]
    df["total_value_y"] = df["quantity"] * df["price_y"]
    df["price_diff"] = df["price_x"] - df["price_y"]
    
    # Divisão segura vetorizada para evitar divisão por zero
    df["price_ratio"] = np.where(df["price_y"] == 0, 0, df["price_x"] / df["price_y"])

    # Extração de datas vetorizada usando o acessor .dt
    if "created_at" in df.columns and pd.api.types.is_datetime64_any_dtype(df["created_at"]):
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

    # Agregações por cliente vetorizadas com transform
    df["client_transaction_count"] = df.groupby("name")["sale_id"].transform("nunique")
    df["client_total_spent"] = df.groupby("name")["total_value_x"].transform("sum")

    # Agregação por produto vetorizada com transform
    df["product_mean_price"] = df.groupby("product")["price_y"].transform("mean")

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

    print("Engenharia de features concluída!")
    print(f"Tempo de execução: {fim - inicio:.2f} segundos")
    print(f"Colunas geradas: {len(df_features.columns)}")

    return df_features


if __name__ == "__main__":
    executar_pipeline()