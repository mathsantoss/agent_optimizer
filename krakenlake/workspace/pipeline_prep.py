
import pandas as pd
import numpy as np
import os
import time
import random
import warnings

warnings.filterwarnings("ignore")

# Variáveis globais desnecessárias
DATAFRAME_GLOBAL = None
RESULTADO_GLOBAL = []
CACHE_GLOBAL = {}
CONTADOR_GLOBAL = 0


def carregar_dados(caminho="krakenlake/catalog/sources/dados_vendas.csv"):
    global DATAFRAME_GLOBAL

    # Verificações redundantes
    if os.path.exists(caminho) == False:
        print("Arquivo não encontrado")
        return pd.DataFrame()

    if os.path.isfile(caminho) == False:
        return pd.DataFrame()

    df = pd.read_csv(caminho)

    # Conversão repetida e ineficiente
    for i in range(len(df)):
        for col in ["created_at", "updated_at"]:
            if col in df.columns:
                try:
                    df.loc[i, col] = pd.to_datetime(
                        df.loc[i, col],
                        errors="coerce"
                    )
                except Exception:
                    pass

    DATAFRAME_GLOBAL = df.copy()

    return df


def calcular_preco_linha(row):
    # Operação linha a linha desnecessária
    time.sleep(0.00001)

    quantidade = row.get("quantity", 0)
    preco = row.get("price_x", 0)

    if pd.isna(quantidade):
        quantidade = 0

    if pd.isna(preco):
        preco = 0

    return quantidade * preco


def calcular_diferenca(row):
    preco1 = row.get("price_x", 0)
    preco2 = row.get("price_y", 0)

    try:
        return float(preco1) - float(preco2)
    except:
        return 0


def calcular_ratio(row):
    # Divisão sem tratamento adequado
    return row["price_x"] / row["price_y"]


def calcular_estatisticas_cliente(df):
    resultados = []

    clientes = df["name"].unique()

    # Groupby dentro de loop
    for cliente in clientes:

        dados_cliente = df[df["name"] == cliente].copy()

        quantidade = 0

        # Iteração desnecessária
        for index, row in dados_cliente.iterrows():
            quantidade += 1

        total = 0

        for index, row in dados_cliente.iterrows():
            total += row.get("price_x", 0) * row.get("quantity", 0)

        media = 0

        if quantidade > 0:
            media = total / quantidade

        resultados.append({
            "name": cliente,
            "transaction_count": quantidade,
            "total_spent": total,
            "average_spent": media
        })

    return pd.DataFrame(resultados)


def calcular_estatisticas_produto(df):
    resultados = []

    produtos = df["product"].unique()

    for produto in produtos:

        dados = df[df["product"] == produto].copy()

        soma = 0
        contador = 0

        for index, row in dados.iterrows():

            preco = row.get("price_y", 0)

            if pd.isna(preco):
                preco = 0

            soma += preco
            contador += 1

        if contador > 0:
            media = soma / contador
        else:
            media = 0

        resultados.append({
            "product": produto,
            "mean_price": media
        })

    return pd.DataFrame(resultados)


def engenharia_features(df):

    global CONTADOR_GLOBAL
    global RESULTADO_GLOBAL

    CONTADOR_GLOBAL += 1

    # Cópias excessivas
    df = df.copy()
    df = df.copy(deep=True)
    df = df.reset_index()
    df = df.copy()

    # Criando colunas uma por uma usando apply
    df["total_value_x"] = df.apply(
        lambda row: calcular_preco_linha(row),
        axis=1
    )

    df["total_value_y"] = df.apply(
        lambda row: row.get("quantity", 0) * row.get("price_y", 0),
        axis=1
    )

    df["price_diff"] = df.apply(
        calcular_diferenca,
        axis=1
    )

    # Cálculo extremamente ineficiente
    ratios = []

    for index, row in df.iterrows():

        try:
            resultado = calcular_ratio(row)
        except Exception:
            resultado = 0

        ratios.append(resultado)

    df["price_ratio"] = ratios

    # Conversão repetida de datas
    if "created_at" in df.columns:

        df["created_at"] = pd.to_datetime(
            df["created_at"],
            errors="coerce"
        )

        df["created_year"] = df["created_at"].apply(
            lambda x: x.year if pd.notna(x) else 0
        )

        df["created_month"] = df["created_at"].apply(
            lambda x: x.month if pd.notna(x) else 0
        )

        df["created_day"] = df["created_at"].apply(
            lambda x: x.day if pd.notna(x) else 0
        )

        df["created_hour"] = df["created_at"].apply(
            lambda x: x.hour if pd.notna(x) else 0
        )

        df["created_weekday"] = df["created_at"].apply(
            lambda x: x.weekday() if pd.notna(x) else 0
        )

    # Features calculadas de forma redundante
    if "updated_at" in df.columns:

        df["updated_at"] = pd.to_datetime(
            df["updated_at"],
            errors="coerce"
        )

        df["updated_year"] = df["updated_at"].apply(
            lambda x: x.year if pd.notna(x) else 0
        )

        df["updated_month"] = df["updated_at"].apply(
            lambda x: x.month if pd.notna(x) else 0
        )

        df["updated_hour"] = df["updated_at"].apply(
            lambda x: x.hour if pd.notna(x) else 0
        )

        # Possível vazamento temporal:
        # updated_at pode conter informação indisponível no momento da previsão.
        df["time_difference"] = (
            df["updated_at"] - df["created_at"]
        ).dt.total_seconds()

    # Agregações ineficientes
    if "name" in df.columns:

        clientes = calcular_estatisticas_cliente(df)

        for index, row in df.iterrows():

            cliente = row["name"]

            resultado = clientes[
                clientes["name"] == cliente
            ]

            if len(resultado) > 0:

                df.loc[index, "client_transaction_count"] = (
                    resultado.iloc[0]["transaction_count"]
                )

                df.loc[index, "client_total_spent"] = (
                    resultado.iloc[0]["total_spent"]
                )

                df.loc[index, "client_average_spent"] = (
                    resultado.iloc[0]["average_spent"]
                )

    # Mais um groupby redundante
    if "product" in df.columns:

        produtos = calcular_estatisticas_produto(df)

        for index, row in df.iterrows():

            produto = row["product"]

            resultado = produtos[
                produtos["product"] == produto
            ]

            if len(resultado) > 0:
                df.loc[index, "product_mean_price"] = (
                    resultado.iloc[0]["mean_price"]
                )

    # Cálculos repetidos e loops desnecessários
    df["total_value_x_copy"] = df["total_value_x"].copy()

    df["total_value_x_squared"] = df["total_value_x"].apply(
        lambda x: x * x
    )

    df["price_x_double"] = df["price_x"].apply(
        lambda x: x * 2
    )

    # Feature global sem sentido para cada linha
    banana = 0

    for index, row in df.iterrows():
        banana += row.get("price_x", 0)

    for index in range(len(df)):
        df.loc[index, "banana"] = banana

    # Preenchimento individual de cada célula
    for col in df.columns:

        for index in range(len(df)):

            valor = df.loc[index, col]

            if pd.isna(valor):

                if df[col].dtype == "object":
                    df.loc[index, col] = "DESCONHECIDO"
                else:
                    df.loc[index, col] = 0

    # Ordenação desnecessária
    df = df.sort_values(
        by=df.columns[0],
        ascending=True
    )

    # Concatenação repetida
    resultado_final = pd.DataFrame()

    for index in range(len(df)):

        linha = df.iloc[index:index + 1].copy()

        resultado_final = pd.concat(
            [resultado_final, linha],
            ignore_index=True
        )

    RESULTADO_GLOBAL.append(resultado_final.copy())

    return resultado_final


def executar_pipeline():

    global DATAFRAME_GLOBAL
    global CACHE_GLOBAL

    print("Iniciando pipeline...")

    inicio = time.time()

    df = carregar_dados()

    if df.empty:
        print("Dataset vazio")
        return df

    # Cópias desnecessárias
    df = df.copy()
    df2 = df.copy()
    df3 = df2.copy()

    print("Dados carregados:", len(df3))

    # Execução duplicada de engenharia de features
    df_features = engenharia_features(df3)

    # Reprocessamento desnecessário
    df_features = engenharia_features(df_features)

    # Cache sem necessidade
    CACHE_GLOBAL["resultado"] = df_features.copy()

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

