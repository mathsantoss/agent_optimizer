"""Pipeline de Feature Engineering (Pandas) gerado para modelagem de Machine Learning."""
from pathlib import Path
import numpy as np
import pandas as pd


def run():
    """Executa a ingestão, limpeza e criação vetorizada de features em Pandas."""
    project_root = Path(__file__).resolve().parents[1]
    candidate_paths = [
        project_root / "krakenlake" / "catalog" / "sources" / "dados_vendas.csv",
        project_root / "krakenlake" / "datalake" / "dados_vendas.csv",
        Path("krakenlake/catalog/sources/dados_vendas.csv").resolve(),
        Path("krakenlake/datalake/dados_vendas.csv").resolve(),
        Path("dados_vendas.csv").resolve(),
    ]
    data_path = None
    for p in candidate_paths:
        if p.exists():
            data_path = p
            break
    if data_path is None:
        data_path = Path("krakenlake/catalog/sources/dados_vendas.csv").resolve()

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset de entrada não encontrado: {data_path}")

    # 1. Ingestão segura dos dados
    if str(data_path).endswith('.parquet'):
        df = pd.read_parquet(data_path)
    elif str(data_path).endswith('.json') or str(data_path).endswith('.jsonl'):
        try:
            df = pd.read_json(data_path)
        except ValueError:
            df = pd.read_json(data_path, lines=True)
    else:
        df = pd.read_csv(data_path, sep=None, engine='python')

    # 2. Conversão otimizada de colunas temporais
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')

    # 3. Engenharia de Features (Vetorizada)
    # Ano extraído da coluna temporal 'created_at'
    df['created_at_year'] = df['created_at'].dt.year

    # Mês extraído da coluna temporal 'created_at' (1 a 12)
    df['created_at_month'] = df['created_at'].dt.month

    # Dia da semana da coluna 'created_at' (0=Segunda a 6=Domingo)
    df['created_at_dayofweek'] = df['created_at'].dt.dayofweek

    # Flag binária indicando final de semana para 'created_at'
    df['created_at_is_weekend'] = df['created_at'].dt.dayofweek.isin([5, 6]).astype(int)

    # Ano extraído da coluna temporal 'updated_at'
    df['updated_at_year'] = df['updated_at'].dt.year

    # Mês extraído da coluna temporal 'updated_at' (1 a 12)
    df['updated_at_month'] = df['updated_at'].dt.month

    # Dia da semana da coluna 'updated_at' (0=Segunda a 6=Domingo)
    df['updated_at_dayofweek'] = df['updated_at'].dt.dayofweek

    # Flag binária indicando final de semana para 'updated_at'
    df['updated_at_is_weekend'] = df['updated_at'].dt.dayofweek.isin([5, 6]).astype(int)

    # Diferença aritmética absoluta (price_y - quantity)
    df['diff_price_y_quantity'] = df['price_y'] - df['quantity']

    # Razão normalizada com proteção contra divisão por zero (price_y / quantity)
    df['ratio_price_y_quantity'] = (df['price_y'] / df['quantity'].replace(0, np.nan)).fillna(0.0)

    # Produto de interação multiplicativa (price_y * quantity, ex: volume financeiro/transacional)
    df['interacao_price_y_x_quantity'] = df['price_y'].fillna(0) * df['quantity'].fillna(0)

    # Transformação logarítmica suavizada log1p(price_y) para redução de assimetria
    df['log_price_y'] = np.log1p(np.maximum(0, df['price_y']))

    # Transformação logarítmica suavizada log1p(quantity) para redução de assimetria
    df['log_quantity'] = np.log1p(np.maximum(0, df['quantity']))

    # Média de 'price_y' agregada por 'name' vetorizada com transform
    df['media_price_y_por_name'] = df.groupby('name')['price_y'].transform('mean')

    # Contagem total de registros agregados por 'name' vetorizada com transform
    df['contagem_por_name'] = df.groupby('name')['price_y'].transform('count')

    return df


if __name__ == "__main__":
    features_df = run()
    print(f'Pipeline de features concluído com sucesso: {features_df.shape[0]} linhas x {features_df.shape[1]} colunas.')